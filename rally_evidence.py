"""Observable ball candidates and human-confirmed rally events; no inferred paddle contact."""
from pathlib import Path
import json
import subprocess
import cv2
import numpy as np
import pandas as pd
import imageio_ffmpeg

EVENT_TYPES=('serve','paddle_contact','bounce','rally_end','occluded')


def rallies_from_events(events,duration):
    """Only explicit confirmed serve/end pairs define rallies. A bounce/lost ball never ends one."""
    active=None; rallies=[]; warnings=[]; previous=-1.
    for event in sorted(events,key=lambda e:float(e['time'])):
        t=float(event['time']); kind=event['kind']
        if not np.isfinite(t) or not 0<=t<=duration: raise ValueError('Mốc sự kiện ngoài video.')
        if kind not in EVENT_TYPES: raise ValueError('Loại sự kiện không hợp lệ.')
        if not isinstance(event.get('confirmed'),bool): raise ValueError('confirmed phải là true hoặc false.')
        if not event['confirmed']: continue
        if t==previous: raise ValueError('Sự kiện đã xác nhận không được trùng thời điểm.')
        previous=t
        if kind=='serve':
            if active is not None: warnings.append(f'Pha từ {active:.3f}s thiếu sự kiện kết thúc; chưa xuất.')
            active=t
        elif kind=='rally_end':
            if active is None: warnings.append(f'Kết thúc tại {t:.3f}s thiếu giao bóng; chưa xuất.')
            elif t>active:
                rallies.append(dict(start=active,end=t,evidence='human_confirmed_events'))
            active=None
    if active is not None: warnings.append(f'Pha từ {active:.3f}s còn mở; chưa xuất.')
    return rallies,warnings


def ball_candidates(frame,previous=None,roi=(0.,0.,1.,1.),hue=(18,48)):
    """Yellow/green ball baseline. Positions refer to the full native-resolution frame."""
    h,w=frame.shape[:2]; x1,y1,x2,y2=roi
    mask=cv2.inRange(cv2.cvtColor(frame,cv2.COLOR_BGR2HSV),np.array([hue[0],80,90]),np.array([hue[1],255,255]))
    spatial=np.zeros((h,w),np.uint8)
    spatial[int(y1*h):int(y2*h),int(x1*w):int(x2*w)]=255
    mask &= spatial
    if previous is not None:
        moving=(cv2.absdiff(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),previous)>10).astype(np.uint8)*255
        mask &= cv2.dilate(moving,np.ones((3,3),np.uint8))
    n,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
    found=[]
    for i in range(1,n):
        x,y,bw,bh,area=stats[i]
        if 3<=area<=max(100,h*w*.001) and .35<=bw/max(bh,1)<=2.8 and area/(bw*bh)>.25:
            found.append((float(centers[i,0]),float(centers[i,1]),int(area)))
    return found


