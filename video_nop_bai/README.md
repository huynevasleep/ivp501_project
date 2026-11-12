# Video nộp bài (Remotion)

Video demo 1:48 (1080p) cho bài nộp Nhóm 03. Sửa tên/vai trò/mọi chữ trong `src/data.ts`.

```bash
cd video_nop_bai
npm install
npm run render        # ra out/nop_bai.mp4
```

**Chạy render từ Terminal thường** (Terminal.app/iTerm). Chrome headless không khởi động được
trong shell sandbox của một số app — triệu chứng: treo ở "Getting composition" rồi
`Target closed`.

Hai clip demo trong `public/` không commit (cắt từ YouTube Shorts, xem URL ở
`reports/qc/qc-rally-highlights.md` mục 6.2). Tạo lại từ thư mục gốc dự án:

```bash
.venv/bin/python - <<'EOF'
import subprocess, imageio_ffmpeg
exe = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([exe,'-y','-ss','1.5','-i','runs/qc_eval/short_00002_roi/evidence/ball_overlay.mp4','-t','10.5','-vf','scale=540:960','-c:v','libx264','-pix_fmt','yuv420p','-an','video_nop_bai/public/demo_overlay.mp4'],check=True)
subprocess.run([exe,'-y','-ss','3','-i','video_thu_nghiem/short_00001.mp4','-t','5','-vf','scale=540:960','-c:v','libx264','-pix_fmt','yuv420p','-an','video_nop_bai/public/demo_raw.mp4'],check=True)
EOF
```

(`runs/qc_eval/...` sinh bởi `reports/qc/danh_gia_video_that.py`; `video_thu_nghiem/` tải bằng yt-dlp.)

## Cảnh "Demo ứng dụng" (quay màn hình app thật)

`public/demo_app.mp4` (≈70 s) là bản quay Streamlit chạy clip 50 s của trận 67 phút, dựng lại với
phụ đề từng bước. Quay lại khi app đổi giao diện:

```bash
# 1. chạy app (terminal thường)
.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8599
# 2. quay bằng Chrome tự động (Playwright): ra runs/quay_demo/raw.webm + moc.json
.venv/bin/pip install playwright
.venv/bin/python video_nop_bai/quay_app.py video_thu_nghiem/demo_67p_50s.mp4 runs/quay_demo
# 3. dựng: phóng 1080p, tua nhanh đoạn chờ, in phụ đề theo moc.json
.venv/bin/python video_nop_bai/dung_demo_app.py runs/quay_demo video_nop_bai/public/demo_app.mp4
```

Clip đầu vào `video_thu_nghiem/demo_67p_50s.mp4` = `match2.mp4` (youtu.be/pthJ1IQPqGE) từ 735,7 s,
dài 50,3 s, thu 1280×720 — hai pha trọn + khoảng nghỉ, chọn vì kết quả trên clip trùng kết quả trên
cả trận (lệch mốc < 4 s). Nếu `SCENES.appDemo` trong `src/Main.tsx` không khớp thời lượng clip, cập nhật.
