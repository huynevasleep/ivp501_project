# [BẢN NHÁP NỘI DUNG] Báo cáo nộp bài — đổ vào template khi có

*Nhóm 03 · Lê Hữu Huy · Nguyễn Xuân Kha · Nguyễn Hồ Công Anh · Đoàn Nguyễn Tuấn Anh*
*IVP501 — Xử lý Ảnh và Video số · Đề tài 10 · 11/2026*

> File này là nội dung đã tổng hợp từ `reports/anhnhc/tach-pha-bong.md`, `reports/project-audit.md` và `reports/qc/qc-rally-highlights.md`, sắp theo bố cục báo cáo học phần điển hình. Khi có template chính thức: giữ nguyên chữ, đổi khung.

## 1. Giới thiệu bài toán

Đầu vào là video quay một trận pickleball (phát sóng hoặc tự quay). Nhóm giải ba bài toán:

1. **Xác định pha bóng**: tìm timecode bắt đầu (cú giao bóng) và kết thúc (bóng chết: chạm sàn mà không còn cú chạm vợt nào sau đó — luật hai lần nảy, bóng ra ngoài, hoặc vào lưới) của từng pha.
2. **Ghép toàn bộ pha thành video highlight**, mỗi pha lấy trọn vẹn, kèm bảng timecode video gốc → highlight.
3. **(Mở rộng) Ảnh vận động viên góc ngang**: chọn khoảnh khắc vung vợt, khử nhiễu, tăng nét, giảm mờ.

Ràng buộc nhóm tự đặt: chỉ dùng kỹ thuật xử lý ảnh kinh điển chạy CPU (không mô hình học sâu), mọi ngưỡng chọn tự động theo từng video, mọi con số trong báo cáo kèm lệnh chạy lại.

Lưu ý nghiệp vụ quan trọng: pickleball có **luật hai lần nảy** nên "bóng chạm sàn" chưa chắc hết pha, và **đài đổi góc máy giữa pha** (61/154 pha của trận thử) nên "chuyển cảnh" cũng không phải ranh giới pha.

## 2. Phương pháp

### 2.1 Tách pha bóng từ video phát sóng (pipeline chính)

Nhận xét then chốt: trong lúc giao tranh, (a) đài luôn dùng **camera cố định quay toàn sân**, và (b) **khán giả im lặng**, hết điểm mới reo. Pha bóng = camera sân đang lên hình ∧ khán giả im. Các bước (code: `core.py`):

| # | Bước | Kỹ thuật (bài học Colab) |
|---|---|---|
| 1 | Lấy mẫu 2 khung/giây, thu 320×180 | Lấy mẫu (Bài 1) |
| 2 | Lọc Gauss 3×3 (giảm nhiễu) → bản đồ biên Canny 50/150 | Canny (Bài 7, Ex7_3) |
| 3 | Gom 12 cụm góc máy bằng K-means trên bố cục màu Lab 16×9 | Phân cụm; Lab gần cảm nhận mắt |
| 4 | Khuôn biên mỗi cụm = trung vị bản đồ biên; độ khớp khung–khuôn = Dice hai chiều (recall/precision, dung sai giãn nở 1 px) | Hình thái học (Bài 6) |
| 5 | Cụm cố định = phía cao Otsu trên log self-match; **cụm camera sân** = cụm cố định có đường thẳng Hough (vạch sân, lưới) | Otsu (Bài 5), Hough (Bài 7, Ex7_4) |
| 6 | Âm lượng RMS cửa sổ 0,5 s (dBFS); **khán giả im** = phía thấp Otsu trên âm lượng cả trận | Otsu trên tín hiệu 1-D |
| 7 | Pha = sân ∧ im; lấp lỗ ≤ 1 s, bỏ đoạn < 1,5 s (làm mượt chuỗi nhị phân — đóng/mở 1-D) | Hình thái học 1-D (Bài 6) |
| 8 | Đệm +1 s trước (không lùi quá đầu cảnh sân — giữ cú giao bóng) và +2 s sau (giữ tiếng reo); hai pha chồng đệm → cắt giữa khoảng nghỉ | — |
| 9 | Điểm pha = trung bình thứ hạng (độ dài pha, tiếng reo to nhất 3 s sau pha) | Chuẩn hóa thứ hạng |
| 10 | Chọn pha trọn vẹn theo ngân sách (greedy hoặc knapsack 0/1); mặc định lấy toàn bộ pha | Tối ưu tổ hợp |
| 11 | ffmpeg cắt từng pha, nối đúng thứ tự; ghi `report.json` (start/end giây) + `timecodes.csv` | — |