def track_ball(source,start,end,out,roi=(0.,0.,1.,1.),hue=(18,48),progress=None,bounce_vy=None,dead_gap=2.5):
    """Native-fps inspectable baseline; draws only observed candidates, resets on loss/cut.

    Besides direction-change candidates it emits, all unconfirmed:
    - bounce_candidate: screen-vertical velocity flips from down to up (> bounce_vy px/frame
      both ways, default 0.2% of frame height so centroid jitter at high resolutions
      does not count) on a continuous track - the trajectory shape of a floor bounce;
    - dead_ball_candidate: a second bounce within dead_gap seconds of the first with no
      direction-change (possible paddle hit) between them - the two-bounce dead-ball rule.
    Both are image-space trajectory shapes, not a floor or paddle detector: a human confirms.
    """
    if not np.isfinite(start+end) or not 0<=start<end or end-start>120:
        raise ValueError('Chọn đoạn kiểm tra dài tối đa 120 giây.')
    if not (0<=roi[0]<roi[2]<=1 and 0<=roi[1]<roi[3]<=1): raise ValueError('Vùng sân không hợp lệ.')
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    cap=cv2.VideoCapture(str(source)); fps=cap.get(cv2.CAP_PROP_FPS)
    if fps<=0: cap.release(); raise ValueError('Không đọc được video.')
    duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps
    if end>duration+1/fps: cap.release(); raise ValueError('Khoảng kiểm tra vượt video.')
    first=int(np.ceil(start*fps)); count=max(1,int(np.floor(end*fps))-first)
    cap.set(cv2.CAP_PROP_POS_FRAMES,first)
    writer=None; prev=None; last=None; velocity=np.zeros(2); lost=0; track_id=0; last_bounce=None
    rows=[]; history=[]; events=[]
    tmp=out/'overlay_work.mp4'
    try:
        for j in range(count):
            ok,frame=cap.read()
            if not ok: break
            h,w=frame.shape[:2]; gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            if writer is None:
                writer=cv2.VideoWriter(str(tmp),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
                if not writer.isOpened(): raise ValueError('Không ghi được video bằng chứng.')
            cut=prev is not None and np.mean(cv2.absdiff(gray,prev))/255>.25
            if cut: last=None; history=[]; lost=0; last_bounce=None
            candidates=ball_candidates(frame,prev,roi,hue); t=(first+j)/fps; selected=None
            if not cut and candidates:
                if last is None:
                    # Reacquisition is explicitly a new track, not continuity evidence.
                    selected=max(candidates,key=lambda p:p[2]); track_id+=1; velocity=np.zeros(2); history=[]; last_bounce=None
                else:
                    predicted=last+velocity*(lost+1)
                    best=min(candidates,key=lambda p:np.linalg.norm(np.array(p[:2])-predicted))
                    if np.linalg.norm(np.array(best[:2])-predicted)<max(15,np.hypot(w,h)*.06)*(lost+1): selected=best
            if selected:
                position=np.array(selected[:2]); last_velocity=velocity.copy()
                if last is not None: velocity=(position-last)/(lost+1)
                if len(history)>=3 and lost==0 and (not events or t-events[-1]['time']>.2):
                    # Bounce: screen-vertical velocity flips down -> up on a continuous track.
                    vy_min=bounce_vy if bounce_vy is not None else max(1.,h*.002)
                    bounce=last_velocity[1]>vy_min and velocity[1]<-vy_min
                    speeds=np.linalg.norm(velocity),np.linalg.norm(last_velocity)
                    turn=(not bounce and min(speeds)>2 and
                          np.dot(velocity,last_velocity)/(speeds[0]*speeds[1])<.3)
                    if bounce or turn:
                        name=f'turn_{len(events):04d}.jpg'
                        cv2.imwrite(str(out/name),frame)
                        events.append(dict(time=t,kind='bounce_candidate' if bounce else 'direction_change_candidate',confirmed=False,keyframe=name))
                        if bounce:
                            if last_bounce is not None and t-last_bounce<=dead_gap:
                                # Second bounce, no possible paddle hit in between: dead-ball rule.
                                events.append(dict(time=t,kind='dead_ball_candidate',confirmed=False,keyframe=name,bounces=[float(last_bounce),float(t)]))
                                last_bounce=None
                            else: last_bounce=t
                        else: last_bounce=None    # a possible paddle hit restarts the bounce count
                last=position; lost=0; history.append(tuple(map(int,position))); history=history[-12:]
                rows.append(dict(frame=first+j,time=t,x=float(position[0]),y=float(position[1]),observed=True,track_id=track_id,candidate_count=len(candidates)))
                for a,b in zip(history,history[1:]): cv2.line(frame,a,b,(0,255,255),2)
                cv2.circle(frame,history[-1],8,(0,0,255),2)
            else:
                lost+=1; history=[]
                rows.append(dict(frame=first+j,time=t,x=np.nan,y=np.nan,observed=False,track_id=track_id,candidate_count=len(candidates)))
                if lost>max(2,round(fps*.15)): last=None; velocity=np.zeros(2); last_bounce=None
            cv2.putText(frame,f'{t:.3f}s | BALL CANDIDATE - NOT VERIFIED',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),2)
            writer.write(frame); prev=gray
            if progress and j%max(1,int(fps))==0: progress((j+1)/count)
    finally:
        cap.release()
        if writer is not None: writer.release()
    if not rows: raise ValueError('Không có khung để phân tích.')
    table=pd.DataFrame(rows); table.to_csv(out/'ball_tracks.csv',index=False)
    (out/'event_candidates.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
    diagnostics=dict(fps=fps,start=start,end=end,roi=list(roi),hue=list(hue),frames=len(rows),
                     observation_fraction=float(table.observed.mean()),event_candidates=len(events),
                     warning='Observation fraction is not detection accuracy. No paddle/floor detector.')
    (out/'tracking_report.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
    video=out/'ball_overlay.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i',str(tmp),'-c:v','libx264','-pix_fmt','yuv420p','-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2','-movflags','+faststart',str(video)],check=True,capture_output=True)
    tmp.unlink()
    return table,events,video,diagnostics


def timecode_table(segments):
    elapsed=0.; rows=[]
    for i,s in enumerate(sorted(segments,key=lambda s:s['start'])):
        length=s['end']-s['start']
        rows.append(dict(rally=i+1,source_start=s['start'],source_end=s['end'],
                         highlight_start=elapsed,highlight_end=elapsed+length))
        elapsed+=length
    return pd.DataFrame(rows)


def rally_metrics(predicted,truth,iou_threshold=.5):
    """Maximum-cardinality one-to-one interval matching at specified IoU."""
    from scipy.optimize import linear_sum_assignment
    if not 0<iou_threshold<=1: raise ValueError('Ngưỡng IoU phải thuộc (0,1].')
    def valid(intervals):
        for a,b in intervals:
            if not np.isfinite(a+b) or not 0<=a<b: raise ValueError('Khoảng nhãn không hợp lệ.')
    valid(predicted); valid(truth)
    matrix=np.zeros((len(predicted),len(truth)))
    for i,(a,b) in enumerate(predicted):
        for j,(c,d) in enumerate(truth):
            overlap=max(0,min(b,d)-max(a,c)); matrix[i,j]=overlap/(b-a+d-c-overlap)
    pairs=[]
    if matrix.size:
        # The integer reward dominates IoU tie-break across the whole assignment.
        reward=(matrix>=iou_threshold)*(min(matrix.shape)+1)+matrix
        r,c=linear_sum_assignment(-reward)
        pairs=[(i,j) for i,j in zip(r,c) if matrix[i,j]>=iou_threshold]
    hits=len(pairs); n=len(predicted); m=len(truth)
    return dict(precision=hits/n if n else float(not m),recall=hits/m if m else float(not n),
                f1=2*hits/(n+m) if n+m else 1.,matched=hits,predicted=n,reference=m,
                start_mae_seconds=float(np.mean([abs(predicted[i][0]-truth[j][0]) for i,j in pairs])) if pairs else None,
                end_mae_seconds=float(np.mean([abs(predicted[i][1]-truth[j][1]) for i,j in pairs])) if pairs else None)
