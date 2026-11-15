import json, numpy as np
from scipy.ndimage import gaussian_filter1d
D = json.load(open('/home/claude/work/dets.json')); N = D['n']; S = D['dets']
W,H = 1280,720
MISS = 0.75
# Viterbi: states per sample = dets + miss
costs=[]; back=[]
prev=None
for k,s in enumerate(S):
    st = [(d, 1.4*d[5] + 0.8*d[6] - 0.15*d[4]) for d in s['d']]
    cur = [c for _,c in st] + [MISS]
    if prev is None:
        costs.append(np.array(cur)); back.append(None); prev=(st, np.array(cur)); continue
    pst, pc = prev
    new = np.zeros(len(cur)); bp = np.zeros(len(cur), int)
    for j in range(len(cur)):
        best=1e9; bi=0
        for i in range(len(pc)):
            if j < len(st) and i < len(pst):
                a, b = pst[i][0], st[j][0]
                ca=((a[0]+a[2])/2,(a[1]+a[3])/2); cb=((b[0]+b[2])/2,(b[1]+b[3])/2)
                hh=max(a[3]-a[1], b[3]-b[1])
                tr = min(3.0, 2.5*np.hypot(ca[0]-cb[0], ca[1]-cb[1])/hh)
            else: tr = 0.0 if (j==len(st) and i==len(pst)) else 0.35
            v = pc[i]+tr
            if v<best: best=v; bi=i
        new[j]=best+cur[j]; bp[j]=bi
    back.append(bp); costs.append(new); prev=(st,new)
# backtrack
path=[0]*len(S); j=int(np.argmin(costs[-1]))
for k in range(len(S)-1,-1,-1):
    path[k]=j
    if back[k] is not None: j=back[k][j]
cx=np.full(N,np.nan); cy=np.full(N,np.nan); bh=np.full(N,np.nan)
for k,s in enumerate(S):
    j=path[k]
    if j < len(s['d']):
        d=s['d'][j]; f=s['f']
        cx[f]=(d[0]+d[2])/2; cy[f]=(d[1]+d[3])/2; bh[f]=d[3]-d[1]
found = ~np.isnan(cx)
print('coverage %.1f%%' % (found.sum()/len(S)*100))
json.dump({'cx':[None if np.isnan(v) else float(v) for v in cx],'cy':[None if np.isnan(v) else float(v) for v in cy],'bh':[None if np.isnan(v) else float(v) for v in bh]}, open('/home/claude/work/track.json','w'))
