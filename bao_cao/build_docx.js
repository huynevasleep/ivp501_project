// Dựng báo cáo nộp bài theo template "Project_Template_MSE_FPT University.docx"
// Chạy:  node build_docx.js   →  BaoCao_Nhom03_VideoLens.docx
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  Table, TableRow, TableCell, WidthType, BorderStyle, ImageRun, LevelFormat,
  ShadingType, TabStopType, TabStopPosition, LeaderType,
} = require('docx');

const TNR = 'Times New Roman';
const ARIAL = 'Arial';
const BODY = { font: TNR, size: 24 };            // 12 pt
const LINE15 = { line: 360, before: 120, after: 0 }; // giãn dòng 1,5; 6pt trước

// ---------- helpers ----------
const P = (text, opts = {}) => new Paragraph({
  spacing: LINE15, alignment: opts.align || AlignmentType.JUSTIFIED,
  children: (Array.isArray(text) ? text : [{ t: text, ...opts }]).map(r =>
    new TextRun({ text: r.t ?? r, ...BODY, bold: r.bold, italics: r.i, ...(r.size ? { size: r.size } : {}) })),
});
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, alignment: AlignmentType.CENTER, children: [new TextRun({ text, font: ARIAL, size: 32, bold: true })] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: ARIAL, size: 26, bold: true })] });
const bullet = (text) => new Paragraph({ numbering: { reference: 'dash', level: 0 }, spacing: { line: 360 }, alignment: AlignmentType.JUSTIFIED, children: [new TextRun({ text, ...BODY })] });

let figN = 0, tabN = 0;
const figures = [], tables = [];
const img = (path, w, h, captionText) => {
  figN += 1; figures.push(`Hình ${figN}. ${captionText}`);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 40 }, children: [new ImageRun({ type: path.endsWith('.png') ? 'png' : 'jpg', data: fs.readFileSync(path), transformation: { width: w, height: h } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [new TextRun({ text: `Hình ${figN}. ${captionText}`, font: TNR, size: 22, italics: true })] }),
  ];
};
const imgPair = (p1, p2, w, h, captionText) => {
  figN += 1; figures.push(`Hình ${figN}. ${captionText}`);
  const cell = (p) => new TableCell({ width: { size: 4650, type: WidthType.DXA }, borders: noBorders, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: 'jpg', data: fs.readFileSync(p), transformation: { width: w, height: h } })] })] });
  return [
    new Table({ alignment: AlignmentType.CENTER, columnWidths: [4650, 4650], width: { size: 9300, type: WidthType.DXA }, rows: [new TableRow({ children: [cell(p1), cell(p2)] })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 40, after: 160 }, children: [new TextRun({ text: `Hình ${figN}. ${captionText}`, font: TNR, size: 22, italics: true })] }),
  ];
};
const noBorders = { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } };
const thin = { style: BorderStyle.SINGLE, size: 4, color: '888888' };
const allBorders = { top: thin, bottom: thin, left: thin, right: thin, insideHorizontal: thin, insideVertical: thin };

const table = (caption, widths, header, rows) => {
  tabN += 1; tables.push(`Bảng ${tabN}. ${caption}`);
  const total = widths.reduce((a, b) => a + b, 0);
  const mk = (cells, isHead) => new TableRow({
    tableHeader: isHead,
    children: cells.map((c, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: isHead ? { type: ShadingType.CLEAR, fill: 'E8EDF4' } : undefined,
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({ spacing: { line: 276 }, children: [new TextRun({ text: String(c), font: TNR, size: 22, bold: isHead })] })],
    })),
  });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 40 }, children: [new TextRun({ text: `Bảng ${tabN}. ${caption}`, font: TNR, size: 22, italics: true })] }),
    new Table({ alignment: AlignmentType.CENTER, columnWidths: widths, width: { size: total, type: WidthType.DXA }, borders: allBorders, rows: [mk(header, true), ...rows.map(r => mk(r, false))] }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
};

// ---------- trang bìa (theo template) ----------
const coverLine = (text, size, opts = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: opts.before ?? 0, after: opts.after ?? 0 }, children: [new TextRun({ text, font: ARIAL, size, bold: opts.bold })] });
const cover = [
  coverLine('MINISTRY OF EDUCATION AND TRAINING', 28, { before: 600 }),
  coverLine('FPT UNIVERSITY', 26, { after: 1800 }),
  coverLine('Pickleball Rally Segmentation and Highlight Generation', 36, { bold: true }),
  coverLine('from Match Videos', 36, { bold: true, after: 200 }),
  coverLine('(Tách pha bóng pickleball và dựng video highlight)', 24, { after: 1200 }),
  coverLine('by', 24, { after: 200 }),
  coverLine('Lê Hữu Huy', 26), coverLine('Nguyễn Xuân Kha', 26),
  coverLine('Nguyễn Hồ Công Anh', 26), coverLine('Đoàn Nguyễn Tuấn Anh', 26),
  coverLine('Group 03', 24, { before: 200, after: 1200 }),
  coverLine('A group project submitted in conformity with the requirements', 22),
  coverLine('for the fulfillment of the course “Image and Video Processing”', 22, { after: 800 }),
  coverLine('Lecturer: Dr. Nguyen Ngoc Truong Minh', 24, { after: 800 }),
  coverLine('© Copyright by Group 03 — 2026', 22),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------- abstract ----------
const abstract = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 }, children: [new TextRun({ text: 'Tóm tắt (Abstract)', font: ARIAL, size: 32, bold: true })] }),
  P('Báo cáo trình bày hệ thống tách pha bóng pickleball từ video trận đấu và ghép toàn bộ các pha (kèm timecode bắt đầu/kết thúc) thành video highlight, chỉ dùng kỹ thuật xử lý ảnh kinh điển chạy CPU. Nhận xét then chốt: trong lúc giao tranh, đài truyền hình luôn dùng camera cố định quay toàn sân và khán giả im lặng. Hệ thống nhận camera sân bằng khuôn biên Canny của từng cụm K-means (so khớp Dice hai chiều, xác nhận vạch sân bằng biến đổi Hough), nhận khoảng im lặng bằng ngưỡng Otsu trên âm lượng, làm mượt chuỗi quyết định rồi xuất từng pha trọn vẹn bằng FFmpeg. Trên trận thử 67 phút, hệ thống tách được 154 pha (trung vị 6,3 giây); trên video thực tế, pipeline quỹ đạo vẽ được đường bay của bóng tới điểm nảy khi giới hạn vùng sân và đề xuất ứng viên bóng nảy/bóng chết theo luật hai lần nảy. Thuật toán Otsu được nhóm tự cài đặt và kiểm chứng khớp OpenCV. Toàn bộ 39 kiểm thử tự động pass; số liệu trên video thực tế và kiểm thử đều kèm script chạy lại. Hạn chế chính — chưa có nhãn người gán để đo F1 và ranh giới pha còn gián tiếp — được phân tích cùng hướng phát triển.'),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------- mục lục (tĩnh, điền số trang sau lần render đầu) ----------
