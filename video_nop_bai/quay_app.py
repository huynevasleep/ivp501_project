"""Quay video demo ỨNG DỤNG đang chạy (Streamlit) bằng trình duyệt tự động Playwright.

Cần: app đang chạy (`.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8599`),
      `.venv/bin/pip install playwright` và Google Chrome (dùng Chrome thật để phát được H.264).
Chạy:  .venv/bin/python video_nop_bai/quay_app.py <video_dau_vao.mp4> <thu_muc_ra>
Ra:    <thu_muc_ra>/raw.webm (quay thô) + moc.json (mốc thời gian từng bước, để dựng/tua nhanh).
Chạy từ Terminal thường: trình duyệt không khởi động được trong shell sandbox của một số app.
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = 'http://localhost:8599'
RW, RH = 1600, 900


def main(video, out):
    video, out = Path(video).resolve(), Path(out); out.mkdir(parents=True, exist_ok=True)
    marks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        # Quay ở 1600×900 rồi phóng lên 1920×1080 khi dựng: chữ giao diện to hơn quay thẳng 1920.
        # (device_scale_factor không giúp được: Playwright không phóng khung hình theo nó, và khung
        # hẹp hơn thì panel quyết định bóp trình phát video còn ô nhỏ.)
        ctx = browser.new_context(viewport={'width': RW, 'height': RH}, record_video_dir=str(out),
                                  record_video_size={'width': RW, 'height': RH})
        page = ctx.new_page()
        t0 = time.time()
        mark = lambda name: (marks.append((name, round(time.time()-t0, 2))), print(f'{time.time()-t0:6.1f}s  {name}', flush=True))
        pause = lambda ms: page.wait_for_timeout(ms)

        page.goto(URL); page.wait_for_selector('text=VideoLens', timeout=60000); pause(2500); mark('mo_app')
        page.get_by_text('Phòng thí nghiệm: baseline / video khác').click(); pause(2500)
        page.locator('input[type=file]').first.set_input_files(str(video))
        page.wait_for_selector(f'text={video.name}', timeout=120000); pause(2000); mark('tai_video')

        page.locator('input[aria-label="Loại video"]').click(); pause(1500)
        page.get_by_role('option', name='Thể thao có pha bóng (pickleball, tennis…)').click(); pause(2500)
        page.wait_for_selector('text=Lấy toàn bộ pha bóng', timeout=10000); mark('chon_che_do')

        page.get_by_role('button', name='Phân tích & tạo highlight').click(); mark('bat_dau_phan_tich')
        page.wait_for_selector('text=Độ dài bản tóm tắt', timeout=900000); mark('xong_phan_tich'); pause(3500)
        try:                                   # thu gọn thanh bên: kết quả chiếm trọn chiều ngang
            page.get_by_test_id('stSidebarCollapseButton').locator('button').click(force=True, timeout=5000)
        except Exception as e:
            print('Không thu gọn được thanh bên:', e)
        pause(2000); mark('thu_gon_thanh_ben')

        frame_el = page.locator('iframe').first
        frame_el.scroll_into_view_if_needed(); pause(1500); mark('trinh_phat')
        f = page.frame_locator('iframe').first
        f.locator('#v').evaluate('v => { v.muted = true; v.play(); }'); pause(7000); mark('phat_highlight')

        f.locator('#dbgbtn').click(); pause(3000); mark('debug')
        for view, name in (('canny', 'canny'), ('match', 'khop_khuon'), ('ball', 'duong_bong'), ('gray', 'xam')):
            f.locator(f'.tabs button[data-v={view}]').click(); pause(3500); mark(name)
        f.locator('#next').click(); pause(800)
        f.locator('#v').evaluate('v => { v.muted = true; v.play(); }'); pause(7000); mark('pha_sau')
        f.locator('#dbgbtn').click(); pause(1500)
        f.locator('#v').evaluate('v => v.pause()')

        page.get_by_text('Ảnh cầu thủ lúc vung vợt').scroll_into_view_if_needed(); pause(3500)
        page.mouse.wheel(0, 350); pause(2500); mark('anh_cau_thu')
        page.get_by_role('tab', name='📊 Phân tích').scroll_into_view_if_needed(); pause(800)
        page.get_by_role('tab', name='📊 Phân tích').click(); pause(3500); mark('tab_phan_tich')
        page.mouse.wheel(0, 500); pause(3500)
        page.keyboard.press('Home'); pause(2000); mark('ket_thuc')

        ctx.close()
        raw = Path(page.video.path())
        browser.close()
    raw.replace(out/'raw.webm')
    (out/'moc.json').write_text(json.dumps(dict(marks), indent=2, ensure_ascii=False), encoding='utf-8')
    print('Xong:', out/'raw.webm')


if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(*sys.argv[1:])
