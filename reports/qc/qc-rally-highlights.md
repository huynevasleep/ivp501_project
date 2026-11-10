# QC nhánh rally-highlight: đối chiếu từng khẳng định với code và bằng chứng

*QC · 09/11/2026 · nhánh `qc/rally-highlights-review` (tách từ `origin/rally-highlight`, commit `b77f853`)*

Nhiệm vụ QC: kiểm tra tính chính xác của các thuật toán đã khai báo (detect biên, detect mặt sân, detect hình học/vạch sân, bóng chạm vợt, bóng chết), kiểm tra rằng **từng bước chọn timecode highlight đều mô tả được và chứng minh được bằng code + test**, và bắt mọi khẳng định trong báo cáo mà repo không chứng minh được.

**Cách kiểm:** đọc đối chiếu toàn bộ `core.py`, `pickleball.py`, `rally_evidence.py`, `photo_finish.py`, `rally_export.py`, `rally_preview.py`, `match_ui.py`, `project_tools_ui.py`, `app.py` với hai báo cáo `reports/anhnhc/tach-pha-bong.md` và `reports/project-audit.md`; chạy lại toàn bộ kiểm thử và viết thêm thí nghiệm ca biên (`reports/qc/qc_experiments.py`). Video trận 67 phút **không có trong repo**, nên các con số đo trên trận thật chỉ đối chiếu được về mô tả thuật toán, không chạy lại được trên máy QC (xem mục 4.2).

## 1. Kết quả chạy trên máy QC (macOS, Python 3.14, venv từ `requirements.txt`)

| Lệnh | Kết quả |
|---|---|
| `.venv/bin/python -m pytest -q` | **39 passed** (33 + 2 skipped ban đầu; 36 sau test hồi quy mục 3.1; 38 sau 2 test bóng nảy/bóng chết mục 6.1; 39 sau test kiểm chứng Otsu với OpenCV `test_otsu_matches_opencv_reference`) |
| `.venv/bin/python smoke_test.py` | PASS: cuts, duration budget, MP4 export, Streamlit initial render |
| `.venv/bin/python reports/qc/qc_experiments.py` | 4/4 ca PASS **sau khi sửa lỗi mục 3.1** (trước khi sửa: ca "một cụm duy nhất" FAIL) |
| `.venv/bin/python reports/qc/danh_gia_video_that.py <video> [--roi …]` | đánh giá trên hai video thật, kết quả ở mục 6.2 |

## 2. Các khẳng định ĐÃ chứng minh được

### 2.1 Từng bước chọn timecode highlight (mục 3.2 báo cáo tách pha) ↔ code ↔ test

Yêu cầu "trong report phải mô tả được từng bước mình chọn đoạn timecode đó làm highlight" **đạt** đối với bản nền gián tiếp: chuỗi dưới đây là đường đi đầy đủ từ video đến từng cặp `start`/`end` trong `report.json`, mỗi bước có code và test tương ứng.

