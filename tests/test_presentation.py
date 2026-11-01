from presentation import timestamp,reason,segment_table,plain_report

def test_time_carries_and_long_video():
    assert timestamp(59.99)=='01:00.0'
    assert timestamp(3601.2)=='01:00:01.2'

def test_explanations_use_measured_signals():
    s={'start':4.5,'end':5.5,'score':.6,'contributions':{'motion_norm':.4,'faces_norm':.2}}
    table=segment_table([s])
    assert 'cluster' not in table.columns
    assert 'chuyển động' in reason(s)
    assert '04.5' in plain_report([s],60)
    assert 'nổi trội' in reason({'contributions':{}})
