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


def otsu_threshold(values, weights=None, bins=256):
    """1-D Otsu: threshold maximizing between-class variance of a bimodal distribution."""
    values = np.asarray(values, dtype=float); keep = np.isfinite(values)
    values = values[keep]
    weights = np.ones_like(values) if weights is None else np.asarray(weights, dtype=float)[keep]
    if len(values) == 0: raise ValueError('Không có giá trị để chọn ngưỡng.')
    if values.min() == values.max(): return float(values[0])
    hist, edges = np.histogram(values, bins, weights=weights); mids = (edges[:-1]+edges[1:])/2
    w0 = np.cumsum(hist); w1 = w0[-1]-w0; s0 = np.cumsum(hist*mids)
    m0 = s0/np.maximum(w0, 1e-12); m1 = (s0[-1]-s0)/np.maximum(w1, 1e-12)
    return float(edges[1:][np.argmax(w0*w1*(m0-m1)**2)])


def audio_loudness(path, times, window):
    """RMS loudness (dB full scale) of the mono soundtrack around each time; NaN when no audio."""
    sr = 8000
    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'], capture_output=True).stdout
    signal = np.frombuffer(raw, np.int16).astype(np.float64)/32768
    if len(signal) < sr//10: return np.full(len(times), np.nan)
    energy = np.concatenate([[0.], np.cumsum(signal**2)])
    half = window/2; out = []
    for t in times:
        a = int(np.clip((t-half)*sr, 0, len(signal)-1)); b = int(np.clip((t+half)*sr, a+1, len(signal)))
        out.append(10*np.log10((energy[b]-energy[a])/(b-a)+1e-12))
    return np.array(out)


def _edges(gray):
    """Canny edge map (bool) of a 320x180 frame; Gaussian 3x3 first to drop sensor noise."""
    return cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 50, 150) > 0


_TOLERANCE = np.ones((3, 3), np.uint8)       # a 1-pixel shift of an edge still counts as the same edge


def edge_match(edges, template, template_wide):
    """(Dice, recall, precision) of an edge map against a template.
    recall = template edges found in the frame; precision = frame edges lying on the template.
    Precision keeps busy images (crowd, aerial shots), whose dense edges cover any template, low."""
    wide = cv2.dilate(edges.astype(np.uint8), _TOLERANCE) > 0
    recall = (wide & template).sum()/max(template.sum(), 1)
    precision = (edges & template_wide).sum()/max(edges.sum(), 1)
    return float(2*recall*precision/max(recall+precision, 1e-9)), float(recall), float(precision)


def edge_dice(edges, template, template_wide):
    """Two-way agreement of an edge map with a template (Dice of recall and precision)."""
    return edge_match(edges, template, template_wide)[0]


def hough_space(binary, theta_step=1., rho_step=1.):
    """Standard Hough transform: votes of every edge pixel for lines x cos(t) + y sin(t) = rho.
    Returns (accumulator [rho, theta], rho_max); theta in [0, 180) degrees."""
    ys, xs = np.nonzero(binary)
    thetas = np.deg2rad(np.arange(0, 180, theta_step))
    rho_max = float(np.hypot(*binary.shape))
    n_rho = int(np.ceil(2*rho_max/rho_step))+1
    acc = np.zeros((n_rho, len(thetas)), np.int32)
    for j, t in enumerate(thetas):
        rho = np.round((xs*np.cos(t)+ys*np.sin(t)+rho_max)/rho_step).astype(int)
        acc[:, j] = np.bincount(rho, minlength=n_rho)[:n_rho]
    return acc, rho_max


def segment_rho_theta(segment):
    """(rho, theta in degrees [0, 180)) of the line through a segment, matching hough_space."""
    x1, y1, x2, y2 = map(float, segment)
    theta = np.arctan2(-(x2-x1), y2-y1) % np.pi
    return float(x1*np.cos(theta)+y1*np.sin(theta)), float(np.degrees(theta))


