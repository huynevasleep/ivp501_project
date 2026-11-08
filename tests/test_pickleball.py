import numpy as np
import pandas as pd
import pytest
from pickleball import propose_rallies,choose_rallies,review_rallies,analyze_match

def features(seconds,intervals,rate=3):
    t=np.arange(seconds*rate)/rate
    activity=np.zeros(len(t))
    for a,b in intervals: activity[(t>=a)&(t<b)]=.8
    return pd.DataFrame({'time':t,'activity':activity,'cut':False})

def test_keeps_rallies_with_context_and_bridges_short_pause():
    df=features(60,[(10,16),(17,25),(40,48)])
    result=propose_rallies(df,60)
    assert len(result)==2
    assert result[0]['start']==pytest.approx(8)
    assert result[0]['end']==pytest.approx(27)
    assert result[0]['end']-result[0]['start']>4
    assert result[1]['start']==pytest.approx(38)

def test_long_match_budget_and_nonoverlap():
    df=features(7200,[(i,i+15) for i in range(10,7190,30)])
    proposals=propose_rallies(df,7200)
    selected=choose_rallies(proposals,180)
    assert len(proposals)>200
    assert sum(s['end']-s['start'] for s in selected)<=180
    assert all(a['end']<=b['start'] for a,b in zip(selected,selected[1:]))

def test_static_and_suspicious_activity():
    assert not propose_rallies(features(60,[]),60)
    p=propose_rallies(features(150,[(5,140)]),150)
    assert p[0]['needs_review']
    assert not choose_rallies(p,150)

def test_scene_cut_separates_candidates():
    df=features(40,[(5,35)]); df.loc[60,'cut']=True
    p=propose_rallies(df,40)
    assert len(p)==2
    assert p[0]['end']<=20<=p[1]['start']

def test_review_rejects_overlaps_and_budget():
    table=pd.DataFrame([dict(keep=True,start=0,end=10),dict(keep=True,start=9,end=15)])
    with pytest.raises(ValueError): review_rallies(table,60)
    table.loc[1,'start']=10
    with pytest.raises(ValueError): review_rallies(table,60,12)
    assert len(review_rallies(table,60,15))==2

def test_streaming_decoder_static_video(tmp_path):
    import cv2
    source=tmp_path/'static.mp4'
    w=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),24,(320,180))
    for _ in range(120): w.write(np.zeros((180,320,3),np.uint8))
    w.release()
    df,meta,candidates=analyze_match(source,tmp_path/'out')
    assert len(df)==15
    assert meta['duration']==pytest.approx(5)
    assert candidates==[]
    assert not list((tmp_path/'out').glob('*.jpg'))
