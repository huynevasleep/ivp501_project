# Đối chiếu dự án theo ba mục tiêu pickleball

Cập nhật 08/11/2026. Phạm vi số liệu: kiểm thử tổng hợp và kiểm thử giao diện, chưa đo độ chính xác trên trận có nhãn. Báo cáo anhnhc giữ nguyên các số đo riêng của tác giả trên trận 67 phút; không gộp với kiểm thử hiện tại.

## 1. Thiếu gì, đã bổ sung gì

| Mục tiêu | Trước đợt chỉnh | Bổ sung | Giới hạn còn lại |
|---|---|---|---|
| Xác định pha bằng bóng/vợt | Hai baseline gián tiếp: chuyển động sân; camera + âm thanh. Chưa có quỹ đạo | `rally_evidence.py`: ứng viên HSV + chuyển động + hình dạng; nối theo dự đoán vận tốc; chạy FPS gốc trên đoạn ≤120s; overlay, CSV, ảnh ứng viên đổi hướng | Chưa có detector mặt vợt/sàn; đổi hướng chưa xác nhận tiếp xúc. Vẫn cần dữ liệu thật và nhãn để đánh giá |
| Ranh giới pha có bằng chứng | Mốc heuristic, không có nhãn sự kiện | Bảng xác nhận giao bóng/chạm vợt/bóng nảy/mất dấu/kết thúc; máy trạng thái chỉ ghép cặp giao bóng–kết thúc đã xác nhận; lưu nhãn JSON | Sự kiện xác nhận do người xem nhập; không được báo cáo là phát hiện tự động |
| Ghép toàn bộ pha | Mặc định giới hạn ba phút hoặc tỷ lệ, có thể bỏ pha | Mặc định toàn bộ ứng viên đủ điều kiện, tùy chọn giới hạn; xuất tất cả pha đã xác nhận; CSV mapping source_start/end → highlight_start/end | “Toàn bộ ứng viên” không bảo đảm đủ toàn bộ pha thật; khoảng dài bất thường cần duyệt |
| Ảnh góc ngang | Trừ nền chọn ảnh, chưa xác nhận góc ngang, chưa xử lý nét/mờ | Người dùng xác nhận góc ngang có sẵn, chọn khoảng ≤20s và ROI vận động viên; khung nét nhất ở FPS gốc; NLM + unsharp; tùy chọn inverse filter PSF tuyến tính có regularization; ảnh gốc/sau, thông số JSON | Không tạo góc nhìn không có trong nguồn. PSF sai có thể tạo ringing; không thể phục hồi chắc chắn chi tiết đã mất |
| Đánh giá phù hợp môn vợt | F1 summary/boundary chung | Event/rally interval F1 với ghép một-một tại IoU≥0.5; sai số mốc đầu/cuối trên cặp khớp; nhập nhãn độc lập trong giao diện | Cần nhiều trận, nhiều góc camera, nhãn độc lập; chưa có số đo accuracy thật |

## 2. Phần không cần đặt ở luồng chính

- Bài giảng, khuôn mặt, histogram và chọn cụm đa dạng không xác định trực tiếp pha pickleball. Giữ trong **Phòng thí nghiệm: baseline / video khác** để ablation, không đưa thành tiêu chí chính của sản phẩm.
- Knapsack/chọn tỷ lệ chỉ cần cho video ngắn quảng bá; không ép ngân sách khi mục tiêu là ghép toàn bộ pha.
- Ảnh vận động viên là tùy chọn, không chạy bắt buộc cho toàn trận; ưu tiên hoàn thành và đánh giá hai mục tiêu đầu.
- Không thêm mô hình lớn hoặc các API sinh nội dung khi chưa có dữ liệu đánh giá. Không dùng ảnh tăng nét để tuyên bố đã nhận đúng bóng/vợt.

## 3. Thuật toán bằng chứng và logic pha

Nguồn ở FPS gốc → ROI sân → HSV vàng/xanh ∩ sai khác khung → connected components → kích thước/tỷ lệ/hình dạng → dự đoán vị trí bằng vận tốc → nối ứng viên trong khoảng gating → mốc đổi hướng và ảnh bằng chứng.