const TOC = [
  ['Tóm tắt (Abstract)', 2], ['1. Giới thiệu', 4], ['2. Tổng quan phương pháp liên quan', 6],
  ['3. Phương pháp (dữ liệu + thuật toán)', 7], ['4. Thực nghiệm và kết quả', 13],
  ['5. Thảo luận', 17], ['6. Kết luận', 18], ['Tài liệu tham khảo', 19], ['Phụ lục', 20],
];
const tocPage = () => [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 }, children: [new TextRun({ text: 'Mục lục', font: ARIAL, size: 32, bold: true })] }),
  ...TOC.map(([t, p]) => new Paragraph({
    tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX, leader: LeaderType.DOT }],
    spacing: { line: 360 },
    children: [new TextRun({ text: t, ...BODY }), new TextRun({ text: `\t${p}`, ...BODY })],
  })),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400, after: 240 }, children: [new TextRun({ text: 'Danh mục hình và bảng', font: ARIAL, size: 32, bold: true })] }),
  ...figures.map(f => new Paragraph({ spacing: { line: 300 }, children: [new TextRun({ text: f, font: TNR, size: 22 })] })),
  ...tables.map(t => new Paragraph({ spacing: { line: 300 }, children: [new TextRun({ text: t, font: TNR, size: 22 })] })),
];

// ---------- 1. Giới thiệu ----------
const gioiThieu = [
  H1('1. Giới thiệu'),
  H2('1.1. Bài toán và động lực'),
  P('Pickleball phát triển nhanh tại Việt Nam, kéo theo nhu cầu dựng video highlight từ các trận đấu dài. Việc cắt tay một trận 60–90 phút tốn nhiều giờ công; người xem lại đòi hỏi mỗi pha phải trọn vẹn — từ lúc chuẩn bị giao bóng đến khi kết thúc điểm — thay vì các lát cắt rời rạc. Đầu vào của hệ thống là một file video trận đấu (phát sóng hoặc tự quay); đầu ra là (i) danh sách pha bóng với timecode bắt đầu/kết thúc, (ii) video highlight ghép từ các pha trọn vẹn cùng bảng ánh xạ timecode nguồn → highlight, và (iii) tùy chọn ảnh vận động viên đã tăng cường.'),
  P('Về nghiệp vụ, pickleball có luật hai lần nảy (two-bounce rule): cú giao bóng và cú trả giao đều phải để bóng chạm sàn trước khi đánh, nên “bóng chạm sàn” chưa chắc kết thúc pha; pha chỉ chết khi bóng chạm sàn mà không còn cú chạm vợt nào sau đó, bóng ra ngoài, hoặc vào lưới [10]. Ngoài ra đài truyền hình thường đổi góc máy ngay giữa pha (61/154 pha của trận thử), nên “chuyển cảnh” cũng không phải ranh giới pha. Hai đặc thù này loại trực tiếp cách tóm tắt video dựa trên chuyển cảnh thông thường.'),
  H2('1.2. Mục tiêu'),
  bullet('Xác định pha bóng: tìm thuật toán và chuỗi bước xử lý ảnh/âm thanh để định vị timecode bắt đầu và kết thúc của từng pha.'),
  bullet('Ghép toàn bộ pha thành video highlight, mỗi pha lấy trọn, giữ thứ tự thời gian và âm thanh gốc.'),
  bullet('(Mở rộng) Ảnh vận động viên góc ngang: chọn khoảnh khắc vung vợt, khử nhiễu, tăng nét, giảm mờ.'),
  H2('1.3. Đóng góp chính'),
  bullet('Phương pháp nhận camera sân không cần huấn luyện: khuôn biên Canny theo cụm K-means, so khớp Dice hai chiều với dung sai 1 pixel, xác nhận bằng đường thẳng Hough của vạch sân (mục 3.2).'),
  bullet('Quy tắc pha bóng “camera sân ∧ khán giả im” với mọi ngưỡng chọn tự động bằng Otsu trên chính video, kèm làm mượt chuỗi quyết định và luật đệm giữ trọn cú giao bóng lẫn tiếng reo (mục 3.3).'),
  bullet('Pipeline bằng chứng quỹ đạo bóng ở FPS gốc: vẽ quỹ đạo, ứng viên bóng nảy (đổi dấu vận tốc dọc) và bóng chết theo luật hai lần nảy, luôn phân biệt rõ “ứng viên” với “sự kiện người xác nhận” (mục 3.5).'),
  bullet('Bộ kiểm thử 39 test trên dữ liệu tổng hợp, thí nghiệm ca biên, script tái lập cho mọi số liệu, và tự cài đặt thuật toán Otsu có kiểm chứng với OpenCV (mục 3.7, 4.4).'),
  P('Ràng buộc nhóm tự đặt: chỉ dùng kỹ thuật kinh điển của môn học chạy CPU (không mô hình học sâu), và báo cáo nói đúng mức bằng chứng: điều gì mới kiểm bằng mắt, điều gì chưa đo được đều ghi rõ.'),
];

