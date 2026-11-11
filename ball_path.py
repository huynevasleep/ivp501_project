"""Ball flight path on a fixed court camera: candidates -> tracklets -> path -> bounce / hit candidates.

Pipeline (classical CV only):
1. Candidates per frame: `rally_evidence.ball_candidates` (yellow HSV & frame difference & blob shape).
2. Ground: the convex hull of the camera's painted court lines plus the low-texture floor around it
   (so bounces just outside the lines are kept). Candidates are searched over the ground and straight
   above it (an upright camera shows a ball in the air above its floor point).
3. Tracklets: a candidate continues the tracklet whose constant-velocity prediction is nearest.
   Crowd flicker, flags and feet do not make long, smooth, fast tracks; the ball does.
4. Flights: each tracklet is cut into parabolic pieces (x linear, y quadratic in time; number of
   pieces by BIC). A ball piece curves down with gravity, travels far (Otsu on log travel) and has a
   point over the ground (it leaves from or lands on the court). A bounce must lie on the ground.
5. Events where one flight ends and the next starts at the same place:
   - bounce: moving down, then up, with the same horizontal direction (the floor flips only vy);
   - hit: the horizontal direction reverses (a paddle sends the ball back).
   A bounce inside the court hull is "in", outside is "out". Two bounces with no hit between = double bounce.
   The bounce/hit split relies on the side-to-side motion, so it is clearest on a side camera.
"""
from pathlib import Path
import json
import cv2
import numpy as np
from core import otsu_threshold
from rally_evidence import ball_candidates

ANALYSIS_SIZE = (320, 180)          # court lines are stored in this frame size
LINK_RADIUS = .014                  # max miss of the constant-velocity prediction, share of frame width (12 px at 854)
MIN_TRACK_SECONDS = .2              # shortest tracklet kept as ball flight
SCENE_CUT = .25                     # mean abs frame difference that marks a cut (rally_evidence.track_ball's rule)


def court_hull(lines, size):
    """Convex hull (N, 2) int32 of painted court line end points, scaled to a (w, h) frame."""
    if not lines: return None
    sx, sy = size[0]/ANALYSIS_SIZE[0], size[1]/ANALYSIS_SIZE[1]
    pts = np.array([[x*sx, y*sy] for l in lines for x, y in (l[:2], l[2:])], np.float32)
    return cv2.convexHull(pts).reshape(-1, 2).astype(np.int32)


def floor_mask(median_gray, hull):
    """Low-texture area connected to the court: Otsu split of local edge density, kept where it touches the hull."""
    h, w = median_gray.shape
    edges = cv2.Canny(cv2.GaussianBlur(median_gray, (3, 3), 0), 50, 150).astype(np.float32)/255
    k = max(3, w//40) | 1
    density = cv2.blur(edges, (k, k))
    flat = (density <= otsu_threshold(density.ravel())).astype(np.uint8)
    court = np.zeros((h, w), np.uint8); cv2.fillConvexPoly(court, hull, 1)
    n, labels = cv2.connectedComponents(flat | court)
    keep = np.unique(labels[court > 0]); keep = keep[keep > 0]
    return np.isin(labels, keep)


def ground_mask(hull, size, floor=None):
    """Bool mask (h, w) of the playing surface: court hull plus the floor around it."""
    w, h = size
    court = np.zeros((h, w), np.uint8); cv2.fillConvexPoly(court, hull, 1)
    return (court > 0) | (floor if floor is not None else False)


def court_region(ground):
    """Where the ball can be seen: the ground and everything straight above it."""
    return np.maximum.accumulate(ground[::-1].astype(np.uint8), axis=0)[::-1] > 0


def candidates(video, start, end, region=None):
    """Per frame list of (x, y) ball candidates in [start, end) seconds at native fps; stops at a scene cut
    (stretches come from 2 fps samples, so a cut can fall up to half a second inside)."""
    cap = cv2.VideoCapture(str(video)); fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(start*fps)))
    prev = None; out = []; size = None
    for _ in range(int(round((end-start)*fps))):
        ok, frame = cap.read()
        if not ok: break
        size = frame.shape[1], frame.shape[0]; gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev is not None and np.mean(cv2.absdiff(gray, prev))/255 > SCENE_CUT: break   # the court shot ended
        found = [(x, y) for x, y, _ in ball_candidates(frame, prev)]
        if region is not None: found = [(x, y) for x, y in found if region[int(y), int(x)]]
        out.append(found); prev = gray
    cap.release()
    return out, fps, size