Hai cách đã thử và loại: đếm vạch trắng HoughLinesP trực tiếp trên khung (nhận nhầm áo trắng, băng rôn) và diện tích màu sàn (áo/băng rôn xanh lẫn). So với cách cũ chia video theo chuyển cảnh histogram: cách cũ cho 519 mẩu trung vị 1 giây, cắt ngang lúc chuẩn bị giao bóng — không phải highlight.

### 2.2 Bám bóng và sự kiện quỹ đạo (bằng chứng, người xác nhận)

Bóng ở 480p chỉ vài pixel; tách màu HSV đơn thuần cho 54–176 vật vàng mỗi khung (khán giả, chữ, giày). Pipeline ứng viên (code: `rally_evidence.py`, chạy FPS gốc trên đoạn ≤ 120 s):

1. **ROI vùng sân** (người dùng khoanh) → mặt nạ màu vàng/xanh HSV ∩ **trừ khung liên tiếp** (chỉ giữ vật chuyển động — Bài 3).
2. Gán nhãn thành phần liên thông (Bài 5), lọc kích thước/độ tròn → **ứng viên bóng**.
3. Nối ứng viên qua khung bằng **dự đoán vận tốc + cổng khoảng cách**; mất dấu/cắt cảnh thì tách track mới, không nội suy giả.
4. **Vẽ quỹ đạo** chồng lên video (overlay ghi rõ "BALL CANDIDATE — NOT VERIFIED") + CSV tọa độ.
5. Sự kiện ứng viên, tất cả `confirmed=false`:
   - **Đổi hướng** (cosine hai vận tốc < 0,3): cú chạm vợt khả dĩ.
   - **Bóng nảy**: vận tốc dọc màn hình đổi dấu rơi→bật (ngưỡng 0,2 % chiều cao khung).
   - **Bóng chết**: nảy lần 2 trong ≤ 2,5 s, không có đổi hướng nào ở giữa (luật hai lần nảy); chuỗi reset khi đổi hướng/mất dấu/cắt cảnh.
6. **Người xem xác nhận** từng mốc trên giao diện; chỉ cặp giao bóng–kết thúc đã xác nhận mới tạo pha xuất (máy trạng thái từ chối pha mở, cảnh báo thiếu mốc). Bóng nảy một lần hay mất dấu không bao giờ tự đóng pha.

### 2.3 Ảnh vận động viên (mục tiêu mở rộng)

Trừ nền **MOG2** → mở/đóng hình thái → gán nhãn vùng; giữ người đứng trên màu sàn (histogram hue–sat phần dưới khung); "khoảnh khắc ra lực" = đổi dáng mạnh nhất (1 − IoU mặt nạ hai khung); lấy khung nét nhất quanh đó (phương sai Laplacian). Xử lý ảnh: khử nhiễu Non-Local Means → (tùy chọn) lọc nghịch đảo regularized với PSF vệt thẳng, họ **Wiener** (Bài 5, Ex5_2) → **unsharp mask**. Luôn lưu ảnh gốc + thông số JSON; không sinh chi tiết mới.

## 3. Thực nghiệm và kết quả

### 3.1 Dữ liệu

- Trận pickleball phát sóng 67 phút, 854×480, 29,97 fps (đo của tác giả pipeline).
- Hai video một-pha thật (YouTube Shorts, tải yt-dlp): ① `youtube.com/shorts/WQo-yvMozaI` (trong nhà, 1080×1920, 24 fps, 14,3 s); ② `youtube.com/shorts/eqp3tj8Y_Hg` (ngoài trời, 720×1280, 30 fps, 12,4 s). Ngày truy cập 09/11/2026.
- Video tổng hợp trong bộ kiểm thử (bóng parabol, sân vẽ, người di chuyển).

### 3.2 Tách pha trên trận 67 phút

**154 pha**; độ dài p10/trung vị/p90 = 1,5 / 6,3 / 18,5 s; tổng 21,9 phút; camera sân 37,5 phút. 3 cụm sân tự nhận có Dice tự khớp 0,89–0,92, khuôn 7 500–7 800 điểm biên, 5–14 đường Hough; 9 cụm còn lại ≤ 0,13. Ngưỡng Otsu âm lượng −26,3 dBFS (sân-im −30,4 / sân-ồn −21,8 / cảnh khác −21,1 dB trung vị). Highlight 10 % = 17 pha / 6,7 phút, xuất trong 14 s. Kiểm bằng mắt: pha bắt đầu đúng lúc chuẩn bị giao bóng. **Chưa có nhãn người gán nên chưa đo F1** — đây là kiểm định còn thiếu, không phải kết quả bị giấu.

### 3.3 Bám bóng trên hai video thật (có script chạy lại: `reports/qc/danh_gia_video_that.py`)

