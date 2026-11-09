import json
import cv2
import numpy as np
import pytest
from rally_evidence import rallies_from_events,ball_candidates,track_ball,timecode_table,rally_metrics
from photo_finish import finish_photo
from pickleball import choose_rallies


def event(t,kind,confirmed=True):
    return dict(time=t,kind=kind,confirmed=confirmed)


def test_bounces_and_lost_ball_do_not_end_rally():
    events=[event(1,'serve'),event(2,'bounce'),event(3,'paddle_contact'),event(4,'bounce'),event(5,'occluded'),event(8,'rally_end')]
    rallies,warnings=rallies_from_events(events,10)
    assert [(s['start'],s['end']) for s in rallies]==[(1,8)]
    assert not warnings


def test_unconfirmed_and_open_rallies_are_not_exported():
    rallies,warnings=rallies_from_events([event(1,'serve'),event(5,'rally_end',False)],10)
    assert not rallies and warnings
    with pytest.raises(ValueError): rallies_from_events([event(20,'serve')],10)
    with pytest.raises(ValueError): rallies_from_events([event(1,'serve'),event(1,'rally_end')],10)


def test_all_mode_never_discards_eligible_rallies():
    rallies=[dict(start=i*20,end=i*20+15,score=.1,needs_review=False) for i in range(20)]
    assert len(choose_rallies(rallies))==20
    assert sum(s['end']-s['start'] for s in choose_rallies(rallies,30))<=30
    table=timecode_table(rallies)
    assert table.iloc[-1].highlight_end==300
    assert table.iloc[-1].source_end==395


def test_rally_metrics_one_to_one_and_boundaries():
    metric=rally_metrics([(0,10),(1,11)],[(0,10)])
    assert metric['matched']==1
    assert metric['f1']==pytest.approx(2/3)
    assert metric['start_mae_seconds']==0
    assert rally_metrics([],[])['f1']==1
    assert rally_metrics([],[(0,10)])['f1']==0


def test_small_yellow_moving_ball_but_not_large_board():
    frame=np.zeros((240,320,3),np.uint8)
    cv2.circle(frame,(100,100),4,(0,255,255),-1)
    cv2.rectangle(frame,(180,30),(260,80),(0,255,255),-1)
    candidates=ball_candidates(frame,np.zeros((240,320),np.uint8))
    assert len(candidates)==1
    assert candidates[0][:2]==pytest.approx((100,100))
    assert not ball_candidates(frame,cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY))


@pytest.fixture
def video(tmp_path):
    path=tmp_path/'ball.mp4'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),24,(320,240))
    for i in range(72):
        frame=np.full((240,320,3),30,np.uint8)
        cv2.circle(frame,(30+i*3,120),5,(0,255,255),-1)
        writer.write(frame)
    writer.release()
    return path


def bouncing_video(path,reverse_mid=False):
    """Ball on a parabola: floor bounces at t=1s and t=2s (24 fps); optionally a sharp
    horizontal reversal (a paddle-like hit) at t=1.5s between the two bounces."""
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),24,(320,240))
    x=30.
    for j in range(72):
        x+=-3. if reverse_mid and j>=36 else 3.
        y=200-80*abs(np.sin(np.pi*j/24))
        frame=np.full((240,320,3),30,np.uint8)
        cv2.circle(frame,(int(x),int(y)),5,(0,255,255),-1)
        writer.write(frame)
    writer.release()
    return path


def test_two_bounces_without_paddle_hit_flag_a_dead_ball(tmp_path):
    _,events,_,_=track_ball(bouncing_video(tmp_path/'bounce.mp4'),0,3,tmp_path/'evidence')
    bounces=[e for e in events if e['kind']=='bounce_candidate']
    dead=[e for e in events if e['kind']=='dead_ball_candidate']
    assert len(bounces)>=2
    assert len(dead)==1
    assert dead[0]['time']==pytest.approx(2.,abs=.2)
    assert dead[0]['bounces'][0]==pytest.approx(1.,abs=.2)
    assert all(not e['confirmed'] for e in events)


def test_a_direction_change_between_bounces_resets_the_dead_ball_count(tmp_path):
    _,events,_,_=track_ball(bouncing_video(tmp_path/'hit.mp4',reverse_mid=True),0,3,tmp_path/'evidence')
    kinds=[e['kind'] for e in events]
    assert 'direction_change_candidate' in kinds
    assert 'dead_ball_candidate' not in kinds


def test_tracking_outputs_native_fps_evidence(video,tmp_path):
    table,events,overlay,report=track_ball(video,0,3,tmp_path/'evidence')
    assert len(table)==72
    assert table.observed.mean()>.9
    assert abs(table.loc[table.observed,'x'].iloc[-1]-243)<4
    assert all(not e['confirmed'] for e in events)
    assert overlay.exists()
    cap=cv2.VideoCapture(str(overlay)); assert cap.isOpened(); cap.release()


def test_photo_preserves_original_and_dimensions(video,tmp_path):
    original,enhanced,report=finish_photo(video,0,2,tmp_path/'photo',blur_length=5)
    assert cv2.imread(str(original)).shape==cv2.imread(str(enhanced)).shape==(240,320,3)
    assert 0<=report['time']<2
    assert json.loads((tmp_path/'photo'/'photo_report.json').read_text())['wiener_psf_length']==5
    with pytest.raises(ValueError): finish_photo(video,0,10,tmp_path/'bad')
