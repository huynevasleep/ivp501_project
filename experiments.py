"""Reproducible batch evaluation: python experiments.py manifest.json output_dir."""
import argparse
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from core import analyze, select, boundary_f1, summary_f1

METHODS=[('uniform','uniform',False,'greedy'),('motion','motion',False,'greedy'),('hybrid','balanced',True,'greedy'),('no_diversity','balanced',False,'greedy'),('no_motion','no_motion',True,'greedy'),('knapsack','balanced',False,'knapsack')]

def compare(df,meta,labels,ratio=.15):
    rows=[]
    for name,mode,div,opt in METHODS:
        started=time.perf_counter()
        segments,_=select(df,meta,ratio,mode,div,opt)
        metrics=summary_f1(segments,labels['summaries'],meta['duration'])
        rows.append(dict(method=name,f1_mean=metrics['mean'],f1_max=metrics['max'],actual_ratio=sum(s['end']-s['start'] for s in segments)/meta['duration'],clusters=len({s['cluster'] for s in segments}),selection_seconds=time.perf_counter()-started))
    return pd.DataFrame(rows)

def aggregate(table):
    rng=np.random.default_rng(42); rows=[]
    for method,g in table.groupby('method'):
        x=g.f1_mean.to_numpy()
        boots=rng.choice(x,(2000,len(x)),replace=True).mean(axis=1)
        rows.append(dict(method=method,videos=len(x),mean=float(x.mean()),std=float(x.std(ddof=1)) if len(x)>1 else 0.,ci95_low=float(np.quantile(boots,.025)),ci95_high=float(np.quantile(boots,.975))))
    return pd.DataFrame(rows)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('manifest'); parser.add_argument('output'); args=parser.parse_args()
    manifest=Path(args.manifest).resolve(); out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    config=json.loads(manifest.read_text(encoding='utf-8')); tables=[]
    for i,item in enumerate(config['videos']):
        started=time.perf_counter()
        df,meta=analyze(manifest.parent/item['video'],out/str(i))
        labels=json.loads((manifest.parent/item['labels']).read_text(encoding='utf-8'))
        table=compare(df,meta,labels,config.get('ratio',.15))
        table['video']=item['video']; table['boundary_f1']=boundary_f1(meta['cuts'],labels['boundaries'])
        table['pipeline_seconds']=time.perf_counter()-started; tables.append(table)
    if not tables: raise ValueError('Manifest phải có ít nhất một video.')
    result=pd.concat(tables,ignore_index=True); result.to_csv(out/'per_video.csv',index=False)
    aggregate(result).to_csv(out/'aggregate.csv',index=False)
    (out/'protocol.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print(aggregate(result).to_string(index=False))

if __name__=='__main__': main()
