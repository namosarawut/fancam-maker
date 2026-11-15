import cv2, json, os
from ultralytics import YOLO
m = YOLO('/home/claude/models/yolov8s.pt')
cap = cv2.VideoCapture('/home/claude/work/in.mp4'); out=[]; i=0; STEP=2
os.makedirs('/home/claude/work/thumbs', exist_ok=True)
seen={}
while True:
    ok, fr = cap.read()
    if not ok: break
    if i % STEP == 0:
        r = m.track(fr, classes=[0], conf=0.2, imgsz=960, persist=True, tracker='botsort.yaml', verbose=False)[0]
        dets=[]
        if r.boxes.id is not None:
            for b,t in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.id.cpu().numpy()):
                x1,y1,x2,y2=[int(v) for v in b]; t=int(t)
                dets.append([t,x1,y1,x2,y2])
                seen.setdefault(t,[]).append((i,x1,y1,x2,y2))
        out.append({'f':i,'d':dets})
        if i%300==0: print(i, flush=True)
    i+=1
json.dump({'n':i,'dets':out}, open('/home/claude/work/mot.json','w'))
