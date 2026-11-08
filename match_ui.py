from pathlib import Path
import json
import uuid
import shutil
import pandas as pd
import plotly.express as px
import streamlit as st
from rally_export import export_individual, show_individual
from pickleball import analyze_match,choose_rallies,review_rallies
from presentation import timestamp
from rally_evidence import timecode_table
from project_tools_ui import render_tools
from rally_preview import preview_clip


def render():
    st.subheader('🏓 Highlight pickleball — video toàn trận')
    st.write('Tìm pha → kiểm tra bằng chứng → xuất mỗi pha thành một video riêng có timecode. Ảnh vận động viên là phần tùy chọn bên dưới.')
    st.info('Phù hợp nhất với góc máy cố định nhìn toàn sân. Các đoạn đề xuất dựa trên chuyển động; chưa xác định bóng, điểm thắng hay cú đánh đẹp. Video quay lia, replay và người đi lại giữa các pha cần được duyệt lại.')
    with st.sidebar:
        source_type=st.radio('Nguồn video',['Tải lên','File trên máy (video lớn)'])
        source_text=st.text_input('Đường dẫn đầy đủ đến video',placeholder=r'D:\Videos\tran_pickleball.mp4') if source_type.startswith('File') else ''
        upload=st.file_uploader('Video trận đấu',type=['mp4','mkv','mov','avi'],key='match_upload') if source_type=='Tải lên' else None
        output_mode=st.radio('Nội dung xuất',['Toàn bộ pha đề xuất','Chọn ít pha theo thời lượng'])
        budget=st.number_input('Highlight tối đa (phút)',.25,60.,3.,.25) if output_mode!='Toàn bộ pha đề xuất' else None
        limit=budget*60 if budget is not None else None
        st.caption('Hỗ trợ tải video tối đa 4 GB. File lớn cần đủ RAM và dung lượng ổ đĩa; có thể dùng đường dẫn cục bộ nếu gặp giới hạn bộ nhớ.')
        with st.expander('Điều chỉnh vùng sân và độ nhạy'):
            st.caption('Vùng sân là hình chữ nhật theo % khung hình, tính từ góc trên trái. Loại khán đài giúp giảm chuyển động gây nhiễu. Mặc định dùng toàn khung.')
            horizontal=st.slider('Biên trái – phải (%)',0,100,(0,100))
            vertical=st.slider('Biên trên – dưới (%)',0,100,(0,100))
            threshold=st.slider('Ngưỡng hoạt động (thấp = nhiều đề xuất)',.1,.8,.32,.01)
            gap=st.slider('Cho phép tạm ít chuyển động trong pha (giây)',.5,5.,2.,.5)
            min_seconds=st.slider('Hoạt động tối thiểu để đề xuất (giây)',2.,12.,4.,.5)
            pre=st.slider('Giữ thêm trước pha (giây)',0.,5.,2.,.5)
            post=st.slider('Giữ thêm sau pha (giây)',0.,5.,2.,.5)
        start=st.button('Phân tích trận & tạo highlight',type='primary')
    if start:
        st.session_state.pop('match',None)
        out=Path('runs')/uuid.uuid4().hex; out.mkdir(parents=True)
        bar=st.progress(0.,text='Đang đọc trận đấu và đo hoạt động trên sân…')
        try:
            if source_type=='Tải lên':
                if upload is None: raise ValueError('Hãy chọn video trước.')
                source=out/('input'+Path(upload.name).suffix)
                upload.seek(0)
                with source.open('wb') as target: shutil.copyfileobj(upload,target,1024*1024)
            else:
                if not source_text.strip(): raise ValueError('Hãy nhập đường dẫn video trên máy.')
                source=Path(source_text.strip().strip('"')).resolve()
            roi=(horizontal[0]/100,vertical[0]/100,horizontal[1]/100,vertical[1]/100)
            df,meta,candidates=analyze_match(source,out,roi=roi,threshold=threshold,min_seconds=min_seconds,gap_seconds=gap,pre=pre,post=post,progress=lambda p:bar.progress(p))
            st.session_state.match=dict(out=out,source=source,df=df,meta=meta,candidates=candidates)
            selected=choose_rallies(candidates,limit)
            if selected:
                bar.progress(.99,text='Đang xuất từng pha thành MP4 riêng…')
                bundle=export_individual(source,selected,out)
                (out/'report.json').write_text(json.dumps(dict(metadata=meta,segments=selected,budget_seconds=limit,reviewed=False),indent=2),encoding='utf-8')
                timecode_table(selected).to_csv(out/'timecodes.csv',index=False)
                st.session_state.match['export']=bundle
        except Exception as e: st.error(str(e))
        finally: bar.empty()
    if 'match' not in st.session_state:
        st.caption('Quy trình: tải video → tìm pha đề xuất → tạo highlight MP4 → xem và điều chỉnh nếu cần. Thời gian phân tích tăng theo độ dài trận; chỉ ảnh đại diện các pha được lưu.')
        return
    state=st.session_state.match; candidates=state['candidates']; meta=state['meta']; out=state['out']
    st.write(f"Video: **{timestamp(meta['duration'])}** · **{len(candidates)} pha đề xuất**")
    if not candidates:
        st.warning('Chưa tìm được khoảng hoạt động phù hợp. Thử giảm ngưỡng hoạt động, giảm thời gian tối thiểu hoặc giới hạn vùng sân. Hệ thống không tự ghép đoạn ngẫu nhiên khi không có ứng viên.')
        render_tools(state)
        return
    if any(s['needs_review'] for s in candidates):
        st.warning('Có khoảng hoạt động liên tục trên 90 giây: có thể gồm nhiều pha hoặc chuyển động gây nhiễu. Những khoảng này không được tự động chọn; cần duyệt và sửa mốc.')
    chosen=choose_rallies(candidates,limit)
    if not chosen: st.warning('Không có pha tự động phù hợp giới hạn hiện tại. Tăng thời lượng hoặc duyệt và chọn thủ công bên dưới.')
    options=list(range(len(candidates)))
    pick=st.selectbox('Xem video riêng của một pha',options,format_func=lambda i:f"Pha {i+1}: {timestamp(candidates[i]['start'])} → {timestamp(candidates[i]['end'])} trong video gốc")
    current=candidates[pick]
    if current.get('needs_review') or current['end']-current['start']>90:
        st.warning('Khoảng này quá dài để coi là một pha. Hãy sửa mốc ở bảng bên dưới trước khi xuất; chưa phát cả đoạn dài như một pha riêng.')
    else:
        try:
            with st.spinner('Đang mở video riêng của pha…'):
                clip=preview_clip(state['source'],current,out,state.get('export'))
            st.caption(f"Video pha {pick+1} · dài {current['end']-current['start']:.2f} giây · phát từ 0:00. Mốc trong video gốc: {timestamp(current['start'])} → {timestamp(current['end'])}.")
            st.video(str(clip))
            st.download_button('Tải pha đang xem',clip.read_bytes(),f'pha_{pick+1:04d}.mp4','video/mp4',key=f'preview_download_{out.name}')
        except Exception as e: st.error(f'Không mở được video pha: {e}')
    if st.checkbox('Mở video gốc để đối chiếu (hiển thị toàn bộ thời lượng)',key=f'source_view_{out.name}'):
        st.caption('Đây là VIDEO GỐC, không phải file pha đã cắt. Thanh thời lượng bên dưới thuộc toàn trận.')
        st.video(str(state['source']),start_time=current['start'],end_time=current['end'])
    st.image(str(out/current['keyframe']),width=360,caption='Ảnh đại diện của pha đề xuất')
    table=pd.DataFrame([dict(keep=s in chosen,start=s['start'],end=s['end'],score=round(s['score']*100,1),needs_review=s['needs_review'],candidate=i) for i,s in enumerate(candidates)])
    edited=st.data_editor(table,hide_index=True,key=f'match_edit_{out.name}_{budget}',disabled=['score','needs_review','candidate'],column_config={
        'keep':st.column_config.CheckboxColumn('Giữ lại'),
        'start':st.column_config.NumberColumn('Bắt đầu (giây)',format='%.2f'),
        'end':st.column_config.NumberColumn('Kết thúc (giây)',format='%.2f'),
        'score':'Điểm hoạt động / 100','needs_review':'Cần kiểm tra khoảng dài','candidate':None})
    st.caption('Có thể sửa bắt đầu/kết thúc để giữ trọn pha. Điểm hoạt động không phải xác suất phát hiện đúng rally. Chế độ toàn bộ không giới hạn tổng thời lượng; khoảng dài cần kiểm tra trước khi chọn.')
    if st.button('Xuất video riêng cho các pha đã chọn',type='primary'):
        try:
            reviewed=review_rallies(edited,meta['duration'],limit)
            segments=[{**candidates[int(s['candidate'])],'start':s['start'],'end':s['end']} for s in reviewed]
            with st.spinner('Đang xuất các video pha riêng…'):
                bundle=export_individual(state['source'],segments,out)
            report=dict(metadata=meta,segments=segments,budget_seconds=limit,reviewed=True)
            (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            timecode_table(segments).to_csv(out/'timecodes.csv',index=False)
            state['export']=bundle
        except Exception as e: st.error(str(e))
    if 'export' in state:
        result=state['export']; seconds=sum(s['end']-s['start'] for s in result['segments'])
        st.success(f"Bản xuất gần nhất: {len(result['segments'])} pha · {timestamp(seconds)}. Nếu sửa bảng, hãy xuất lại để cập nhật video.")
        if 'files' in result:
            show_individual(result,out.name)
        else:
            st.info('Kết quả cũ là video ghép. Nhấn bên dưới để tách theo các mốc đã lưu, không cần phân tích lại.')
            if st.button('Tách kết quả hiện tại thành từng video pha'):
                with st.spinner('Đang xuất video riêng cho từng pha…'):
                    state['export']=export_individual(state['source'],result['segments'],out)
                st.rerun()
        st.download_button('Tải mốc các pha đã xuất',(out/'report.json').read_bytes(),'pickleball_report.json','application/json')
        if (out/'timecodes.csv').exists():
            st.download_button('Tải bảng timecode video gốc → highlight',(out/'timecodes.csv').read_bytes(),'timecodes.csv')
    with st.expander('Xem hoạt động trên sân và xuất dữ liệu nghiên cứu'):
        chart=state['df'].rename(columns={'time':'Thời gian (giây)','activity':'Hoạt động trên sân'})
        st.plotly_chart(px.line(chart,x='Thời gian (giây)',y='Hoạt động trên sân'),width='stretch')
        st.download_button('Tải đặc trưng CSV',(out/'features.csv').read_bytes(),'match_features.csv')
    render_tools(state)