def is_painted_line(gray, segment, inner=2, outer=5, samples=24):
    """Share of points along a Hough segment where a thin bright line runs beside it.

    Canny marks the two borders of a painted court line, so the Hough segment lies on a border,
    not on the paint. At each sample point the brightest pixel within `inner` px across the
    segment must be brighter than both pixels `outer` px away on either side: a thin bright
    ridge. The border of a banner or ad board is a step (bright on one side only) and fails.
    """
    x1, y1, x2, y2 = map(float, segment)
    length = np.hypot(x2-x1, y2-y1)
    if length == 0: return 0.
    nx, ny = -(y2-y1)/length, (x2-x1)/length
    h, w = gray.shape; hits = total = 0
    for s in np.linspace(.1, .9, samples):
        x, y = x1+s*(x2-x1), y1+s*(y2-y1)
        offsets = range(-outer, outer+1)
        points = {o: (int(round(x+o*nx)), int(round(y+o*ny))) for o in offsets}
        if not all(0 <= px < w and 0 <= py < h for px, py in points.values()): continue
        value = {o: float(gray[py, px]) for o, (px, py) in points.items()}
        total += 1
        hits += max(value[o] for o in range(-inner, inner+1)) > max(value[-outer], value[outer])
    return hits/max(total, 1)