Điểm mất dấu được ghi `observed=false`; không vẽ nội suy như quan sát thật. Sau mất dấu dài hoặc chuyển cảnh, tracker tạo track mới. Khởi tạo lại chọn blob lớn nhất trong tập ứng viên nhỏ nên có thể nhầm giày/mũ/bảng điểm. `observation_fraction` chỉ là tỷ lệ khung có ứng viên được nối, tuyệt đối không phải accuracy/recall. Hiện hue và ROI chỉnh được; các thông số hình dạng là heuristic cần validation theo dữ liệu.

State machine: chờ `serve` được xác nhận → pha đang mở → các `paddle_contact`/`bounce`/`occluded` không tự đóng pha → `rally_end` được xác nhận đóng pha. Giao bóng mới khi pha cũ chưa đóng sẽ đưa cảnh báo, không âm thầm ghép. Pha còn mở cuối video cũng không tự coi là hoàn chỉnh.

Bóng nảy một lần không kết thúc pha. Tham khảo quy tắc hai lần nảy: https://usapickleball.org/rules/summary/. Ranh giới tự động hoàn toàn từ bóng–vợt–sàn chưa đạt; giao diện phân biệt bằng chứng thử nghiệm, ứng viên và nhãn đã xác nhận.

## 4. Phương pháp đánh giá cần thực hiện trước bảo vệ

1. Thu ít nhất vài trận ở nhiều góc nhìn/độ phân giải; tách theo trận thành validation/test. Không chọn ngưỡng trên test.
2. Chấm nhãn bóng từng khung trên các đoạn ngắn: tọa độ, visible/occluded. Chấm cả mốc giao bóng/chạm vợt/bóng nảy/kết thúc. Hai người đối chiếu bất đồng.
3. Đo detection recall/precision theo khoảng cách pixel đã quy định, tỷ lệ track đứt, sai sự kiện; không lấy tỷ lệ observed làm độ chính xác.
4. Đánh giá rally: precision/recall/F1 tại IoU 0.3/0.5/0.7, MAE start/end trên cặp khớp; báo cáo số pha bị bỏ/ghép nhầm/cắt mất đầu/cuối. Tách kết quả tự động và sau người duyệt.
5. Đối với ảnh: đánh giá mù ảnh gốc/sau, ngẫu nhiên thứ tự; hỏi độ nét tự nhiên, khuôn mặt/tư thế, ringing. Không dùng chỉ số Laplacian tăng sau sharpen làm bằng chứng chất lượng tốt hơn.

## 5. Trạng thái công việc của nhánh rally-highlight

V3 có bản thử nghiệm ứng viên bóng/quỹ đạo và bằng chứng chạy được; **chưa hoàn tất điều kiện đo với đếm tay trên video thật**. V4 có công cụ xác nhận và máy trạng thái, **chưa tự động nhận tiếp xúc bóng–vợt/sàn**. V6 có bộ lọc và so sánh gốc/sau, góc ngang **do người dùng xác nhận**, chưa phân loại góc tự động. V1/V2/V5 cần dữ liệu/đánh giá tiếp. Không đánh dấu các việc đó hoàn thành chỉ vì có giao diện.

## 6. Chạy và demo

`python -m pytest -q` chạy các kiểm thử. `python -m streamlit run app.py` mở localhost. Notebook `ProjectGoals.ipynb` minh họa ba mục tiêu với dữ liệu tổng hợp; code tái tạo trong `make_project_notebook.py`. Sinh lại HTML: `python reports/build_html.py reports/project-audit.md` (cần package markdown).

Demo: tải video → toàn bộ pha → xem/chỉnh mốc → kiểm tra quỹ đạo đoạn ngắn → nhập sự kiện đã kiểm tra → xuất pha đã xác nhận cùng timecodes → chọn góc ngang có sẵn → xem ảnh trước/sau. Không có nhãn/video thật đủ để tuyên bố dự án đã tự động hiểu mọi pha hay bảo đảm điểm môn học.
