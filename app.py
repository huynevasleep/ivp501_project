from pathlib import Path
import json
import uuid
import zipfile
import io
import pandas as pd
import plotly.express as px
import streamlit as st
from core import analyze, select, export_video, boundary_f1, summary_f1
from experiments import compare

st.set_page_config(page_title='VideoLens • Video Analytics', page_icon='🎬', layout='wide')
st.title('🎬 VideoLens')
st.caption('Phân tích video • Khung hình chính • Highlight có giải thích')
with st.sidebar:
    st.header('Thiết lập phân tích')
    upload=st.file_uploader('Video của bạn', type=['mp4','mov','avi','mkv'])
    ratio=st.slider('Độ dài tóm tắt (%)',5,80,15)/100
    mode=st.selectbox('Chế độ', ['balanced','sports','lecture','motion','no_motion'])
    rate=st.slider('Số khung phân tích / giây',1,5,2)
    sensitivity=st.slider('Ngưỡng chuyển cảnh (cao = ít cảnh)',1.,6.,3.)
    diversity=st.checkbox('Ưu tiên đa dạng cụm màu',True)
    optimizer=st.selectbox('Thuật toán chọn đoạn',['greedy','knapsack'])
    if optimizer=='knapsack': st.caption('Knapsack tối ưu tổng điểm × thời lượng; không sử dụng thưởng đa dạng.')
    run=st.button('Phân tích & tạo highlight',type='primary',disabled=upload is None)
    st.caption('Xử lý trên máy của bạn. Video dài cần thêm thời gian và dung lượng. Chế độ bài giảng chưa hiểu nội dung lời nói.')
if run:
    out=Path('runs')/uuid.uuid4().hex; out.mkdir(parents=True)
    source=out/('input'+Path(upload.name).suffix.lower()); source.write_bytes(upload.getbuffer())
    try:
        bar=st.progress(0.,text='Trích xuất đặc trưng…')
        df,meta=analyze(source,out,rate,sensitivity,lambda x:bar.progress(x))
        segments,scores=select(df,meta,ratio,mode,diversity,optimizer)
        bar.progress(1.,text='Đang ghép video và âm thanh…')
        video=export_video(source,segments,out)
        report={'input_name':upload.name,'metadata':meta,'settings':dict(ratio=ratio,mode=mode,diversity=diversity,optimizer=optimizer),'segments':segments}
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        st.session_state.result=(out,df,meta,segments,scores,video)
        bar.empty()
    except Exception as e:
        st.error(f'Không thể hoàn tất: {e}')
if 'result' not in st.session_state:
    st.info('Tải video lên ở thanh bên để bắt đầu. Có thể dùng video tự quay hoặc dữ liệu được phép sử dụng.')
    st.markdown('**Quy trình:** Video → Đặc trưng thị giác → Chuyển cảnh → Phân cụm → Chọn đoạn theo ngân sách → Highlight')
