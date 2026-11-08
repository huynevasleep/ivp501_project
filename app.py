from pathlib import Path
import json
import uuid
import zipfile
import io
import logging
import pandas as pd
import plotly.express as px
import streamlit as st
from core import analyze, select, export_video, best_shots, boundary_f1, summary_f1
from experiments import compare
from presentation import FEATURES, MODES, METHODS, timestamp, reason, segment_table, plain_report

st.set_page_config(page_title='VideoLens • Video Analytics', page_icon='🎬', layout='wide')
st.title('🎬 VideoLens')
st.caption('Phân tích video • Khung hình chính • Highlight có giải thích')
workflow=st.sidebar.radio('Mục đích sử dụng',['Dự án pickleball','Phòng thí nghiệm: baseline / video khác'],index=1 if 'result' in st.session_state else 0)
if workflow=='Dự án pickleball':
    from match_ui import render
    render()
    st.stop()
with st.sidebar:
    st.header('Thiết lập phân tích')
    upload=st.file_uploader('Video của bạn', type=['mp4','mov','avi','mkv'])
    ratio=st.slider('Độ dài tóm tắt (%)',5,80,15)/100
    mode=st.selectbox('Loại video', list(MODES),format_func=MODES.get)
    rate=st.slider('Số khung phân tích / giây',1,5,2)
    sensitivity=st.slider('Ngưỡng chuyển cảnh (cao = ít cảnh)',1.,6.,3.)
    diversity=st.checkbox('Ưu tiên đa dạng cụm màu',True)
    optimizer=st.selectbox('Cách chọn nội dung',['greedy','knapsack'],format_func=lambda x:{'greedy':'Ưu tiên từng đoạn nổi bật (Greedy)','knapsack':'Tối ưu tổng điểm trong thời lượng (Knapsack)'}[x])
    if optimizer=='knapsack': st.caption('Knapsack tối ưu tổng điểm × thời lượng; không sử dụng thưởng đa dạng.')
    run=st.button('Phân tích & tạo highlight',type='primary',disabled=upload is None)
    st.caption('Xử lý trên máy của bạn. Video dài cần thêm thời gian và dung lượng. Chế độ bài giảng chưa hiểu nội dung lời nói.')
if run:
    st.session_state.pop('result', None)
    out=Path('runs')/uuid.uuid4().hex; out.mkdir(parents=True)
    source=out/('input'+Path(upload.name).suffix.lower()); source.write_bytes(upload.getbuffer())
    try:
        bar=st.progress(0.,text='Trích xuất đặc trưng…')
        df,meta=analyze(source,out,rate,sensitivity,lambda x:bar.progress(x))
        segments,scores=select(df,meta,ratio=ratio,mode=mode,diversity=diversity,optimizer=optimizer)
        bar.progress(1.,text='Đang ghép video và âm thanh…')
        video=export_video(source,segments,out)
        if mode=='rally':
            bar.progress(1.,text='Đang chọn ảnh cầu thủ lúc vung vợt…')
            (out/'shots.json').write_text(json.dumps(best_shots(source,segments,out),ensure_ascii=False,indent=2),encoding='utf-8')
        report={'input_name':upload.name,'metadata':meta,'settings':dict(ratio=ratio,mode=mode,diversity=diversity,optimizer=optimizer),'segments':segments}
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        st.session_state.result=(out,df,meta,segments,scores,video)
        bar.empty()
    except Exception as e:
        logging.exception('Video analysis failed: %s', source)
        st.error(f'Không thể hoàn tất: {e}')
    finally:
        bar.empty()
if 'result' not in st.session_state:
    st.info('Tải video lên ở thanh bên để bắt đầu. Có thể dùng video tự quay hoặc dữ liệu được phép sử dụng.')
    st.markdown('**Quy trình:** Video → Đặc trưng thị giác → Chuyển cảnh → Phân cụm → Chọn đoạn theo ngân sách → Highlight')