def link_tracklets(per_frame, width):
    """Greedy constant-velocity linking. Returns [{'f': [frame...], 'p': [(x, y)...]}]."""
    radius = LINK_RADIUS*width
    done, live = [], []
    for j, cs in enumerate(per_frame):
        cs = [np.array(c, float) for c in cs]; used = set(); nxt = []
        for tr in sorted(live, key=lambda t: -len(t['p'])):             # long tracks choose first
            p = tr['p'][-1]+(tr['p'][-1]-tr['p'][-2] if len(tr['p']) > 1 else 0)
            r = radius if len(tr['p']) > 1 else 3*radius                  # no velocity yet: wider search
            d = [np.linalg.norm(c-p) if i not in used else np.inf for i, c in enumerate(cs)]
            if d and min(d) < r:
                i = int(np.argmin(d)); used.add(i); tr['p'].append(cs[i]); tr['f'].append(j); nxt.append(tr)
            else: done.append(tr)
        nxt += [dict(f=[j], p=[c]) for i, c in enumerate(cs) if i not in used]
        live = nxt
    return [dict(f=t['f'], p=[tuple(map(float, q)) for q in t['p']]) for t in done+live]


def _fit(f, p):
    """Free flight model: x linear in time, y quadratic (gravity). Returns (coef_x, coef_y, rss)."""
    cx = np.polyfit(f, p[:, 0], 1); cy = np.polyfit(f, p[:, 1], 2)
    rss = float(((p[:, 0]-np.polyval(cx, f))**2).sum()+((p[:, 1]-np.polyval(cy, f))**2).sum())
    return cx, cy, rss


def _bic(rss, n, k):
    return n*np.log(max(rss, 1e-6)/n)+k*np.log(n)


def split_flights(track, min_len):
    """Cut a tracklet into free-flight pieces: one parabola per piece, the number of pieces chosen by BIC.
    A hit or a bounce the linker bridged shows up as a kink no single parabola can follow."""
    f = np.array(track['f'], float); p = np.array(track['p'], float)
    if len(f) < 2*min_len: return [track]
    whole = _bic(_fit(f, p)[2], 2*len(f), 5)
    best, cut = whole, None
    for i in range(min_len, len(f)-min_len+1):
        rss = _fit(f[:i], p[:i])[2]+_fit(f[i-1:], p[i-1:])[2]           # the kink frame belongs to both
        b = _bic(rss, 2*len(f), 11)
        if b < best: best, cut = b, i
    if cut is None: return [track]
    a = dict(f=track['f'][:cut], p=track['p'][:cut]); b = dict(f=track['f'][cut-1:], p=track['p'][cut-1:])
    return split_flights(a, min_len)+split_flights(b, min_len)


def flight_stats(t):
    f = np.array(t['f'], float); p = np.array(t['p'], float)
    cx, cy, rss = _fit(f, p)
    return dict(gravity=float(cy[0]), travel=float(np.ptp(p, axis=0).max()), rms=float(np.sqrt(rss/len(f))))


def on_ground(track, ground):
    """A ball flight leaves from or lands on the playing surface: some point lies over the ground."""
    h, w = ground.shape
    return any(ground[min(h-1, int(y)), min(w-1, int(x))] for x, y in track['p'])


def ball_tracklets(tracklets, fps):
    """Ball flights: tracklets of >= MIN_TRACK_SECONDS cut into parabolic pieces, kept when a piece
    curves down with gravity (y'' >= 0 in image rows) and travels far (high side of an Otsu split
    of log travel). Crowd flicker and feet jiggle in place and curve either way."""
    min_len = max(3, round(MIN_TRACK_SECONDS*fps))
    pieces = [q for t in tracklets if len(t['p']) >= min_len for q in split_flights(t, min_len)]
    pieces = [q for q in pieces if len(q['p']) >= min_len]
    if len(pieces) < 2: return pieces, 0.
    stats = [flight_stats(q) for q in pieces]
    travel = np.log1p([s['travel'] for s in stats])
    cut = otsu_threshold(travel)
    keep = [q for q, s, t in zip(pieces, stats, travel) if t > cut and s['gravity'] >= 0]
    return sorted(keep, key=lambda q: q['f'][0]), float(np.expm1(cut))


