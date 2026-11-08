# VideoLens — Đề tài 10

## Báo cáo trong `reports/` (đọc trước khi sửa phần highlight)

Người và agent làm tiếp phần highlight/ảnh vận động viên: đọc báo cáo trong `reports/` trước, rồi cập nhật nó khi đổi thuật toán hoặc có số đo mới.

| Báo cáo | Tác giả | Nội dung | Tình trạng (08/11/2026) |
|---|---|---|---|
| [`reports/anhnhc/tach-pha-bong.md`](reports/anhnhc/tach-pha-bong.md) (bản HTML cùng thư mục, sinh từ file `.md`) | anhnhc | 3 mục tiêu đề tài; thuật toán tách pha bóng đang chạy (camera sân + khán giả im, Otsu), các bước, hình và số đo trên trận pickleball 67 phút; kế hoạch bắt bóng–vợt và tăng nét/giảm mờ ảnh | Mục tiêu 2 (ghép pha có timecode) đã chạy. Mục tiêu 1 mới có bản nền gián tiếp, **chưa nhận bóng/vợt**. Mục tiêu 3 mới chọn khung (~4/12 ảnh dùng được), chưa tăng nét. **Chờ chốt:** định nghĩa kết thúc pha (luật hai lần nảy, mục 3.1) và có video 1080p không |

## Bản nâng cấp thực nghiệm

Giao diện có lựa chọn greedy/knapsack, timeline đoạn chọn, biểu đồ đóng góp đặc trưng và tab gán nhãn trực tiếp khi xem video gốc. Tải lại localhost để dùng bản mới; phân tích lại video để tạo báo cáo có trường giải thích.

Knapsack 0/1 tối ưu tổng `score × duration`, với tối đa 2000 ô ngân sách; làm tròn thời lượng lên và ngân sách xuống để bảo đảm không vượt tỷ lệ. Đây là tối ưu trên chi phí lượng tử hóa, không phải bảo đảm tóm tắt tốt nhất về ngữ nghĩa. Thưởng đa dạng chỉ áp dụng cho greedy. Baseline uniform chọn theo chia đôi thời gian đệ quy, không dùng điểm thị giác.

Chạy thí nghiệm hàng loạt:
```powershell
.venv\Scripts\python experiments.py examples/manifest.json runs/experiment
```
Manifest chứa tỷ lệ và danh sách đường dẫn video/labels (tương đối với manifest). Mỗi video được so sánh 6 biến thể: uniform, motion, hybrid, no_diversity, no_motion, knapsack. Đầu ra gồm per_video.csv, aggregate.csv và protocol.json. Báo cáo tỷ lệ thực tế, số cụm, thời gian lựa chọn, F1 và bootstrap CI95% theo video (2000 lần, seed 42). CI của một video không có giá trị suy rộng. Video mẫu synthetic chỉ kiểm tra pipeline.

Đóng góp có thể trình bày trong báo cáo: so sánh tối ưu ngân sách với ưu tiên đa dạng; phân tích đặc trưng nào ảnh hưởng điểm; đo ablation trên video độc lập; đánh giá mức biến thiên giữa video. Chưa có bằng chứng phương pháp nâng cấp vượt bản cũ trên video thực — cần dùng công cụ thực nghiệm để kiểm chứng.

Ứng dụng Python 3.13 chạy CPU, nhận video do người dùng tải lên. Mục tiêu: phát hiện chuyển cảnh, chọn khung đại diện và tạo highlight có thể giải thích, kiểm tra được bằng nhãn người.

## Chế độ thể thao có pha bóng (mặc định)

Dành cho video phát sóng môn vợt (pickleball, tennis…). Highlight chỉ gồm **trọn pha bóng**, không cắt ngang:

- Camera quay sân: gom khung theo bố cục màu thu nhỏ (16×9, Lab), nhóm có chuyển động thấp (Otsu trên log chuyển động) là camera cố định quay sân.
- Pha bóng: khoảng lặng khi camera sân đang quay (khán giả im khi đánh, reo khi hết pha); ngưỡng lặng do Otsu chọn trên âm lượng của chính video. Mỗi pha thêm 1 giây trước (không lùi quá đầu cảnh sân) và 2 giây sau để có cú phát bóng và tiếng reo.
- Điểm pha: trung bình thứ hạng độ dài pha và độ lớn tiếng reo trong 3 giây sau. Chọn pha điểm cao nhất vừa ngân sách thời lượng.
- Ảnh cầu thủ (thử nghiệm): trừ nền MOG2 + gán nhãn thành phần liên thông, chân phải đứng trên màu mặt sân, bám cùng một người qua các khung; lúc "ra lực" = đổi dáng mạnh nhất (1 − IoU mặt nạ hai khung liên tiếp), lấy khung có phương sai Laplacian lớn nhất quanh đó.

Giới hạn đã thấy trên một trận 67 phút, 480p: tách được 154 pha, kiểm bằng mắt các pha được chọn bắt đầu đúng lúc chuẩn bị phát bóng, nhưng chưa có nhãn người để đo độ chính xác. Ảnh cầu thủ chỉ khoảng 4/12 dùng được (còn lại dính hai người, chỉ được chân, dính bảng quảng cáo); muốn chọn đúng tư thế cần mô hình nhận người/tư thế. Phát bóng ăn điểm trực tiếp chưa nhận ra chắc chắn được (cần theo dõi bóng). Không áp dụng cho môn khán giả ồn suốt trận.

## Chạy trên macOS

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

## Chạy trên Windows

