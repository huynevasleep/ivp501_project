"""Regression check on an existing local upload; no network transfer."""
from pathlib import Path
import json
import cv2
from core import analyze,select,export_video
from streamlit.testing.v1 import AppTest

source=next(Path('runs').glob('*/input.mp4'))
out=Path('runs/regression_uploaded'); out.mkdir(exist_ok=True)
df,meta=analyze(source,out)
for optimizer in ['greedy','knapsack']:
    segments,scores=select(df,meta,optimizer=optimizer)
    assert segments
    total=sum(s['end']-s['start'] for s in segments)
    assert total<=meta['duration']*.15+1e-6
    video=export_video(source,segments,out)
    cap=cv2.VideoCapture(str(video))
    assert cap.isOpened()
    actual=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    assert abs(actual-total)<max(.5,len(segments)/meta['fps']*2)
    (out/'report.json').write_text(json.dumps({'settings':{'ratio':.15}}))
    app=AppTest.from_file('app.py')
    app.session_state['result']=(out,df,meta,segments,scores,video)
    app.run(timeout=60)
    assert not app.exception,app.exception
    print(optimizer,'PASS',round(meta['duration'],2),round(actual,2),len(segments),flush=True)