def court_cameras(edges, camera, gray_of=None):
    """Find the fixed court cameras from edges alone and score every frame against them.

    edges: (N, H*W/8) packed Canny maps; camera: K-means layout cluster per frame;
    gray_of(k): the 320x180 grayscale frame k (used to tell painted lines from other edges).
    For each cluster the template is the median edge map (edge in >= half of its frames).
    A fixed camera keeps its edges in place, so its frames match its template; a hand-held
    or moving shot does not. Fixed clusters = high side of an Otsu split of log median
    self-match (weighted by size). Court lines = Hough segments of the template that are
    painted lines (`is_painted_line` >= half the points) on the cluster's median frame; a
    court camera = fixed AND at least one court line. Without gray_of every Hough segment counts.
    Returns (per-frame best Dice against court templates, court cluster ids,
             {cluster id: court line segments [x1, y1, x2, y2] in 320x180 pixels},
             debug: per-frame recall / precision / best court cluster, court templates,
             every Hough segment with its painted-line share).
    """
    shape = (180, 320)
    unpack = lambda k: np.unpackbits(edges[k])[:shape[0]*shape[1]].reshape(shape).astype(bool)
    camera = np.asarray(camera); stats = []
    for c in np.unique(camera):
        idx = np.flatnonzero(camera == c)
        template = np.mean([unpack(k) for k in idx], axis=0) >= .5
        wide = cv2.dilate(template.astype(np.uint8), _TOLERANCE) > 0
        match = np.median([edge_dice(unpack(k), template, wide) for k in idx])
        found = cv2.HoughLinesP(template.astype(np.uint8)*255, 1, np.pi/180, 30, minLineLength=shape[1]//5, maxLineGap=4)
        segments = [] if found is None else [list(map(int, l)) for l in found[:, 0]]
        painted = [1.]*len(segments)
        if segments and gray_of is not None:
            picks = idx[np.linspace(0, len(idx)-1, min(25, len(idx))).astype(int)]
            median = np.median([gray_of(k) for k in picks], axis=0)      # players and ball fade out
            painted = [is_painted_line(median, l) for l in segments]
        lines = [l for l, f in zip(segments, painted) if f >= .5]
        stats.append((c, len(idx), match, lines, template, wide, list(zip(segments, painted))))
    log_match = np.log(np.clip([s[2] for s in stats], 1e-3, None))
    cut = otsu_threshold(log_match, [s[1] for s in stats])
    # A single cluster cannot be split by Otsu (the threshold equals its own value),
    # so a one-camera video relies on the court-line gate alone.
    court = [s for s, m in zip(stats, log_match) if (len(stats) == 1 or m > cut) and s[3]]
    score, recall, precision = np.zeros(len(camera)), np.zeros(len(camera)), np.zeros(len(camera))
    best = np.full(len(camera), -1)
    for k in range(len(camera)):
        e = unpack(k)
        for s in court:
            d, r, p = edge_match(e, s[4], s[5])
            if d > score[k] or best[k] < 0: score[k], recall[k], precision[k], best[k] = d, r, p, s[0]
    debug = dict(recall=recall, precision=precision, best=best,
                 templates={int(s[0]): s[4] for s in court}, segments={int(s[0]): s[6] for s in court})
    return score, [int(s[0]) for s in court], {int(s[0]): s[3] for s in court}, debug


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
    rows, histograms, layouts, edge_maps = [], [], [], []
    prev = ph = None
    i = 0
    try:
        while True:
            # grab() advances without converting the frame; retrieve() only the sampled ones.
            if not cap.grab(): break
            if i % step == 0:
                ok, frame = cap.retrieve()
                if not ok: break
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
                # Coarse colour layout: frames from the same fixed camera look alike.
                layouts.append(cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2LAB), (16, 9), interpolation=cv2.INTER_AREA).astype(np.float32).ravel())
                edge_maps.append(np.packbits(_edges(gray)))     # 7 KB per frame; a 67-minute match needs ~58 MB
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
    df['camera'] = KMeans(n_clusters=min(12, len(df), len(np.unique(layouts, axis=0))), random_state=42, n_init=10).fit_predict(np.asarray(layouts))
    gray_of = lambda k: cv2.cvtColor(cv2.imread(str(out/rows[k]['image'])), cv2.COLOR_BGR2GRAY)
    df['court_score'], court_ids, court_lines, court_debug = court_cameras(np.asarray(edge_maps), df.camera.to_numpy(), gray_of)
    df['court_recall'], df['court_precision'] = court_debug['recall'], court_debug['precision']
    df['court_template'] = court_debug['best']
    # Debug images: the binary maps the decisions are made on (1-bit PNG, ~1-2 KB each).
    df['edges'] = [f'edge_{k:06d}.png' for k in range(len(df))]
    for k, packed in enumerate(edge_maps):
        cv2.imwrite(str(out/df.edges.iloc[k]), np.unpackbits(packed)[:180*320].reshape(180, 320)*255)
    debug_meta = {}
    for c, template in court_debug['templates'].items():
        acc, rho_max = hough_space(template)
        view = np.log1p(acc.astype(np.float64)); view = (255*view/max(view.max(), 1e-9)).astype(np.uint8)
        cv2.imwrite(str(out/f'court_template_{c}.png'), template.astype(np.uint8)*255)
        cv2.imwrite(str(out/f'court_hough_{c}.png'), view)
        debug_meta[str(c)] = dict(template=f'court_template_{c}.png', hough=f'court_hough_{c}.png', rho_max=rho_max,
                                  rho_bins=int(acc.shape[0]), theta_bins=int(acc.shape[1]),
                                  segments=[dict(seg=seg, painted=round(float(f), 2), kept=bool(f >= .5),
                                                 rho_theta=segment_rho_theta(seg)) for seg, f in court_debug['segments'][c]])
    df['loudness_db'] = audio_loudness(path, df.time.to_numpy(), step/fps)
    for col in ['motion', 'faces', 'sharpness', 'color', 'difference']:
        df[col+'_norm'] = normalize(df[col])
    meta = dict(duration=duration, fps=fps, frames=i, sample_fps=fps/step, cuts=cuts, threshold=threshold,
                court_cameras=court_ids, court_lines={str(k): v for k, v in court_lines.items()}, court_debug=debug_meta, court_threshold=otsu_threshold(df.court_score) if df.court_score.max() > 0 else 1.)
    df.to_csv(out/'features.csv', index=False)
    (out/'metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return df, meta


def _runs(mask):
    """[(start, end)) index pairs of consecutive True values."""
    edges = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def _rank(x):
    """Percentile rank in (0, 1]; ties share the higher rank."""
    x = np.nan_to_num(np.asarray(x, dtype=float), nan=-np.inf)
    return np.searchsorted(np.sort(x), x, side='right')/len(x)


def court_mask(df, meta):
    """Per sample: is a court camera on screen? (the rule detect_rallies uses)."""
    if 'court_score' in df and 'court_threshold' in meta:
        # Court camera from edges: the frame matches a fixed court camera's edge template.
        return (df.court_score > meta['court_threshold']).to_numpy()
    # Analyses made before edge templates existed: fixed cameras = low log median motion.
    stats = df.groupby('camera').motion.agg(['median', 'size'])
    log_motion = np.log(stats['median'].to_numpy()+1e-3)
    fixed = stats.index[log_motion <= otsu_threshold(log_motion, stats['size'])]
    return df.camera.isin(fixed).to_numpy()


def quiet_mask(df):
    """Per sample: is the crowd quiet? Returns (mask, Otsu threshold in dBFS or None without audio)."""
    loud = df.loudness_db.to_numpy()
    if np.isnan(loud).all(): return np.ones(len(df), bool), None
    threshold = otsu_threshold(loud)
    return loud < threshold, float(threshold)


def detect_rallies(df, meta, pre=1., post=2., min_len=1.5, gap=1., reaction=3.):
    """Rallies of a broadcast racket-sport match, as whole intervals that are never cut.

    A rally is a quiet stretch while a fixed court camera is on screen: a frame is on a court camera
    when its Canny edges match a court camera's edge template (`court_cameras`), and "quiet" is
    the low side of an Otsu split of loudness (crowds hush during play, cheer after the point).
    Interval = [first quiet sample - pre, last quiet sample + post), so the serve and the
    reaction are inside; the pre-roll never reaches back past the start of the court shot. Score = mean percentile rank of rally length and of the loudest
    moment within `reaction` seconds after it.
    """
    if df.empty or 'camera' not in df or 'loudness_db' not in df:
        raise ValueError('Thiếu đặc trưng camera/âm thanh: hãy phân tích lại video.')
    step = 1/meta['sample_fps']; t = df.time.to_numpy(); duration = meta['duration']
    court = court_mask(df, meta)
    loud = df.loudness_db.to_numpy()
    quiet, _ = quiet_mask(df)
    play = court & quiet
    # Bridge short gaps (a camera switch or a shout mid-rally) between two quiet stretches.
    hole = int(round(gap/step))
    for a, b in _runs(~play):
        if 0 < a and b < len(play) and b-a <= hole: play[a:b] = True
    cores = [(a, b) for a, b in _runs(play) if (b-a)*step >= min_len]
    if not cores: return []
    rallies = []
    for a, b in cores:
        after = (t >= t[b-1]+step) & (t < t[b-1]+step+reaction)
        mid = (a+b)//2
        lead = a                              # pre-roll stays on the court camera: no flash of the close-up before
        while lead > 0 and court[lead-1]: lead -= 1
        rallies.append(dict(core_start=float(t[a]), core_end=float(t[b-1]+step), court_start=float(t[lead]),
                            cheer_db=float(np.nanmax(loud[after])) if after.any() and not np.isnan(loud[after]).all() else np.nan,
                            cluster=int(df.camera.iloc[mid]), keyframe=str(df.image.iloc[mid])))
    for r, prev in zip(rallies[1:], rallies[:-1]):
        r['start'] = max(r['core_start']-pre, r['court_start']); prev['end'] = min(prev['core_end']+post, duration)
        if prev['end'] > r['start']:            # padding overlaps: split at the middle of the pause
            prev['end'] = r['start'] = (prev['core_end']+r['core_start'])/2
    rallies[0]['start'] = max(rallies[0]['core_start']-pre, rallies[0]['court_start'])
    rallies[-1]['end'] = min(rallies[-1]['core_end']+post, duration)
    length = _rank([r['core_end']-r['core_start'] for r in rallies]); cheer = _rank([r['cheer_db'] for r in rallies])
    for r, l, c in zip(rallies, length, cheer):
        r['score'] = float((l+c)/2)
        r['contributions'] = {'rally_length': float(l/2), 'crowd_reaction': float(c/2)}
    return rallies


def select(df, meta, ratio=.15, mode='balanced', diversity=True, optimizer='greedy'):
    if not 0 < ratio <= 1: raise ValueError('ratio phải thuộc (0, 1].')
    if optimizer not in ('greedy','knapsack'): raise ValueError('Thuật toán chọn đoạn không hợp lệ.')
    if df.empty: raise ValueError('Không có đặc trưng để chọn đoạn.')
    if mode == 'rally':
        rallies = detect_rallies(df, meta); budget = meta['duration']*ratio
        score = np.zeros(len(df))
        for r in rallies: score[(df.time >= r['start']).to_numpy() & (df.time < r['end']).to_numpy()] = r['score']
        if optimizer == 'knapsack': return knapsack_select(rallies, budget), score
        chosen, remaining = [], budget       # best rallies first; a rally is kept whole or not at all
        for r in sorted(rallies, key=lambda r: -r['score']):
            if r['end']-r['start'] <= remaining+1e-8: chosen.append(r); remaining -= r['end']-r['start']
        return sorted(chosen, key=lambda s: s['start']), score
    weights = {'balanced': [.25,.15,.2,.25,.15], 'sports': [.55,.05,.1,.2,.1], 'lecture': [.1,.3,.25,.2,.15], 'motion': [1,0,0,0,0], 'no_motion': [0,.2,.25,.35,.2]}
    weights['uniform'] = [0,0,0,0,0]
    if mode not in weights: raise ValueError('Chế độ chọn đoạn không hợp lệ.')
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


def _floor_mask(frame, cover=.8, lower=.4):
    """Pixels whose hue/saturation is among the colours covering `cover` of the lower part of the frame.

    On a court broadcast the lower part is mostly playing surface, so this marks the floor
    (court + surround) and excludes stands, crowd and boards.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    bins = (hsv[..., 0]//10).astype(np.int32)*8+hsv[..., 1]//32          # 18 hue x 8 saturation bins
    counts = np.bincount(bins[int(frame.shape[0]*(1-lower)):].ravel(), minlength=144)
    order = np.argsort(-counts); keep = order[:np.searchsorted(np.cumsum(counts[order]), cover*counts.sum())+1]
    mask = np.isin(bins, keep).astype(np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)).astype(bool)


def _overlap(a, b):
    """Intersection over union of two (x, y, w, h) boxes."""
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[0]+a[2], b[0]+b[2]), min(a[1]+a[3], b[1]+b[3])
    inter = max(0, x1-x0)*max(0, y1-y0)
    return inter/(a[2]*a[3]+b[2]*b[3]-inter) if inter else 0.


def best_shots(source, segments, out, max_shots=12, min_height=.12, margin=.3, swings=3):
    """Sharpest frame of a player at the peak of a swing, one per segment, from full-resolution frames.

    Fixed court camera → background subtraction (MOG2) isolates moving players; the
    foreground is eroded (splits players standing close) and labelled; components taller than
    `min_height` × frame height, taller than wide and standing on the floor (`_floor_mask` under
    the feet) are kept, the tallest (nearest, so largest in the photo) per frame. Swing = local
    peak of silhouette change (1 - IoU of consecutive player masks); the `swings` strongest peaks
    of each segment are kept, and around each (±3 frames) the frame with the largest Laplacian
    variance in the box is the candidate. Candidates are ranked by box height, swing energy and
    sharpness (mean percentile rank). No pose model: "power" means "largest shape change", not
    a judged posture.
    """
    from scipy.signal import find_peaks
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(source)); fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0: raise ValueError('Không đọc được video gốc.')
    candidates = []
    try:
        for k, s in enumerate(segments):
            first = int(round(s['start']*fps)); cap.set(cv2.CAP_PROP_POS_FRAMES, first)
            mog = cv2.createBackgroundSubtractorMOG2(history=int(fps*2), detectShadows=False)
            prev = prev_mask = prev_box = None; track = []; floor = None
            for j in range(int((s['end']-s['start'])*fps)):
                ok, frame = cap.read()
                if not ok: break
                H, W = frame.shape[:2]
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                fg = mog.apply(frame)
                if floor is None: floor = _floor_mask(frame)
                fg = cv2.morphologyEx(cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
                box = None
                if j >= fps/2:                    # let the background model settle first
                    n, labels, st, _ = cv2.connectedComponentsWithStats(cv2.erode(fg, np.ones((5, 5), np.uint8)))
                    def on_floor(b):
                        feet = floor[min(b[1]+b[3], H-1):min(b[1]+b[3]+6, H), b[0]+b[2]//4:b[0]+3*b[2]//4+1]
                        return feet.size > 0 and feet.mean() > .5
                    people = [c for c in range(1, n) if st[c, 3] >= min_height*H and st[c, 3] >= st[c, 2] and on_floor(st[c])
              and st[c, 0] > 0 and st[c, 1] > 0 and st[c, 0]+st[c, 2] < W]   # cut by the frame edge: no photo
                    if people:
                        # Follow the same player: the component overlapping the previous box most;
                        # otherwise start a new track on the tallest (energy is not measured on a switch).
                        overlap = {c: _overlap(st[c, :4], prev_box) for c in people} if prev_box else {}
                        same = max(overlap, key=overlap.get) if overlap and max(overlap.values()) > 0 else None
                        c = same if same is not None else max(people, key=lambda c: st[c, 3])
                        box = st[c, :4]; mask = labels == c
                        if same is None: prev_mask = None
                if box is not None and prev_mask is not None:
                    x, y, w, h = map(int, box)
                    # Silhouette change = 1 - IoU of this and the previous player mask over both boxes:
                    # a lunge or an arm swinging out changes the shape; texture and fast moves do not
                    # fool it the way pixel difference or small-window optical flow do.
                    px, py, pw, ph = prev_box
                    a0, b0 = min(x, px), min(y, py); a1, b1 = max(x+w, px+pw), max(y+h, py+ph)
                    now, before = mask[b0:b1, a0:a1], prev_mask[b0:b1, a0:a1]
                    shared = (now & before).sum()
                    # No shared pixel: the boxes touched but it is another player, not a movement.
                    energy = float(1-shared/max((now | before).sum(), 1)) if shared else None
                    sharp = float(cv2.Laplacian(gray[y:y+h, x:x+w], cv2.CV_64F).var())
                    if energy is not None: track.append((j, energy, sharp, (x, y, w, h)))
                prev = gray
                prev_mask, prev_box = (mask, tuple(map(int, box))) if box is not None else (None, None)
            if len(track) < 3: continue
            energies = np.array([e for _, e, _, _ in track])
            peaks, _ = find_peaks(energies, distance=max(1, int(fps/2)))
            for p in sorted(peaks, key=lambda p: -energies[p])[:swings]:   # the hardest swings of the rally
                window = track[max(p-3, 0):p+4]
                j, e, sh, box = max(window, key=lambda c: c[2])
                candidates.append(dict(segment=k, frame=first+j, time=(first+j)/fps, energy=energies[p], sharpness=sh, height=box[3], box=box))
        if not candidates: return []
        rank = (_rank([c['height'] for c in candidates])+_rank([c['energy'] for c in candidates])+_rank([c['sharpness'] for c in candidates]))/3
        for c, r in zip(candidates, rank): c['score'] = float(r)
        best = {}
        for c in candidates:                       # one photo per segment, best-scoring
            if c['segment'] not in best or c['score'] > best[c['segment']]['score']: best[c['segment']] = c
        shots = sorted(best.values(), key=lambda c: -c['score'])[:max_shots]
        for i, c in enumerate(sorted(shots, key=lambda c: c['time'])):
            cap.set(cv2.CAP_PROP_POS_FRAMES, c['frame'])
            ok, frame = cap.read()
            if not ok: continue
            H, W = frame.shape[:2]; x, y, w, h = c['box']
            mx, my = int(w*margin), int(h*margin)
            crop = frame[max(y-my, 0):min(y+h+my, H), max(x-mx, 0):min(x+w+mx, W)]
            c['image'] = f'shot_{i:02d}.jpg'; c['full_image'] = f'shot_{i:02d}_full.jpg'
            cv2.imwrite(str(out/c['image']), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
            cv2.imwrite(str(out/c['full_image']), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            c['box'] = [int(v) for v in c['box']]
    finally:
        cap.release()
    return [c for c in sorted(shots, key=lambda c: c['time']) if 'image' in c]


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
