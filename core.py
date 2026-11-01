"""CPU video analytics. Times and intervals use seconds, [start, end)."""
from pathlib import Path
import subprocess
import json
import cv2
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import imageio_ffmpeg


def normalize(x):
    x = np.asarray(x, dtype=float)
    lo, hi = np.percentile(x, [5, 95])
    return np.clip((x-lo)/(hi-lo), 0, 1) if hi > lo else np.zeros_like(x)


def analyze(path, out, sample_fps=2., sensitivity=3., progress=None):
    if not np.isfinite(sample_fps) or sample_fps <= 0:
        raise ValueError('Tốc độ lấy mẫu phải dương và hữu hạn.')
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS); count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if not cap.isOpened() or fps <= 0 or count <= 0:
        cap.release(); raise ValueError('Không đọc được video. Hãy dùng MP4/H.264 hợp lệ.')
    step = max(1, round(fps/sample_fps))
    face = cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    rows, histograms = [], []
    prev = ph = None
    i = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok: break
            if i % step == 0:
                frame = cv2.resize(frame, (320, 180))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]).flatten()
                h /= max(h.sum(), 1)
                diff = float(np.mean(cv2.absdiff(gray, prev))/255) if prev is not None else 0.
                change = float(cv2.compareHist(h, ph, cv2.HISTCMP_BHATTACHARYYA)) if ph is not None else 0.
                motion = 0.
                if prev is not None:
                    flow = cv2.calcOpticalFlowFarneback(prev, gray, None, .5, 3, 15, 3, 5, 1.2, 0)
                    motion = float(np.linalg.norm(flow, axis=2).mean())
                faces = len(face.detectMultiScale(gray, 1.1, 4, minSize=(24, 24)))
                sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                thumb = f'frame_{len(rows):06d}.jpg'
                cv2.imwrite(str(out/thumb), frame)
                rows.append(dict(time=i/fps, color=change, difference=diff, motion=motion, faces=faces, sharpness=sharp, image=thumb))
                histograms.append(h); prev, ph = gray, h
                if progress: progress(min(i/count, .99))
            i += 1
    finally:
        cap.release()
    if not rows: raise ValueError('Video không có khung hình giải mã được.')
    df = pd.DataFrame(rows)
    signal = .7*df.color.to_numpy()+.3*df.difference.to_numpy()
    med = np.median(signal); mad = np.median(np.abs(signal-med))
    threshold = max(.12, med+sensitivity*1.4826*mad)
    cuts = []; last = -1.
    for j in range(1, len(df)):
        t = float(df.time.iloc[j])
        if signal[j] > threshold and t-last >= 1.:
            cuts.append(t); last = t
    duration = i/fps
    df['cluster'] = KMeans(n_clusters=min(8, len(df), len(np.unique(histograms, axis=0))), random_state=42, n_init=10).fit_predict(np.asarray(histograms))
    for col in ['motion', 'faces', 'sharpness', 'color', 'difference']:
        df[col+'_norm'] = normalize(df[col])
    meta = dict(duration=duration, fps=fps, frames=i, sample_fps=fps/step, cuts=cuts, threshold=threshold)
    df.to_csv(out/'features.csv', index=False)
    (out/'metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return df, meta


def select(df, meta, ratio=.15, mode='balanced', diversity=True, optimizer='greedy'):
    if not 0 < ratio <= 1: raise ValueError('ratio phải thuộc (0, 1].')
    weights = {'balanced': [.25,.15,.2,.25,.15], 'sports': [.55,.05,.1,.2,.1], 'lecture': [.1,.3,.25,.2,.15], 'motion': [1,0,0,0,0], 'no_motion': [0,.2,.25,.35,.2]}
    weights['uniform'] = [0,0,0,0,0]
    if mode not in weights: raise ValueError('Chế độ chọn đoạn không hợp lệ.')
    if optimizer not in ('greedy','knapsack'): raise ValueError('Thuật toán chọn đoạn không hợp lệ.')
    if df.empty: raise ValueError('Không có đặc trưng để chọn đoạn.')
    cols = ['motion_norm','faces_norm','sharpness_norm','color_norm','difference_norm']
    score = df[cols].to_numpy() @ np.array(weights[mode])
    budget = meta['duration']*ratio
    boundaries = sorted(set([0., *meta['cuts'], meta['duration']]))
    segments = []
    # Split long scenes so even short summaries have feasible candidates.
    for a,b in zip(boundaries[:-1], boundaries[1:]):
        n = max(1, int(np.ceil((b-a)/min(4., budget))))
        edges = np.linspace(a,b,n+1)
        for start,end in zip(edges[:-1],edges[1:]):
            idx = np.flatnonzero((df.time >= start)&(df.time < end))
            if not len(idx): idx = np.array([int(np.argmin(abs(df.time-(start+end)/2)))])
            key = int(idx[np.argmax(score[idx])])
            contribution = df.iloc[idx][cols].mean().to_numpy() * np.array(weights[mode])
            segments.append(dict(start=float(start), end=float(end), score=float(score[idx].mean()), cluster=int(df.cluster.iloc[key]), keyframe=str(df.image.iloc[key]), contributions=dict(zip(cols, map(float, contribution)))))
    if optimizer == 'knapsack' and mode != 'uniform':
        return knapsack_select(segments, budget), score
    if mode == 'uniform':
        # Even temporal spacing, independent of visual features.
        order=[]
        for target in np.linspace(0,meta['duration'],len(segments),endpoint=False):
            candidates=[s for s in segments if s not in order]
            order.append(min(candidates,key=lambda s:abs((s['start']+s['end'])/2-target)))
        # Visit center, endpoints, then progressively fill gaps.
        priorities=[]
        pending=[(0,len(order))]
        while pending:
            a,b=pending.pop(0)
            if a>=b: continue
            mid=(a+b)//2; priorities.append(order[mid])
            pending.extend([(a,mid),(mid+1,b)])
        segments=priorities
    chosen=[]; used=set(); remaining=budget
    while True:
        candidates = [s for s in segments if s not in chosen and s['end']-s['start'] <= remaining+1e-8]
        if not candidates: break
        if mode == 'uniform': best = candidates[0]
        else: best=max(candidates, key=lambda s: s['score'] + (.25 if diversity and s['cluster'] not in used else 0))
        chosen.append(best); used.add(best['cluster']); remaining -= best['end']-best['start']
    return sorted(chosen, key=lambda s:s['start']), score


def knapsack_select(segments, budget, max_bins=2000):
    """0/1 DP: maximize integral importance; conservative quantized durations.

    Diversity bonus is deliberately excluded: it is not an additive objective.
    """
    if budget <= 0: return []
    unit=min(budget,max(.05,budget/max_bins))
    capacity=int(np.floor(budget/unit+1e-9))
    values=np.zeros(capacity+1)
    decisions=np.zeros((len(segments),capacity+1),dtype=bool)
    costs=[]
    for i,s in enumerate(segments):
        duration=s['end']-s['start']
        cost=max(1,int(np.ceil(duration/unit-1e-9))); costs.append(cost)
        if cost>capacity: continue
        candidate=values[:-cost]+(s['score']+1e-9)*duration
        improve=candidate>values[cost:]
        decisions[i,cost:]=improve
        values[cost:]=np.maximum(values[cost:],candidate)
    chosen=[]; c=capacity
    for i in range(len(segments)-1,-1,-1):
        if decisions[i,c]: chosen.append(segments[i]); c-=costs[i]
    return sorted(chosen,key=lambda s:s['start'])


def export_video(source, segments, out):
    out = Path(out); exe = imageio_ffmpeg.get_ffmpeg_exe()
    out.mkdir(parents=True,exist_ok=True)
    if not segments: raise ValueError('Không có đoạn được chọn.')
    clips=[]
    for i,s in enumerate(segments):
        p=out/f'clip_{i:04d}.mp4'; clips.append(p)
        cmd=[exe,'-y','-ss',str(s['start']),'-i',str(source),'-t',str(s['end']-s['start']),'-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2','-c:a','aac',str(p)]
        subprocess.run(cmd, check=True, capture_output=True)
    listing=out/'concat.txt'
    listing.write_text('\n'.join("file '"+p.name+"'" for p in clips), encoding='utf-8')
    target=out/'summary.mp4'
    subprocess.run([exe,'-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(target)],check=True,capture_output=True)
    for p in clips: p.unlink()
    return target


def boundary_f1(pred, truth, tolerance=.5):
    if not np.isfinite(tolerance) or tolerance < 0: raise ValueError('Sai số phải không âm và hữu hạn.')
    if any(not np.isfinite(x) or x<0 for x in [*pred,*truth]): raise ValueError('Ranh giới phải là số hữu hạn không âm.')
    # Sorted greedy matching maximizes cardinality for ordered tolerance intervals.
    p=sorted(pred); g=sorted(truth); i=j=hits=0
    while i<len(p) and j<len(g):
        if abs(p[i]-g[j])<=tolerance: hits+=1; i+=1; j+=1
        elif p[i]<g[j]: i+=1
        else: j+=1
    return 2*hits/(len(p)+len(g)) if p or g else 1.


def summary_f1(segments, references, duration, hz=10):
    if not np.isfinite(duration) or duration<=0 or not np.isfinite(hz) or hz<=0:
        raise ValueError('Thời lượng và tần số đánh giá phải dương và hữu hạn.')
    t=np.arange(0,duration,1/hz)
    def mask(intervals):
        m=np.zeros(len(t),bool)
        for a,b in intervals:
            if not 0<=a<b<=duration+1e-6: raise ValueError('Nhãn nằm ngoài thời lượng hoặc start >= end.')
            m |= (t>=a)&(t<b)
        return m
    pred=mask([(s['start'],s['end']) for s in segments]); values=[]
    for ref in references:
        gt=mask(ref); den=int(pred.sum()+gt.sum())
        values.append(float(2*(pred&gt).sum()/den) if den else 1.)
    if not values: raise ValueError('Cần ít nhất một người gán nhãn.')
    return {'per_user':values,'mean':float(np.mean(values)), 'max':float(np.max(values)), 'resolution_seconds':1/hz}
