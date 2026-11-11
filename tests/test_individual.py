import json
import zipfile
import cv2
import numpy as np
import pytest
from rally_export import export_individual
from rally_preview import preview_clip


def test_each_file_contains_only_its_rally_and_zip_is_current(tmp_path):
    source=tmp_path/'input.mp4'
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),24,(160,120))
    for color in [(0,0,255),(0,255,0),(255,0,0)]:
        for _ in range(24): writer.write(np.full((120,160,3),color,np.uint8))
    writer.release()
    segments=[dict(start=0.,end=1.),dict(start=2.,end=3.)]
    result=export_individual(source,segments,tmp_path)
    assert len(result['files'])==2
    assert preview_clip(source,segments[1],tmp_path,result)==result['files'][1]
    preview=preview_clip(source,dict(start=1,end=2),tmp_path)
    assert preview!=source
    assert preview_clip(source,dict(start=1,end=2),tmp_path)==preview
    for i,p in enumerate(result['files']):
        cap=cv2.VideoCapture(str(p))
        assert cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS)==pytest.approx(1,abs=.08)
        ok,frame=cap.read(); assert ok
        assert int(np.argmax(frame.mean(axis=(0,1))))==[2,0][i]
        cap.release()
    with zipfile.ZipFile(result['archive']) as z:
        assert set(z.namelist())=={'pha_0001.mp4','pha_0002.mp4','rallies.json'}
        assert json.loads(z.read('rallies.json'))[1]['source_start']==2
    second=export_individual(source,segments[:1],tmp_path)
    assert second['archive']!=result['archive']
    with zipfile.ZipFile(second['archive']) as z: assert 'pha_0002.mp4' not in z.namelist()
    with pytest.raises(ValueError): export_individual(source,[dict(start=1,end=5)],tmp_path)