| # | Bước (như báo cáo mô tả) | Code | Bằng chứng |
|---|---|---|---|
| 1 | Lấy mẫu 2 khung/giây, thu 320×180 | `core.analyze` (`grab`/`retrieve`, `step=round(fps/2)`) | đọc code khớp |
| 2 | Bố cục màu Lab 16×9 → vector 432 số | `core.py` dòng 131; 16·9·3 = 432 ✓ | khớp số trong báo cáo |
| 3 | **Giảm nhiễu** Gauss 3×3 rồi **detect biên** Canny 50/150; nén bit ≈7 KB/khung | `core._edges`; 320·180/8 = 7 200 byte ✓ | khớp số trong báo cáo |
| 4 | Âm lượng RMS cửa sổ 0,5 s, dBFS, mono 8 kHz | `core.audio_loudness` (cửa sổ = `step/fps` = 0,5 s **khi** lấy mẫu 2 fps) | `test_otsu_splits_bimodal` cho phần ngưỡng |
| 5 | K-means 12 cụm bố cục màu, seed 42 | `core.py` dòng 149 (`min(12, …)`, `random_state=42`) | khớp |
| 6 | **Detect mặt sân/hình học**: khuôn biên mỗi cụm = trung vị bản đồ biên; độ khớp = Dice hai chiều recall/precision (dung sai lệch 1 pixel); cụm cố định = phía cao Otsu trên log self-match; cụm camera sân = cụm cố định có **đường thẳng Hough** (vạch sân, lưới) | `core.edge_dice`, `core.court_cameras` | `test_court_cameras_from_edges_alone` (cụm sân nhận đúng, cảnh quay tay và cảnh tĩnh không vạch bị loại); thí nghiệm QC ca 1, 3, 4 |
| 7 | Khung sân = điểm khớp cao nhất với các khuôn sân, vượt ngưỡng Otsu | `core.analyze` (`court_score`, `court_threshold`), `core.detect_rallies` | `test_detect_rallies_uses_edge_court_score` |
| 8 | Khán giả im = phía thấp Otsu trên âm lượng cả trận | `core.detect_rallies` (`quiet`) | `test_rallies_are_quiet_court_stretches_with_serve_and_reaction` |
| 9 | **Làm mượt chuỗi thời gian**: pha = sân AND im; lấp lỗ ≤ 1 s; bỏ đoạn < 1,5 s | `detect_rallies` (`gap=1`, `min_len=1.5`, `_runs`) | cùng test trên (0,5 s im không thành pha) |
| 10 | Đệm +1 s trước (không lùi quá đầu cảnh sân) và +2 s sau | `detect_rallies` (`pre`, `post`, vòng lùi `lead`) | `test_pre_roll_does_not_reach_into_the_close_up` |
| 11 | Hai pha chồng phần đệm → cắt giữa khoảng nghỉ | `core.py` dòng 215–216 | `test_close_padding_is_split_in_the_pause` |
| 12 | Điểm pha = trung bình thứ hạng phần trăm của (độ dài pha, âm lượng lớn nhất 3 s sau pha) | `core._rank`, `reaction=3` | `test_scores_reward_long_rally_and_loud_reaction` |
| 13 | Chọn pha **trọn hoặc bỏ** theo ngân sách (greedy hoặc knapsack 0/1) | `core.select(mode='rally')`, `core.knapsack_select` | `test_select_keeps_whole_rallies_within_budget`, `test_ratio_one_keeps_every_rally` |
| 14 | Ghi `start`/`end` (giây) vào `report.json`; ffmpeg cắt từng pha rồi nối đúng thứ tự; có timecode nguồn → highlight | `app.py` dòng 49–50, `core.export_video`, `rally_evidence.timecode_table`, `rally_export.export_individual` | `test_each_file_contains_only_its_rally_and_zip_is_current`, `test_all_mode_never_discards_eligible_rallies` |

Pipeline pickleball cục bộ (`pickleball.py`, góc máy cố định tự quay) cũng mô tả được từng bước: optical flow Farneback trừ vector trung vị (khử chuyển động máy quay) → chuẩn hóa → **làm mượt trung vị trượt** → hysteresis hai ngưỡng (0,32 / 60%) → lấp khoảng nghỉ ≤ 2 s → bỏ hoạt động < 4 s → đệm trước/sau chặn ở chuyển cảnh → khoảng > 90 s gắn `needs_review`, không tự chọn. Test: `tests/test_pickleball.py` (6 test).

### 2.2 Thuật toán môn học dùng ở đâu (trả lời "dùng các thuật toán nào đã học")

Cột "Bài học" đối chiếu với notebook Colab của môn (Session 2–8, nhóm đã tải về `colab_tham_khao/` — không commit): QC đã đọc toàn bộ 8 notebook và xác nhận các kỹ thuật dưới đây đúng là nội dung đã học.

