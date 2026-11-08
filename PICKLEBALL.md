# Highlight pickleball từ video toàn trận

**Xuất riêng từng pha:** mỗi khoảng pha đã chọn tạo một MP4 `pha_0001.mp4`, `pha_0002.mp4`… Có chọn video để xem, tải từng pha và ZIP chứa tất cả pha cùng `rallies.json`. Mỗi lần xuất có thư mục riêng trong `runs/<id>/individual/` để không lẫn video cũ. Kết quả ghép cũ có nút tách theo mốc đã lưu, không cần phân tích lại. Đây là thay đổi cách xuất; độ đúng ranh giới vẫn phụ thuộc phát hiện và duyệt pha.

Ô **Xem video riêng của một pha** phát file đã cắt thật từ 0:00, hiển thị thời lượng riêng của pha. Video gốc chỉ mở khi bật **Mở video gốc để đối chiếu**; trình phát gốc sẽ hiển thị thời lượng toàn trận. Các khoảng bất thường trên 90 giây phải chỉnh mốc trước khi xem như một pha riêng.

## Cập nhật theo ba mục tiêu

Mặc định xuất **Toàn bộ pha đề xuất**, không còn giới hạn ba phút. Khoảng hoạt động dài cần duyệt vẫn không tự chọn. Có thể bật chế độ giới hạn thời lượng nếu chỉ cần clip ngắn. Sau xuất có `timecodes.csv` chứa mốc video gốc và vị trí tương ứng trong highlight.

Các công cụ bên dưới kết quả:

1. **Kiểm tra bóng:** chọn đoạn ≤120 giây, chỉnh hue bóng nếu cần, xem overlay ở FPS gốc, tải CSV và ảnh đổi hướng. Đường quỹ đạo là ứng viên, không chứng minh chạm vợt hay sàn.
2. **Xác nhận sự kiện:** thêm các hàng giao bóng (`serve`) và kết thúc (`rally_end`), đánh dấu đã xác nhận để ghép toàn bộ pha. Bóng nảy/mất dấu không tự đóng pha. Pha mở bị cảnh báo. Công cụ vẫn dùng được khi baseline không tìm thấy ứng viên.
3. **Ảnh góc ngang:** kiểm tra góc nhìn trong video gốc, chọn khoảng ≤20 giây, ROI người và mức khử nhiễu/tăng nét. Có giảm mờ thử nghiệm theo PSF vệt thẳng; so sánh ảnh gốc và sau, tải cả thông số.

Đánh giá theo pha dùng JSON `{"rallies": [{"start": 10, "end": 20}]}`. UI báo F1 ghép một-một tại IoU 0.5 và MAE đầu/cuối. Nhãn phải được người xem tạo độc lập. Xem `ProjectGoals.ipynb` và `reports/project-audit.md` để biết phần nghiên cứu còn thiếu.

Chạy `python -m streamlit run app.py` bằng Python trong `.venv`, mở http://localhost:8501. Chọn **Highlight pickleball**, tải video, chọn toàn bộ pha hoặc giới hạn phút nếu cần, nhấn **Phân tích trận & tạo highlight**. Chế độ này là mặc định; chế độ video tổng quát vẫn có thể chọn ở thanh bên.

## Những thay đổi so với bộ tóm tắt tổng quát

