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
    source=Path('runs/synthetic.mp4').resolve()
    if not source.exists(): return
    cv2.imwrite(str(tmp_path/'rally.jpg'),np.zeros((100,100,3),np.uint8))
    s=dict(start=1.,end=6.,score=.6,cluster=0,keyframe='rally.jpg',needs_review=False)
    meta=dict(duration=12.,pipeline='pickleball')
    df=pd.DataFrame({'time':[0.,1.],'activity':[0.,.8]})
    df.to_csv(tmp_path/'features.csv',index=False)
    app.session_state['match']=dict(out=tmp_path,source=source,df=df,meta=meta,candidates=[s])
    app.run(timeout=60)
    assert not app.exception
    next(b for b in app.button if b.label.startswith('Xuất highlight')).click().run(timeout=60)
    assert not app.exception
    assert (tmp_path/'summary.mp4').exists()
    report=json.loads((tmp_path/'report.json').read_text())
    assert report['reviewed'] is True