| Kỹ thuật đã học | Bài học (Colab) | Vị trí trong code | Vai trò |
|---|---|---|---|
| **Detect biên**: Canny (Gauss trước, hai ngưỡng) | Session 7 Ex7_3 (Canny); Ex7_1/7_2 nền tảng gradient Prewitt/Sobel | `core._edges` | nhận camera sân bằng khuôn biên |
| **Detect hình học**: biến đổi Hough đường thẳng | Session 7 Ex7_4/7_5 (Hough line, deskew), Ex7_7 (Hough circle) | `core.court_cameras` (`HoughLinesP`) | xác nhận khuôn có vạch sân/mép lưới |
| **Detect mặt sân** (màu sàn) | Session 2 (histogram); Session 6 (phép đóng) | `core._floor_mask` (histogram hue–sat phần dưới khung + morphological close) | lọc "chân đứng trên sàn" khi chọn ảnh cầu thủ |
| **Giảm nhiễu**: Gauss, lọc trung bình, mở/đóng hình thái học, Non-Local Means | Session 4 Ex4_1/4_2 (lọc không gian), Ex4_3 (min/max cho muối tiêu); Session 3 Ex3_5 (trung bình nhiều khung) | `core._edges`, `core.best_shots`, `photo_finish.finish_photo` | trước Canny; dọn mặt nạ trừ nền; khử nhiễu ảnh trước tăng nét |
| **Làm mượt tín hiệu thời gian**: trung vị trượt; lấp lỗ/bỏ run ngắn | mở rộng 1-D của lọc trung vị/phép đóng (Session 4, 6) | `pickleball.propose_rallies`; `core.detect_rallies` | chống nhấp nháy khi quyết định pha |
| **Ngưỡng tự động Otsu** | Session 5 Ex5_3, Session 6, Session 7 Ex7_5 (`THRESH_OTSU`) | `core.otsu_threshold` (3 chỗ: cụm cố định, khung sân, âm lượng) | không phải chỉnh tay theo video |
| **Gán nhãn thành phần liên thông / region labelling** | Session 5 Ex5_3 (đếm cá), Session 6 Ex6_3 (đếm xu bằng phép co) | `core.best_shots`, `rally_evidence.ball_candidates` (`connectedComponentsWithStats`) | tách người/ứng viên bóng |
| **Hình thái học**: giãn/co, mở/đóng, biên bằng giãn−co | Session 6 Ex6_1–6_7 | `core.best_shots`, `core._floor_mask`, `core.edge_dice` (dilate làm dung sai 1 px) | dọn mặt nạ, dung sai so khớp biên |
| **Trừ nền**: MOG2; sai khác khung | sai khác khung = phép trừ ảnh Session 3 Ex3_2 | `core.best_shots`; `rally_evidence.ball_candidates` | tách người chuyển động; tách vật chuyển động nhỏ |
| **Vẽ quỹ đạo + bám vật**: nối ứng viên bằng dự đoán vận tốc (gating), polyline chồng khung, reset khi mất dấu/cắt cảnh | tổng hợp từ trừ ảnh + region labelling (Session 3, 5) | `rally_evidence.track_ball` | bằng chứng quỹ đạo bóng ở FPS gốc, kèm CSV và ảnh mốc đổi hướng |
| **Tăng nét**: unsharp mask / kernel khử mờ; **giảm mờ**: lọc nghịch đảo regularized với PSF vệt thẳng (họ Wiener) | Session 5 Ex5_1 (kernel khử mờ), Ex5_2 (Butterworth + **Wiener**) | `photo_finish.finish_photo` | ảnh góc ngang; lưu cả ảnh gốc và thông số JSON |
| **Cân bằng phổ / CLAHE** | Session 2 Ex2_2–2_4, Session 8 (CLAHE trong DoH) | chưa dùng trong luồng chính (ứng viên cho tiền xử lý ảnh góc ngang) | — |
| **Nội suy khi phóng ảnh** (nearest/linear/cubic) | Session 3 Ex3_7 | kế hoạch mục 5.2 báo cáo tách pha (song khối) | chưa chạy |
| **Xử lý ảnh cơ bản**: kênh màu, nhị phân hóa, lấy mẫu/lượng tử hóa | Session 1 Ex1_1–1_3 | nền của mọi bước (chuyển xám, HSV, Lab, nhị phân) | — |
| **Optical flow Farneback**; **K-means**; **MOG2**; **Non-Local Means** | **không có trong cả hai folder Colab đã chia sẻ** (toàn bộ Session 1–8 là xử lý ảnh tĩnh) | `pickleball.analyze_match`, `core.analyze`, `core.best_shots`, `photo_finish` | hoạt động trên sân; gom góc camera; trừ nền; khử nhiễu |