| Đo | Video ① | Video ② |
|---|---|---|
| Nhận camera sân | 34 % khung đạt (camera rung tay → khuôn biên trôi) → chỉ tách được 3 s cuối | 84 % khung đạt → tách đúng **cả clip là một pha** |
| Bám bóng toàn khung | 97,7 % khung nối được | 87,4 % **nhưng bám nhầm vật vàng tĩnh trên hàng rào** (kiểm bằng mắt) |
| Bám bóng + ROI sân | nhiều đổi hướng thật (đôi đánh nhanh) | **bám đúng bóng, quỹ đạo vẽ đúng điểm nảy thật ~3,0 s** |

Ba bài học đo được: (i) quỹ đạo vẽ được trên video thật; (ii) "tỉ lệ khung nối được" ≠ độ chính xác — có phản ví dụ cụ thể, bắt buộc kiểm overlay bằng mắt + ROI; (iii) đổi dấu vận tốc dọc chưa phân biệt bóng chạm sàn với cú vợt đánh bổng → ứng viên bóng chết chỉ là gợi ý cho người xác nhận, chưa làm `rally_end` tự động.

### 3.4 Kiểm thử tự động và tái lập

**38/38 test pass** (`pytest -q`): tách pha trên dòng thời gian tổng hợp, camera sân từ biên, pha trọn vẹn trong ngân sách, máy trạng thái sự kiện, bóng nảy/bóng chết trên video tổng hợp, xuất MP4 từng pha, metric IoU một-một. Thí nghiệm ca biên `reports/qc/qc_experiments.py` (4/4) — trong đó đã phát hiện và sửa một lỗi thật: video một cụm camera bị trả về 0 pha do Otsu trên một giá trị. Môi trường: Python 3.13+/3.14, `pip install -r requirements.txt`.

### 3.5 Ảnh vận động viên

Khoảng 4/12 ảnh dùng được (còn lại dính hai người, chỉ phần chân, dính bảng quảng cáo); 8/12 từ camera góc ngang. Nguồn 480p giới hạn chất lượng; bộ lọc Wiener sai PSF gây viền — giao diện luôn hiện cặp ảnh gốc/sau để người dùng tự đánh giá.

## 4. Hạn chế và hướng phát triển

1. Ranh giới pha đang **gián tiếp** (camera sân + khán giả im): lệch theo phản ứng khán giả, mất cảnh camera lia, không dùng được cho môn ồn suốt trận. Hướng: sự kiện bóng–vợt–sàn tự động (cần nhận cầu thủ để phân biệt chạm vợt với nảy), đọc bảng điểm bằng so khớp mẫu chữ số làm mốc hết pha.
2. **Chưa có nhãn người gán** → kế hoạch: gán nhãn start/end theo định nghĩa mục 1, đo precision/recall/F1 tại IoU 0,3/0,5/0,7 và MAE mốc đầu/cuối; tách validation/test theo trận.
3. Bám bóng cần ROI tay và nhạy tham số; chưa đo recall so với đếm tay từng khung.
4. Mới thử một trận phát sóng + hai clip ngắn; K = 12 và các ngưỡng hình dạng chưa kiểm trên nhiều trận.

## 5. Phân công công việc *(nhóm sửa lại theo thực tế)*

| Thành viên | Phần việc |
|---|---|
| Lê Hữu Huy | Pipeline tách pha, nhận camera sân bằng khuôn biên |
| Nguyễn Xuân Kha | Bám bóng, sự kiện quỹ đạo, đánh giá video thật |
| Nguyễn Hồ Công Anh | Thuật toán tách pha, đo đạc trận 67 phút, báo cáo kỹ thuật |
| Đoàn Nguyễn Tuấn Anh | QC, kiểm thử tự động, xuất video + timecode, video demo |

## 6. Tài liệu tham khảo

1. Slide & notebook môn IVP501, Session 1–8 (Canny, Hough, Otsu, hình thái học, Wiener, trừ ảnh, histogram/CLAHE).
2. USA Pickleball — Tóm tắt luật (luật hai lần nảy): https://usapickleball.org/rules/summary/ (truy cập 09/11/2026).
3. OpenCV documentation: Canny, HoughLinesP, K-means, MOG2, fastNlMeansDenoisingColored.
4. Hai video thử nghiệm: URL ở mục 3.1.
5. Mã nguồn + báo cáo chi tiết: github.com/huynevasleep/ivp501_project (nhánh `qc/rally-highlights-review`).

## Phụ lục A. Chạy lại toàn bộ

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                                   # 38 test
.venv/bin/python -m streamlit run app.py                        # giao diện
.venv/bin/python reports/qc/qc_experiments.py                   # ca biên camera sân
.venv/bin/python reports/qc/danh_gia_video_that.py <video.mp4> [--roi 0.05,0.3,0.85,0.95]
```

Hình cho báo cáo: `reports/anhnhc/img/` (7 hình trận 67 phút) + khung overlay bám bóng trong `runs/qc_eval/`.
