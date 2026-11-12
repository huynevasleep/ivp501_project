"""Dựng clip demo app từ bản quay thô: phóng lên 1080p, bỏ bớt khoảng chờ, thêm phụ đề từng bước.

Chạy:  .venv/bin/python video_nop_bai/dung_demo_app.py runs/quay_demo video_nop_bai/public/demo_app.mp4
Dùng moc.json (mốc từng bước của quay_app.py) để cắt và đặt phụ đề; không cần font: vẽ bằng drawtext
của FFmpeg với font hệ thống hỗ trợ tiếng Việt.
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

FONT = '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'

# (mốc bắt đầu, mốc kết thúc, phụ đề). Khoảng không liệt kê bị cắt (chờ phân tích, cuộn chuột).
SCRIPT = [
    ('mo_app', 'tai_video', 'Mở VideoLens, chọn video trận đấu (clip 50 s từ trận 67 phút)'),
    ('tai_video', 'bat_dau_phan_tich', 'Chọn loại video “Thể thao có pha bóng”, lấy toàn bộ pha'),
    ('bat_dau_phan_tich', 'xong_phan_tich', 'Phân tích: Canny → khuôn biên → Hough → Otsu âm lượng (tua nhanh)'),
    ('xong_phan_tich', 'trinh_phat', 'Kết quả: 50,3 s → 2 pha → highlight 32 s'),
    ('trinh_phat', 'debug', 'Trình phát highlight + panel “Code đang quyết định gì?” (đường bóng vẽ trên video)'),
    ('debug', 'canny', 'Debug: ảnh xám đúng khung mà code đã quyết định'),
    ('canny', 'khop_khuon', 'Bản đồ biên Canny (nhị phân)'),
    ('khop_khuon', 'duong_bong', 'Khớp khuôn: xanh = biên trùng khuôn, đỏ = lệch; Dice + không gian Hough'),
    ('duong_bong', 'xam', 'Đường bóng: ứng viên nảy / chạm vợt (chưa dùng để cắt pha)'),
    ('xam', 'pha_sau', 'Pha sau ▶ — camera sân, âm lượng và dòng thời gian cập nhật theo'),
    ('pha_sau', 'anh_cau_thu', 'Ảnh cầu thủ lúc vung vợt (trừ nền MOG2, chọn khung nét nhất)'),
    ('anh_cau_thu', 'ket_thuc', 'Tab Phân tích: điểm từng pha và đóng góp của từng tín hiệu'),
]
SPEEDUP = {'bat_dau_phan_tich': 4.0}     # tua nhanh đoạn chờ phân tích


def esc(s):
    return s.replace('\\', '\\\\').replace(':', '\\:').replace("'", "’").replace('%', '\\%')


def main(raw_dir, out):
    raw_dir, out = Path(raw_dir), Path(out)
    marks = json.loads((raw_dir/'moc.json').read_text(encoding='utf-8'))
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    parts = []
    for i, (a, b, text) in enumerate(SCRIPT):
        t0, t1 = marks[a], marks[b]
        if t1-t0 < .3: continue
        speed = SPEEDUP.get(a, 1.0)
        p = raw_dir/f'part_{i:02d}.mp4'
        box = (f"drawbox=x=0:y=ih-92:w=iw:h=92:color=black@0.62:t=fill,"
               f"drawtext=fontfile='{FONT}':text='{esc(text)}':fontcolor=white:fontsize=34:x=40:y=h-64,"
               f"drawtext=fontfile='{FONT}':text='Bước {i+1}/{len(SCRIPT)}':fontcolor=#ffd34d:fontsize=24:x=w-tw-40:y=h-60")
        vf = f"scale=1920:1080:flags=lanczos,setpts=PTS/{speed},{box},fps=30"
        subprocess.run([exe, '-v', 'error', '-y', '-ss', str(t0), '-to', str(t1), '-i', str(raw_dir/'raw.webm'),
                        '-vf', vf, '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p', str(p)], check=True)
        parts.append(p)
    lst = raw_dir/'concat.txt'
    lst.write_text('\n'.join(f"file '{p.resolve()}'" for p in parts), encoding='utf-8')
    subprocess.run([exe, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', '-movflags', '+faststart', str(out)], check=True)
    r = subprocess.run([exe, '-i', str(out)], capture_output=True, text=True)
    print('Xong:', out, [l.strip() for l in r.stderr.splitlines() if 'Duration' in l][0])


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(*sys.argv[1:])