Ghi chú nguồn tham khảo (đã truy cập cả hai folder Colab): folder thứ nhất chứa ảnh dữ liệu của từng session và notebook `Session_1.ipynb` (ảnh cơ bản); folder thứ hai chứa notebook Session 2–8. **Hai điểm QC bắt thêm:**

1. Trích dẫn trong mục 5.2 của báo cáo tách pha **không khớp đánh số notebook**: "unsharp mask (Ví dụ 1.3)" — nhưng Ex1_3 của Colab là *lấy mẫu và lượng tử hóa*; "Richardson–Lucy hoặc Wiener (Ví dụ 1.5, Bài 5)" — notebook không có Ex1_5, Wiener nằm ở Session 5 Ex5_2 (khớp "Bài 5"); "nội suy song khối (Ví dụ 2.10)" — Session 2 chỉ có Ex2_1–2_4, nội suy cubic nằm ở Session 3 Ex3_7; "lọc trung vị (Bài 5)" — notebook không có lọc trung vị (Session 4 chỉ có trung bình và min/max). Các "Ví dụ x.y" này nhiều khả năng đánh số theo **slide**, không có trong hai folder đã chia sẻ → khi viết báo cáo cuối, trích theo số Session + Ex của notebook (hoặc đính kèm slide) để người chấm tra được.
2. Các kỹ thuật video của dự án (optical flow, MOG2, K-means, NLM) **nằm ngoài tài liệu đã học được chia sẻ**: trong báo cáo cuối nên trình bày chúng là phần mở rộng tự nghiên cứu dựa trên nền tảng môn học (trừ ảnh → trừ nền; lọc không gian → lọc thời gian), không gộp chung vào "thuật toán đã học".

### 2.3 "Bóng chết" và ranh giới pha — đúng luật, đúng mức khiêm tốn

- Định nghĩa trong báo cáo (mục 3.1) khớp luật hai lần nảy của pickleball: một lần bóng chạm sàn **không** kết thúc pha; pha chỉ đóng khi bóng chạm sàn mà không còn cú chạm vợt nào sau đó (tức nảy lần hai/bóng chết), ra ngoài, hoặc vào lưới.
- Code tôn trọng đúng định nghĩa đó ở phần sự kiện: `rally_evidence.rallies_from_events` chỉ ghép **cặp giao bóng–kết thúc đã được người xác nhận**; `bounce` và `occluded` không bao giờ tự đóng pha (`test_bounces_and_lost_ball_do_not_end_rally`); pha mở hoặc chưa xác nhận không được xuất (`test_unconfirmed_and_open_rallies_are_not_exported`).
- "Chuyển góc máy không phải kết thúc pha": `detect_rallies` chỉ lấp lỗ ≤ 1 s, nên về mặt code chuyển cảnh ngắn giữa pha không cắt pha; chuyển cảnh dài hơn vẫn cắt sai — báo cáo đã tự khai ở ví dụ 10:55 và việc mở V5/V7.

## 3. Những điểm QC BẮT

### 3.1 LỖI (đã tái lập, đã sửa trên nhánh này): video một cụm camera duy nhất → 0 pha