// ---------- 2. Tổng quan ----------
const tongQuan = [
  H1('2. Tổng quan phương pháp liên quan'),
  P('Tóm tắt video (video summarization) thường theo hai hướng. Hướng chọn khung/đoạn đại diện tối ưu độ bao phủ nội dung, với các bộ dữ liệu chuẩn TVSum [7] và SumMe [8]: video được chia theo chuyển cảnh (sai khác histogram màu, sai khác khung), từng đoạn được chấm điểm theo đặc trưng thị giác rồi chọn theo ngân sách thời lượng. Nhóm dùng đúng hướng này làm baseline (mục 3.1) và đo được vì sao nó thất bại với thể thao: đoạn bị cắt vụn trung vị 1 giây, đứt ngay lúc chuẩn bị giao bóng.'),
  P('Hướng thứ hai chuyên cho thể thao: phát hiện sự kiện (event detection) dựa trên cấu trúc phát sóng — loại góc máy, âm thanh khán giả, bảng điểm. Hệ thống của nhóm thuộc hướng này nhưng chỉ dùng khối kinh điển: phát hiện biên Canny [1] với tiền xử lý Gauss; ngưỡng tự động Otsu [2] cho cả tín hiệu hình (độ khớp khuôn biên) lẫn tiếng (âm lượng); biến đổi Hough [3] xác nhận vạch sân; phân cụm K-means trên bố cục màu Lab thu nhỏ để gom góc máy. Với bằng chứng quỹ đạo, nhóm dùng trừ khung + thành phần liên thông và nối ứng viên bằng dự đoán vận tốc — dạng giản lược của các bộ bám đối tượng kinh điển; trừ nền MOG2 [4] tách cầu thủ; luồng quang Farnebäck [5] đo hoạt động trên sân cho pipeline video tự quay. Khối ảnh tĩnh dùng khử nhiễu Non-Local Means [9], lọc nghịch đảo có điều hòa họ Wiener [6] và unsharp mask.'),
  P('So với các hệ thống highlight thể thao dùng học sâu (nhận diện bóng/person detector), cách tiếp cận kinh điển đổi độ chính xác tiềm năng lấy ba thứ: chạy CPU thời gian ngắn, giải thích được từng quyết định bằng tín hiệu trung gian (khuôn biên, ngưỡng Otsu, dòng thời gian), và không cần dữ liệu huấn luyện — phù hợp ràng buộc môn học. Giới hạn kèm theo được phân tích ở mục 5.'),
];

