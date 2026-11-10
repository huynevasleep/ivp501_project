"""Highlight player with a collapsible side panel: what the rally code decided at this moment.

The panel follows the playing highlight: it maps the highlight time back to the source time,
takes the nearest analysed sample (2 per second) and shows the evidence detect_rallies used
there - court camera (edge-template match vs Otsu threshold, with the camera's painted court
lines drawn on the current frame), crowd loudness vs its Otsu threshold, and whether the moment
is the pre-roll, the rally core or the post-roll of the kept rally.
"""
import json
from pathlib import Path
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from core import court_mask, quiet_mask


def decision_data(df, meta, segments):
    """Everything the panel shows, from the same rules detect_rallies applies."""
    court = court_mask(df, meta); quiet, loud_cut = quiet_mask(df)
    t = df.time.to_numpy(); has_score = 'court_score' in df
    rallies, samples, offset = [], [], 0.
    for i, s in enumerate(segments):
        duration = s['end']-s['start']
        rallies.append(dict(i=i, start=s['start'], end=s['end'], core_start=s.get('core_start', s['start']),
                            core_end=s.get('core_end', s['end']), hl_start=offset, score=s.get('score', 0.),
                            parts=s.get('contributions', {})))
        offset += duration
        for k in np.flatnonzero((t >= s['start']) & (t < s['end'])):
            loud = df.loudness_db.iloc[k]
            samples.append(dict(r=i, t=round(float(t[k]), 2), cam=int(df.camera.iloc[k]), court=bool(court[k]), img=str(df.image.iloc[k]),
                                score=round(float(df.court_score.iloc[k]), 3) if has_score else None,
                                db=None if np.isnan(loud) else round(float(loud), 1), quiet=bool(quiet[k])))
    return dict(rallies=rallies, samples=samples, court_threshold=meta.get('court_threshold'),
                loud_threshold=loud_cut, court_lines=meta.get('court_lines', {}), total=offset)


def render(video, df, meta, segments, out, height=560):
    """Highlight player + collapsible decision panel (needs the analysis that produced `segments`).

    The keyframe shown is the analysed sample itself (out/frame_*.jpg, 320x180), so the panel
    shows exactly the image the decision was made on. Files are served by Streamlit's media
    manager, the same way st.video serves the highlight.
    """
    from streamlit import runtime
    media = runtime.get_instance().media_file_mgr
    url = media.add(str(video), 'video/mp4', f'decision_view:{video}')
    data = decision_data(df, meta, segments)
    for s in data['samples']:
        s['img'] = media.add(str(Path(out)/s['img']), 'image/jpeg', f'decision_view:{out}:{s["img"]}')
    data = json.dumps(data, ensure_ascii=False)
    components.html(_HTML.replace('__URL__', url).replace('__DATA__', data), height=height, scrolling=False)