- Không chia đều thành clip 4 giây. Khoảng hoạt động được ghép thành ứng viên pha, cho phép khoảng ngắt ngắn 2 giây và giữ thêm 2 giây trước/sau.
- Chuyển động được đo trong vùng sân do người dùng chọn; trừ vector optical flow trung vị để giảm ảnh hưởng chuyển động máy quay, giảm điểm khi máy quay di chuyển và loại tín hiệu ở cắt cảnh mạnh.
- Hysteresis: bắt đầu ở ngưỡng cao, tiếp tục ở ngưỡng 60% mức đó; lọc hoạt động ngắn dưới 4 giây. Pha có thể bị bỏ sót khi vận động viên đứng gần như yên hoặc dính nhau khi họ đi lại liên tục. Đây chưa phải mô hình nhận diện rally được huấn luyện.
- Chấm điểm bằng 75% hoạt động trung bình và 25% độ dài hoạt động (bão hòa ở 30 giây). Knapsack chọn các ứng viên dưới ngân sách, giữ thứ tự thời gian. Chưa suy ra điểm thắng, rally chất lượng cao, cú smash/dink, tiếng bóng, bảng điểm hoặc replay.
- Khoảng hoạt động trên 90 giây được đánh dấu cần duyệt; không tự chọn hay cắt nhỏ tùy ý. Không có ứng viên thì thông báo rõ, không ghép highlight giả.

## Video dài

FFmpeg giải mã tuần tự, lấy 3 khung/giây và thu nhỏ vùng sân trước khi truyền khung xám sang Python. Không giữ toàn bộ video trong RAM; chỉ giữ bảng đặc trưng theo thời gian và khung liền trước để tính flow. Chỉ lưu ảnh đại diện ứng viên. Tuy nhiên FFmpeg vẫn phải giải mã video nguồn, thời gian xử lý tăng theo độ dài/resolution/codec; chưa đo tốc độ trên trận thật dài.

Giới hạn upload cấu hình 4096 MB. Streamlit vẫn dùng RAM cho file upload nên giới hạn này không bảo đảm máy nào cũng tải được 4 GB. Dữ liệu nguồn và output chiếm ổ đĩa; có lựa chọn đọc đường dẫn cục bộ cho máy ít RAM. Chỉ phần video highlight được nạp vào bộ nhớ để tải xuống. Kết quả trong `runs/<id>/`: features.csv, metadata.json, candidates.json, report.json và summary.mp4.

## Duyệt kết quả

Video highlight tự tạo sau phân tích nếu có ứng viên phù hợp. Chọn pha trong danh sách để xem đúng khoảng trên video gốc; bật/tắt giữ lại và sửa mốc bắt đầu/kết thúc bằng giây. Nhấn **Xuất highlight từ các pha đã chọn** để cập nhật MP4. Hệ thống kiểm tra đoạn chồng nhau, mốc vượt video và tổng thời lượng vượt ngân sách. File report ghi `reviewed=false` cho bản tự động, `true` cho bản xuất sau thao tác duyệt; trường này chỉ cho biết thao tác giao diện, không phải chứng nhận nhãn đúng.

Mặc định dùng toàn khung; nếu thấy khán giả hoặc người ngoài sân gây nhiễu, mở phần điều chỉnh và thu vùng sân theo % chiều rộng/chiều cao. Giảm ngưỡng để tìm thêm pha; tăng ngưỡng để giảm đề xuất. Thay đổi ngưỡng/vùng sân cần phân tích lại. Thay đổi ngân sách cập nhật gợi ý chọn trong bảng, còn video gần nhất chỉ cập nhật khi xuất lại.

## Kiểm chứng cho báo cáo

`python -m pytest -q` kiểm tra ghép khoảng ngắn, ranh giới cảnh, không chồng đoạn, ngân sách, video tĩnh, bảng hoạt động dài 2 giờ và xuất MP4 qua giao diện. Bảng 2 giờ là tín hiệu tổng hợp, không phải thử nghiệm giải mã một trận 2 giờ. Notebook Pickleball.ipynb minh họa cơ chế và cho phép chọn video thật bằng hộp thoại.

Chưa có nhãn/video pickleball toàn trận để đo độ chính xác. Để kết luận chất lượng, tách validation/test theo trận; nhờ người xem đánh dấu bắt đầu/kết thúc rally và các rally đáng đưa vào highlight. Báo cáo riêng độ phủ rally, cắt mất đầu/cuối pha, khoảng nghỉ được giữ nhầm, F-score khoảng thời gian và khảo sát tính hấp dẫn. Không dùng điểm trên video tổng hợp làm điểm chất lượng pickleball.
