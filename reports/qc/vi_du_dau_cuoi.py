"""Ví dụ ĐẦU-CUỐI: một video trận đấu → các bước xử lý → video highlight, kèm ảnh từng bước.

Chạy:  .venv/bin/python reports/qc/vi_du_dau_cuoi.py video_thu_nghiem/match_11p.mp4 runs/vi_du_dau_cuoi [audio|court]
Chế độ (tham số 3, mặc định audio — từ QC 11/11 với gap=5, pre=3 chế độ âm thanh đủ bền trên video có BLV):
  court — tách pha CHỈ theo camera sân (use_audio=False): không bao giờ cắt giữa pha,
          chấp nhận giữ khoảng nghỉ. Dùng cho video có bình luận viên nói suốt lúc đánh
          (QC 10/11: chế độ audio cắt pha 51→55,5 s dù trận còn đánh tới ~70 s).
  audio — thêm điều kiện khán giả im (mặc định của pipeline, cho phát sóng khán giả im khi đánh).
In ra số của CẢ HAI chế độ để so sánh; xuất highlight + ảnh từng bước theo chế độ đã chọn.
Phân tích được tái dùng nếu <out>/analysis/features.csv đã có. Cần matplotlib.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core import _edges, analyze, detect_rallies, export_video, knapsack_select, otsu_threshold


def save(path, image, color=False):
    cv2.imwrite(str(path), image if color else (image.astype(np.uint8)*255 if image.dtype == bool else image))
    print('OK', path)


def main(video, out, mode='audio'):
    video, out = Path(video), Path(out)
    steps = out/'steps'; steps.mkdir(parents=True, exist_ok=True)

    analysis = out/'analysis'
    if (analysis/'features.csv').exists():
        print('— Dùng lại phân tích có sẵn trong', analysis)
        df = pd.read_csv(analysis/'features.csv')
        meta = json.loads((analysis/'metadata.json').read_text(encoding='utf-8'))
    else:
        print('— Phân tích (lấy mẫu 2 khung/giây)…')
        df, meta = analyze(video, analysis)

    both = {m: detect_rallies(df, meta, use_audio=(m == 'audio')) for m in ('court', 'audio')}
    for m, rs in both.items():
        tt = sum(r['end']-r['start'] for r in rs)
        print(f'— Chế độ {m:5s}: {len(rs)} pha, {tt/60:.1f} phút ({tt/meta["duration"]:.0%} gốc)')
    rallies = both[mode]
    chosen = sorted(rallies, key=lambda r: r['start'])
    total = sum(r['end']-r['start'] for r in chosen)
    print(f'— Dùng chế độ "{mode}" cho highlight và ảnh từng bước.')
    quarter = knapsack_select(rallies, meta['duration']*.25)
    q_total = sum(r['end']-r['start'] for r in quarter)
    print(f'— Bản 25% ({mode}): {len(quarter)} pha, {q_total/60:.1f} phút')

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
    # Hough chỉ là CỔNG xác nhận "khuôn có đường thẳng ổn định". Hình minh họa tô hai màu
    # cho trung thực: xanh = đường ở nửa dưới khung (vạch sân, mép lưới); xám = cấu trúc
    # tĩnh khác (khung mái, mép băng rôn) — cũng là bằng chứng camera cố định.
    hough_img = cv2.cvtColor((template*255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    lines = cv2.HoughLinesP((template*255).astype(np.uint8), 1, np.pi/180, 30, minLineLength=64, maxLineGap=4)
    n_court = n_other = 0
    for l in sorted((lines if lines is not None else []), key=lambda l: (l[0][1]+l[0][3])/2)[:80]:
        x1, y1, x2, y2 = l[0]
        on_court = (y1+y2)/2 > template.shape[0]*.45
        n_court += on_court; n_other += not on_court
        cv2.line(hough_img, (x1, y1), (x2, y2), (0, 220, 0) if on_court else (150, 150, 150), 2)
    save(steps/'b4_hough.png', hough_img, color=True)
    print(f'— Khuôn biên cụm {cluster}: {int(template.sum())} điểm; Hough: {n_court} vạch sân/lưới (nửa dưới) + {n_other} cấu trúc tĩnh khác')

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
        video=str(video), mode=mode, duration_minutes=meta['duration']/60, rallies=len(rallies),
        highlight_all_minutes=total/60, kept_fraction=total/meta['duration'],
        quarter_rallies=len(quarter), quarter_minutes=q_total/60,
        modes={m: dict(rallies=len(rs), minutes=sum(r['end']-r['start'] for r in rs)/60) for m, rs in both.items()},
        segments=[(r['start'], r['end']) for r in chosen]), indent=2), encoding='utf-8')
    print('— Xong. Kết quả:', out/'ket_qua.json')


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4): raise SystemExit(__doc__)
    main(*sys.argv[1:])
