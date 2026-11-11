"""Thí nghiệm QC cho nhánh rally-highlight: ca biên của `court_cameras` (core.py).

Chạy:  .venv/bin/python reports/qc/qc_experiments.py
In ra PASS/FAIL cho từng ca; dùng cùng bộ sinh khung tổng hợp với tests/test_rally.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np

from core import _edges, court_cameras


def court_frame(rng, shift=0):
    """Khung camera sân cố định: vạch thẳng trên nền có vân; người chơi di chuyển."""
    img = (rng.random((180, 320))*30+60).astype(np.uint8)
    for y in (40, 90, 150):
        cv2.line(img, (20, y), (300, y), 255, 2)
    cv2.line(img, (20, 40), (20, 150), 255, 2)
    cv2.line(img, (300, 40), (300, 150), 255, 2)
    x = int(rng.integers(40, 260))
    cv2.rectangle(img, (x, 60+shift), (x+12, 100+shift), 200, -1)
    return cv2.GaussianBlur(img, (5, 5), 0)


def pack(frames):
    return np.array([np.packbits(_edges(f)) for f in frames])


def case(name, condition, detail):
    print(f'{"PASS" if condition else "FAIL"}: {name} — {detail}')
    return condition


def main():
    rng = np.random.default_rng(0)
    ok = True

    # Ca 1: video chỉ có MỘT camera sân, K-means vẫn ép thành 12 cụm (nhãn chia vòng).
    # Mong muốn: ít nhất một cụm được nhận là camera sân (video quay tay một góc là ca dùng thật).
    frames = [court_frame(rng) for _ in range(120)]
    camera = [i % 12 for i in range(120)]
    score, ids, _, _ = court_cameras(pack(frames), camera)
    ok &= case('một camera sân, 12 cụm nhân tạo', len(ids) > 0,
               f'cụm sân nhận được: {ids}; điểm khung min={score.min():.2f}')
    if len(ids):
        ok &= case('…và mọi khung đều vượt mức khớp cao', score.min() > .6,
                   f'score min={score.min():.2f} (toàn khung là sân thật)')

    # Ca 2: video một camera sân, K-means chỉ ra MỘT cụm (nhãn đồng nhất).
    # log_match một giá trị → Otsu trả về chính nó → so sánh "strictly greater" loại mọi cụm?
    score, ids, _, _ = court_cameras(pack(frames), [0]*120)
    ok &= case('một camera sân, một cụm duy nhất', len(ids) > 0,
               f'cụm sân nhận được: {ids} (rỗng nghĩa là 0 pha trên video một góc máy)')

    # Ca 3: không có camera sân nào (toàn cảnh quay tay) — không được nhận nhầm.
    moving = []
    for _ in range(60):
        img = np.zeros((180, 320), np.uint8)
        cx, cy = rng.integers(60, 260), rng.integers(40, 140)
        cv2.circle(img, (int(cx), int(cy)), int(rng.integers(20, 60)), 255, -1)
        moving.append(cv2.GaussianBlur(img, (5, 5), 0))
    score, ids, _, _ = court_cameras(pack(moving), [i % 4 for i in range(60)])
    ok &= case('toàn cảnh quay tay, không có sân', len(ids) == 0,
               f'cụm sân nhận được: {ids} (phải rỗng)')

    print('\nKết luận QC:', 'mọi ca đạt' if ok else 'CÓ CA KHÔNG ĐẠT — xem FAIL ở trên')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
