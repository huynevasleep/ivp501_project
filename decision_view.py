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
                                db=None if np.isnan(loud) else round(float(loud), 1), quiet=bool(quiet[k]),
                                edges=str(df.edges.iloc[k]) if 'edges' in df else None,
                                rec=round(float(df.court_recall.iloc[k]), 3) if 'court_recall' in df else None,
                                prec=round(float(df.court_precision.iloc[k]), 3) if 'court_precision' in df else None,
                                tpl=int(df.court_template.iloc[k]) if 'court_template' in df else None))
    hist = None
    if has_score:                                       # Otsu view when no Hough applies to a frame
        counts, edges = np.histogram(df.court_score.to_numpy(), bins=40, range=(0, 1))
        hist = dict(counts=counts.tolist(), lo=0., hi=1.)
    return dict(rallies=rallies, samples=samples, court_threshold=meta.get('court_threshold'),
                loud_threshold=loud_cut, court_lines=meta.get('court_lines', {}), total=offset,
                court_debug=meta.get('court_debug', {}), score_hist=hist)


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
    add = lambda name, kind: media.add(str(Path(out)/name), kind, f'decision_view:{out}:{name}')
    for s in data['samples']:
        s['img'] = add(s['img'], 'image/jpeg')
        if s['edges'] and (Path(out)/s['edges']).exists(): s['edges'] = add(s['edges'], 'image/png')
        else: s['edges'] = None
    for cam in data['court_debug'].values():            # debug images of each court camera
        cam['template'] = add(cam['template'], 'image/png'); cam['hough'] = add(cam['hough'], 'image/png')
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
#panel.debug{width:620px}
#dbg{display:none}#panel.debug #dbg{display:block}#panel.debug #normalcap{display:none}
.cols{display:flex;gap:8px}.cols>.main{flex:1;min-width:0}.cols>.side{width:0;overflow:hidden}#panel.debug .cols>.side{width:210px;flex:none;overflow:visible}
.tabs{display:flex;gap:4px;margin:4px 0}.tabs button{padding:2px 8px;font-size:12px}.tabs button.on{border-color:var(--accent);color:var(--accent)}
.kv{font-size:12px;color:var(--muted);margin-top:4px}.kv b{color:var(--fg);font-weight:600}

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
<aside id="panel"><div class="head"><span class="title">Code đang quyết định gì?</span><span><button id="dbgbtn" title="Ảnh xám / nhị phân và Hough mà code dùng">Debug</button> <button id="tog" title="Thu gọn / mở rộng">⟨⟩</button></span></div>
<div class="body">
<div class="row"><span id="rally" class="title"></span> <span id="phase" class="chip"></span><div id="src" class="muted"></div></div>
<div class="cols"><div class="main">
<div id="dbg"><div class="tabs"><button data-v="gray" class="on">Xám</button><button data-v="canny">Canny (nhị phân)</button><button data-v="match">Khớp khuôn (nhị phân)</button></div></div>
<canvas id="kf" width="320" height="180"></canvas>
<div class="muted" id="kfcap" style="font-size:12px;margin-top:3px"></div>
<div id="dbgcap" class="kv"></div>
</div><div class="side"><div class="kv" id="sidetitle" style="margin-top:0"></div><canvas id="side" width="200" height="300"></canvas><div class="kv" id="sidecap"></div></div></div>
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
const cache={},pix={};let debug=false,view='gray';
const side=$('side').getContext('2d');
function img(url,S){if(!url)return null;let im=cache[url];if(!im){im=cache[url]=new Image();im.onload=()=>{if(last===S)drawKeyframe(S)};im.src=url}return im.complete&&im.naturalWidth?im:null}
function pixels(url,im){if(pix[url])return pix[url];const c=document.createElement('canvas');c.width=320;c.height=180;const x=c.getContext('2d');x.drawImage(im,0,0,320,180);
 try{return pix[url]=x.getImageData(0,0,320,180).data}catch(e){return null}}
