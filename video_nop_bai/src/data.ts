// ========= SỬA THÔNG TIN NHÓM Ở ĐÂY rồi chạy lại: npm run render =========
export const COURSE = 'IVP501 · Xử lý Ảnh và Video số';
export const TOPIC = 'Nhóm 03 · Đề tài 10 · VideoLens';
export const TITLE = 'Tách pha bóng pickleball & dựng video highlight';
export const DATE = 'Tháng 11/2026';

export const TEAM: { name: string; id: string; role: string }[] = [
  { name: 'Lê Hữu Huy', id: 'Nhóm 03', role: 'Pipeline tách pha · camera sân' },
  { name: 'Nguyễn Xuân Kha', id: 'Nhóm 03', role: 'Bám bóng · sự kiện quỹ đạo' },
  { name: 'Nguyễn Hồ Công Anh', id: 'Nhóm 03', role: 'Thuật toán tách pha · báo cáo' },
  { name: 'Đoàn Nguyễn Tuấn Anh', id: 'Nhóm 03', role: 'QC · kiểm thử · xuất video' },
];

export const GOALS = [
  'Xác định pha bóng: từ cú giao bóng đến khi bóng chết (chạm sàn 2 lần, ra ngoài, vào lưới)',
  'Ghép toàn bộ các pha (có timecode bắt đầu / kết thúc) thành một video highlight',
  '(Làm thêm) Ảnh góc ngang vận động viên: chọn khoảnh khắc, khử nhiễu, tăng nét, giảm mờ',
];

// Ảnh từng bước sinh từ CHÍNH video 11 phút bằng reports/qc/vi_du_dau_cuoi.py
export const PIPELINE: { step: string; algo: string; img: string; cap: string }[] = [
  { step: 'Lấy mẫu 2 khung/giây, thu 320×180', algo: 'Lấy mẫu', img: 'steps/b1_goc.png', cap: 'Khung mẫu 320×180 lấy từ video 11 phút' },
  { step: 'Giảm nhiễu Gauss 3×3 → detect biên Canny 50/150', algo: 'Canny', img: 'steps/b2_canny.png', cap: 'Bản đồ biên Canny của đúng khung đó' },
  { step: 'Khuôn biên mỗi cụm camera = trung vị bản đồ biên', algo: 'K-means + Dice', img: 'steps/b3_khuon.png', cap: 'Khuôn biên: chỉ giữ biên đứng yên qua các khung cùng cụm' },
  { step: 'Camera sân = khuôn ổn định có vạch thẳng Hough', algo: 'Hough', img: 'steps/b4_hough.png', cap: 'Đoạn thẳng ổn định: xanh = vạch sân/lưới (nửa dưới), xám = khung mái, băng rôn' },
  { step: 'Khán giả im = phía thấp của ngưỡng Otsu trên âm lượng', algo: 'Otsu', img: 'steps/b5_am_luong.png', cap: 'Âm lượng + ngưỡng Otsu — video này BLV nói suốt lúc đánh nên QC tắt điều kiện âm thanh' },
  { step: 'Pha = sân ∧ im; lấp lỗ ≤ 1 s, bỏ đoạn < 1,5 s (làm mượt)', algo: 'Đóng/mở 1-D', img: 'steps/b6_dong_thoi_gian.png', cap: 'Dải vàng = 22 pha theo camera sân — không cắt giữa pha' },
  { step: 'Đệm +1 s trước (không lùi quá đầu cảnh sân) và +2 s sau', algo: 'Luật đệm', img: 'steps/b6_dong_thoi_gian.png', cap: 'Mỗi pha đệm thêm để giữ trọn cú giao bóng và tiếng reo' },
  { step: 'Chấm điểm pha → chọn trọn pha → ffmpeg cắt và nối', algo: 'Greedy / Knapsack', img: 'steps/b8_ket_qua.png', cap: 'Keyframe của 4 pha dài nhất được ghép vào highlight' },
];

// Kết quả đầu-cuối trên video công khai (youtube.com/watch?v=PMRSb3ogWq4) — số từ runs/vi_du_dau_cuoi/ket_qua.json
export const END2END = {
  url: 'youtube.com/watch?v=PMRSb3ogWq4',
  input: '11,0 phút', rallies: '22 pha', output: '8,2 phút', percent: '75%',
  note: 'Video này có bình luận viên nói trong lúc đánh nên QC tắt điều kiện "khán giả im" (chế độ đó cho 6,6 phút nhưng cắt pha giữa chừng) — tách thuần theo camera sân: không bao giờ cắt giữa pha.',
};

export const DEMO_CAPTIONS: { fromSec: number; text: string }[] = [
  { fromSec: 0, text: 'Mặt nạ màu HSV ∩ trừ khung liên tiếp → ứng viên bóng (vài pixel)' },
  { fromSec: 3.5, text: 'Nối ứng viên bằng dự đoán vận tốc → vẽ quỹ đạo (đường vàng)' },
  { fromSec: 6.5, text: 'Vận tốc dọc đổi dấu rơi → bật: ứng viên BÓNG NẢY (chạm sàn)' },
  { fromSec: 9, text: 'Nảy 2 lần, không có cú chạm vợt ở giữa → ứng viên BÓNG CHẾT' },
];

export const ALGOS: { name: string; where: string }[] = [
  { name: 'Canny + Gauss', where: 'Detect biên → nhận camera sân' },
  { name: 'Biến đổi Hough', where: 'Vạch sân, mép lưới trên khuôn biên' },
  { name: 'Ngưỡng Otsu', where: 'Cụm cố định · khung sân · âm lượng' },
  { name: 'Hình thái học', where: 'Dọn mặt nạ, dung sai so khớp biên 1 px' },
  { name: 'Gán nhãn vùng', where: 'Tách cầu thủ, ứng viên bóng' },
  { name: 'Trừ ảnh', where: 'Trừ nền, tách vật chuyển động' },
  { name: 'Lọc nhiễu', where: 'Gauss trước Canny, NLM trước tăng nét' },
  { name: 'Wiener + unsharp', where: 'Giảm mờ, tăng nét ảnh vận động viên' },
];

export const RESULTS = [
  { value: '154', label: 'pha tách được (trận 67 phút)' },
  { value: '6,3 s', label: 'độ dài pha trung vị' },
  { value: '21,9 ph', label: 'tổng thời lượng các pha' },
  { value: '39/39', label: 'kiểm thử tự động pass' },
];

export const HONEST = [
  'Chưa có nhãn người gán → chưa đo F1; chất lượng pha kiểm bằng mắt',
  'Bóng nảy / bóng chết mới là ỨNG VIÊN từ quỹ đạo — người xem xác nhận mới xuất pha',
  'Timecode hiện lấy từ camera sân + khán giả im; sự kiện bóng–vợt–sàn tự động là việc mở V4',
];

export const REPO = 'github.com/huynevasleep/ivp501_project · nhánh qc/rally-highlights-review';