// ---------- 3. Phương pháp ----------
const phuongPhap = [
  H1('3. Phương pháp (dữ liệu + thuật toán)'),
  H2('3.1. Kiến trúc tổng thể và baseline so sánh'),
  P('Hệ thống gồm bốn khối: (A) tách pha từ video phát sóng; (B) bằng chứng quỹ đạo bóng và sự kiện; (C) ghép highlight với timecode; (D) ảnh vận động viên (tùy chọn). Baseline so sánh là cách tóm tắt video tổng quát: chia video theo chuyển cảnh (độ lệch histogram HSV + sai khác khung, ngưỡng thích nghi trung vị/MAD), chấm điểm từng mẩu ≤ 4 giây theo chuyển động/độ nét/khuôn mặt rồi chọn theo ngân sách. Trên trận thử 67 phút, baseline báo 1.243 lần “chuyển cảnh” (người chạy và bóng bay làm histogram đổi) và cho 519 đoạn trung vị 1,0 giây — đúng hiện tượng người xem phàn nàn: “cắt ngay đoạn chuẩn bị phát bóng, chưa có gì gọi là highlight”. Cải tiến của nhóm thay đơn vị lựa chọn từ “mẩu thời gian” sang “pha bóng trọn vẹn”.'),
  H2('3.2. Nhận camera sân bằng khuôn biên (detect biên + hình học)'),
  P('Video được lấy mẫu 2 khung/giây, thu về 320×180. Mỗi khung được lọc Gauss 3×3 để giảm nhiễu cảm biến rồi tính bản đồ biên Canny với hai ngưỡng 50/150 [1]. Hình 1 minh họa từng bước trên một khung thật của video thử nghiệm: ảnh gốc → ảnh xám → sau Gauss → bản đồ biên; hàng dưới so sánh với hai bộ phát hiện gradient Prewitt và Sobel ở cùng điều kiện — Canny cho biên mảnh một pixel và ít đứt gãy hơn hẳn, là lý do nhóm chọn nó làm nền của khuôn biên. Bố cục màu của khung là ảnh Lab thu về 16×9 (vector 432 chiều); K-means (K = 12, seed cố định) gom các khung cùng góc máy vào một cụm.'),
  ...img('img/canny_tung_buoc.png', 600, 283, 'Detect biên từng bước trên khung thật: (a) ảnh gốc → (b) ảnh xám → (c) giảm nhiễu Gauss 3×3 → (d) biên Canny 50/150; hàng dưới: (e) phần Gauss đã thay đổi, (f)–(h) so sánh Prewitt / Sobel / Canny. Sinh lại bằng reports/qc/minh_hoa_bien.py.'),
  P('Khuôn biên của mỗi cụm là trung vị bản đồ biên (pixel là biên ở ít nhất một nửa số khung của cụm). Camera cố định giữ vạch sân, mép lưới, mép bảng quảng cáo ở đúng vị trí suốt trận nên khung của nó khớp khuôn của chính cụm; cảnh quay tay thì không. Độ khớp giữa một khung và một khuôn là hệ số Dice hai chiều: recall (biên của khuôn xuất hiện trong khung) và precision (biên của khung nằm trên khuôn), mỗi chiều cho dung sai lệch 1 pixel bằng phép giãn nở hình thái học; Dice = 2·P·R/(P+R). Chiều precision giữ cảnh đông đúc (khán giả, flycam) — nơi biên dày đặc phủ kín mọi khuôn — ở mức thấp.'),
  P('Cụm máy cố định là phía cao của ngưỡng Otsu trên log độ-khớp-tự-thân của các cụm (trọng số theo số khung); cụm camera sân là cụm cố định mà khuôn chứa các đoạn thẳng do HoughLinesP tìm được — chính là vạch sân và mép lưới. Mỗi khung sau đó được chấm bằng độ khớp cao nhất với các khuôn sân và so với một ngưỡng Otsu thứ hai; nhờ vậy khung sân lỡ rơi vào cụm khác vẫn được nhận. Hai cách đã thử và loại: đếm vạch trắng Hough trực tiếp trên từng khung (nhận nhầm áo trắng, băng rôn, chữ) và diện tích màu sàn (áo, băng rôn cùng màu lẫn vào). Hình 2 chạy đúng chuỗi này trên video thử nghiệm: khuôn biên của cụm sân, sáu vạch Hough xác nhận vạch sân/lưới, khung cùng camera đạt Dice 0,87 (nhận) trong khi khung của video khác chỉ 0,32 (loại).'),
  ...img('img/khuon_bien_va_dice.png', 620, 151, 'Nhận camera sân trên khung thật: (a) khuôn biên trung vị của cụm K-means; (b) vạch Hough trên khuôn → là sân; (c)–(d) so khớp Dice: xanh = biên khớp khuôn, đỏ = lệch khuôn. Sinh lại bằng reports/qc/minh_hoa_bien.py.'),
  ...img('img/cum_camera.jpg', 400, 455, 'Khung mẫu của 12 cụm camera K-means trên trận thử; ba cụm sân được nhận tự động bằng khuôn biên.'),
  H2('3.3. Khoảng im lặng và ghép pha (làm mượt chuỗi quyết định)'),
  P('Âm thanh được tách mono 8 kHz; âm lượng là RMS trong cửa sổ 0,5 giây quanh mỗi khung mẫu, đổi sang dBFS. Khán giả im trong lúc đánh và reo khi kết thúc điểm, nên phân bố âm lượng của trận có hai đỉnh; ngưỡng Otsu [2] tách chúng mà không cần chỉnh tay. Chuỗi nhị phân “pha = camera sân ∧ im” được làm mượt như phép đóng/mở hình thái học một chiều: lấp lỗ ≤ 1 giây (một cú đổi góc máy hay tiếng hét giữa pha không cắt đôi pha) và bỏ run ngắn hơn 1,5 giây. Mỗi pha được đệm +1 giây phía trước — nhưng không lùi quá đầu cảnh sân, tránh dính mặt cận trước đó — và +2 giây phía sau để giữ trọn cú giao bóng lẫn tiếng reo; hai pha chồng phần đệm thì cắt tại trung điểm khoảng nghỉ.'),
  ...img('img/am_luong.png', 580, 232, 'Phân bố âm lượng của trận thử; vạch đứt là ngưỡng Otsu −26,3 dBFS tách “im” và “ồn”.'),
  ...img('img/dong_thoi_gian.png', 600, 253, 'Dòng thời gian 150 giây: dải trên là camera sân, dải vàng là pha tách được (đã đệm), vạch dưới là pha được chọn vào highlight 10%.'),
  H2('3.4. Chấm điểm và chọn pha'),
  P('Điểm của một pha là trung bình hai thứ hạng phần trăm trong trận: độ dài pha và âm lượng lớn nhất trong 3 giây sau pha (tiếng reo); dùng thứ hạng để giây và dB về cùng thang 0–1. Khi người dùng đặt ngân sách thời lượng, pha được chọn theo greedy điểm giảm dần hoặc quy hoạch động knapsack 0/1 — một pha hoặc lấy trọn, hoặc bỏ, không bao giờ cắt ngắn; mặc định hệ thống giữ toàn bộ pha. FFmpeg cắt từng pha (H.264 + AAC) rồi nối đúng thứ tự; timecode ghi vào report.json và timecodes.csv (ánh xạ nguồn → highlight).'),
  H2('3.5. Bằng chứng quỹ đạo bóng: vẽ quỹ đạo, bóng nảy, bóng chết'),
  P('Bóng ở 480p chỉ rộng vài pixel: tách màu HSV đơn thuần cho 54–176 vật màu vàng mỗi khung (Hình 6). Pipeline ứng viên chạy ở FPS gốc trong vùng sân người dùng khoanh (ROI): mặt nạ màu vàng/xanh HSV ∩ mặt nạ chuyển động từ trừ khung liên tiếp → thành phần liên thông lọc theo diện tích, tỉ lệ cạnh và độ đặc → nối ứng viên qua khung bằng dự đoán vận tốc với cổng khoảng cách; mất dấu hoặc cắt cảnh thì mở track mới, tuyệt đối không nội suy thành “quan sát”. Quỹ đạo được vẽ chồng lên video cùng nhãn “BALL CANDIDATE — NOT VERIFIED”, kèm CSV tọa độ từng khung.'),
  ...img('img/vat_mau_vang.jpg', 600, 168, 'Vật màu vàng tách theo HSV (khung tím): chỉ màu là không đủ để nhận bóng.'),
  P('Từ quỹ đạo, hệ thống đề xuất ba loại sự kiện, tất cả ở trạng thái chưa xác nhận: (i) đổi hướng — cosine giữa hai vector vận tốc liên tiếp < 0,3, dấu hiệu cú chạm vợt; (ii) bóng nảy — vận tốc dọc màn hình đổi dấu từ rơi sang bật trên track liên tục, ngưỡng 0,2% chiều cao khung để nhiễu trọng tâm ở độ phân giải cao không bị tính; (iii) bóng chết — lần nảy thứ hai trong ≤ 2,5 giây sau lần nảy trước mà không có ứng viên đổi hướng nào ở giữa, đúng luật hai lần nảy; chuỗi nảy bị reset khi có đổi hướng, mất dấu, cắt cảnh hoặc track mới. Máy trạng thái xuất pha chỉ chấp nhận cặp giao bóng – kết thúc đã được người xem xác nhận trên giao diện: bóng nảy một lần hay mất dấu không bao giờ tự đóng pha, pha còn mở bị cảnh báo thay vì âm thầm ghép.'),
  H2('3.6. Ảnh vận động viên (mục tiêu mở rộng)'),
  P('Trong mỗi pha đã chọn: trừ nền MOG2 [4] tách người chuyển động; mặt nạ được dọn bằng phép mở/đóng rồi gán nhãn thành phần liên thông; giữ thành phần cao hơn 12% khung, cao hơn rộng và đứng trên màu sàn (histogram hue–saturation phần dưới khung). “Khoảnh khắc ra lực” là cực đại thay đổi hình dáng (1 − IoU mặt nạ hai khung liên tiếp); quanh đó chọn khung nét nhất theo phương sai Laplacian. Ảnh được khử nhiễu Non-Local Means [9], tùy chọn lọc nghịch đảo có điều hòa với PSF vệt thẳng người dùng khai báo (họ Wiener [6]) rồi unsharp mask; luôn lưu cặp ảnh gốc/sau cùng thông số JSON, không sinh chi tiết mới.'),
  H2('3.7. Thuật toán tự cài đặt và kiểm chứng; các kỹ thuật đã áp dụng'),
  P('Nhóm tự cài đặt thuật toán Otsu 1-D tổng quát (chạy trên giá trị thực bất kỳ, hỗ trợ trọng số mẫu — cần cho log độ khớp theo cụm và âm lượng dBFS, điều hàm OpenCV không làm được vì chỉ nhận ảnh 8-bit). Kiểm chứng: trên ảnh hai đỉnh, ngưỡng của bản tự cài lệch không quá 2 mức xám so với cv2.threshold(THRESH_OTSU) (kiểm thử test_otsu_matches_opencv_reference). Hệ số Dice hai chiều, bộ nối quỹ đạo, máy trạng thái pha và knapsack 0/1 cũng do nhóm tự viết. Bảng 1 liệt kê các kỹ thuật đã áp dụng và vị trí sử dụng.'),
  ...table('Các kỹ thuật xử lý ảnh/video đã áp dụng và vị trí sử dụng', [3600, 5500],
    ['Kỹ thuật', 'Vị trí sử dụng'],
    [
      ['Canny + tiền xử lý Gauss', 'Detect biên → khuôn biên nhận camera sân'],
      ['Biến đổi Hough đường thẳng', 'Xác nhận vạch sân, mép lưới trên khuôn biên'],
      ['Ngưỡng Otsu (tự cài đặt)', 'Cụm cố định; khung sân; âm lượng khán giả'],
      ['Hình thái học giãn/co, mở/đóng', 'Dung sai so khớp biên 1 px; dọn mặt nạ; làm mượt chuỗi 1-D'],
      ['Gán nhãn thành phần liên thông', 'Tách cầu thủ; ứng viên bóng'],
      ['Trừ ảnh / trừ khung liên tiếp', 'Mặt nạ chuyển động cho ứng viên bóng'],
      ['Lọc nhiễu không gian; Non-Local Means', 'Trước Canny; trước tăng nét ảnh'],
      ['Wiener (nghịch đảo điều hòa) + unsharp mask', 'Giảm mờ, tăng nét ảnh vận động viên'],
      ['Luồng quang Farnebäck; K-means (tự nghiên cứu thêm)', 'Hoạt động trên sân (video tự quay); gom góc máy'],
    ]),
  P([{ t: 'Lưu ý minh bạch: ', bold: true }, { t: 'luồng quang Farnebäck, MOG2, K-means và Non-Local Means là phần nhóm tự nghiên cứu thêm ngoài nội dung thực hành của môn, xây trên nền các kỹ thuật đã học (trừ ảnh → trừ nền; lọc không gian → làm mượt chuỗi thời gian).' }]),
];

