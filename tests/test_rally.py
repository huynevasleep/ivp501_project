import cv2
import numpy as np
import pandas as pd
import pytest
from core import detect_rallies, select, best_shots, otsu_threshold

FPS = 2


def timeline(spec):
    """spec: list of (seconds, camera, loudness_db). Camera 0 = fixed court view, 1 = handheld close-up."""
    rows = []
    for seconds, camera, db in spec:
        for _ in range(int(seconds*FPS)):
            rows.append(dict(time=len(rows)/FPS, camera=camera, motion=.5 if camera == 0 else 6., loudness_db=db, image=f'f{len(rows)}.jpg'))
    df = pd.DataFrame(rows)
    return df, dict(duration=len(rows)/FPS, sample_fps=FPS)


MATCH = [(5, 1, -20), (3, 0, -21), (12, 0, -31), (4, 1, -18),   # waiting, long rally, close-up cheer
         (3, 0, -21), (3, 0, -30), (3, 0, -15),                  # short rally, huge cheer (an ace?)
         (5, 1, -20), (0.5, 0, -31), (5, 1, -20)]                 # 0.5 s quiet: not a rally


def test_otsu_splits_bimodal():
    values = np.r_[np.full(50, -31.), np.full(50, -20.)]
    assert -31 < otsu_threshold(values) < -20


def test_otsu_matches_opencv_reference():
    """Self-implemented Otsu agrees with cv2.THRESH_OTSU on a bimodal image (within 2 gray levels)."""
    rng = np.random.default_rng(0)
    img = np.clip(np.r_[rng.normal(70, 12, 4000), rng.normal(185, 15, 6000)], 0, 255).astype(np.uint8)
    reference, _ = cv2.threshold(img.reshape(100, 100), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ours = otsu_threshold(img.astype(float))
    assert abs(ours - reference) <= 2


def test_rallies_are_quiet_court_stretches_with_serve_and_reaction():
    df, meta = timeline(MATCH)
    rallies = detect_rallies(df, meta)
    assert [(r['core_start'], r['core_end']) for r in rallies] == [(8., 20.), (27., 30.)]
    assert rallies[0]['start'] == 7. and rallies[0]['end'] == 22.      # 1 s before the serve, 2 s of reaction
    assert all(a['end'] <= b['start'] for a, b in zip(rallies, rallies[1:]))


def test_pre_roll_does_not_reach_into_the_close_up():
    df, meta = timeline([(4, 1, -20), (6, 0, -31), (4, 1, -18)])   # close-up, then the serve right after the cut
    (rally,) = detect_rallies(df, meta)
    assert rally['start'] == rally['core_start'] == 4.


def test_scores_reward_long_rally_and_loud_reaction():
    df, meta = timeline(MATCH)
    long_rally, ace = detect_rallies(df, meta)
    assert long_rally['contributions']['rally_length'] > ace['contributions']['rally_length']
    assert ace['contributions']['crowd_reaction'] > long_rally['contributions']['crowd_reaction']


def test_close_padding_is_split_in_the_pause():
    df, meta = timeline([(4, 0, -31), (1, 0, -18), (4, 0, -31), (3, 1, -20)])
    a, b = detect_rallies(df, meta, gap=0)
    assert a['end'] == b['start'] == 4.5


def test_select_keeps_whole_rallies_within_budget():
    df, meta = timeline(MATCH)
    rallies = detect_rallies(df, meta)
    for optimizer in ('greedy', 'knapsack'):
        chosen, score = select(df, meta, ratio=.4, mode='rally', optimizer=optimizer)
        assert chosen and all(any(c['start'] == r['start'] and c['end'] == r['end'] for r in rallies) for c in chosen)
        assert sum(c['end']-c['start'] for c in chosen) <= meta['duration']*.4
        assert len(score) == len(df)
    chosen, _ = select(df, meta, ratio=.05, mode='rally')    # 2.4 s budget: no rally fits, none is cut
    assert chosen == []


def test_ratio_one_keeps_every_rally():
    df, meta = timeline(MATCH)
    chosen, _ = select(df, meta, ratio=1., mode='rally')
    assert [(c['start'], c['end']) for c in chosen] == [(r['start'], r['end']) for r in detect_rallies(df, meta)]


def test_best_shot_crops_the_moving_player(tmp_path):
    path = tmp_path/'court.mp4'; fps = 24
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (320, 240))
    rng = np.random.default_rng(0)
    floor = (rng.random((240, 320, 3))*60+90).astype(np.uint8)     # textured, so sharpness is measurable
    player = (rng.random((100, 40, 3))*255).astype(np.uint8)
    phase = 0.
    for i in range(fps*4):
        phase += .6 if 30 <= i < 60 else .08                            # moves slowly, swings fast in the middle
        x = 100+int(40*np.sin(phase))
        frame = floor.copy(); frame[90:190, x:x+40] = player
        writer.write(frame)
    writer.release()
    shots = best_shots(path, [dict(start=0., end=4.)], tmp_path)
    assert len(shots) == 1
    shot = shots[0]
    assert 30 <= shot['frame'] < 60
    assert shot['box'][3] >= 90
    assert (tmp_path/shot['image']).exists() and (tmp_path/shot['full_image']).exists()