else:
    out,df,meta,segments,scores,video=st.session_state.result
    a,b,c=st.columns(3)
    a.metric('Video gốc',f"{meta['duration']:.1f} s")
    b.metric('Highlight',f"{sum(s['end']-s['start'] for s in segments):.1f} s")
    c.metric('Chuyển cảnh',len(meta['cuts']))
    preview,analytics,evaluation,annotation=st.tabs(['▶ Kết quả','📊 Phân tích','🧪 Đánh giá','✍ Gán nhãn'])
    with preview:
        st.video(str(video))
        st.download_button('Tải highlight MP4',video.read_bytes(),'highlight.mp4','video/mp4')
        st.subheader('Storyboard')
        cols=st.columns(4)
        for i,s in enumerate(segments):
            cols[i%4].image(str(out/s['keyframe']),caption=f"{s['start']:.1f}–{s['end']:.1f}s · điểm {s['score']:.2f}")
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
            for name in ['features.csv','metadata.json','report.json']:
                z.write(out/name,name)
            for name in {s['keyframe'] for s in segments}: z.write(out/name,name)
        st.download_button('Tải báo cáo & storyboard ZIP',buffer.getvalue(),'analysis.zip')
    with analytics:
        timeline=pd.DataFrame([{'start':s['start'],'duration':s['end']-s['start'],'segment':str(i+1),'score':s['score']} for i,s in enumerate(segments)])
        st.plotly_chart(px.bar(timeline,x='duration',y='segment',base='start',orientation='h',color='score',title='Các đoạn được giữ trên dòng thời gian',labels={'duration':'Giây','segment':'Đoạn'}),width='stretch')
        if segments and 'contributions' in segments[0]:
            index=st.selectbox('Giải thích điểm của đoạn',range(len(segments)),format_func=lambda i:f"{segments[i]['start']:.1f}–{segments[i]['end']:.1f}s")
            contributions=segments[index]['contributions']
            st.plotly_chart(px.bar(x=list(contributions),y=list(contributions.values()),labels={'x':'Đặc trưng','y':'Đóng góp vào điểm'},title='Đóng góp sau chuẩn hóa và nhân trọng số'),width='stretch')
        chart=df.copy(); chart['importance']=scores
        st.plotly_chart(px.line(chart,x='time',y=['motion_norm','color_norm','faces_norm','importance'],labels={'time':'Thời gian (s)'}),width='stretch')
        st.dataframe(pd.DataFrame(segments),width='stretch')
        st.caption('Điểm là heuristic thị giác, không phải xác suất sự kiện quan trọng. Cụm màu có thể gộp những cảnh khác nội dung.')
    with evaluation:
        st.markdown('Nạp JSON có `boundaries` (giây) và `summaries` (danh sách người gán nhãn, mỗi người có các cặp `[start, end]`).')
        labels=st.file_uploader('Nhãn đánh giá JSON',type=['json'])
        tolerance=st.number_input('Sai số ranh giới cho phép (giây)',.0,5.,.5)
        if labels:
            try:
                gt=json.load(labels)
                st.metric('Boundary F1',f"{boundary_f1(meta['cuts'],gt['boundaries'],tolerance):.3f}")
                saved=json.loads((out/'report.json').read_text(encoding='utf-8'))
                st.write('Kết quả highlight hiện tại',summary_f1(segments,gt['summaries'],meta['duration']))
                table=compare(df,meta,gt,saved['settings']['ratio']); st.dataframe(table)
                st.plotly_chart(px.bar(table,x='method',y='f1_mean',title='So sánh 6 biến thể — cùng ngân sách'),width='stretch')
                st.download_button('Tải so sánh CSV',table.to_csv(index=False),'evaluation.csv')
                st.caption('F-score theo lưới 0.1 giây; đây là giao thức nội bộ, chưa thay thế script benchmark chính thức.')
            except (ValueError,KeyError,TypeError) as e: st.error(f'Nhãn không hợp lệ: {e}')
    with annotation:
        st.subheader('Tạo nhãn khoảng thời gian')
        st.caption('Để đánh giá độc lập, người gán nhãn cần xem video gốc trước khi xem highlight của máy. Mỗi lần xuất là nhãn của một người; gộp các danh sách summaries để đánh giá nhiều người.')
        sources=list(out.glob('input.*'))
        if sources: st.video(str(sources[0]))
        edited=st.data_editor(pd.DataFrame({'start':[0.0],'end':[min(1.,meta['duration'])]}),num_rows='dynamic',key=f'labels_{out.name}')
        boundary_text=st.text_input('Ranh giới cảnh (giây, ngăn bằng dấu phẩy)',key=f'cuts_{out.name}')
        try:
            boundaries=[float(x.strip()) for x in boundary_text.split(',') if x.strip()]
            intervals=edited[['start','end']].to_numpy(dtype=float).tolist()
            summary_f1([], [intervals],meta['duration'])
            if any(not 0<x<meta['duration'] for x in boundaries): raise ValueError('Ranh giới phải nằm bên trong video.')
            st.download_button('Xuất nhãn JSON',json.dumps({'boundaries':sorted(set(boundaries)),'summaries':[intervals]},indent=2),'labels.json','application/json')
        except (ValueError,TypeError) as e: st.error(str(e))
