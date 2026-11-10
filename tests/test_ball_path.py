import cv2
import numpy as np
import pytest
from ball_path import ball_path, link_tracklets, split_flights, rally_calls

W, H, FPS = 640, 360, 30
COURT = [[40, 110, 280, 110], [40, 170, 280, 170], [40, 110, 40, 170], [280, 110, 280, 170]]   # 320x180 frame


def _video(path, ball_at, crowd=True, frames=90):
    """Red floor, blue court, grey crowd strip; a yellow ball at ball_at(i) (or None); a jiggling yellow blob in the crowd."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), FPS, (W, H))
    rng = np.random.default_rng(0)
    crowd_tex = (rng.random((150, W, 3))*120+60).astype(np.uint8)
    for i in range(frames):
        img = np.full((H, W, 3), (40, 40, 150), np.uint8)                       # red floor (BGR)
        img[:150] = crowd_tex                                                   # textured crowd above the floor
        cv2.rectangle(img, (80, 220), (560, 340), (140, 70, 30), -1)            # blue court
        cv2.rectangle(img, (80, 220), (560, 340), (255, 255, 255), 3)
        if crowd:
            x = 300+int(6*np.sin(i*1.7)); cv2.circle(img, (x, 60+int(5*np.cos(i*2.3))), 5, (0, 230, 230), -1)
        p = ball_at(i)
        if p is not None: cv2.circle(img, (int(p[0]), int(p[1])), 5, (0, 230, 230), -1)
        writer.write(img)
    writer.release()


def _median(path):
    cap = cv2.VideoCapture(str(path)); ok, f = cap.read(); cap.release()
    return cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (320, 180))


def _bounce_then_hit(i):
    """Left to right: falls onto the court, bounces at frame 30, then a paddle sends it back at frame 55."""
    if i < 30: return 100+8*i, 255-6*i+.25*i*i                                   # arc landing at (340, 300), falling
    if i < 55: k = i-30; return 340+8*k, 300-9*k+.25*k*k                       # rises again: same direction (bounce)
    k = i-55; return 540-9*k, 231-7*k+.25*k*k                                   # sent back to the left (hit)


def test_bounce_and_hit_on_a_synthetic_rally(tmp_path):
    path = tmp_path/'rally.mp4'; _video(path, _bounce_then_hit)
    r = ball_path(path, 0, 3, COURT, _median(path))
    kinds = [(e['kind'], e['frame']) for e in r['events']]
    assert [k for k, _ in kinds] == ['bounce', 'hit']
    assert abs(kinds[0][1]-30) <= 2 and abs(kinds[1][1]-55) <= 2
    assert r['events'][0]['inside'] is True
    assert all(min(y for _, y in t['p']) > 150 for t in r['tracks'])          # the crowd blob is not a flight


def test_crowd_flicker_alone_gives_no_flight(tmp_path):
    path = tmp_path/'crowd.mp4'; _video(path, lambda i: None)
    r = ball_path(path, 0, 3, COURT, _median(path))
    assert r['tracks'] == [] and r['events'] == []


def test_split_flights_finds_the_kink():
    f = list(range(40)); p = [(10.+5*i, 200-6*i+.2*i*i) if i < 20 else (110.-5*(i-20), 200-6*20+.2*400+4*(i-20)) for i in f]
    pieces = split_flights(dict(f=f, p=p), 6)
    assert len(pieces) == 2 and abs(pieces[0]['f'][-1]-20) <= 1


def test_linker_follows_constant_velocity_through_a_distractor():
    frames = [[(10.+8*i, 100.), (60., 30.+(i % 2)*3)] for i in range(20)]       # ball moving right + flicker in place
    tracks = link_tracklets(frames, 854)
    ball = max(tracks, key=lambda t: np.ptp([x for x, _ in t['p']]))
    assert len(ball['p']) == 20


def test_double_bounce_needs_one_continuous_flight():
    b1 = dict(kind='bounce', frame=10, flight_in=0, flight_out=1, inside=True)
    b2 = dict(kind='bounce', frame=25, flight_in=1, flight_out=2, inside=True)
    gap = dict(kind='bounce', frame=40, flight_in=5, flight_out=6, inside=True)  # a different, unconnected flight
    assert [c['call'] for c in rally_calls([b1, b2])] == ['double_bounce']
    assert rally_calls([b1, gap]) == []
    out = dict(kind='bounce', frame=3, flight_in=0, flight_out=1, inside=False)
    assert rally_calls([out]) == [dict(frame=3, call='out')]


def test_flights_curve_down_with_gravity():
    from ball_path import ball_tracklets
    f = list(range(12))
    falling = dict(f=f, p=[(10.+12*i, 200-8*i+.5*i*i) for i in f])             # y'' > 0: a thrown ball
    rising = dict(f=f, p=[(10.+12*i, 100+8*i-.5*i*i) for i in f])              # y'' < 0: not a free flight
    jiggle = [dict(f=f, p=[(300.+2*(i % 2), 50.+(i % 3)) for i in f]) for _ in range(3)]
    kept, _ = ball_tracklets([falling, rising]+jiggle, 30)
    assert kept == [falling]