`court_cameras` chọn cụm cố định bằng Otsu trên log self-match rồi so sánh **`m > cut`**. Khi K-means chỉ trả về **một** cụm, `otsu_threshold` của một giá trị trả về chính giá trị đó, phép so sánh ngặt loại luôn cụm duy nhất → không có camera sân → `detect_rallies` trả **0 pha**, dù toàn video là camera sân có vạch Hough rõ. Nhánh fallback theo chuyển động dùng `<=` (bao gồm) nên không bị — hai nhánh không nhất quán.

- Tái lập: `reports/qc/qc_experiments.py` ca 2 (FAIL tại `b77f853`).
- Sửa: một cụm duy nhất thì chỉ cần qua cổng Hough (`core.py`, hàm `court_cameras`); cảnh tĩnh không vạch và cảnh quay tay vẫn bị loại (ca 3–4 PASS).
- Test hồi quy: `tests/test_rally.py::test_single_cluster_video_keeps_its_court_camera`.
- Mức ảnh hưởng: thấp với trận phát sóng nhiều góc (K-means luôn ra nhiều cụm), nhưng chặn đúng loại video nhóm định tự quay một góc máy (việc mở V1). Chưa kiểm chứng lại trên trận 67 phút vì repo không có video (mục 4.2).

### 3.2 Chưa chứng minh được: timecode highlight hiện tại KHÔNG đến từ bóng–vợt–sàn

Đây là khoảng trống lớn nhất giữa mục tiêu đề tài và bằng chứng hiện có, và cả hai báo cáo đều **đã tự khai đúng** — QC xác nhận khai báo khớp code:

- Không có detector mặt vợt, không có detector bóng chạm sàn. Ranh giới pha của highlight đang lấy từ *camera sân + khán giả im* (gián tiếp), không phải từ sự kiện bóng. *(Cập nhật sau QC: đã có **ứng viên** bóng nảy và bóng chết hai-lần-nảy từ hình dạng quỹ đạo — mục 6 — nhưng chúng vẫn là gợi ý cho người xác nhận, chưa tham gia chọn timecode.)*
- `direction_change_candidate` (cosine hai vận tốc < 0,3 trong `track_ball`) **không phân biệt** chạm vợt / chạm sàn / nhiễu bám; overlay cũng ghi rõ "BALL CANDIDATE – NOT VERIFIED". Ngoài ra, cú nảy mà thành phần ngang của vận tốc chiếm ưu thế có thể không đổi hướng đủ mạnh để cosine < 0,3 — tức ứng viên đổi hướng **không bảo đảm bắt được mọi cú nảy**, chưa nói đến phân loại.
- Vậy: mọi câu trong báo cáo cuối cùng dạng "highlight được chọn vì bóng chết / vì bóng chạm vợt lúc X" đều **chưa chứng minh được bằng pipeline tự động**; chỉ được phép nói vậy cho các pha đi qua bảng xác nhận sự kiện của người xem (`rallies_from_events`). Ai viết report thuyết trình cần giữ đúng ranh giới này.

### 3.3 Chưa chứng minh được: các con số đo trên trận 67 phút không tái lập được từ repo

Mục 7 của báo cáo tách pha tự đặt luật *"Số liệu phải đo được và kèm lệnh hoặc script để chạy lại"*, nhưng chính báo cáo đang vi phạm luật đó ở các điểm sau (QC đã grep toàn repo, không có script nào sinh ra các số/hình này):

- "61/154 pha có đổi camera giữa pha, tổng 87 lần", ví dụ phút 10:55 — không có script đếm số lần đổi camera trong pha.
- Toàn bộ 7 hình trong `reports/anhnhc/img/` (phân bố âm lượng, dòng thời gian, cụm camera, vật màu vàng…) — không có script vẽ lại.
- Dice 0,89–0,92, ngưỡng Otsu −26,3 dBFS, 154 pha, "4/12 ảnh dùng được", "54–176 vật màu vàng mỗi khung" — không có `features.csv`/`report.json` của lần chạy đó trong repo, cũng không có video (dễ hiểu vì dung lượng/bản quyền, nhưng cần ghi URL + lệnh chạy để người khác tái lập; mục "Dữ liệu và giao thức" của README yêu cầu đúng điều này cho video dùng).