// ---------- 4. Thực nghiệm ----------
const thucNghiem = [
  H1('4. Thực nghiệm và kết quả'),
  H2('4.1. Dữ liệu và thiết lập'),
  bullet('Trận pickleball phát sóng 67 phút, 854×480, 29,97 fps — dữ liệu chính để đo pipeline tách pha (video do nhóm thu thập; link tải và ngày truy cập ghi trong README của repo).'),
  bullet('Hai video một-pha thực tế (YouTube Shorts, tải bằng yt-dlp, truy cập 09/11/2026): (1) youtube.com/shorts/WQo-yvMozaI — trong nhà, đánh đôi, 1080×1920, 24 fps, 14,3 s; (2) youtube.com/shorts/eqp3tj8Y_Hg — ngoài trời có mái, 720×1280, 30 fps, 12,4 s.'),
  bullet('Video tổng hợp trong bộ kiểm thử: sân vẽ vạch + người di chuyển; quả bóng chuyển động parabol nảy hai lần.'),
  P('Môi trường: Python 3.13+, OpenCV [11], scikit-learn, SciPy, FFmpeg (imageio-ffmpeg), CPU. Phân tích trận 67 phút (8.022 khung mẫu) mất 107 giây; xuất highlight 10% mất 14 giây. Mọi kết quả chạy lại bằng các lệnh ở Phụ lục B.'),
  H2('4.2. Tách pha trên trận 67 phút'),
  P('Hệ thống tách được 154 pha; độ dài p10/trung vị/p90/max = 1,5 / 6,3 / 18,5 / 33,5 giây; tổng 21,9 phút chơi trên 37,5 phút camera sân. Ba cụm sân tự nhận có Dice tự thân 0,89–0,92 với khuôn 7.500–7.800 điểm biên và 5–14 đường Hough; chín cụm còn lại khớp ≤ 0,13. Khung sân đạt điểm 0,88 (p10) – 0,92 (trung vị), khung khác trung vị 0,42; ngưỡng Otsu 0,66 tách gọn hai nhóm. Ngưỡng âm lượng Otsu −26,3 dBFS (camera sân lúc im −30,4 dB; lúc ồn −21,8 dB; cảnh khác −21,1 dB, theo trung vị). Kiểm tra bằng mắt các pha được chọn: bắt đầu đúng lúc chuẩn bị giao bóng, kết thúc sau tiếng reo.'),
  ...img('img/do_dai_pha.png', 560, 196, 'Phân bố độ dài 154 pha tách được trên trận thử 67 phút.'),
  ...table('Highlight theo ngân sách thời lượng (trận 67 phút)', [2200, 1800, 1900, 2600],
    ['Ngân sách', 'Số pha', 'Tổng thời lượng', 'Độ dài mỗi pha'],
    [['5%', '7', '3,3 phút', '15,5–36,5 s'], ['10%', '17', '6,7 phút', '12,5–36,5 s'], ['15%', '29', '10,0 phút', '3,3–36,5 s']]),
  ...img('img/pha_duoc_chon.jpg', 600, 270, 'Bốn pha điểm cao nhất, mỗi hàng một pha: 1 s trước giao bóng, lúc giao bóng, giữa pha, cuối pha, tiếng reo.'),
  P([{ t: 'So với baseline: ', bold: true }, { t: 'cùng trận, baseline chuyển cảnh cho 519 đoạn trung vị 1,0 giây và cắt ngang lúc chuẩn bị giao bóng; pipeline pha trọn vẹn cho 154 đơn vị có nghĩa, trung vị 6,3 giây. Chưa có nhãn người gán nên chưa đo F1 — công cụ đánh giá (ghép khoảng một-một tại IoU ≥ 0,5, MAE mốc đầu/cuối) đã có sẵn trong hệ thống chờ nhãn.' }]),
  H2('4.3. Bằng chứng quỹ đạo trên hai video thực tế'),
  ...table('Kết quả trên hai video một-pha (script: reports/qc/danh_gia_video_that.py)', [2700, 3200, 3200],
    ['Phép đo', 'Video 1 (trong nhà)', 'Video 2 (ngoài trời)'],
    [
      ['Nhận camera sân', '34% khung đạt (camera rung tay làm khuôn biên trôi) → chỉ tách được 3 s cuối', '84% khung đạt → tách đúng cả clip là một pha trọn [0 → 12,4 s]'],
      ['Bám bóng toàn khung', '97,7% khung nối được ứng viên', '87,4% nhưng bám nhầm vật vàng tĩnh trên hàng rào (kiểm bằng mắt)'],
      ['Bám bóng + ROI vùng sân', 'Nhiều ứng viên đổi hướng thật (đánh đôi tốc độ cao trên lưới)', 'Bám đúng bóng; quỹ đạo vẽ đúng đường rơi tới điểm nảy thật tại ~3,0 s'],
    ]),
  ...imgPair('img/overlay_bam_nham.jpg', 'img/overlay_bam_dung.jpg', 240, 427,
    'Video 2 trước/sau khi giới hạn ROI vùng sân. Trái: tracker khóa vào vật vàng tĩnh trên hàng rào (vòng đỏ, góc phải trên) dù “87% khung nối được”. Phải: bám đúng bóng, quỹ đạo (đường vàng) vẽ đường rơi tới điểm nảy thật.'),
  P('Ba kết luận đo được: (i) vẽ quỹ đạo hoạt động trên video thực tế; (ii) tỉ lệ khung nối được không phải độ chính xác — có phản ví dụ cụ thể ở Hình 9, nên mọi lần chạy phải kiểm overlay bằng mắt và giới hạn ROI; (iii) đổi dấu vận tốc dọc chưa phân biệt được bóng chạm sàn với cú vợt đánh bổng lên, nên ứng viên bóng chết chỉ dùng làm gợi ý cho người xác nhận, chưa làm mốc kết thúc pha tự động.'),
  H2('4.4. Kiểm thử tự động, kiểm chứng và ablation'),
  P('Toàn bộ 39 kiểm thử pass (pytest): tách pha trên dòng thời gian tổng hợp (pha đúng mốc, đệm không lùi quá đầu cảnh sân, chồng đệm cắt giữa khoảng nghỉ), nhận camera sân từ biên (cảnh quay tay và cảnh tĩnh không vạch bị loại; video một cụm vẫn giữ được camera sân — lỗi phát hiện trong quá trình QC, đã sửa kèm test hồi quy), bóng nảy/bóng chết trên video tổng hợp (hai lần nảy không chạm vợt → đúng một ứng viên bóng chết; chèn một cú đổi hướng ở giữa → không còn), Otsu tự cài khớp OpenCV trong 2 mức xám, xuất MP4 đúng từng pha, và metric ghép khoảng một-một. Về ablation: khối nhận camera sân từng dùng chuyển động quang học trung vị theo cụm, khi thay bằng khuôn biên kết quả gần như trùng (153 so với 154 pha) nhưng bỏ được phụ thuộc vào luồng quang; công cụ experiments.py so sánh sáu biến thể lựa chọn (uniform/motion/hybrid/no-diversity/no-motion/knapsack) cho phần phòng thí nghiệm.'),
  H2('4.5. Sản phẩm demo'),
  P('Ứng dụng Streamlit chạy cục bộ: tải video → toàn bộ pha đề xuất → xem video riêng từng pha → chỉnh mốc → xuất từng pha MP4 + ZIP + timecodes.csv; các công cụ kiểm tra bóng, xác nhận sự kiện, đánh giá F1 theo nhãn và ảnh vận động viên nằm cùng giao diện. Video demo nộp kèm được dựng bằng Remotion từ chính kết quả hệ thống.'),
];