function dilate(m){const o=new Uint8Array(m.length);for(let y=0;y<180;y++)for(let x=0;x<320;x++){if(!m[y*320+x])continue;
 for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const yy=y+dy,xx=x+dx;if(yy>=0&&yy<180&&xx>=0&&xx<320)o[yy*320+xx]=1}}return o}
function binary(url,im){const d=pixels(url,im);if(!d)return null;const m=new Uint8Array(320*180);for(let i=0;i<m.length;i++)m[i]=d[i*4]>127?1:0;return m}
function drawSegs(segs){for(const g of segs){kf.strokeStyle=g.kept?'#3ecf6e':'#ef6b5b';kf.lineWidth=g.kept?2:1.5;kf.setLineDash(g.kept?[]:[4,3]);
 kf.beginPath();kf.moveTo(g.seg[0],g.seg[1]);kf.lineTo(g.seg[2],g.seg[3]);kf.stroke()}kf.setLineDash([])}
const done={};
function drawKeyframe(S){if(!S)return;last=S;const rgb=img(S.img,S);if(!rgb)return;
 const key=(debug?view:'rgb')+'|'+S.img+'|'+S.tpl;if(done.key===key&&done.ok)return;done.key=key;done.ok=false;
 const cd=S.tpl!=null?D.court_debug[String(S.tpl)]:null;
 if(!debug){kf.drawImage(rgb,0,0,320,180);
  const lines=S.court?(D.court_lines[String(S.cam)]||[]):[];kf.strokeStyle='#3ecf6e';kf.lineWidth=2;
  for(const l of lines){kf.beginPath();kf.moveTo(l[0],l[1]);kf.lineTo(l[2],l[3]);kf.stroke()}done.ok=true}
 else if(view==='gray'){const d=pixels(S.img,rgb);if(d){const out=kf.createImageData(320,180);
   for(let i=0;i<320*180;i++){const y=Math.round(.299*d[i*4]+.587*d[i*4+1]+.114*d[i*4+2]);out.data[i*4]=out.data[i*4+1]=out.data[i*4+2]=y;out.data[i*4+3]=255}
   kf.putImageData(out,0,0);done.ok=true}else kf.drawImage(rgb,0,0,320,180)}
 else if(view==='canny'){const e=img(S.edges,S);kf.fillStyle='#000';kf.fillRect(0,0,320,180);if(e){kf.drawImage(e,0,0,320,180);done.ok=true}if(S.court&&cd)drawSegs(cd.segments)}
 else{const e=img(S.edges,S),t=cd?img(cd.template,S):null;kf.fillStyle='#000';kf.fillRect(0,0,320,180);
  if(e&&t){const E=binary(S.edges,e),T=binary(cd.template,t);if(E&&T){const Ew=dilate(E),Tw=dilate(T),out=kf.createImageData(320,180);
   for(let i=0;i<E.length;i++){let c=[0,0,0];if(T[i]&&Ew[i])c=[62,207,110];else if(T[i])c=[90,96,108];else if(E[i]&&!Tw[i])c=[239,107,91];else if(E[i])c=[62,207,110];
    out.data[i*4]=c[0];out.data[i*4+1]=c[1];out.data[i*4+2]=c[2];out.data[i*4+3]=255}kf.putImageData(out,0,0);done.ok=true}}}
 kf.strokeStyle=S.court?'#3ecf6e':'#ef6b5b';kf.lineWidth=4;kf.strokeRect(2,2,316,176);
 if(debug){const n=S.rec==null?'':'khớp khuôn cam '+S.tpl+': recall <b>'+S.rec.toFixed(2)+'</b> · precision <b>'+S.prec.toFixed(2)+'</b> → Dice <b>'+(S.score??0).toFixed(2)+'</b> (ngưỡng Otsu '+(D.court_threshold??0).toFixed(2)+')';
  const leg={gray:'Ảnh xám: đầu vào của Gauss 3×3 → Canny.',canny:'Canny 50/150 sau Gauss 3×3 (đúng ảnh code lưu). Đoạn Hough của khuôn: xanh = vạch sơn giữ, đỏ đứt = loại.',
   match:'Xanh = biên trùng khuôn · đỏ = biên của khung không nằm trên khuôn (làm giảm precision) · xám = khuôn không thấy trong khung (làm giảm recall).'}[view];
  $('dbgcap').innerHTML=leg+'<br>'+n;if(!drawSide(S,cd))done.ok=false}}
