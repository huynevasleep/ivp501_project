"""Training-free rally proposals for fixed-camera pickleball. Not ball tracking."""
from pathlib import Path
import json
import subprocess
import tempfile
import cv2
import numpy as np
import pandas as pd
import imageio_ffmpeg
from core import normalize, knapsack_select


def propose_rallies(df, duration, rate=3., threshold=.32, min_seconds=4.,
                    gap_seconds=2., pre=2., post=2., max_seconds=90.):
    """Hysteresis with short-gap bridging; never split long activity arbitrarily."""
    smooth=df.activity.rolling(max(1,round(rate)),center=True,min_periods=1).median().to_numpy()
    active=None; last=None; raw=[]
    for i,value in enumerate(smooth):
        t=float(df.time.iloc[i])
        if bool(df.cut.iloc[i]):
            if active is not None: raw.append((active,last+1/rate))
            active=last=None
            continue
        if value >= (threshold if active is None else threshold*.6):
            if active is None: active=t
            last=t
        elif active is not None and t-last>gap_seconds:
            raw.append((active,last+1/rate)); active=last=None
    if active is not None: raw.append((active,min(duration,last+1/rate)))
    cuts=df.loc[df.cut,'time'].to_numpy(); proposals=[]
    for a,b in raw:
        if b-a<min_seconds: continue
        prior=cuts[cuts<=a]; following=cuts[cuts>=b]
        start=max(0.,a-pre,float(prior[-1]) if len(prior) else 0.)
        end=min(duration,b+post,float(following[0]) if len(following) else duration)
        if proposals and start<proposals[-1]['end']:
            midpoint=(start+proposals[-1]['end'])/2
            proposals[-1]['end']=midpoint; start=midpoint
        mask=(df.time>=a)&(df.time<b)
        score=float(.75*df.activity[mask].mean()+.25*min((b-a)/30,1))
        key=int(df.loc[mask,'activity'].idxmax())
        proposals.append(dict(start=start,end=end,score=score,cluster=0,
            key_time=float(df.time.iloc[key]),keyframe=f'rally_{len(proposals):05d}.jpg',
            needs_review=bool(b-a>max_seconds),active_seconds=b-a,
            contributions={'court_activity':float(.75*df.activity[mask].mean()),
                           'rally_duration':float(.25*min((b-a)/30,1))}))
    return proposals


