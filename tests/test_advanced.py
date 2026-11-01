import pytest
from core import knapsack_select
from experiments import aggregate
import pandas as pd

def test_knapsack_beats_single_high_score():
    segments=[dict(start=0,end=3,score=3),dict(start=3,end=5,score=2.5),dict(start=5,end=7,score=2.5)]
    result=knapsack_select(segments,4)
    assert len(result)==2
    assert sum(s['score']*(s['end']-s['start']) for s in result)==10

def test_quantization_never_exceeds_budget():
    segments=[dict(start=i,end=i+.333,score=1) for i in range(10)]
    result=knapsack_select(segments,1)
    assert sum(s['end']-s['start'] for s in result)<=1

def test_bootstrap_reproducible():
    t=pd.DataFrame({'method':['a','a','a'],'f1_mean':[.2,.5,.8]})
    a=aggregate(t); b=aggregate(t)
    assert a.equals(b)
    assert a['mean'][0]==pytest.approx(.5)