// ---------- 5. Thảo luận ----------
const thaoLuan = [
  H1('5. Thảo luận'),
  H2('5.1. Phân tích lỗi'),
  bullet('Bám nhầm vật tĩnh: rung máy nhẹ làm vật vàng bất động lọt mặt nạ chuyển động, khởi tạo lại chọn blob lớn nhất nên tracker khóa vào nó (Hình 9, trái). Khắc phục hiện tại: ROI vùng sân; gốc rễ cần mô hình nền tốt hơn hoặc nhận cầu thủ.'),
  bullet('Nhập nhằng bóng nảy / cú vợt đánh bổng: cả hai đều đổi dấu vận tốc dọc. Trên video 2, ngưỡng 1 px/khung sinh nảy giả theo nhịp rung còn ngưỡng 0,2% chiều cao lọc sạch nhiễu nhưng rụng một ứng viên bóng chết cuối pha có vẻ hợp lý — cần vị trí cầu thủ để phân xử.'),
  bullet('Camera lia theo bóng bị loại khỏi “camera sân” nên pha chiếu bằng góc đó bị mất hoặc cắt đôi; ví dụ phút 10:55 của trận thử, đài chen góc cận giữa pha dài hơn 1 giây làm pha bị tách sai.'),
  bullet('43/154 pha chỉ dài 1,5–3 giây, nhiều khả năng là khoảng im giữa hai điểm; cú giao bóng ăn điểm trực tiếp bị lép khi chấm theo độ dài.'),
  H2('5.2. Hạn chế'),
  P('Ranh giới pha hiện gián tiếp qua camera sân + khán giả im: lệch theo phản ứng khán giả và không dùng được cho môn ồn suốt trận. Chưa có nhãn người gán nên mọi nhận định chất lượng là kiểm bằng mắt. Các số đo trên trận 67 phút đo bằng mã của nhánh tác giả; K = 12 và các ngưỡng hình dạng mới thử trên một trận phát sóng và hai clip ngắn. Bóng nảy/bóng chết là ứng viên hình dạng quỹ đạo, chưa phải phát hiện tiếp xúc.'),
  H2('5.3. Hướng phát triển'),
  bullet('Gán nhãn start/end cho ít nhất một phần trận thử, đo precision/recall/F1 tại IoU 0,3/0,5/0,7 và MAE mốc đầu/cuối; tách validation/test theo trận.'),
  bullet('Phân biệt cú chạm vợt với bóng nảy bằng vị trí cầu thủ (đã có khối tách người bằng MOG2); khi ổn, thay timecode gián tiếp bằng sự kiện bóng–vợt–sàn.'),
  bullet('Đọc bảng điểm bằng so khớp mẫu chữ số làm mốc kết thúc pha độc lập với tiếng reo; giữ cảnh camera lia bằng bám khuôn biên có bù dịch chuyển.'),
  bullet('Thu video ≥ 1080p có góc ngang để hoàn thiện mục tiêu ảnh vận động viên.'),
];

