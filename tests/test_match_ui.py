from pathlib import Path
import json
import cv2
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest


def test_match_empty_input_and_review_export(tmp_path):
    app=AppTest.from_file(Path('app.py').resolve()).run(timeout=60)
    assert not app.exception
    app.button[0].click().run(timeout=60)
    assert not app.exception
    assert app.error
    source=tmp_path/'input.mp4'
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),24,(320,180))
    for i in range(288):
        frame=np.zeros((180,320,3),np.uint8)
        cv2.rectangle(frame,(i%240,50),(i%240+30,100),(255,255,255),-1)
        writer.write(frame)
    writer.release()
    cv2.imwrite(str(tmp_path/'rally.jpg'),np.zeros((100,100,3),np.uint8))
    s=dict(start=1.,end=6.,score=.6,cluster=0,keyframe='rally.jpg',needs_review=False)
    meta=dict(duration=12.,pipeline='pickleball')
    df=pd.DataFrame({'time':[0.,1.],'activity':[0.,.8]})
    df.to_csv(tmp_path/'features.csv',index=False)
    app.session_state['match']=dict(out=tmp_path,source=source,df=df,meta=meta,candidates=[s])
    app.run(timeout=60)
    assert not app.exception
    next(b for b in app.button if b.label.startswith('Xuất video riêng')).click().run(timeout=60)
    assert not app.exception
    assert list((tmp_path/'individual').glob('*/pha_0001.mp4'))
    report=json.loads((tmp_path/'report.json').read_text())
    assert report['reviewed'] is True
    assert report['budget_seconds'] is None
    assert (tmp_path/'timecodes.csv').exists()
    next(b for b in app.button if b.label=='Vẽ quỹ đạo ứng viên bóng').click().run(timeout=60)
    assert not app.exception
    assert (tmp_path/'evidence'/'ball_overlay.mp4').exists()
    next(c for c in app.checkbox if c.label.startswith('Tôi đã kiểm tra')).check().run(timeout=60)
    next(b for b in app.button if b.label=='Chọn khung và xử lý ảnh').click().run(timeout=60)
    assert not app.exception
    assert (tmp_path/'photo'/'enhanced.png').exists()
    app.session_state[f'events_{tmp_path.name}']={'edited_rows':{0:{'time':1.,'confirmed':True},1:{'time':6.,'confirmed':True}},'added_rows':[],'deleted_rows':[]}
    next(b for b in app.button if b.label=='Xuất từng pha từ sự kiện đã xác nhận').click().run(timeout=60)
    assert not app.exception
    assert list((tmp_path/'confirmed'/'individual').glob('*/pha_0001.mp4'))
    confirmed=json.loads((tmp_path/'confirmed'/'rallies.json').read_text())
    assert confirmed['rallies'][0]['start']==1.
    assert confirmed['rallies'][0]['end']==6.
