"""Ví dụ ĐẦU-CUỐI: một video trận đấu → các bước xử lý → video highlight, kèm ảnh từng bước.

Chạy:  .venv/bin/python reports/qc/vi_du_dau_cuoi.py video_thu_nghiem/match_11p.mp4 runs/vi_du_dau_cuoi
In ra: thời lượng gốc, số pha, tổng thời lượng highlight (giữ toàn bộ pha) và bản 25%.
Sinh:  <out>/highlight/summary.mp4 (toàn bộ pha) và bộ ảnh từng bước trong <out>/steps/:
  b1_goc.png  b2_canny.png  b3_khuon.png  b4_hough.png  b5_am_luong.png  b6_dong_thoi_gian.png  b8_ket_qua.png
Cần matplotlib (pip install matplotlib). Mọi bước dùng đúng hàm của pipeline (core.py).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core import _edges, analyze, detect_rallies, export_video, otsu_threshold, select


def save(path, image, color=False):
    cv2.imwrite(str(path), image if color else (image.astype(np.uint8)*255 if image.dtype == bool else image))
    print('OK', path)


def main(video, out):
    video, out = Path(video), Path(out)
    steps = out/'steps'; steps.mkdir(parents=True, exist_ok=True)

    print('— Phân tích (lấy mẫu 2 khung/giây)…')
    df, meta = analyze(video, out/'analysis')
    rallies = detect_rallies(df, meta)
    chosen, _ = select(df, meta, ratio=1., mode='rally')
    total = sum(r['end']-r['start'] for r in chosen)
    print(f'— Video {meta["duration"]/60:.1f} phút → {len(rallies)} pha → highlight toàn bộ pha: '
          f'{total/60:.1f} phút ({total/meta["duration"]:.0%} thời lượng gốc)')
    quarter, _ = select(df, meta, ratio=.25, mode='rally')
    q_total = sum(r['end']-r['start'] for r in quarter)
    print(f'— Bản 25%: {len(quarter)} pha, {q_total/60:.1f} phút')

    print('— Xuất video highlight…')
    export_video(video, chosen, out/'highlight')

    # ---------- ảnh từng bước ----------
    court = (df.court_score > meta['court_threshold']).to_numpy()
    cluster = df.loc[court, 'camera'].mode().iloc[0]                 # cụm sân đông khung nhất
    members = df.index[(df.camera == cluster) & court].to_numpy()
    rep = members[len(members)//2]

    frame = cv2.imread(str(out/'analysis'/df.image.iloc[rep]))
    save(steps/'b1_goc.png', frame, color=True)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    save(steps/'b2_canny.png', _edges(gray))

    picks = members[np.linspace(0, len(members)-1, min(40, len(members))).astype(int)]
    maps = [_edges(cv2.cvtColor(cv2.imread(str(out/'analysis'/df.image.iloc[i])), cv2.COLOR_BGR2GRAY)) for i in picks]
    template = np.mean(maps, axis=0) >= .5
    save(steps/'b3_khuon.png', template)
    hough_img = cv2.cvtColor((template*255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    lines = cv2.HoughLinesP((template*255).astype(np.uint8), 1, np.pi/180, 30, minLineLength=64, maxLineGap=4)
    for l in (lines if lines is not None else [])[:80]:
        x1, y1, x2, y2 = l[0]; cv2.line(hough_img, (x1, y1), (x2, y2), (0, 220, 0), 2)
    save(steps/'b4_hough.png', hough_img, color=True)
    print(f'— Khuôn biên cụm {cluster}: {int(template.sum())} điểm, {0 if lines is None else len(lines)} vạch Hough')

    loud = df.loudness_db.to_numpy(); finite = loud[np.isfinite(loud)]
    cut = otsu_threshold(finite) if len(finite) else None
    if cut is not None:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.hist(finite, bins=60, color='#f2b705')
        ax.axvline(cut, color='k', ls='--', label=f'Ngưỡng Otsu {cut:.1f} dBFS')
        ax.set_xlabel('Âm lượng (dBFS)'); ax.set_ylabel('Số khung mẫu'); ax.legend(fontsize=9)
        fig.tight_layout(); fig.savefig(steps/'b5_am_luong.png', dpi=150); plt.close(fig)
        print('OK', steps/'b5_am_luong.png')
    else:
        print('— Video không có âm thanh: bỏ qua biểu đồ âm lượng (tách pha chỉ dùng camera sân).')

    t = df.time.to_numpy()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 3.4), sharex=True, height_ratios=[1, 3])
    a1.fill_between(t, 0, 1, where=court, color='#2e8b57', step='mid'); a1.set_ylabel('camera\nsân', fontsize=8)
    a1.set_yticks([])
    if len(finite): a2.plot(t, loud, lw=.4, color='#444')
    if cut is not None: a2.axhline(cut, color='k', ls='--', lw=.8)
    for r in rallies: a2.axvspan(r['start'], r['end'], color='#f6d78b', alpha=.8)
    a2.set_xlabel('giây'); a2.set_ylabel('dBFS')
    a2.set_xlim(0, float(meta['duration']))
    fig.suptitle('Vàng = pha tách được (đã đệm); dải xanh trên = camera sân', fontsize=9)
    fig.tight_layout(); fig.savefig(steps/'b6_dong_thoi_gian.png', dpi=150); plt.close(fig)
    print('OK', steps/'b6_dong_thoi_gian.png')

    grid = [cv2.imread(str(out/'analysis'/r['keyframe'])) for r in sorted(rallies, key=lambda r: -(r['core_end']-r['core_start']))[:4]]
    if len(grid) == 4:
        save(steps/'b8_ket_qua.png', np.vstack([np.hstack(grid[:2]), np.hstack(grid[2:])]), color=True)

    (out/'ket_qua.json').write_text(json.dumps(dict(
        video=str(video), duration_minutes=meta['duration']/60, rallies=len(rallies),
        highlight_all_minutes=total/60, kept_fraction=total/meta['duration'],
        quarter_rallies=len(quarter), quarter_minutes=q_total/60,
        segments=[(r['start'], r['end']) for r in chosen]), indent=2), encoding='utf-8')
    print('— Xong. Kết quả:', out/'ket_qua.json')


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
