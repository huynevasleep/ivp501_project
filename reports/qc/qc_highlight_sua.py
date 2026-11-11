"""Thử các phương án SỬA trên chính các mẫu QC đã gán nhãn (nhan.csv của qc_highlight_mau.py).

Chạy:  .venv/bin/python reports/qc/qc_highlight_sua.py runs/match67_v2/analysis runs/qc_mau/nhan.csv

Mỗi mẫu lỗi có một "điểm cắt" (đầu/cuối/chỗ chặt đôi) hoặc các thời điểm đang đánh bị sót.
Một phương án "vá" lỗi khi điểm đó nằm gọn trong MỘT đoạn của phương án (có lề 1–2 s).
Hồi quy: mẫu DUNG bị mất/tách, hoặc khoảng LOAI_DUNG bị phủ ở các khung giữa (cận mặt/replay),
hoặc đoạn dài bất thường (> 90 s, ứng viên gộp nhiều pha). Kèm số đoạn và tổng phút highlight.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from core import _runs, court_mask, detect_rallies, quiet_mask

# thời điểm ĐANG ĐÁNH bị sót, đọc từ ảnh khoang_*.png
SOT = {'K01': [87.0, 106.8], 'K06': [924.6, 926.9]}


def hybrid(df, meta, min_quiet=1.5):
    """Đoạn camera sân liên tục (có hysteresis), giữ đoạn nào chứa >= min_quiet giây khán giả im."""
    step = 1/meta['sample_fps']; t = df.time.to_numpy()
    court = court_mask(df, meta); quiet, _ = quiet_mask(df)
    out = []
    for a, b in _runs(court):
        if quiet[a:b].sum()*step >= min_quiet and (b-a)*step >= 1.5:
            out.append(dict(start=float(t[a]), end=float(min(t[b-1]+step, meta['duration']))))
    return out


def configs(df, meta):
    return {
        # Tham số ghim tường minh: bảng phải tái lập được dù mặc định của detect_rallies đổi.
        'A cũ (âm thanh, lấp 1s, đệm 1s)': detect_rallies(df, meta, gap=1., pre=1.),
        'B âm thanh, lấp 3s': detect_rallies(df, meta, gap=3., pre=1.),
        'C âm thanh, lấp 5s': detect_rallies(df, meta, gap=5., pre=1.),
        'D chỉ camera sân': detect_rallies(df, meta, use_audio=False, gap=1., pre=1.),
        'E camera sân + có ≥1,5s im': hybrid(df, meta),
        'F ĐÃ CHỌN (lấp 5s, đệm 3s)': detect_rallies(df, meta, gap=5., pre=3.),
    }


def cover(segs, a, b):
    """Có một đoạn phủ trọn [a, b]?"""
    return any(s['start'] <= a and s['end'] >= b for s in segs)


def covered(segs, t):
    return any(s['start'] <= t < s['end'] for s in segs)


def evaluate(segs, lab):
    fixed, broken, total_err = 0, 0, 0
    for r in lab.itertuples():
        a, b = r.start, r.end
        if r.nhan in ('CAT_DAU', 'TACH_DOI', 'TRE_GIAO'):
            total_err += 1; fixed += cover(segs, a-2, a+1)
        elif r.nhan == 'CAT_DUOI':
            total_err += 1; fixed += cover(segs, b-1, b+2)
        elif r.nhan == 'CAT_HAI_DAU':
            total_err += 1; fixed += cover(segs, a-2, b+2)
        elif r.nhan == 'SOT_PHA':
            total_err += 1; fixed += all(covered(segs, t) for t in SOT[r.ma])
        elif r.nhan == 'KHONG_PHAI_PHA':
            total_err += 1; fixed += not covered(segs, (a+b)/2)
        elif r.nhan == 'DUNG':
            broken += not cover(segs, a+.5, b-.5)
        elif r.nhan == 'LOAI_DUNG':
            mids = [a+(b-a)*q for q in (.38, .62)]
            broken += any(covered(segs, t) for t in mids)
    return fixed, total_err, broken


def main(analysis, csv):
    df = pd.read_csv(Path(analysis)/'features.csv')
    meta = json.loads((Path(analysis)/'metadata.json').read_text(encoding='utf-8'))
    lab = pd.read_csv(csv)
    n_ok = (lab.nhan == 'DUNG').sum() + (lab.nhan == 'LOAI_DUNG').sum()
    rows = []
    for name, segs in configs(df, meta).items():
        fixed, total_err, broken = evaluate(segs, lab)
        dur = sum(s['end']-s['start'] for s in segs)
        rows.append(dict(phuong_an=name, vá=f'{fixed}/{total_err}', hong=f'{broken}/{n_ok}', so_doan=len(segs),
                         phut=round(dur/60, 1), ty_le=f'{dur/meta["duration"]:.0%}',
                         doan_qua_90s=sum(s['end']-s['start'] > 90 for s in segs)))
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    out.to_csv(Path(csv).parent/'phuong_an_sua.csv', index=False)


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(*sys.argv[1:])
