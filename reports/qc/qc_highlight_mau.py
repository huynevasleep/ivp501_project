"""QC video highlight KHÔNG cần xem hết: lấy mẫu ngẫu nhiên có hạt giống cố định tại các mốc cắt.

Chạy:  .venv/bin/python reports/qc/qc_highlight_mau.py <video> <analysis_dir> <out_dir> [audio|court] [n_pha] [n_khoang] [seed]
Ví dụ: .venv/bin/python reports/qc/qc_highlight_mau.py video_thu_nghiem/match2.mp4 runs/match67_v2/analysis runs/qc_mau audio 30 15 7

Sinh trong <out_dir>:
  pha_01.png …  mỗi tấm 5 pha; mỗi pha một hàng 6 khung:
                [đầu−3s | ĐẦU | đầu+1,5s]   [cuối−1,5s | CUỐI | cuối+3s]
  khoang_01.png … mỗi tấm 5 khoảng BỊ LOẠI (giữa hai pha, ≥ 4 s); 4 khung ở 15/38/62/85% khoảng
  nhan.csv     bảng để người QC điền cột `nhan` (xem NHAN bên dưới)
Sau khi điền nhãn:  .venv/bin/python reports/qc/qc_highlight_mau.py --thong-ke <out_dir>/nhan.csv
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2
import numpy as np
import pandas as pd

from core import detect_rallies

NHAN = {
    # nhãn cho PHA
    'DUNG': 'đúng: có cú giao bóng ở đầu, điểm đã kết thúc ở cuối',
    'CAT_DAU': 'cắt đầu muộn: lúc bắt đầu bóng đã đang bay (mất cú giao bóng)',
    'CAT_DUOI': 'cắt đuôi sớm: sau mốc cuối vẫn đang đánh (pha bị chặt)',
    'CAT_HAI_DAU': 'cắt cả đầu lẫn đuôi: mảnh vụn giữa pha',
    'TRE_GIAO': 'pha còn nguyên nhưng bắt đầu trễ ~1 s: mất động tác giao bóng',
    'TACH_DOI': 'nửa sau của một pha bị chặt đôi: bắt đầu đúng mốc kết thúc của pha liền trước (hình liền nhưng đếm thừa 1 pha)',
    'KHONG_PHAI_PHA': 'không có giao tranh: nghỉ giữa điểm / cận mặt / replay / khán giả',
    'KHONG_RO': 'ảnh tĩnh không đủ phân biệt (vd. đang đánh hay replay) — cần xem clip',
    # nhãn cho KHOẢNG BỊ LOẠI
    'LOAI_DUNG': 'khoảng bị loại đúng: không có giao tranh',
    'SOT_PHA': 'sót: trong khoảng bị loại đang có giao tranh',
}
W, H = 240, 135


def grab(cap, t, fps):
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(round(t*fps))))
    ok, f = cap.read()
    return cv2.resize(f, (W, H)) if ok else np.zeros((H, W, 3), np.uint8)


def label(img, text, color=(255, 255, 255)):
    img = img.copy()
    cv2.rectangle(img, (0, 0), (W, 22), (0, 0, 0), -1)
    cv2.putText(img, text, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, .42, color, 1, cv2.LINE_AA)
    return img


def row_title(text, width):
    bar = np.full((26, width, 3), 40, np.uint8)
    cv2.putText(bar, text, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 220, 255), 1, cv2.LINE_AA)
    return bar


def make(video, analysis, out, mode='audio', n=30, n_gap=15, seed=7):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(Path(analysis)/'features.csv')
    meta = json.loads((Path(analysis)/'metadata.json').read_text(encoding='utf-8'))
    rallies = sorted(detect_rallies(df, meta, use_audio=(mode == 'audio')), key=lambda r: r['start'])
    total = sum(r['end']-r['start'] for r in rallies)
    print(f'{len(rallies)} pha, highlight {total/60:.1f} phút ({total/meta["duration"]:.0%}) — chế độ {mode}')
    rng = np.random.default_rng(seed)
    pick = sorted(rng.choice(len(rallies), min(n, len(rallies)), replace=False))
    gaps = [(a['end'], b['start']) for a, b in zip(rallies, rallies[1:]) if b['start']-a['end'] >= 4]
    gpick = sorted(rng.choice(len(gaps), min(n_gap, len(gaps)), replace=False))
    print(f'Lấy mẫu {len(pick)} pha và {len(gpick)}/{len(gaps)} khoảng bị loại (seed {seed})')

    cap = cv2.VideoCapture(str(video)); fps = cap.get(cv2.CAP_PROP_FPS)
    rows, table = [], []
    for k, i in enumerate(pick, 1):
        r = rallies[i]; a, b = r['start'], r['end']
        g = (160, 160, 160); y = (0, 255, 255)
        shots = [(a-3, 'dau-3', g), (a-1, 'dau-1', g), (a, 'DAU', y), (a+1.5, 'dau+1.5', g),
                 (b-1.5, 'cuoi-1.5', g), (b, 'CUOI', y), (b+1.5, 'cuoi+1.5', g), (b+4, 'cuoi+4', g)]
        strip = np.hstack([label(grab(cap, t, fps), f'{txt} {t:.1f}s', c) for t, txt, c in shots])
        rows.append(np.vstack([row_title(f'P{k:02d}  pha #{i+1}/{len(rallies)}  [{a:.1f} -> {b:.1f}s]  dai {b-a:.1f}s', strip.shape[1]), strip]))
        table.append(dict(ma=f'P{k:02d}', loai='pha', start=round(a, 1), end=round(b, 1), dai=round(b-a, 1), nhan='', ghi_chu=''))
    for s in range(0, len(rows), 5):
        cv2.imwrite(str(out/f'pha_{s//5+1:02d}.png'), np.vstack(rows[s:s+5]))

    grows = []
    for k, i in enumerate(gpick, 1):
        a, b = gaps[i]
        strip = np.hstack([label(grab(cap, a+(b-a)*q, fps), f'{int(q*100)}%  {a+(b-a)*q:.1f}s') for q in (.15, .38, .62, .85)])
        grows.append(np.vstack([row_title(f'K{k:02d}  khoang bi loai [{a:.1f} -> {b:.1f}s]  dai {b-a:.1f}s', strip.shape[1]), strip]))
        table.append(dict(ma=f'K{k:02d}', loai='khoang', start=round(a, 1), end=round(b, 1), dai=round(b-a, 1), nhan='', ghi_chu=''))
    for s in range(0, len(grows), 5):
        cv2.imwrite(str(out/f'khoang_{s//5+1:02d}.png'), np.vstack(grows[s:s+5]))
    cap.release()

    pd.DataFrame(table).to_csv(out/'nhan.csv', index=False)
    (out/'cau_hinh.json').write_text(json.dumps(dict(video=str(video), mode=mode, seed=seed, rallies=len(rallies),
        highlight_minutes=total/60, sampled_rallies=len(pick), sampled_gaps=len(gpick), gaps_total=len(gaps),
        nhan=NHAN), indent=2, ensure_ascii=False), encoding='utf-8')
    print('Xong:', out)


def thong_ke(csv):
    t = pd.read_csv(csv)
    csv = Path(csv)
    cfg_path = next(p for p in (csv.parent/'cau_hinh.json', csv.parent/(csv.stem.replace('_nhan', '')+'_cau_hinh.json')) if p.exists())
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    for kind in ('pha', 'khoang'):
        sub = t[t.loai == kind]
        if sub.empty: continue
        print(f'\n{kind.upper()} — {len(sub)} mẫu')
        for lab, cnt in sub.nhan.value_counts().items():
            p = cnt/len(sub)
            se = np.sqrt(p*(1-p)/len(sub))
            print(f'  {lab:15s} {cnt:3d}  {p:5.0%}  (±{1.96*se:.0%} khoảng tin cậy 95%)  — {NHAN.get(lab, "")}')
    print(f'\nSuy ra cho toàn bộ {cfg["rallies"]} pha của highlight {cfg["highlight_minutes"]:.1f} phút (chế độ {cfg["mode"]}).')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--thong-ke':
        thong_ke(sys.argv[2])
    elif len(sys.argv) >= 4:
        a = sys.argv[1:]
        make(a[0], a[1], a[2], *(a[3:4] or ['audio']), *[int(x) for x in a[4:7]])
    else:
        raise SystemExit(__doc__)