def _end_velocity(t, at_start):
    f = np.array(t['f'], float); p = np.array(t['p'], float)
    cx, cy, _ = _fit(f, p); x = f[0] if at_start else f[-1]
    return np.array([cx[0], 2*cy[0]*x+cy[1]])


def path_events(tracks, hull=None, fps=30., ground=None):
    """Bounce / hit candidates where one flight ends and the next begins (same place, short gap).
    bounce: falling (vy > 0) then rising (vy < 0) with the same horizontal direction;
    hit: the horizontal direction reverses. Other joins (e.g. a volley straight back in depth) stay unlabelled."""
    gap = max(1, round(.1*fps))
    pairs = []                                            # (miss, a, b): flight a hands over to flight b
    for i, a in enumerate(tracks):
        for j, b in enumerate(tracks):
            if i == j or not 0 <= b['f'][0]-a['f'][-1] <= gap: continue
            pa, pb = np.array(a['p'][-1]), np.array(b['p'][0])
            va, vb = _end_velocity(a, False), _end_velocity(b, True)
            reach = (b['f'][0]-a['f'][-1]+1)*max(np.linalg.norm(va), np.linalg.norm(vb))
            miss = float(np.linalg.norm(pb-pa))
            if miss <= reach+1: pairs.append((miss, i, j))
    events = []; used_a, used_b = set(), set()
    for miss, i, j in sorted(pairs):                      # one hand-over per flight end and per flight start
        if i in used_a or j in used_b: continue
        used_a.add(i); used_b.add(j)
        a, b = tracks[i], tracks[j]
        pa, pb = np.array(a['p'][-1]), np.array(b['p'][0])
        va, vb = _end_velocity(a, False), _end_velocity(b, True)
        if va[1] > 0 > vb[1] and np.sign(va[0]) == np.sign(vb[0]): kind = 'bounce'
        elif np.sign(va[0]) != np.sign(vb[0]): kind = 'hit'
        else: continue
        at = (pa+pb)/2
        if kind == 'bounce' and ground is not None and not ground[min(ground.shape[0]-1, int(at[1])), min(ground.shape[1]-1, int(at[0]))]:
            continue                                      # a bounce happens on the floor
        e = dict(frame=int(a['f'][-1]), x=float(at[0]), y=float(at[1]), kind=kind, flight_in=i, flight_out=j)
        if kind == 'bounce' and hull is not None:
            e['inside'] = bool(cv2.pointPolygonTest(hull.astype(np.float32), (float(at[0]), float(at[1])), False) >= 0)
        events.append(e)
    events.sort(key=lambda e: e['frame'])
    return events


def rally_calls(events):
    """End-of-rally candidates seen in the image:
    out = a bounce outside the court hull; double_bounce = two bounces joined by one seen flight
    (the ball was followed the whole way, so no hit can hide between them)."""
    calls = []
    for e in events:
        if e['kind'] == 'bounce' and e.get('inside') is False: calls.append(dict(frame=e['frame'], call='out'))
    for e1 in events:
        for e2 in events:
            if e1['kind'] == e2['kind'] == 'bounce' and e2['flight_in'] == e1['flight_out']:
                calls.append(dict(frame=e2['frame'], call='double_bounce'))
    return sorted(calls, key=lambda c: c['frame'])


def ball_path(video, start, end, lines=None, median_gray=None):
    """Run the whole pipeline on [start, end) s. lines: painted court lines (320x180) of this camera."""
    cap = cv2.VideoCapture(str(video)); size = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); cap.release()
    hull = court_hull(lines, size)
    region = ground = None
    if hull is not None:
        floor = floor_mask(cv2.resize(median_gray, size), hull) if median_gray is not None else None
        ground = ground_mask(hull, size, floor); region = court_region(ground)
    per_frame, fps, _ = candidates(video, start, end, region)
    tracklets = link_tracklets(per_frame, size[0])
    tracks, travel_cut = ball_tracklets(tracklets, fps)
    if ground is not None: tracks = [t for t in tracks if on_ground(t, ground)]
    events = path_events(tracks, hull, fps, ground)
    return dict(fps=fps, size=size, start=start, hull=hull, ground=ground, region=region, per_frame=per_frame,
                tracklets=tracklets, tracks=tracks, travel_cut=travel_cut, events=events, calls=rally_calls(events))