else:
    out,df,meta,segments,scores,video=st.session_state.result
    a,b,c=st.columns(3)
    total=sum(s['end']-s['start'] for s in segments)
    a.metric('Độ dài video gốc',timestamp(meta['duration']))
    b.metric('Độ dài bản tóm tắt',timestamp(total))
    c.metric('Số đoạn được giữ',len(segments))
    st.success(f"Bản tóm tắt giữ {total/meta['duration']:.1%} thời lượng gốc, giúp giảm khoảng {meta['duration']-total:.1f} giây xem. Các đoạn giữ nguyên thứ tự xuất hiện.")
    st.caption('Thời gian hiển thị theo phút:giây.phần mười giây; video dài có thêm giờ.')
    preview,analytics,evaluation,annotation=st.tabs(['▶ Kết quả','📊 Phân tích','🧪 Đánh giá','✍ Gán nhãn'])
    with preview:
        from rally_export import export_individual, show_individual
        if st.button('Xuất mỗi pha thành một video riêng',key='generic_split'):
            sources=list(out.glob('input.*'))
            if sources:
                with st.spinner('Đang xuất từng video pha…'):
                    st.session_state[f'split_{out.name}']=export_individual(sources[0],segments,out)
            else: st.error('Không tìm thấy video nguồn để tách theo mốc đã lưu.')
        if f'split_{out.name}' in st.session_state:
            show_individual(st.session_state[f'split_{out.name}'],f'generic_{out.name}')
        st.video(str(video))
        st.download_button('Tải highlight MP4',video.read_bytes(),'highlight.mp4','video/mp4')
        shots=json.loads((out/'shots.json').read_text(encoding='utf-8')) if (out/'shots.json').exists() else []
        if shots:
            st.subheader('Ảnh cầu thủ lúc vung vợt (thử nghiệm)')
            st.caption('Khung nét nhất quanh lúc dáng người thay đổi mạnh nhất, cắt từ khung gốc, không phóng to. Dùng trừ nền nên có thể cắt nhầm hai người dính nhau hoặc chỉ được một phần cơ thể; chưa có mô hình tư thế nên chưa chấm được tư thế đúng chuẩn.')
            shot_cols=st.columns(4)
            for i,c in enumerate(shots):
                shot_cols[i%4].image(str(out/c['image']),caption=f"{timestamp(c['time'])} · cao {c['box'][3]} px")
            shot_zip=io.BytesIO()
            with zipfile.ZipFile(shot_zip,'w',zipfile.ZIP_DEFLATED) as z:
                for c in shots: z.write(out/c['image'],c['image']); z.write(out/c['full_image'],c['full_image'])
            st.download_button('Tải ảnh (ZIP)',shot_zip.getvalue(),'anh_cau_thu.zip')
        st.subheader('Xem nhanh các đoạn được giữ lại')
        st.caption('Mỗi ảnh đại diện cho một đoạn. Mốc thời gian bên dưới là vị trí trong video gốc.')
        cols=st.columns(4)
        for i,s in enumerate(segments):
            cols[i%4].image(str(out/s['keyframe']),caption=f"Đoạn {i+1} · {timestamp(s['start'])} → {timestamp(s['end'])}")
            cols[i%4].caption(reason(s))
        st.download_button('Tải bản giải thích dễ đọc (.txt)',plain_report(segments,meta['duration']).encode('utf-8-sig'),'tom_tat_de_hieu.txt','text/plain')
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('GIAI_THICH.txt',plain_report(segments,meta['duration']))
            for name in ['features.csv','metadata.json','report.json']:
                z.write(out/name,name)
            for name in {s['keyframe'] for s in segments}: z.write(out/name,name)
        st.download_button('Tải báo cáo & storyboard ZIP',buffer.getvalue(),'analysis.zip')
    with analytics:
        st.subheader('Các đoạn được giữ lại')
        st.write('Bảng này cho biết đoạn nào được lấy từ video gốc và tín hiệu hình ảnh nào đóng góp nhiều nhất vào điểm của đoạn đó.')
        st.dataframe(segment_table(segments),hide_index=True,width='stretch')
        st.info('Điểm ưu tiên được quy đổi về thang 100 để dễ so sánh trong video này. Ví dụ 60/100 không có nghĩa là chính xác 60%. Việc chọn đoạn còn phụ thuộc thời lượng cho phép và cách chọn nội dung.')
        timeline=pd.DataFrame([{'start':s['start'],'duration':s['end']-s['start'],'segment':str(i+1),'score':s['score']} for i,s in enumerate(segments)])
        timeline['score']*=100
        st.plotly_chart(px.bar(timeline,x='duration',y='segment',base='start',orientation='h',color='score',title='Vị trí các đoạn trong video gốc',labels={'duration':'Thời gian trong video gốc (giây)','segment':'Đoạn','start':'Bắt đầu (giây)','score':'Điểm ưu tiên / 100'}),width='stretch')
        if segments and 'contributions' in segments[0]:
            index=st.selectbox('Tìm hiểu một đoạn',range(len(segments)),format_func=lambda i:f"Đoạn {i+1}: {timestamp(segments[i]['start'])} → {timestamp(segments[i]['end'])}")
            contributions=segments[index]['contributions']
            st.write(reason(segments[index]))
            st.plotly_chart(px.bar(x=[FEATURES.get(k,k) for k in contributions],y=[v*100 for v in contributions.values()],labels={'x':'Tín hiệu hình ảnh','y':'Số điểm đóng góp'},title='Điểm ưu tiên của đoạn được tạo từ đâu?'),width='stretch')
            st.caption('Cột càng cao, tín hiệu đó đóng góp càng nhiều vào điểm. Tổng các cột bằng điểm ưu tiên của đoạn; đây không phải đánh giá nội dung hay lời nói.')
        chart=df.copy(); chart['importance']=scores
        with st.expander('Dành cho nghiên cứu: đặc trưng và dữ liệu kỹ thuật'):
            chart=chart.rename(columns={**FEATURES,'importance':'Điểm tổng hợp','time':'Thời gian (giây)'})
            st.plotly_chart(px.line(chart,x='Thời gian (giây)',y=['Chuyển động','Thay đổi màu sắc','Khuôn mặt','Điểm tổng hợp'],labels={'value':'Mức chuẩn hóa (0–1)','variable':'Tín hiệu'}),width='stretch')
            st.dataframe(pd.DataFrame(segments),width='stretch')
            st.caption('cluster: nhóm màu tương tự; keyframe: tên ảnh đại diện; contributions: đóng góp sau nhân trọng số. Các nhóm màu chưa thể hiện ý nghĩa nội dung.')
    with evaluation:
        st.subheader('Bản tóm tắt giống lựa chọn của người xem đến đâu?')
        st.write('Mục này dành cho đánh giá đề tài. Cần có các đoạn quan trọng do người xem đánh dấu trước. Bạn có thể tạo file đó ở tab Gán nhãn; nếu chỉ muốn xem và tải video, không cần thực hiện bước này.')
        st.markdown('Nạp JSON có `boundaries` (giây) và `summaries` (danh sách người gán nhãn, mỗi người có các cặp `[start, end]`).')
        labels=st.file_uploader('Nhãn đánh giá JSON',type=['json'])
        tolerance=st.number_input('Sai số ranh giới cho phép (giây)',.0,5.,.5)
        if labels:
            try:
                gt=json.loads(labels.getvalue())
                st.metric('Mức khớp vị trí chuyển cảnh (F1 / 100)',f"{100*boundary_f1(meta['cuts'],gt['boundaries'],tolerance):.1f}")
                saved=json.loads((out/'report.json').read_text(encoding='utf-8'))
                metric=summary_f1(segments,gt['summaries'],meta['duration'])
                st.metric('Mức khớp các đoạn được chọn (F-score / 100)',f"{metric['mean']*100:.1f}")
                st.caption(f"Trung bình so với {len(metric['per_user'])} người gán nhãn. Điểm cao hơn nghĩa là các khoảng thời gian trùng khớp nhiều hơn, không phải phần trăm hiểu đúng nội dung.")
                table=compare(df,meta,gt,saved['settings']['ratio'])
                readable=table.copy()
                readable['method']=readable['method'].map(METHODS)
                for col in ['f1_mean','f1_max','actual_ratio']: readable[col]=(readable[col]*100).round(1)
                readable=readable.rename(columns={'method':'Cách chọn','f1_mean':'Khớp trung bình / 100','f1_max':'Khớp tốt nhất / 100','actual_ratio':'Thời lượng giữ lại (%)','clusters':'Số nhóm hình ảnh','selection_seconds':'Thời gian chọn (giây)'})
                st.dataframe(readable,hide_index=True)
                st.plotly_chart(px.bar(readable,x='Cách chọn',y='Khớp trung bình / 100',title='So sánh 6 cách chọn — cùng giới hạn thời lượng'),width='stretch')
                st.download_button('Tải so sánh CSV',table.to_csv(index=False),'evaluation.csv')
                st.caption('F-score theo lưới 0.1 giây; đây là giao thức nội bộ, chưa thay thế script benchmark chính thức.')
            except (ValueError,KeyError,TypeError) as e: st.error(f'Nhãn không hợp lệ: {e}')
    with annotation:
        st.subheader('Tạo nhãn khoảng thời gian')
        st.caption('Để đánh giá độc lập, người gán nhãn cần xem video gốc trước khi xem highlight của máy. Mỗi lần xuất là nhãn của một người; gộp các danh sách summaries để đánh giá nhiều người.')
        sources=list(out.glob('input.*'))
        if sources: st.video(str(sources[0]))
        edited=st.data_editor(pd.DataFrame({'start':[0.0],'end':[min(1.,meta['duration'])]}),num_rows='dynamic',column_config={'start':st.column_config.NumberColumn('Bắt đầu (giây)',min_value=0.,format='%.2f'),'end':st.column_config.NumberColumn('Kết thúc (giây)',min_value=0.,format='%.2f')},key=f'labels_{out.name}')
        boundary_text=st.text_input('Ranh giới cảnh (giây, ngăn bằng dấu phẩy)',key=f'cuts_{out.name}')
        try:
            boundaries=[float(x.strip()) for x in boundary_text.split(',') if x.strip()]
            intervals=edited[['start','end']].to_numpy(dtype=float).tolist()
            summary_f1([], [intervals],meta['duration'])
            if any(not 0<x<meta['duration'] for x in boundaries): raise ValueError('Ranh giới phải nằm bên trong video.')
            st.download_button('Xuất nhãn JSON',json.dumps({'boundaries':sorted(set(boundaries)),'summaries':[intervals]},indent=2),'labels.json','application/json')
        except (ValueError,TypeError) as e: st.error(str(e))