def _court_frame(rng, shift=0):
    """Fixed court camera: straight court lines on a textured floor; players move."""
    img = (rng.random((180, 320))*30+60).astype(np.uint8)
    for y in (40, 90, 150):
        cv2.line(img, (20, y), (300, y), 255, 2)
    cv2.line(img, (20, 40), (20, 150), 255, 2); cv2.line(img, (300, 40), (300, 150), 255, 2)
    x = int(rng.integers(40, 260)); cv2.rectangle(img, (x, 60+shift), (x+12, 100+shift), 200, -1)
    return cv2.GaussianBlur(img, (5, 5), 0)


def test_court_cameras_from_edges_alone():
    from core import _edges, court_cameras
    rng = np.random.default_rng(0)
    frames, camera = [], []
    for _ in range(30): frames.append(_court_frame(rng)); camera.append(0)                    # fixed court camera
    for _ in range(30):                                                                          # hand-held close-up: edges move every frame
        img = np.zeros((180, 320), np.uint8); cx, cy = rng.integers(60, 260), rng.integers(40, 140)
        cv2.circle(img, (int(cx), int(cy)), int(rng.integers(20, 60)), 255, -1); frames.append(cv2.GaussianBlur(img, (5, 5), 0)); camera.append(1)
    for _ in range(30):                                                                          # static but with no straight lines
        img = np.zeros((180, 320), np.uint8); cv2.circle(img, (160, 90), 50, 255, -1); frames.append(cv2.GaussianBlur(img, (9, 9), 0)); camera.append(2)
    edges = np.array([np.packbits(_edges(f)) for f in frames])
    score, court_ids = court_cameras(edges, camera)
    assert court_ids == [0]
    assert score[:30].min() > .8 and score[30:].max() < .3


def test_single_cluster_video_keeps_its_court_camera():
    from core import _edges, court_cameras
    rng = np.random.default_rng(0)
    edges = np.array([np.packbits(_edges(_court_frame(rng))) for _ in range(30)])
    score, court_ids = court_cameras(edges, [0]*30)      # one fixed court camera, one cluster
    assert court_ids == [0]
    assert score.min() > .8
    blobs = []
    for _ in range(30):                                   # one static cluster with no straight lines
        img = np.zeros((180, 320), np.uint8); cv2.circle(img, (160, 90), 50, 255, -1)
        blobs.append(np.packbits(_edges(cv2.GaussianBlur(img, (9, 9), 0))))
    _, court_ids = court_cameras(np.array(blobs), [0]*30)
    assert court_ids == []


def test_detect_rallies_uses_edge_court_score():
    df, meta = timeline(MATCH)
    df['court_score'] = np.where(df.camera == 0, .9, .1); meta['court_threshold'] = .5
    df['motion'] = 1.                                           # motion no longer decides
    assert [(r['core_start'], r['core_end']) for r in detect_rallies(df, meta)] == [(8., 20.), (27., 30.)]