Mở PowerShell tại thư mục dự án:
```powershell
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py --server.address 127.0.0.1
```
Truy cập http://localhost:8501. Có thể chạy `run.ps1`. FFmpeg được cung cấp bởi imageio-ffmpeg, không cần cài hệ thống. Kết quả nằm trong `runs/<id>/`. Xóa thư mục kết quả khi không cần để giải phóng ổ đĩa; ứng dụng không tự xóa dữ liệu của người dùng.

Notebook: mở `VideoLens.ipynb` trong VS Code/Jupyter, chọn interpreter `.venv/Scripts/python.exe`. Đổi `VIDEO` và `LABELS` theo dữ liệu của bạn. Muốn chạy ví dụ tổng hợp: `.venv\Scripts\python smoke_test.py` trước.

## Điểm nâng cao để bảo vệ

- Ngưỡng chuyển cảnh thích nghi median/MAD, kết hợp HSV và sai khác khung.
- Optical flow, khuôn mặt Haar và độ nét; phân cụm màu KMeans tái lập bằng seed.
- Chọn đoạn theo ngân sách, ưu tiên đa dạng, giữ trình tự thời gian và âm thanh nguồn.
- Ba cấu hình tổng quát/thể thao/bài giảng; motion-only và bỏ motion để ablation.
- Storyboard, đường điểm, CSV đặc trưng, JSON đoạn chọn và ZIP báo cáo.
- Đánh giá nhiều người gán nhãn, F1 ranh giới ghép một-một, so sánh có/không đa dạng.

## Dữ liệu và giao thức

Ứng dụng nhận file video, không yêu cầu dữ liệu cài sẵn. Dùng video tự quay hoặc video CC có lưu URL, tác giả, loại giấy phép và ngày truy cập. TVSum: https://github.com/yalesong/tvsum — tham khảo cả script đánh giá chính thức trong `matlab/script_evaluate_result.m`. Nhãn gốc TVSum/SumMe cần được chuyển thành các khoảng thời gian theo đúng fps và giao thức lựa chọn của nhóm trước khi nạp JSON; dự án chưa có bộ chuyển đổi MAT/HDF5 tự động.

Định dạng JSON: `{"boundaries": [4, 8], "summaries": [[[0, 2], [8, 10]], [[1, 3]]]}`. Mỗi phần tử summaries là một người. Khoảng [start,end) tính bằng giây. Nhãn mẫu chỉ khớp video tổng hợp 12 giây.

Giao thức nội bộ dùng mặt nạ 10 Hz, báo cáo mean và max riêng biệt, không coi tương đương mặc định với benchmark chính thức. Ranh giới 0 và kết thúc video không đưa vào nhãn. Với benchmark công bố, chạy script gốc và ghi rõ cách tạo nhãn nhị phân, tỷ lệ ngân sách và cách tổng hợp người gán nhãn.

## Kế hoạch thực nghiệm và báo cáo

1. Thu thập tối thiểu 10–20 video đa dạng, có giấy phép. Chia theo video thành validation/test; không chỉnh trọng số trên test.
2. Nhờ ít nhất 3 người đánh dấu đoạn quan trọng độc lập, cùng tỷ lệ 15%. Lưu nhãn trước khi xem kết quả máy.
3. So sánh balanced, motion-only, bỏ motion, bỏ đa dạng; cùng tỷ lệ và tốc độ lấy mẫu. Báo cáo trung bình/độ lệch chuẩn theo video, thời gian chạy, tỷ lệ thực tế.
4. Khảo sát ẩn tên phương pháp, đảo thứ tự trình chiếu: đầy đủ nội dung, ít lặp, liền mạch, hài lòng (1–5). Lưu câu trả lời ẩn danh, báo cáo số người tham gia.
5. Báo cáo: bài toán → nghiên cứu liên quan → công thức đặc trưng/thuật toán → thiết kế phần mềm → dữ liệu/giao thức → bảng kết quả thực → lỗi và hướng phát triển. Demo bằng video chưa xuất hiện khi tinh chỉnh.

Chưa có kết quả thực nghiệm trên TVSum/SumMe; không điền điểm giả. Phương pháp không hiểu lời nói, không có OCR/nhận diện hành động, chưa tối ưu streaming. Haar có thể bỏ sót mặt nghiêng; chuyển động camera và cắt cảnh có thể tăng flow; lấy mẫu bỏ sót chuyển cảnh ngắn; màu tương tự không đồng nghĩa nội dung giống. Hướng mở rộng: OCR slide, transcript có timestamp, embedding ngữ nghĩa và đánh giá mức cải thiện thực tế. Không thể bảo đảm điểm số môn học.

## Kiểm thử
```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python smoke_test.py
```
Kiểm thử synthetic xác nhận chức năng, không đánh giá chất lượng tóm tắt đối với người xem. File requirements-lock.txt ghi môi trường đã kiểm tra; dùng `pip install -r requirements-lock.txt` để tái lập.


oh no, anh cần xem highlight pick thì phải là những đoạn tranh bóng ác liệt hấp dẫn, hoặc phát bóng ăn điểm trực tiếp. nó phải full cái đoạn đó chứ không phải cứ cắt 1-2s rồi chuyển cảnh đâu em, hiện tại anh xem thấy nó bị cắt ngay đoạn chuẩn bị phát bóng, chuyển cảnh liên tục chưa có gì gọi là highlight nó chỉ đang là rút ngắn video lại và không có ý nghĩa gì trong những đoạn rút ngắn