→ Việc mở **Q1** (mục 5): commit script đo + hướng dẫn tái lập, hoặc hạ cấp các con số này trong báo cáo thành "kiểm bằng mắt, chưa tái lập được".

### 3.4 Tài liệu lệch so với code (đã sửa trên nhánh này)

- `README.md` mục "Chế độ thể thao có pha bóng" vẫn mô tả cách nhận camera sân bằng **chuyển động thấp (optical flow)** — đã bị thay bằng khuôn biên Canny từ commit `2087999`. Đã cập nhật mô tả, giữ ghi chú fallback.
- Cuối `README.md` có một đoạn chat góp ý dán thô ("oh no, anh cần xem highlight pick…"). Đây là góp ý định hình yêu cầu "lấy trọn pha" nên không bỏ nội dung, nhưng đã chuyển thành blockquote có ngữ cảnh.
- Báo cáo tách pha mục 6 ghi `tests/test_rally.py` có "7 test" — thực tế 10 (nay 11 sau test hồi quy QC). Đã sửa.

### 3.5 Ghi chú nhỏ (chưa sửa, không chặn)

- Báo cáo viết dung sai "cho lệch 1 pixel" chỉ cho chiều recall; code dilate **cả hai chiều** (biên khung cho recall, khuôn cho precision). Nên viết lại cho đúng khi cập nhật báo cáo.
- "Cửa sổ RMS 0,5 s" chỉ đúng khi lấy mẫu 2 fps (cửa sổ = 1/sample_fps); đổi tốc độ lấy mẫu trên UI thì con số trong báo cáo đổi theo.
- `cheer_db` đo trong 3 s sau pha có thể dính tiếng giao bóng của pha kế tiếp khi hai pha sát nhau — chấp nhận được cho xếp hạng, nên ghi rõ nếu dùng con số này làm bằng chứng.
- `ball_candidates` cho phép blob tới `max(100, 0.1% khung)` ≈ 2 000 px ở 1080p — đủ lọt giày/mũ; audit đã khai việc bám nhầm khi khởi tạo lại, giữ nguyên khai báo đó.

## 4. Giới hạn của chính đợt QC này

1. **Toàn bộ kiểm chứng chạy trên dữ liệu tổng hợp.** 36 test + 4 thí nghiệm QC chứng minh thuật toán làm đúng *điều nó khai* trên tín hiệu sạch; không chứng minh độ chính xác trên trận thật. Kết luận "tách đúng 154 pha" vẫn là kiểm bằng mắt của tác giả.
2. **Không có video trận 67 phút** trong repo nên QC không thể xác nhận các con số của mục 3.2 báo cáo gốc, và không thể đo tác động của sửa lỗi 3.1 lên trận thật (dự đoán: không đổi, vì trận đó có 12 cụm).
3. QC không đánh giá chất lượng cảm quan của highlight hay ảnh cầu thủ.

## 5. Việc mở sau QC (ai nhận thì ghi tên, theo đúng cơ chế mục 7 của báo cáo tách pha)

| # | Việc | Xong khi | Người nhận |
|---|---|---|---|
| Q1 | Script tái lập các con số/hình của báo cáo tách pha (đếm đổi camera trong pha, vẽ lại 7 hình từ `features.csv`) + ghi URL video, lệnh chạy | Chạy một lệnh ra lại đúng các số trong báo cáo, hoặc các số được hạ cấp thành "kiểm bằng mắt" | |
| Q2 | Chạy lại trận 67 phút trên nhánh đã sửa 3.1, xác nhận số pha không đổi | Ghi số pha trước/sau vào báo cáo tách pha | |
| Q3 | Thêm vào báo cáo một ví dụ lần vết **một pha cụ thể**: từ `features.csv` chỉ ra court_score và âm lượng từng mẫu so với hai ngưỡng Otsu, phép đệm → ra đúng `start`/`end` trong `report.json` | Có bảng/hình lần vết kèm lệnh chạy lại | |
| Q4 | Rà soát bản thuyết trình: mọi chỗ nói "bóng chạm vợt/bóng chết quyết định timecode" phải đổi thành "bản nền gián tiếp + sự kiện người xác nhận" (mục 3.2 QC) | Không còn câu nào vượt quá bằng chứng | |

