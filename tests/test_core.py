from core import boundary_f1, summary_f1
import pytest

def test_one_to_one_boundaries():
    assert boundary_f1([1,1.1],[1],.2)==pytest.approx(2/3)
    assert boundary_f1([],[])==1

def test_overlap():
    s=[{'start':0,'end':2}]
    assert summary_f1(s,[[[1,3]]],4)['mean']==pytest.approx(.5)

def test_invalid_labels():
    with pytest.raises(ValueError): summary_f1([],[[[0,8]]],4)
