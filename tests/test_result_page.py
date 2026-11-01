import json
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from core import select, export_video

@pytest.mark.parametrize('optimizer',['greedy','knapsack'])
def test_result_page(tmp_path,optimizer):
    source=Path('runs/synthetic.mp4')
    if not source.exists(): pytest.skip('Run smoke_test.py to create fixture')
    from core import analyze
    df,meta=analyze(source,tmp_path)
    segments,scores=select(df,meta,optimizer=optimizer)
    video=export_video(source,segments,tmp_path)
    (tmp_path/'report.json').write_text(json.dumps({'settings':{'ratio':.15}}))
    app=AppTest.from_file(Path('app.py').resolve())
    app.session_state['result']=(tmp_path,df,meta,segments,scores,video)
    app.run(timeout=60)
    assert not app.exception
    assert len(app.tabs)==4
    app.text_input[0].set_value('nan').run()
    assert not app.exception
    assert len(app.error)==1
