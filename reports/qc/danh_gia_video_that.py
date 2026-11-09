"""Đánh giá pipeline trên video thật (ngắn): tách pha + bám bóng + sự kiện quỹ đạo.

Chạy:  .venv/bin/python reports/qc/danh_gia_video_that.py video1.mp4 [video2.mp4 ...]

Với mỗi video, in ra:
1. Bản nền tách pha (`core.analyze` + `detect_rallies`): số cụm camera, cụm được nhận là
   camera sân, ngưỡng Otsu, các pha [start, end).
2. Bám bóng FPS gốc (`rally_evidence.track_ball` trên toàn video, tối đa 120 s):
   tỉ lệ khung nối được ứng viên, số sự kiện theo loại, danh sách mốc thời gian.
Kết quả chi tiết (overlay, CSV, ảnh mốc) nằm trong runs/qc_eval/<tên video>/.
Mọi con số là ứng viên từ hình dạng quỹ đạo; đối chiếu bằng mắt với video trước khi kết luận.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2

from core import analyze, detect_rallies
from rally_evidence import track_ball


def evaluate(path, roi=(0., 0., 1., 1.)):
    path = Path(path)
    out = Path('runs/qc_eval')/(path.stem+('' if roi == (0., 0., 1., 1.) else '_roi'))
    print(f'\n{"="*60}\n{path} · ROI {roi}\n{"="*60}')
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS); duration = cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps
    width, height = int(cap.get(3)), int(cap.get(4))
    cap.release()
    print(f'{width}x{height} · {fps:.2f} fps · {duration:.1f} s')

    df, meta = analyze(path, out/'analysis')
    court = sorted(df.camera.unique().tolist())
    print(f'\n[1] Tách pha: {df.camera.nunique()} cụm camera {court}; '
          f'cụm sân = {meta["court_cameras"]}; ngưỡng khớp biên Otsu = {meta["court_threshold"]:.2f}')
    frac = float((df.court_score > meta['court_threshold']).mean())
    print(f'    {frac:.0%} khung mẫu vượt ngưỡng camera sân')
    rallies = detect_rallies(df, meta)
    for r in rallies:
        print(f'    pha [{r["start"]:.1f}s → {r["end"]:.1f}s] lõi [{r["core_start"]:.1f}, {r["core_end"]:.1f}) điểm {r["score"]:.2f}')
    if not rallies: print('    (không tách được pha nào)')

    table, events, overlay, diag = track_ball(path, 0, min(duration, 120), out/'evidence', roi=roi)
    print(f'\n[2] Bám bóng: {diag["frames"]} khung, {diag["observation_fraction"]:.1%} khung nối được ứng viên '
          f'(KHÔNG phải độ chính xác); overlay: {overlay}')
    counts = Counter(e['kind'] for e in events)
    for kind, n in counts.items(): print(f'    {kind}: {n}')
    for e in events:
        extra = f' (nảy 1 tại {e["bounces"][0]:.2f}s)' if e['kind'] == 'dead_ball_candidate' else ''
        print(f'    {e["time"]:7.2f}s  {e["kind"]}{extra}')
    (out/'summary.json').write_text(json.dumps(dict(
        video=str(path), duration=duration, rallies=rallies,
        court_cameras=meta['court_cameras'], observation_fraction=diag['observation_fraction'],
        events=events), indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    args = sys.argv[1:]
    roi = (0., 0., 1., 1.)
    if '--roi' in args:
        i = args.index('--roi')
        roi = tuple(float(v) for v in args[i+1].split(','))
        del args[i:i+2]
    if not args:
        raise SystemExit('Cách dùng: python reports/qc/danh_gia_video_that.py <video.mp4> ... [--roi x1,y1,x2,y2]')
    for arg in args:
        evaluate(arg, roi)