// ---------- 6. Kết luận ----------
const ketLuan = [
  H1('6. Kết luận'),
  P('Nhóm xây dựng hệ thống hoàn chỉnh tách pha bóng pickleball và dựng highlight trọn pha chỉ bằng kỹ thuật xử lý ảnh kinh điển: Canny + khuôn biên + Hough nhận camera sân, Otsu tự cài (kiểm chứng với OpenCV) chọn mọi ngưỡng, làm mượt chuỗi quyết định và luật đệm cho timecode từng pha; pipeline quỹ đạo vẽ đường bay của bóng và đề xuất ứng viên bóng nảy/bóng chết theo luật hai lần nảy. Trên trận thử 67 phút hệ thống tách 154 pha trọn vẹn (so với 519 lát cắt 1 giây của baseline); trên video thực tế quỹ đạo bám đúng bóng khi giới hạn vùng sân. Toàn bộ 39 kiểm thử pass; số liệu trên video thực tế và kiểm thử kèm script chạy lại, riêng các số đo trận 67 phút là kết quả đo của nhóm trên một trận (việc mở: script tái lập trọn gói). Đóng góp lớn nhất về phương pháp làm việc là ranh giới bằng chứng rõ ràng: hệ thống phân biệt điều đo được, điều kiểm bằng mắt và điều cần người xác nhận — nền tảng để các bước tự động hóa tiếp theo thay thế dần từng khối mà không phá vỡ độ tin cậy.'),
];

