"""Evidence, event-based export, rally evaluation and optional sports photography."""
import io
import json
import zipfile
import pandas as pd
import streamlit as st
from rally_export import export_individual, show_individual
from rally_evidence import track_ball,rallies_from_events,timecode_table,rally_metrics,EVENT_TYPES
from photo_finish import finish_photo


def render_tools(state):
    out=state['out']; source=state['source']; duration=state['meta']['duration']; key=out.name
    with st.expander('1 · Kiểm tra bóng và bằng chứng ranh giới pha'):
        st.write('Theo dõi ứng viên bóng vàng/xanh ở FPS gốc trong một đoạn ngắn. Dấu đổi hướng, bóng nảy (vận tốc dọc đổi dấu) và bóng chết (nảy 2 lần liên tiếp không có đổi hướng ở giữa) đều chỉ là gợi ý từ hình dạng quỹ đạo: chưa chứng minh bóng chạm mặt vợt hay sàn. Mất dấu cũng không được coi là hết pha.')
        a=st.number_input('Bắt đầu đoạn kiểm tra (giây)',0.,duration,0.,key=f'track_a_{key}')
        b=st.number_input('Kết thúc đoạn kiểm tra (giây)',0.,duration,min(duration,15.),key=f'track_b_{key}')
        hue=st.slider('Màu bóng: khoảng Hue HSV (0–179)',0,179,(18,48),key=f'hue_{key}')
        if a<b: st.video(str(source),start_time=a,end_time=b)
        if st.button('Vẽ quỹ đạo ứng viên bóng',key=f'track_{key}'):
            bar=st.progress(0.)
            try:
                track_out=out/'evidence'
                _,events,video,diagnostics=track_ball(source,a,b,track_out,roi=state['meta'].get('roi',(0.,0.,1.,1.)),hue=hue,progress=lambda x:bar.progress(x))
                state['evidence']=dict(video=video,events=events,diagnostics=diagnostics)
            except Exception as e: st.error(str(e))
            finally: bar.empty()
        if 'evidence' in state:
            e=state['evidence']; st.video(str(e['video']))
            st.caption(f"{e['diagnostics']['observation_fraction']:.1%} khung có ứng viên được nối. Đây không phải độ chính xác nhận bóng; cần đối chiếu video.")
            if e['events']:
                evidence_names={'direction_change_candidate':'Ứng viên đổi hướng (có thể chạm vợt)',
                                'bounce_candidate':'Ứng viên bóng nảy (chạm sàn)',
                                'dead_ball_candidate':'Ứng viên bóng chết (nảy 2 lần)'}
                table=pd.DataFrame(e['events'])[['time','kind']].rename(columns={'time':'Mốc gợi ý (giây)','kind':'Loại bằng chứng'})
                table['Loại bằng chứng']=table['Loại bằng chứng'].map(evidence_names).fillna(table['Loại bằng chứng'])+' — chưa xác nhận'
                st.dataframe(table,hide_index=True)
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
                for p in (out/'evidence').glob('*'):
                    if p.suffix in ('.csv','.json','.jpg'): z.write(p,p.name)
            st.download_button('Tải quỹ đạo, thông số và ảnh bằng chứng',data.getvalue(),'ball_evidence.zip')
    with st.expander('2 · Xác nhận sự kiện, bổ sung pha thiếu và ghép toàn bộ'):
        st.write('Nhập các mốc giao bóng và kết thúc đã kiểm tra trên video. Chạm vợt, bóng nảy và mất dấu được lưu để giải thích; chỉ cặp giao bóng–kết thúc đã xác nhận tạo một pha. Có thể thêm hàng cho nhiều pha.')
        names={'serve':'Giao bóng','paddle_contact':'Chạm vợt','bounce':'Bóng nảy','rally_end':'Kết thúc pha (đã kiểm tra)','occluded':'Bị che / mất dấu'}
        template=pd.DataFrame({'time':[0.,min(5.,duration)],'kind':[names['serve'],names['rally_end']],'confirmed':[False,False]})
        events=st.data_editor(template,num_rows='dynamic',hide_index=True,key=f'events_{key}',column_config={
            'time':st.column_config.NumberColumn('Thời gian (giây)',min_value=0.,max_value=duration,format='%.3f'),
            'kind':st.column_config.SelectboxColumn('Sự kiện',options=list(names.values())),
            'confirmed':st.column_config.CheckboxColumn('Đã xem và xác nhận')})
        st.caption('Chỉ đánh dấu xác nhận sau khi đã kiểm tra đúng sự kiện trong video. Hai hàng ban đầu là ví dụ chưa được xác nhận.')
        if st.button('Xuất từng pha từ sự kiện đã xác nhận',key=f'event_export_{key}'):
            try:
                event_list=events.to_dict('records')
                reverse_names={v:k for k,v in names.items()}
                for event in event_list:
                    if event['kind'] not in reverse_names: raise ValueError('Hãy chọn loại sự kiện cho từng hàng.')
                    event['kind']=reverse_names[event['kind']]
                segments,warnings=rallies_from_events(event_list,duration)
                for warning in warnings: st.warning(warning)
                if not segments: raise ValueError('Chưa có cặp giao bóng–kết thúc đã xác nhận hợp lệ.')
                dest=out/'confirmed'; dest.mkdir(exist_ok=True)
                with st.spinner('Đang xuất mỗi pha đã xác nhận thành MP4 riêng…'): bundle=export_individual(source,segments,dest)
                timecode_table(segments).to_csv(dest/'timecodes.csv',index=False)
                (dest/'events.json').write_text(json.dumps(event_list,indent=2),encoding='utf-8')
                (dest/'rallies.json').write_text(json.dumps({'duration':duration,'rallies':segments,'events':event_list,'warnings':warnings},indent=2),encoding='utf-8')
                state['confirmed']=bundle
            except Exception as e: st.error(str(e))
        if 'confirmed' in state:
            if 'files' in state['confirmed']:
                show_individual(state['confirmed'],f'confirmed_{key}')
            else:
                st.info('Nhấn xuất lại để tạo mỗi pha xác nhận thành một MP4 riêng.')
            st.download_button('Tải timecode nguồn → highlight',(out/'confirmed'/'timecodes.csv').read_bytes(),'timecodes.csv')
            st.download_button('Tải nhãn sự kiện & pha',(out/'confirmed'/'rallies.json').read_bytes(),'rallies.json')
    with st.expander('Đánh giá số pha tìm đúng và sai lệch đầu/cuối pha'):
        st.write('Tải JSON nhãn độc lập dạng {"rallies": [{"start": 10, "end": 20}]}. Không dùng chính kết quả máy làm nhãn. Đánh giá các đề xuất, chưa tính thao tác chỉnh tay.')
        label=st.file_uploader('Nhãn pha từ người xem',type='json',key=f'rally_gt_{key}')
        if label:
            try:
                gt=json.loads(label.getvalue())
                truth=[(r['start'],r['end']) for r in gt['rallies']]
                if any(b>duration for a,b in truth): raise ValueError('Nhãn vượt thời lượng video.')
                metric=rally_metrics([(s['start'],s['end']) for s in state['candidates']],truth)
                st.write(f"Ghép đúng {metric['matched']} / {metric['reference']} pha nhãn tại IoU ≥ 0.5. F1 = {metric['f1']:.3f}.")
                st.caption('IoU đo độ trùng khoảng thời gian; một đề xuất chỉ ghép với một nhãn. Sai lệch đầu/cuối chỉ tính trên các cặp ghép được.')
                st.json(metric)
                st.download_button('Tải kết quả đánh giá',json.dumps(metric,indent=2),'rally_metrics.json')
            except (ValueError,KeyError,TypeError) as e: st.error(f'Nhãn không hợp lệ: {e}')
    with st.expander('3 · Ảnh góc ngang vận động viên (tùy chọn)'):
        st.write('Chọn đúng đoạn có góc máy ngang và vùng vận động viên. Chương trình lấy khung nét nhất trong vùng đã chọn, khử nhiễu và tăng nét; không tạo góc nhìn mới nếu video gốc không có.')
        side=st.checkbox('Tôi đã kiểm tra đoạn này là góc máy ngang',key=f'side_{key}')
        a=st.number_input('Bắt đầu khoảnh khắc (giây)',0.,duration,0.,key=f'photo_a_{key}')
        b=st.number_input('Kết thúc khoảnh khắc (giây)',0.,duration,min(duration,2.),key=f'photo_b_{key}')
        if a<b: st.video(str(source),start_time=a,end_time=b)
        horizontal=st.slider('Vùng vận động viên: trái–phải (%)',0,100,(0,100),key=f'photo_x_{key}')
        vertical=st.slider('Vùng vận động viên: trên–dưới (%)',0,100,(0,100),key=f'photo_y_{key}')
        amount=st.slider('Mức tăng nét',0.,2.,.7,.1,key=f'sharp_{key}')
        denoise=st.slider('Mức khử nhiễu',0.,10.,3.,1.,key=f'noise_{key}')
        deblur=st.checkbox('Thử giảm mờ chuyển động (cần so sánh ảnh gốc)',key=f'deblur_{key}')
        length=st.slider('Độ dài vệt mờ (pixel)',3,25,5,key=f'psf_len_{key}') if deblur else 0
        angle=st.slider('Hướng vệt mờ (độ)',0,179,0,key=f'psf_angle_{key}') if deblur else 0
        st.caption('Bộ lọc giảm mờ dùng mô hình vệt mờ thẳng giả định; sai thông số có thể gây viền giả. Không bảo đảm phục hồi chi tiết bị mất.')
        if st.button('Chọn khung và xử lý ảnh',disabled=not side,key=f'photo_run_{key}'):
            try:
                roi=(horizontal[0]/100,vertical[0]/100,horizontal[1]/100,vertical[1]/100)
                with st.spinner('Đang chọn khung ở độ phân giải gốc…'):
                    original,enhanced,meta=finish_photo(source,a,b,out/'photo',roi=roi,sharpen=amount,denoise=denoise,blur_length=length,blur_angle=angle)
                state['photo']=(original,enhanced,meta)
            except Exception as e: st.error(str(e))
        if 'photo' in state:
            original,enhanced,meta=state['photo']; left,right=st.columns(2)
            left.image(str(original),caption='Ảnh gốc'); right.image(str(enhanced),caption='Ảnh sau xử lý')
            st.caption(f"Khung tại {meta['time']:.3f}s · {meta['width']} × {meta['height']} px. Điểm độ nét không thay thế đánh giá ảnh đẹp.")
            st.download_button('Tải ảnh gốc PNG',original.read_bytes(),'athlete_original.png')
            st.download_button('Tải ảnh xử lý PNG',enhanced.read_bytes(),'athlete_enhanced.png')
            st.download_button('Tải thông số xử lý',(out/'photo'/'photo_report.json').read_bytes(),'photo_report.json')