def analyze_match(source, out, rate=3., roi=(0.,0.,1.,1.), threshold=.32,
                  min_seconds=4., gap_seconds=2., pre=2., post=2., progress=None):
    source=Path(source).resolve(); out=Path(out); out.mkdir(parents=True,exist_ok=True)
    if not source.is_file(): raise ValueError('Không tìm thấy video tại đường dẫn đã nhập.')
    if not 1<=rate<=10: raise ValueError('Tốc độ lấy mẫu phải từ 1 đến 10 fps.')
    x1,y1,x2,y2=roi
    if not (0<=x1<x2<=1 and 0<=y1<y2<=1): raise ValueError('Vùng sân không hợp lệ.')
    cap=cv2.VideoCapture(str(source)); fps=cap.get(cv2.CAP_PROP_FPS)
    count=cap.get(cv2.CAP_PROP_FRAME_COUNT); cap.release()
    if fps<=0 or count<=0: raise ValueError('Không đọc được thông tin video.')
    duration=count/fps
    # FFmpeg decodes sequentially, resizes before Python receives frames.
    width,height=384,216
    crop=f'crop=trunc(iw*{x2-x1}/2)*2:trunc(ih*{y2-y1}/2)*2:iw*{x1}:ih*{y1}'
    filt=f'{crop},fps={rate},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2'
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(source),'-an','-vf',filt,'-pix_fmt','gray','-f','rawvideo','pipe:1']
    rows=[]; prev=None; nbytes=width*height
    with tempfile.TemporaryFile() as errors:
        proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=errors)
        try:
            while True:
                data=bytearray()
                while len(data)<nbytes:
                    block=proc.stdout.read(nbytes-len(data))
                    if not block: break
                    data.extend(block)
                if not data: break
                if len(data)!=nbytes: raise ValueError('Khung hình giải mã không đầy đủ.')
                gray=np.frombuffer(data,np.uint8).reshape(height,width)
                local=global_motion=change=0.
                if prev is not None:
                    flow=cv2.calcOpticalFlowFarneback(prev,gray,None,.5,3,15,3,5,1.2,0)
                    camera=np.median(flow.reshape(-1,2),axis=0)
                    global_motion=float(np.linalg.norm(camera))
                    residual=np.linalg.norm(flow-camera,axis=2)
                    local=float(np.percentile(residual,90))
                    change=float(cv2.absdiff(gray,prev).mean()/255)
                rows.append(dict(time=len(rows)/rate,local_motion=local,camera_motion=global_motion,
                                 difference=change,sharpness=float(cv2.Laplacian(gray,cv2.CV_64F).var())))
                prev=gray.copy()
                if progress and len(rows)%int(rate*3)==0: progress(min(.9,len(rows)/rate/duration*.9))
            code=proc.wait()
            if code:
                errors.seek(0); raise ValueError('FFmpeg không giải mã được video: '+errors.read().decode(errors='replace')[-1500:])
        finally:
            proc.stdout.close()
            if proc.poll() is None: proc.kill(); proc.wait()
    if not rows: raise ValueError('Video không có khung hình đọc được.')
    df=pd.DataFrame(rows)
    duration=min(duration,len(df)/rate)
    df['cut']=df.difference>.28
    # Suppress hard cuts and coherent camera movement. Absolute floor prevents
    # amplifying tiny codec noise into an apparently active match.
    df['activity']=normalize(df.local_motion)/(1+df.camera_motion)
    df.loc[(df.local_motion<.12)|df.cut,'activity']=0.
    candidates=propose_rallies(df,duration,rate,threshold,min_seconds,gap_seconds,pre,post)
    cap=cv2.VideoCapture(str(source))
    try:
        for i,s in enumerate(candidates):
            cap.set(cv2.CAP_PROP_POS_MSEC,s['key_time']*1000); ok,frame=cap.read()
            if not ok: raise ValueError('Không đọc được ảnh đại diện của pha bóng.')
            h,w=frame.shape[:2]; frame=cv2.resize(frame,(480,max(1,round(h*480/w))))
            cv2.imwrite(str(out/s['keyframe']),frame)
            if progress: progress(.9+.09*(i+1)/len(candidates))
    finally: cap.release()
    meta=dict(duration=duration,fps=fps,frames=int(duration*fps),sample_fps=rate,
              cuts=df.loc[df.cut,'time'].tolist(),pipeline='pickleball',source=str(source),
              roi=list(roi),threshold=threshold,min_seconds=min_seconds,gap_seconds=gap_seconds,pre=pre,post=post)
    df.to_csv(out/'features.csv',index=False)
    (out/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    (out/'candidates.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')
    return df,meta,candidates


def choose_rallies(candidates, seconds):
    return knapsack_select([s for s in candidates if not s['needs_review']],seconds)


def review_rallies(table,duration,budget=None):
    result=[]
    for s in table.to_dict('records'):
        if not s.pop('keep'): continue
        a,b=float(s['start']),float(s['end'])
        if not (np.isfinite(a) and np.isfinite(b) and 0<=a<b<=duration):
            raise ValueError('Mỗi đoạn cần 0 ≤ bắt đầu < kết thúc ≤ thời lượng video.')
        s['start'],s['end']=a,b; result.append(s)
    result.sort(key=lambda s:s['start'])
    if not result: raise ValueError('Hãy chọn ít nhất một pha bóng.')
    if any(a['end']>b['start'] for a,b in zip(result,result[1:])):
        raise ValueError('Các đoạn đang chồng nhau. Hãy chỉnh lại mốc thời gian.')
    if budget is not None and sum(s['end']-s['start'] for s in result)>budget+1e-6:
        raise ValueError('Tổng thời lượng đã chọn vượt giới hạn highlight.')
    return result