function drawSide(S,cd){const w=200,h=300;side.fillStyle='#0b0d11';side.fillRect(0,0,w,h);side.font='10px system-ui';
 const hough=S.court&&cd?img(cd.hough,S):null;if(S.court&&cd&&!hough)return false;
 if(hough){const H=270,X0=10;$('sidetitle').innerHTML='Không gian Hough (θ, ρ) của khuôn cam '+S.tpl;
  side.drawImage(hough,0,0,cd.theta_bins,cd.rho_bins,X0,0,180,H);
  for(const g of cd.segments){const x=X0+g.rho_theta[1],y=(g.rho_theta[0]+cd.rho_max)/(2*cd.rho_max)*H;
   side.strokeStyle=g.kept?'#3ecf6e':'#ef6b5b';side.lineWidth=2;side.beginPath();
   if(g.kept)side.arc(x,y,5,0,7);else{side.moveTo(x-4,y-4);side.lineTo(x+4,y+4);side.moveTo(x+4,y-4);side.lineTo(x-4,y+4)}side.stroke()}
  side.fillStyle='#9aa3ad';side.fillText('θ 0°',X0,H+12);side.fillText('180°',X0+158,H+12);side.fillText('ρ↓',0,10);
  const k=cd.segments.filter(g=>g.kept).length;$('sidecap').innerHTML='Mỗi điểm biên bỏ phiếu cho mọi đường đi qua nó; đỉnh sáng = đường thẳng. <span class="ok">○ '+k+' vạch sơn</span> · <span class="bad">× '+(cd.segments.length-k)+' loại</span> (mép băng rôn, bảng QC).'}
 else if(D.score_hist){const c=D.score_hist.counts,mx=Math.max(...c.map(v=>Math.log1p(v))),H=250,bw=180/c.length,X0=10;
  $('sidetitle').innerHTML='Khung này không qua Hough → Otsu trên điểm khớp khuôn (cả trận)';
  c.forEach((v,i)=>{const bh=Math.log1p(v)/mx*H;side.fillStyle=(i+.5)/c.length>(D.court_threshold??1)?'#3ecf6e':'#5a606c';side.fillRect(X0+i*bw,H-bh,bw-1,bh)});
  const tx=X0+(D.court_threshold??0)*180;side.strokeStyle='#e8e6e1';side.setLineDash([3,3]);side.beginPath();side.moveTo(tx,0);side.lineTo(tx,H);side.stroke();side.setLineDash([]);
  if(S.score!=null){const sx=X0+S.score*180;side.fillStyle='#5aa9ff';side.beginPath();side.moveTo(sx,H+2);side.lineTo(sx-5,H+10);side.lineTo(sx+5,H+10);side.fill()}
  side.fillStyle='#9aa3ad';side.fillText('0',X0,H+22);side.fillText('Dice 1',X0+150,H+22);
  $('sidecap').innerHTML='Histogram (thang log) điểm khớp khuôn của mọi khung; nét đứt = ngưỡng Otsu '+(D.court_threshold??0).toFixed(2)+'; ▲ = khung hiện tại ('+(S.score??0).toFixed(2)+').'}
 else{$('sidetitle').textContent='Không có dữ liệu debug (phân tích lại video)';$('sidecap').textContent=''}return true}
$('dbgbtn').onclick=()=>{debug=!debug;done.key=null;$('panel').classList.toggle('debug',debug);$('dbgbtn').classList.toggle('on',debug);if(last)drawKeyframe(last)};
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{view=b.dataset.v;done.key=null;document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('on',x===b));if(last)drawKeyframe(last)});
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
