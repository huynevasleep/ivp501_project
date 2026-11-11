"""One independent MP4 per rally; versioned directories prevent stale exports."""
from pathlib import Path
import json
import math
import subprocess
import uuid
import zipfile
import cv2
import imageio_ffmpeg


def export_individual(source,segments,out,progress=None):
    source=Path(source).resolve()
    cap=cv2.VideoCapture(str(source)); fps=cap.get(cv2.CAP_PROP_FPS)
    duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps if fps>0 else 0
    cap.release()
    if duration<=0: raise ValueError('Không đọc được video nguồn để tách pha.')
    ordered=sorted(segments,key=lambda s:s['start'])
    if not ordered: raise ValueError('Chưa chọn pha để xuất.')
    for s in ordered:
        a,b=float(s['start']),float(s['end'])
        if not math.isfinite(a+b) or not 0<=a<b<=duration+1e-6:
            raise ValueError('Mốc pha ngoài thời lượng video.')
    dest=Path(out)/'individual'/uuid.uuid4().hex
    dest.mkdir(parents=True,exist_ok=True)
    files=[]; manifest=[]
    for i,s in enumerate(ordered,1):
        target=dest/f'pha_{i:04d}.mp4'
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-ss',str(s['start']),'-i',str(source),
             '-t',str(s['end']-s['start']),'-map','0:v:0','-map','0:a:0?',
             '-c:v','libx264','-preset','fast','-pix_fmt','yuv420p',
             '-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2','-c:a','aac','-movflags','+faststart',str(target)]
        subprocess.run(cmd,check=True,capture_output=True)
        files.append(target)
        manifest.append(dict(rally=i,file=target.name,source_start=s['start'],source_end=s['end'],duration=s['end']-s['start']))
        if progress: progress(i/len(ordered))
    (dest/'rallies.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    archive=dest/'tat_ca_pha.zip'
    # MP4 is already compressed. Stream from disk, not a second in-memory copy.
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_STORED) as z:
        for p in files: z.write(p,p.name)
        z.write(dest/'rallies.json','rallies.json')
    return dict(files=files,archive=archive,segments=ordered,video=files[0])


def show_individual(result,key):
    import streamlit as st
    from presentation import timestamp
    st.subheader(f"Video riêng cho {len(result['files'])} pha")
    i=st.selectbox('Chọn video pha để xem / tải',range(len(result['files'])),key=f'clip_{key}',
                   format_func=lambda i:f"Pha {i+1:03d} · {timestamp(result['segments'][i]['start'])} → {timestamp(result['segments'][i]['end'])}")
    p=result['files'][i]
    st.caption(f"File riêng {p.name} · dài {result['segments'][i]['end']-result['segments'][i]['start']:.2f} giây · thanh phát bắt đầu từ 0:00.")
    st.video(str(p))
    st.download_button(f'Tải video pha {i+1:03d}',p.read_bytes(),p.name,'video/mp4',key=f'clip_dl_{key}')
    st.caption('Mỗi MP4 chỉ chứa một khoảng pha đã chọn, giữ âm thanh gốc nếu có. File ZIP chứa tất cả video riêng và mốc thời gian nguồn.')
    archive=result['archive']
    if archive.stat().st_size<=512*1024*1024:
        with archive.open('rb') as f:
            st.download_button('Tải tất cả pha (ZIP)',f,archive.name,'application/zip',key=f'zip_{key}')
    else:
        st.info(f'ZIP lớn hơn 512 MB đã lưu tại: {archive.resolve()}. Mở thư mục này để lấy file; vẫn có thể tải từng pha phía trên.')