_HTML = r'''<!doctype html><html><head><meta charset="utf-8"><style>
:root{--bg:#0f1115;--card:#171a21;--line:#2a2f3a;--fg:#e8e6e1;--muted:#9aa3ad;--ok:#3ecf6e;--warn:#f2b705;--bad:#ef6b5b;--accent:#5aa9ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
#wrap{display:flex;gap:10px;height:100vh;padding:4px}
#left{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}
video{width:100%;max-height:calc(100vh - 60px);background:#000;border-radius:8px}
#bar{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
button{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit}
button:hover{border-color:var(--accent)}
#panel{width:380px;flex:none;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;overflow:auto;transition:width .2s}
#panel.min{width:42px;padding:6px;overflow:hidden}
#panel.min .body{display:none}
#panel .head{display:flex;justify-content:space-between;align-items:center;gap:6px}
#panel.min .head{flex-direction:column}
#panel.min .title{writing-mode:vertical-rl;transform:rotate(180deg);margin-top:8px}
.title{font-weight:600}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-weight:600;font-size:12px}
.pre{background:#2b3a52;color:#9fc7ff}.core{background:#183d27;color:var(--ok)}.post{background:#3d3418;color:var(--warn)}
canvas{width:100%;border-radius:6px;display:block}
.row{margin:8px 0}.row .lbl{display:flex;justify-content:space-between;color:var(--muted);font-size:12px}
.meter{position:relative;height:10px;background:#0b0d11;border:1px solid var(--line);border-radius:5px;margin-top:3px}
.meter .fill{position:absolute;left:0;top:0;bottom:0;border-radius:5px}
.meter .tick{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--fg)}
.verdict{margin-top:8px;padding:8px;border-radius:6px;background:#0b0d11;border:1px solid var(--line)}
.muted{color:var(--muted)}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}
.legend span{margin-right:8px}.dot{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:3px;vertical-align:middle}
</style></head><body><div id="wrap">
<div id="left"><video id="v" src="__URL__" controls preload="metadata"></video>
<div id="bar"><button id="prev">◀ Pha trước</button><button id="next">Pha sau ▶</button><span id="pos" class="muted"></span></div></div>
<aside id="panel"><div class="head"><span class="title">Code đang quyết định gì?</span><button id="tog" title="Thu gọn / mở rộng">⟨⟩</button></div>
<div class="body">
<div class="row"><span id="rally" class="title"></span> <span id="phase" class="chip"></span><div id="src" class="muted"></div></div>
<canvas id="kf" width="320" height="180"></canvas>
<div class="muted" id="kfcap" style="font-size:12px;margin-top:3px"></div>
<div class="row"><div class="lbl"><span>Camera sân (khớp khuôn biên)</span><span id="cs"></span></div><div class="meter"><div class="fill" id="csf"></div><div class="tick" id="cst"></div></div></div>
<div class="row"><div class="lbl"><span>Âm lượng khán giả</span><span id="ld"></span></div><div class="meter"><div class="fill" id="ldf"></div><div class="tick" id="ldt"></div></div></div>
<div class="row"><div class="lbl"><span>Pha hiện tại theo thời gian (bấm để tua)</span></div><canvas id="strip" width="360" height="46"></canvas>
<div class="legend muted" style="font-size:11px;margin-top:3px"><span><i class="dot" style="background:var(--ok)"></i>sân + im</span><span><i class="dot" style="background:var(--warn)"></i>sân, ồn</span><span><i class="dot" style="background:var(--bad)"></i>không phải sân</span></div></div>
<div class="verdict" id="why"></div>
<div class="row muted" id="score" style="font-size:12px"></div>
</div></aside></div>
<script>
const D=__DATA__, v=document.getElementById('v'), $=id=>document.getElementById(id);
const kf=$('kf').getContext('2d'), strip=$('strip'), sc=strip.getContext('2d');
const fmt=s=>{s=Math.max(0,s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=(s%60).toFixed(1).padStart(4,'0');return (h?h+':':'')+String(m).padStart(2,'0')+':'+x};
let cur=-1;
function rallyAt(ht){let lo=0,hi=D.rallies.length-1,a=0;while(lo<=hi){const m=(lo+hi)>>1;if(D.rallies[m].hl_start<=ht){a=m;lo=m+1}else hi=m-1}return a}
function sampleAt(r,src){let best=null;for(const s of D.samples){if(s.r!==r)continue;if(s.t<=src+0.26)best=s;else break}return best||D.samples.find(s=>s.r===r)}
function meter(fill,tick,val,lo,hi,thr,good){const p=x=>Math.min(100,Math.max(0,(x-lo)/(hi-lo)*100));
 fill.style.width=(val==null?0:p(val))+'%';fill.style.background=good?'var(--ok)':'var(--bad)';tick.style.left=(thr==null?-10:p(thr))+'%'}
function drawStrip(R,src){const w=strip.width,h=strip.height;sc.clearRect(0,0,w,h);const x=t=>(t-R.start)/(R.end-R.start)*w;
 for(const s of D.samples){if(s.r!==R.i)continue;sc.fillStyle=!s.court?'#ef6b5b':(s.quiet?'#3ecf6e':'#f2b705');sc.fillRect(x(s.t),10,Math.max(2,w/(R.end-R.start)/2+1),h-20)}
 sc.strokeStyle='#e8e6e1';sc.lineWidth=1;sc.strokeRect(x(R.core_start),6,x(R.core_end)-x(R.core_start),h-12);
 sc.fillStyle='#9aa3ad';sc.font='10px system-ui';sc.fillText('lõi pha',x(R.core_start)+3,h-1);
 sc.strokeStyle='#5aa9ff';sc.lineWidth=2;sc.beginPath();sc.moveTo(x(src),0);sc.lineTo(x(src),h);sc.stroke()}
// Clips are re-encoded one by one; their real lengths drift a few ms each, so map the
// player clock onto the timecodes proportionally (0.25 s over 62 clips measured).
const clock=()=>v.duration&&isFinite(v.duration)?v.currentTime*D.total/v.duration:v.currentTime;
const seekTo=ht=>{v.currentTime=v.duration&&isFinite(v.duration)?ht*v.duration/D.total:ht};
const cache={};
function drawKeyframe(S){if(!S)return;let im=cache[S.img];
 if(!im){im=cache[S.img]=new Image();im.onload=()=>{if(last===S)drawKeyframe(S)};im.src=S.img}
 last=S;if(!im.complete||!im.naturalWidth)return;kf.drawImage(im,0,0,320,180);
 const lines=S.court?(D.court_lines[String(S.cam)]||[]):[];kf.strokeStyle='#3ecf6e';kf.lineWidth=2;
 for(const l of lines){kf.beginPath();kf.moveTo(l[0],l[1]);kf.lineTo(l[2],l[3]);kf.stroke()}
 kf.strokeStyle=S.court?'#3ecf6e':'#ef6b5b';kf.lineWidth=4;kf.strokeRect(2,2,316,176)}
let last=null;
function update(){const ht=clock(),ri=rallyAt(ht),R=D.rallies[ri];const src=R.start+(ht-R.hl_start);const S=sampleAt(ri,src);cur=ri;
 $('rally').textContent='Pha '+(ri+1)+'/'+D.rallies.length;$('pos').textContent='Highlight '+fmt(ht)+' / '+fmt(D.total);
 $('src').textContent='Video gốc '+fmt(src)+' · pha '+fmt(R.start)+' → '+fmt(R.end);
 const ph=src<R.core_start?['pre','Đệm trước (chuẩn bị giao bóng)']:src<R.core_end?['core','Lõi pha: đang đánh']:['post','Đệm sau (phản ứng, tiếng reo)'];
 $('phase').className='chip '+ph[0];$('phase').textContent=ph[1];
 drawKeyframe(S);
 const lines=S&&S.court?(D.court_lines[String(S.cam)]||[]):[];
 $('kfcap').textContent=S?('Khung mẫu '+fmt(S.t)+' · cụm camera '+S.cam+(lines.length?' · '+lines.length+' vạch sân của camera này':'')):'';
 if(S){const cs=S.score;$('cs').innerHTML=cs==null?'<span class="muted">không có điểm khớp</span>':(S.court?'<span class="ok">'+cs.toFixed(2)+' > '+D.court_threshold.toFixed(2)+' ✓</span>':'<span class="bad">'+cs.toFixed(2)+' ≤ '+D.court_threshold.toFixed(2)+' ✗</span>');
  meter($('csf'),$('cst'),cs,0,1,D.court_threshold,S.court);
  $('ld').innerHTML=S.db==null?'<span class="muted">không có âm thanh</span>':(S.quiet?'<span class="ok">'+S.db+' < '+D.loud_threshold.toFixed(1)+' dB · im ✓</span>':'<span class="warn">'+S.db+' ≥ '+D.loud_threshold.toFixed(1)+' dB · ồn</span>');
  meter($('ldf'),$('ldt'),S.db,-45,-10,D.loud_threshold,S.quiet);
  let why;
  if(ph[0]==='core') why=S.court&&S.quiet?'<b class="ok">Giữ</b>: camera sân đang lên hình <i>và</i> khán giả im → đang đánh.':'<b class="ok">Giữ</b> (lõi pha): khoảng ngắt ≤ 1 s giữa hai đoạn đang đánh được lấp, pha không bị cắt đôi.';
  else if(ph[0]==='pre') why='<b class="ok">Giữ</b>: 1 s đệm trước lúc khán giả im để có động tác giao bóng (không lùi quá đầu cảnh sân).';
  else why='<b class="ok">Giữ</b>: 2 s đệm sau khi khán giả ồn lên, để thấy kết quả pha.';
  $('why').innerHTML=why}
 const p=R.parts||{};$('score').textContent='Điểm pha '+(R.score||0).toFixed(2)+(p.rally_length!=null?' = độ dài '+(2*p.rally_length).toFixed(2)+' và tiếng reo '+(2*p.crowd_reaction).toFixed(2)+' (trung bình thứ hạng)':'');
 drawStrip(R,src)}
v.addEventListener('timeupdate',update);v.addEventListener('seeked',update);v.addEventListener('loadeddata',update);
(function loop(){if(!v.paused)update();requestAnimationFrame(loop)})();
$('tog').onclick=()=>$('panel').classList.toggle('min');
$('prev').onclick=()=>{const i=Math.max(0,rallyAt(clock())-1);seekTo(D.rallies[i].hl_start+0.01)};
$('next').onclick=()=>{const i=Math.min(D.rallies.length-1,rallyAt(clock())+1);seekTo(D.rallies[i].hl_start+0.01)};
strip.onclick=e=>{const R=D.rallies[cur<0?0:cur],b=strip.getBoundingClientRect(),f=(e.clientX-b.left)/b.width;seekTo(R.hl_start+f*(R.end-R.start))};
</script></body></html>'''