## 6. Bổ sung sau QC: ứng viên bóng nảy / bóng chết, và đánh giá trên hai video thật

### 6.1 Đã làm thêm (nhận việc theo cơ chế mục 7 báo cáo tách pha)

`track_ball` nay tự đề xuất thêm hai loại bằng chứng, đều `confirmed=false` và chỉ là *gợi ý từ hình dạng quỹ đạo* cho bảng xác nhận của người xem:

- **`bounce_candidate` (bóng nảy):** vận tốc dọc màn hình đổi dấu từ rơi xuống sang bật lên trên một track liên tục, ngưỡng mặc định 0,2 % chiều cao khung (để nhiễu trọng tâm ở video phân giải cao không bị tính).
- **`dead_ball_candidate` (bóng chết, luật hai lần nảy):** lần nảy thứ hai trong ≤ 2,5 s sau lần nảy trước mà **không có** ứng viên đổi hướng (cú chạm vợt khả dĩ) ở giữa; chuỗi nảy được reset khi đổi hướng, mất dấu, cắt cảnh hoặc track mới.

Chứng minh trên video tổng hợp (bóng parabol nảy 2 lần, 24 fps): đúng 1 `dead_ball_candidate` tại lần nảy thứ hai; chèn một cú đảo hướng ngang giữa hai lần nảy thì không còn bóng chết nào — `tests/test_evidence.py::test_two_bounces_without_paddle_hit_flag_a_dead_ball` và `::test_a_direction_change_between_bounces_resets_the_dead_ball_count`. Toàn bộ suite: **39 passed** (test thứ 39 là kiểm chứng Otsu tự cài với OpenCV, thêm khi dựng báo cáo nộp).

### 6.2 Đánh giá trên hai video thật (YouTube Shorts, mỗi video một pha, camera đơn)

Video (tải bằng yt-dlp về `video_thu_nghiem/`, không commit): ① https://www.youtube.com/shorts/WQo-yvMozaI — trong nhà, đôi, 1080×1920, 24 fps, 14,3 s; ② https://www.youtube.com/shorts/eqp3tj8Y_Hg — ngoài trời có mái, 720×1280, 30 fps, 12,4 s. Lệnh chạy lại: `.venv/bin/python reports/qc/danh_gia_video_that.py <video> [--roi 0.05,0.3,0.85,0.95]`; overlay, CSV và ảnh mốc nằm trong `runs/qc_eval/`.

| Đo | Video ① (trong nhà) | Video ② (ngoài trời) |
|---|---|---|
| Nhận camera sân (khuôn biên) | 6/12 cụm là sân; **34 %** khung vượt ngưỡng → bản nền chỉ tách được pha cuối [11,5→14,3 s] | 11/12 cụm là sân; **84 %** khung vượt ngưỡng → tách đúng cả clip là một pha [0→12,4 s] |
| Bám bóng toàn khung | 97,7 % khung nối được | 87,4 % khung nối được **nhưng bám nhầm vật vàng tĩnh trên hàng rào** (kiểm bằng mắt overlay) |
| Bám bóng với ROI vùng sân | 28 sự kiện/14 s (đôi đánh nhanh trên lưới: nhiều đổi hướng thật) | 64,2 % khung nối, **bám đúng bóng**: quỹ đạo vẽ chuẩn đường bóng rơi tới điểm nảy thật tại ~3,0 s (kiểm bằng mắt) |

**Kết luận đo được:**

