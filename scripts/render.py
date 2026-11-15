import json, sys, subprocess, cv2, numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter
W,H=1280,720; OW,OH=1080,1920; ZOOM=float(sys.argv[1]) if len(sys.argv)>1 else 1.2
D=json.load(open('/home/claude/work/mot.json')); N=D['n']; sel={2,120,184}
f,cx,cy,bh=[],[],[],[]
for s in D['dets']:
    for t,x1,y1,x2,y2 in s['d']:
        if t in sel: f.append(s['f']); cx.append((x1+x2)/2); cy.append((y1+y2)/2); bh.append(y2-y1)
f=np.array(f); bh=median_filter(np.array(bh,float),size=31,mode='nearest')
# use top of box (head) anchored: center from y1 + h/2 using smoothed height is more stable
allf=np.arange(N)
X=np.interp(allf,f,cx); Y=np.interp(allf,f,cy); Hh=np.interp(allf,f,bh)
X=gaussian_filter1d(X,9); Y=gaussian_filter1d(Y,12); Hh=gaussian_filter1d(Hh,25)
ch=np.clip(Hh*ZOOM,300,720); cw=ch*9/16
cap=cv2.VideoCapture('/home/claude/work/in.mp4')
p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{OW}x{OH}','-r','30','-i','-',
   '-i','/home/claude/work/in.mp4','-map','0:v','-map','1:a','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',
   '-c:a','aac','-b:a','192k','-shortest','/home/claude/work/fancam.mp4'],stdin=subprocess.PIPE)
for i in range(N):
    ok,fr=cap.read()
    if not ok: break
    h=ch[i]; w=cw[i]
    x0=np.clip(X[i]-w/2,0,W-w); y0=np.clip(Y[i]-h/2,0,H-h)
    s=OH/h
    M=np.float32([[s,0,-x0*s],[0,s,-y0*s]])
    out=cv2.warpAffine(fr,M,(OW,OH),flags=cv2.INTER_LANCZOS4)
    p.stdin.write(out.tobytes())
p.stdin.close(); p.wait(); print('done')
