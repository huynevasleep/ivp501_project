from pathlib import Path
import cv2
import numpy as np
from core import analyze,select,export_video
root=Path('runs'); root.mkdir(exist_ok=True)
p=root/'synthetic.mp4'
w=cv2.VideoWriter(str(p),cv2.VideoWriter_fourcc(*'mp4v'),24,(320,180))
for i in range(288):
    frame=np.zeros((180,320,3),np.uint8)
    frame[:]=[(40,20,180),(30,170,20),(180,40,20)][i//96]
    cv2.rectangle(frame,(i%240,50),(i%240+40,100),(255,255,255),-1)
    w.write(frame)
w.release()
df,meta=analyze(p,root/'smoke')
assert len(meta['cuts'])==2, meta
segments,_=select(df,meta,.25)
assert 0<sum(s['end']-s['start'] for s in segments)<=3.00001
out=export_video(p,segments,root/'smoke')
cap=cv2.VideoCapture(str(out)); assert cap.isOpened()
assert abs(cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS)-sum(s['end']-s['start'] for s in segments))<.2
cap.release()
from streamlit.testing.v1 import AppTest
app=AppTest.from_file('app.py').run(timeout=30)
assert not app.exception, app.exception
print('PASS: cuts, duration budget, MP4 export, Streamlit initial render')
