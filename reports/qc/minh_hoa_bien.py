"""Minh họa TỪNG BƯỚC detect biên và nhận camera sân trên khung hình thật.

Sinh hai hình cho báo cáo (ảnh gốc → kết quả từng bước, kèm con số đo thật):
  reports/qc/img/canny_tung_buoc.png    — gốc → xám → Gauss 3×3 → Canny; so sánh Prewitt/Sobel/Canny
  reports/qc/img/khuon_bien_va_dice.png — khuôn biên trung vị → vạch Hough → so khớp Dice (sân vs video khác)

Chạy:  .venv/bin/pip install matplotlib   (chỉ cần cho script này)
       .venv/bin/python reports/qc/minh_hoa_bien.py video_thu_nghiem/short_00002.mp4 video_thu_nghiem/short_00001.mp4
Tham số 1: video chính (dùng làm khuôn biên); tham số 2: video đối chứng (phải cho Dice thấp).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

from core import _edges, court_cameras, edge_dice, _TOLERANCE

OUT = Path(__file__).parent/'img'
FS = 11


def sample_frames(path, n=24):
    """n khung rải đều toàn video, thu về 320×180 như pipeline thật."""
    cap = cv2.VideoCapture(str(path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for i in np.linspace(0, total-1, n).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
        ok, frame = cap.read()
        if ok: frames.append(cv2.resize(frame, (320, 180)))
    cap.release()
    if not frames: raise SystemExit(f'Không đọc được {path}')
    return frames


def gradient_edges(gray, kx, ky, cut):
    """Biên theo gradient (Prewitt/Sobel): căn bậc hai tổng bình phương hai hướng, nén log, lấy ngưỡng."""
    g = gray.astype(np.float64)
    gx = cv2.filter2D(g, -1, kx, borderType=cv2.BORDER_REPLICATE)
    gy = cv2.filter2D(g, -1, ky, borderType=cv2.BORDER_REPLICATE)
    mag = np.log1p(gx**2 + gy**2)
    return mag/mag.max() > cut


def show(ax, image, title, cmap=None):
    ax.imshow(image, cmap=cmap)
    ax.set_title(title, fontsize=FS)
    ax.axis('off')


def main(main_video, other_video):
    OUT.mkdir(exist_ok=True)
    frames = sample_frames(main_video)
    others = sample_frames(other_video)
    frame = frames[len(frames)//2]                      # khung đại diện giữa video
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    canny = cv2.Canny(blur, 50, 150)

    # ---------- Hình 1: gốc → xám → Gauss → Canny, và Prewitt/Sobel/Canny ----------
    pv = np.array([[-1, 0, 1]]*3, np.float64); ph = pv.T
    sx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.float64); sy = sx.T
    prewitt = gradient_edges(blur, ph, pv, .25)
    sobel = gradient_edges(blur, sx, sy, .25)

    fig, axes = plt.subplots(2, 4, figsize=(14, 6.6))
    show(axes[0, 0], cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), '(a) Ảnh gốc 320×180')
    show(axes[0, 1], gray, '(b) Ảnh xám', 'gray')
    show(axes[0, 2], blur, '(c) Giảm nhiễu Gauss 3×3', 'gray')
    show(axes[0, 3], canny, '(d) Biên Canny 50/150', 'gray')
    show(axes[1, 0], np.abs(cv2.absdiff(gray, blur)) > 2, '(e) Pixel bị Gauss thay đổi (>2 mức)', 'gray')
    show(axes[1, 1], prewitt, '(f) Prewitt (ngưỡng 0,25)', 'gray')
    show(axes[1, 2], sobel, '(g) Sobel (ngưỡng 0,25)', 'gray')
    show(axes[1, 3], canny > 0, '(h) Canny: biên mảnh 1 px, ít đứt', 'gray')
    fig.suptitle(f'Detect biên từng bước trên khung thật ({Path(main_video).name})', fontsize=FS+2)
    fig.tight_layout()
    fig.savefig(OUT/'canny_tung_buoc.png', dpi=150)
    print('OK', OUT/'canny_tung_buoc.png')

    # ---------- Hình 2: khuôn biên → Hough → so khớp Dice (đúng pipeline: cụm K-means trước) ----------
    def layout(f):
        return cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2LAB), (16, 9), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
    edge_maps = [_edges(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)) for f in frames]
    packed = np.array([np.packbits(e) for e in edge_maps])
    k = min(12, len(frames))
    camera = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(np.array([layout(f) for f in frames]))
    score, court_ids, _, _ = court_cameras(packed, camera)
    best = max(court_ids, key=lambda c: (camera == c).sum())           # cụm sân đông khung nhất
    members = np.flatnonzero(camera == best)
    template = np.mean([edge_maps[i] for i in members], axis=0) >= .5
    template_wide = cv2.dilate(template.astype(np.uint8), _TOLERANCE) > 0

    hough = cv2.cvtColor((template*255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    lines = cv2.HoughLinesP((template*255).astype(np.uint8), 1, np.pi/180, 30, minLineLength=64, maxLineGap=4)
    n_lines = 0 if lines is None else len(lines)
    for l in (lines if lines is not None else [])[:60]:
        x1, y1, x2, y2 = l[0]
        on_court = (y1+y2)/2 > template.shape[0]*.45       # nửa dưới khung = vạch sân/lưới
        cv2.line(hough, (x1, y1), (x2, y2), (0, 220, 0) if on_court else (150, 150, 150), 2)

    def match_vis(test_frame):
        e = _edges(cv2.cvtColor(test_frame, cv2.COLOR_BGR2GRAY))
        dice = edge_dice(e, template, template_wide)
        vis = np.zeros((180, 320, 3), np.uint8)
        vis[template] = (90, 90, 90)                                   # khuôn: xám
        vis[e & template_wide] = (0, 255, 0)                           # khớp khuôn: xanh
        vis[e & ~template_wide] = (255, 60, 60)                        # lệch khuôn: đỏ
        return vis, dice

    vis_same, dice_same = match_vis(frames[members[len(members)//2]])  # khung thuộc cụm sân
    vis_other, dice_other = match_vis(others[len(others)//2])          # khung của video đối chứng

    fig, axes = plt.subplots(1, 4, figsize=(16, 3.9))
    show(axes[0], template, f'(a) Khuôn biên cụm sân\n(trung vị {len(members)} bản đồ biên của cụm)', 'gray')
    show(axes[1], cv2.cvtColor(hough, cv2.COLOR_BGR2RGB), f'(b) {n_lines} đoạn thẳng ổn định trên khuôn\nxanh = vạch sân/lưới (nửa dưới), xám = cấu trúc khác')
    show(axes[2], vis_same, f'(c) Khung cùng camera sân\nDice = {dice_same:.2f} → nhận')
    show(axes[3], vis_other, f'(d) Khung của video khác\nDice = {dice_other:.2f} → loại')
    fig.suptitle('Nhận camera sân như pipeline thật: khuôn biên theo cụm, vạch Hough, so khớp Dice (xanh = khớp khuôn, đỏ = lệch)', fontsize=FS+2)
    fig.tight_layout()
    fig.savefig(OUT/'khuon_bien_va_dice.png', dpi=150)
    print('OK', OUT/'khuon_bien_va_dice.png')
    print(f'Cụm sân: {len(court_ids)}/{k}; Dice cùng camera = {dice_same:.3f}; video khác = {dice_other:.3f}; Hough = {n_lines}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