1. **Vẽ quỹ đạo trên video thật: hoạt động.** Overlay video ② (ROI) vẽ đường bóng cong xuống đúng điểm chạm sàn.
2. **`observation_fraction` cao không phải bám đúng — nay có bằng chứng cụ thể:** video ② toàn khung đạt 87 % nhưng vòng bám nằm trên một vật vàng **tĩnh** ở hàng rào (rung máy làm vật tĩnh lọt mặt nạ chuyển động, khởi tạo lại chọn blob lớn nhất). Giới hạn ROI vùng sân (tính năng có sẵn) khắc phục được. Mọi lần chạy đều phải kiểm overlay bằng mắt.
3. **Nảy theo đổi dấu vận tốc dọc chưa phân biệt được chạm sàn với cú vợt đánh bổng lên**, và nhạy với ngưỡng: ngưỡng 1 px/khung sinh nảy giả theo nhịp rung; ngưỡng 0,2 % chiều cao lọc sạch nhiễu nhưng cũng rụng một ứng viên bóng chết cuối pha (11,1 s, video ②) có vẻ hợp lý. → `dead_ball_candidate` dùng đúng như thiết kế: **gợi ý cho người xác nhận**, chưa đủ làm `rally_end` tự động; V4 vẫn mở phần phân biệt chạm vợt (cần vị trí cầu thủ) và so với đếm tay.
4. **Bản nền tách pha hoạt động đúng thiết kế trên camera cố định** (video ②, một pha trọn vẹn — các cụm K-means cùng một camera đều được nhận là sân), nhưng **yếu với video quay tay rung** (video ①: khuôn biên trôi → 34 % khung đạt): video dọc tự quay nên dùng pipeline pickleball cục bộ hoặc cần ổn định hình trước.

### 6.3 Vòng QC 10/11 trên video 11 phút: hai giả định bị phá, hai lần khắc phục, một hạn chế còn lại

Stakeholder xem demo và nghi đoạn preview "bị cắt đứt giữa chừng pha". Điều tra (script `reports/qc/vi_du_dau_cuoi.py` + soi khung nguồn, ảnh `img/qc_cat_giua_pha.png`):

1. **Chế độ mặc định (∧ khán giả im) cắt giữa pha — xác nhận.** Pha bị đóng tại 55,5 s; khung 62 s cho thấy vẫn đang đánh; điểm kết thúc thật (~70 s, đập tay). Nguyên nhân: video có **bình luận viên nói liên tục trong lúc đánh**. Khắc phục: thêm `use_audio=False` cho `detect_rallies` + test `test_without_audio_rallies_follow_the_court_camera_alone`.
2. **Chế độ camera sân cũng cắt tại 57,5 s — truy tiếp bằng chuỗi `court_score`:** camera **zoom theo bóng giữa pha**, điểm khớp khuôn rơi 0,73–0,76, ngay dưới ngưỡng Otsu 0,78 suốt 60–72 s. Khắc phục: **hysteresis** (vào tại ngưỡng, duy trì tại 88% ngưỡng) + test `test_zoomed_court_shot_is_kept_by_hysteresis`; cứu được các đoạn zoom ổn định.
3. **Còn lại:** khoảnh khắc *chuyển* zoom (mờ chuyển động, điểm rơi tới 0,62 trong ~4 s) vẫn tách đoạn — thuộc việc mở V5 (bám khuôn có bù tỷ lệ). Vì vậy trên video này đầu ra được mô tả đúng mức là **19 đoạn toàn sân liên tục / 8,8 phút (79%)** — KHÔNG claim "pha trọn vẹn" (so sánh: bật âm thanh 51 mảnh / 7,1 phút). Suite sau hai sửa: **41 test pass**.

Bài học QC: con số pha/phút tự nó không chứng minh gì — **soi khung hình tại mốc cắt** là phép kiểm bắt buộc, và chính nó bắt được cả hai lỗi trên.

## 7. Sinh lại bản HTML

```bash
.venv/bin/pip install markdown
.venv/bin/python reports/build_html.py
```
