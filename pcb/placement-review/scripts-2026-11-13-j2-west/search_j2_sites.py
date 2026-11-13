"""Search J2 (Tag-Connect) sites: >= 2 mm from every 15.6 mm switch-body square (2026-11-13, run before the move)."""
import pcbnew, math
import sys
b=pcbnew.LoadBoard(sys.argv[1] if len(sys.argv)>1 else 'pcb/ts52k.kicad_pcb')
m=lambda v:v/1e6
SQ=[];STAB=[];BOT=[]
for f in b.GetFootprints():
    r=f.GetReference(); cx,cy=m(f.GetPosition().x),m(f.GetPosition().y)
    if r.startswith('MX'):
        SQ.append((r,cx-7.8,cy-7.8,cx+7.8,cy+7.8))
        holes=[(m(p.GetPosition().x),m(p.GetPosition().y)) for p in f.Pads() if p.GetNumber()=='' and abs(m(p.GetPosition().x)-cx)>6]
        xs=sorted(set(round(h[0],2) for h in holes))
        for x in xs:
            ys=[h[1] for h in holes if abs(h[0]-x)<0.1]
            STAB.append((r,x-3.5,min(ys)-2.5,x+3.5,max(ys)+2.5))
    elif r=='SW2':
        bb=f.GetCourtyard(pcbnew.F_CrtYd).BBox() if False else f.GetBoundingBox(False)
        SQ.append((r,m(bb.GetLeft()),m(bb.GetTop()),m(bb.GetRight()),m(bb.GetBottom())))
    elif r!='J2' and f.GetLayer()==pcbnew.B_Cu:
        bb=f.GetBoundingBox(False)
        BOT.append((r,m(bb.GetLeft()),m(bb.GetTop()),m(bb.GetRight()),m(bb.GetBottom())))
def rd(a,b):  # rect distance (0 if overlap)
    dx=max(b[0]-a[2],a[0]-b[2],0); dy=max(b[1]-a[3],a[1]-b[3],0); return math.hypot(dx,dy)
eb=b.GetBoardEdgesBoundingBox(); E=(m(eb.GetLeft()),m(eb.GetTop()),m(eb.GetRight()),m(eb.GetBottom()))
print('edge',E)
import sys
L,W=12.7,9.906
res=[]
for rot in (0,90):
    hx,hy=(L/2,W/2) if rot==0 else (W/2,L/2)
    y=E[1]+hy
    while y<=E[3]-hy:
        x=E[0]+hx
        while x<=E[2]-hx:
            env=(x-hx,y-hy,x+hx,y+hy)
            ds=min(rd(env,s[1:]) for s in SQ)
            if ds>=2.0:
                dst=min(rd(env,s[1:]) for s in STAB)
                db=min(rd(env,s[1:]) for s in BOT)
                res.append((round(x,2),round(y,2),rot,round(ds,2),round(dst,2),round(db,2)))
            x+=0.5
        y+=0.5
print(len(res))
# cluster print
for r in res:
    if r[0]<60 or r[0]>270: print(r)
print('=====')
for (L,W) in [(12.7,9.906),(9.906,7.239),(9.906,6.096),(7.0,4.0)]:
  best={}
  for rot in (0,90):
    hx,hy=(L/2,W/2) if rot==0 else (W/2,L/2)
    y=E[1]+hy
    while y<=E[3]-hy:
        x=E[0]+hx
        while x<=E[2]-hx:
            env=(x-hx,y-hy,x+hx,y+hy)
            ds=min(rd(env,s[1:]) for s in SQ)
            if ds>=2.0 and not (env[0]<0.23 and env[3]>45 and env[1]<82):
                dst=min(rd(env,s[1:]) for s in STAB)
                key=int(x//20)
                cand=(round(ds,2),round(dst,2),round(x,2),round(y,2),rot)
                if key not in best or (min(cand[0],3),cand[1])>(min(best[key][0],3),best[key][1]): best[key]=cand
            x+=0.25
        y+=0.25
  print(L,W,[best[k] for k in sorted(best)])