def draw(result, background, path=None):
    """Path overlay: region outline, tracks coloured by time, B = bounce (green in / red out), H = hit."""
    img = background.copy(); n = max(1, len(result['per_frame']))
    if result['ground'] is not None:
        cs, _ = cv2.findContours(result['ground'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, cs, -1, (200, 200, 200), 1)
    if result['hull'] is not None: cv2.polylines(img, [result['hull']], True, (255, 255, 255), 1)
    for t in result['tracks']:
        col = cv2.applyColorMap(np.uint8([[int(255*t['f'][0]/n)]]), cv2.COLORMAP_JET)[0, 0].tolist()
        cv2.polylines(img, [np.int32(t['p'])], False, col, 2)
    for e in result['events']:
        c = (int(e['x']), int(e['y']))
        if e['kind'] == 'bounce':
            col = (0, 220, 0) if e.get('inside', True) else (0, 0, 255)
            cv2.circle(img, c, 7, col, 2); cv2.putText(img, 'B', (c[0]+8, c[1]+5), cv2.FONT_HERSHEY_SIMPLEX, .5, col, 2)
        else:
            cv2.drawMarker(img, c, (255, 255, 255), cv2.MARKER_TILTED_CROSS, 12, 2)
            cv2.putText(img, 'H', (c[0]+8, c[1]+5), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 2)
    if path: cv2.imwrite(str(path), img)
    return img


def rally_ball_paths(video, df, meta, segments, out=None, progress=None):
    """Ball path over every court-camera stretch of the kept rallies, in analysis (320x180) pixels
    and source seconds. Written to out/ball_paths.json for the decision panel."""
    from core import court_mask
    court = court_mask(df, meta); t = df.time.to_numpy(); step = 1/meta.get('sample_fps', 2.)
    cam_of = df.court_template.to_numpy() if 'court_template' in df else df.camera.to_numpy()
    debug, lines_of = meta.get('court_debug', {}), meta.get('court_lines', {})
    stretches = []
    for i, s in enumerate(segments):
        idx = np.flatnonzero((t >= s['start']) & (t < s['end']) & court)
        if not len(idx): continue
        for run in np.split(idx, np.flatnonzero((np.diff(idx) != 1) | (np.diff(cam_of[idx]) != 0))+1):
            cam = int(cam_of[run[0]])
            if len(run) >= 2 and lines_of.get(str(cam)):
                stretches.append(dict(r=i, cam=cam, start=float(t[run[0]]), end=float(min(t[run[-1]]+step, s['end']))))
    total = sum(x['end']-x['start'] for x in stretches) or 1.; seen = 0.
    tracks, events, calls, hulls = [], [], [], {}
    medians = {}
    for x in stretches:
        cam = x['cam']; lines = lines_of[str(cam)]
        if cam not in medians:
            name = debug.get(str(cam), {}).get('median')
            medians[cam] = cv2.imread(str(Path(out)/name), 0) if out and name and (Path(out)/name).exists() else None
        r = ball_path(video, x['start'], x['end'], lines, medians[cam])
        sx, sy = ANALYSIS_SIZE[0]/r['size'][0], ANALYSIS_SIZE[1]/r['size'][1]
        first = int(round(x['start']*r['fps'])); T = lambda f: round((first+f)/r['fps'], 3)
        hulls[str(cam)] = court_hull(lines, ANALYSIS_SIZE).tolist()
        for tr in r['tracks']:
            tracks.append(dict(r=x['r'], cam=cam, t=[T(f) for f in tr['f']],
                               x=[round(p[0]*sx, 1) for p in tr['p']], y=[round(p[1]*sy, 1) for p in tr['p']]))
        for e in r['events']:
            events.append(dict(r=x['r'], cam=cam, t=T(e['frame']), kind=e['kind'], x=round(e['x']*sx, 1),
                               y=round(e['y']*sy, 1), inside=e.get('inside')))
        calls += [dict(r=x['r'], cam=cam, t=T(c['frame']), call=c['call']) for c in r['calls']]
        seen += x['end']-x['start']
        if progress: progress(seen/total)
    result = dict(stretches=stretches, tracks=tracks, events=sorted(events, key=lambda e: e['t']),
                  calls=sorted(calls, key=lambda c: c['t']), hulls=hulls)
    if out: (Path(out)/'ball_paths.json').write_text(json.dumps(result), encoding='utf-8')
    return result
