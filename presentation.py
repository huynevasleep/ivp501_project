"""User-facing descriptions derived only from measured visual features."""
import pandas as pd

FEATURES = {'motion_norm':'Chuyển động', 'faces_norm':'Khuôn mặt',
            'sharpness_norm':'Độ nét', 'color_norm':'Thay đổi màu sắc',
            'difference_norm':'Thay đổi hình ảnh'}
MODES = {'balanced':'Tổng quát', 'sports':'Thể thao', 'lecture':'Bài giảng',
         'motion':'Thử nghiệm: chỉ chuyển động', 'no_motion':'Thử nghiệm: bỏ chuyển động'}
METHODS = {'uniform':'Chọn trải đều theo thời gian','motion':'Chỉ chuyển động',
           'hybrid':'Kết hợp + đa dạng','no_diversity':'Kết hợp, bỏ đa dạng',
           'no_motion':'Kết hợp, bỏ chuyển động','knapsack':'Tối ưu tổng điểm'}

def timestamp(seconds):
    ticks=round(float(seconds)*10)
    hours,rem=divmod(ticks,36000); minutes,rem=divmod(rem,600)
    secs,decimal=divmod(rem,10)
    return (f'{hours:02d}:' if hours else '')+f'{minutes:02d}:{secs:02d}.{decimal}'

def reason(segment):
    contributions=segment.get('contributions',{})
    ranked=sorted(((k,v) for k,v in contributions.items() if v>0),key=lambda x:x[1],reverse=True)
    if not ranked: return 'Không có tín hiệu nổi trội trong điểm của đoạn này.'
    names=[FEATURES.get(k,k).lower() for k,_ in ranked[:2]]
    return 'Tín hiệu đóng góp nhiều nhất: '+', '.join(names)+'.'

def segment_table(segments):
    return pd.DataFrame([{'Đoạn':i+1,'Bắt đầu (video gốc)':timestamp(s['start']),
        'Kết thúc (video gốc)':timestamp(s['end']),'Độ dài (giây)':round(s['end']-s['start'],2),
        'Điểm ưu tiên / 100':round(s['score']*100,1),'Giải thích':reason(s)} for i,s in enumerate(segments)])

def plain_report(segments,duration):
    total=sum(s['end']-s['start'] for s in segments)
    lines=['KẾT QUẢ TÓM TẮT VIDEO',f'Video gốc: {timestamp(duration)}',
           f'Bản tóm tắt: {timestamp(total)} — {len(segments)} đoạn, giữ {total/duration:.1%} thời lượng.',
           'Các mốc dưới đây tính theo video gốc. Điểm ưu tiên không phải phần trăm chính xác.',
           'Giải thích dựa trên tín hiệu hình ảnh, chưa đánh giá ý nghĩa lời nói.','']
    for i,s in enumerate(segments):
        lines.append(f"Đoạn {i+1}: {timestamp(s['start'])} → {timestamp(s['end'])} | {reason(s)}")
    return '\n'.join(lines)
