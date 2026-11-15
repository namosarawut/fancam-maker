import cv2, json, sys, numpy as np
from ultralytics import YOLO
m = YOLO('/home/claude/models/yolov8s.pt')
ref = cv2.imread('/mnt/user-data/uploads/d22f58ce-image.png')
def hist(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv],[0,1],None,[30,32],[0,180,0,256]); cv2.normalize(h,h,1,0,cv2.NORM_L1); return h
rt = hist(ref[300:520,190:390]); rl = hist(ref[580:860,210:330])
cap = cv2.VideoCapture('/home/claude/work/in.mp4'); out=[]; i=0; STEP=2
while True:
    ok, fr = cap.read()
    if not ok: break
    if i % STEP == 0:
        r = m.predict(fr, classes=[0], conf=0.25, imgsz=960, verbose=False)[0]
        dets=[]
        for b,c in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()):
            x1,y1,x2,y2 = [int(v) for v in b]; h=y2-y1; w=x2-x1
            if h<40: continue
            t = fr[y1+int(.18*h):y1+int(.48*h), x1+int(.2*w):x2-int(.2*w)]
            l = fr[y1+int(.55*h):y1+int(.9*h), x1+int(.25*w):x2-int(.25*w)]
            st = cv2.compareHist(rt, hist(t), cv2.HISTCMP_BHATTACHARYYA) if t.size else 1
            sl = cv2.compareHist(rl, hist(l), cv2.HISTCMP_BHATTACHARYYA) if l.size else 1
            dets.append([x1,y1,x2,y2,float(c),float(st),float(sl)])
        out.append({'f':i,'d':dets})
        if i%300==0: print(i, flush=True)
    i+=1
json.dump({'n':i,'dets':out}, open('/home/claude/work/dets.json','w'))
