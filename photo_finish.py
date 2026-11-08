"""Classical image processing on an explicitly selected existing camera view."""
from pathlib import Path
import json
import cv2
import numpy as np


def finish_photo(source,start,end,out,roi=(0.,0.,1.,1.),sharpen=.7,denoise=3.,blur_length=0,blur_angle=0.,regularization=.03):
    if not 0<=start<end or end-start>20: raise ValueError('Chọn khoảnh khắc tối đa 20 giây.')
    if not 0<=roi[0]<roi[2]<=1 or not 0<=roi[1]<roi[3]<=1: raise ValueError('Vùng cắt không hợp lệ.')
    if not 0<=sharpen<=2 or not 0<=denoise<=10 or not 0<=blur_length<=25 or not .001<=regularization<=1:
        raise ValueError('Tham số xử lý ảnh ngoài giới hạn.')
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    cap=cv2.VideoCapture(str(source)); fps=cap.get(cv2.CAP_PROP_FPS)
    if fps<=0: cap.release(); raise ValueError('Không đọc được video.')
    if end>cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps+1/fps:
        cap.release(); raise ValueError('Khoảng chọn vượt thời lượng video.')
    first=int(np.ceil(start*fps)); cap.set(cv2.CAP_PROP_POS_FRAMES,first)
    best=None; best_score=-1.; best_time=None
    try:
        # Native fps: a sharp swing frame may last less than half a second.
        for i in range(max(1,int(np.floor(end*fps))-first)):
            ok,frame=cap.read()
            if not ok: break
            h,w=frame.shape[:2]
            crop=frame[int(roi[1]*h):int(roi[3]*h),int(roi[0]*w):int(roi[2]*w)]
            if min(crop.shape[:2])<8: raise ValueError('Vùng cắt quá nhỏ.')
            gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
            score=float(cv2.Laplacian(gray,cv2.CV_64F).var())
            if score>best_score: best=crop.copy(); best_score=score; best_time=(first+i)/fps
    finally: cap.release()
    if best is None: raise ValueError('Không có khung hình phù hợp.')
    clean=cv2.fastNlMeansDenoisingColored(best,None,denoise,denoise,7,21) if denoise>0 else best.copy()
    if blur_length>=3:
        # Experimental regularized inverse of a user-specified linear-motion PSF.
        pad=int(blur_length)+2; padded=cv2.copyMakeBorder(clean,pad,pad,pad,pad,cv2.BORDER_REFLECT)
        h,w=padded.shape[:2]; psf=np.zeros((h,w),np.float32)
        angle=np.deg2rad(blur_angle); dx=int((blur_length-1)*np.cos(angle)/2); dy=int((blur_length-1)*np.sin(angle)/2)
        cv2.line(psf,(w//2-dx,h//2-dy),(w//2+dx,h//2+dy),1.,1)
        psf/=psf.sum(); transfer=np.fft.fft2(np.fft.ifftshift(psf))
        inverse=transfer.conj()/(abs(transfer)**2+regularization)
        channels=[np.fft.ifft2(np.fft.fft2(padded[:,:,c])*inverse).real for c in range(3)]
        clean=np.clip(np.stack(channels,axis=2),0,255).astype(np.uint8)[pad:-pad,pad:-pad]
    enhanced=cv2.addWeighted(clean,1+sharpen,cv2.GaussianBlur(clean,(0,0),1.1),-sharpen,0)
    cv2.imwrite(str(out/'original.png'),best)
    cv2.imwrite(str(out/'enhanced.png'),enhanced)
    metadata=dict(time=best_time,start=start,end=end,roi=list(roi),width=best.shape[1],height=best.shape[0],
                  input_laplacian_variance=best_score,denoise=denoise,unsharp_amount=sharpen,
                  wiener_psf_length=blur_length,wiener_psf_angle=blur_angle,wiener_regularization=regularization,
                  view='user_selected_side_view',note='Sharpness score is not perceptual quality. No new viewpoint or details synthesized.')
    (out/'photo_report.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return out/'original.png',out/'enhanced.png',metadata