// ---------- Tài liệu tham khảo ----------
const refs = [
  'J. Canny, “A computational approach to edge detection,” IEEE Trans. Pattern Anal. Mach. Intell., vol. PAMI-8, no. 6, pp. 679–698, 1986.',
  'N. Otsu, “A threshold selection method from gray-level histograms,” IEEE Trans. Syst., Man, Cybern., vol. 9, no. 1, pp. 62–66, 1979.',
  'R. O. Duda and P. E. Hart, “Use of the Hough transformation to detect lines and curves in pictures,” Commun. ACM, vol. 15, no. 1, pp. 11–15, 1972.',
  'Z. Zivkovic, “Improved adaptive Gaussian mixture model for background subtraction,” in Proc. ICPR, 2004, pp. 28–31.',
  'G. Farnebäck, “Two-frame motion estimation based on polynomial expansion,” in Proc. SCIA, 2003, pp. 363–370.',
  'R. C. Gonzalez and R. E. Woods, Digital Image Processing, 4th ed. Pearson, 2018 (lọc Wiener, khôi phục ảnh).',
  'Y. Song, J. Vallmitjana, A. Stent, and A. Jaimes, “TVSum: Summarizing web videos using titles,” in Proc. CVPR, 2015, pp. 5179–5187.',
  'M. Gygli, H. Grabner, H. Riemenschneider, and L. Van Gool, “Creating summaries from user videos,” in Proc. ECCV, 2014, pp. 505–520.',
  'A. Buades, B. Coll, and J.-M. Morel, “A non-local algorithm for image denoising,” in Proc. CVPR, 2005, pp. 60–65.',
  'USA Pickleball, “Basic rules overview” (luật hai lần nảy), https://usapickleball.org/rules/summary/, truy cập 09/11/2026.',
  'G. Bradski, “The OpenCV library,” Dr. Dobb’s Journal of Software Tools, 2000.',
];
const taiLieu = [
  H1('Tài liệu tham khảo'),
  ...refs.map((r, i) => new Paragraph({ spacing: { line: 300, after: 80 }, alignment: AlignmentType.JUSTIFIED, children: [new TextRun({ text: `[${i + 1}] ${r}`, ...BODY })] })),
];

// ---------- Phụ lục ----------
const phuLuc = [
  H1('Phụ lục'),
  H2('Phụ lục A. Phân công công việc (Nhóm 03)'),
  ...table('Phân công công việc', [3200, 5900],
    ['Thành viên', 'Phần việc chính'],
    [
      ['Lê Hữu Huy', 'Pipeline tách pha; nhận camera sân bằng khuôn biên; quản lý repo'],
      ['Nguyễn Xuân Kha', 'Bám bóng, sự kiện quỹ đạo; đánh giá trên video thực tế'],
      ['Nguyễn Hồ Công Anh', 'Thuật toán tách pha; đo đạc trận 67 phút; báo cáo kỹ thuật'],
      ['Đoàn Nguyễn Tuấn Anh', 'QC, kiểm thử tự động; xuất video + timecode; video demo'],
    ]),
  P([{ t: 'Mã nguồn: ', bold: true }, { t: 'github.com/huynevasleep/ivp501_project (nhánh qc/rally-highlights-review). Phân công ở bảng trên đối chiếu được với lịch sử commit của repo; báo cáo QC nội bộ và các việc mở nằm trong thư mục reports/.' }]),
  H2('Phụ lục B. Hướng dẫn chạy lại'),
  P('Cài đặt và chạy toàn bộ kiểm thử, giao diện và các script tái lập số liệu:'),
  ...['python3 -m venv .venv && .venv/bin/pip install -r requirements.txt',
      '.venv/bin/python -m pytest -q                        # 39 kiểm thử',
      '.venv/bin/python -m streamlit run app.py             # giao diện demo',
      '.venv/bin/python reports/qc/qc_experiments.py        # ca biên nhận camera sân',
      '.venv/bin/python reports/qc/danh_gia_video_that.py <video.mp4> --roi 0.05,0.3,0.85,0.95',
     ].map(c => new Paragraph({ spacing: { line: 276 }, shading: { type: ShadingType.CLEAR, fill: 'F2F2F2' }, children: [new TextRun({ text: c, font: 'Courier New', size: 20 })] })),
  P('Video nguồn không kèm theo repo (dung lượng/bản quyền): URL hai video Shorts ở mục 4.1; link tải trận 67 phút ghi trong README của repo. Thư mục kết quả của mỗi lần chạy nằm trong runs/.'),
  H2('Phụ lục C. Khai báo sử dụng công cụ AI'),
  P('Theo quy định học thuật của môn, nhóm khai báo: có sử dụng công cụ AI Claude Code (Anthropic) với vai trò trợ lý lập trình trong các việc — rà soát/QC mã nguồn và báo cáo (đối chiếu từng khẳng định với code, phát hiện và sửa một lỗi nhận camera sân kèm test hồi quy), viết bổ sung phần phát hiện bóng nảy/bóng chết và các kiểm thử tổng hợp, viết script đánh giá trên video thực tế, dàn trang báo cáo này theo template và dựng video demo bằng Remotion. Toàn bộ thiết kế thuật toán gốc, số liệu và kết luận do nhóm kiểm soát; mọi thành viên nắm và giải thích được mã nguồn khi bảo vệ. Lịch sử commit ghi rõ các commit có hỗ trợ AI (Co-Authored-By).'),
];

// ---------- document ----------
const doc = new Document({
  styles: {
    default: { document: { run: BODY } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: ARIAL, size: 32, bold: true, color: '000000' },
        paragraph: { spacing: { before: 240, after: 240 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: ARIAL, size: 26, bold: true, color: '000000' },
        paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [{ reference: 'dash', levels: [{ level: 0, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } }, run: BODY } }] }],
  },
  sections: [{
    properties: { page: { margin: { top: 1418, bottom: 1418, left: 1701, right: 1134 } } }, // 2,5/2,5/3/2 cm
    children: [
      // các mảng thân bài đã được dựng ở trên nên figures/tables đã đầy đủ khi gọi tocPage()
      ...cover, ...abstract, ...tocPage(),
      ...gioiThieu, ...tongQuan, ...phuongPhap, ...thucNghiem, ...thaoLuan, ...ketLuan, ...taiLieu, ...phuLuc,
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync('BaoCao_Nhom03_VideoLens.docx', buf);
  console.log('OK BaoCao_Nhom03_VideoLens.docx', buf.length, 'bytes;', figN, 'hình,', tabN, 'bảng');
});
