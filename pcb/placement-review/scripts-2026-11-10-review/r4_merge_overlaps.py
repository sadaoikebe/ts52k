"""同一ネット・同一層・同一幅で、同一直線上に重なっている線分の組を1本にまとめる（銅箔形状は不変）。"""
import sys,os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','scripts-2026-11-10'))
from lib import *
b=pcbnew.LoadBoard(PCB); n=0
while True:
    T=[t for t in b.GetTracks() if t.GetClass()=='PCB_TRACK' and t.GetStart()!=t.GetEnd()]
    done=False
    for i,a in enumerate(T):
        s,e=a.GetStart(),a.GetEnd(); dx,dy=e.x-s.x,e.y-s.y; L2=dx*dx+dy*dy; L=L2**.5
        for c in T[i+1:]:
            if c.GetNetCode()!=a.GetNetCode() or c.GetLayer()!=a.GetLayer() or c.GetWidth()!=a.GetWidth(): continue
            cr=lambda p:abs(dx*(p.y-s.y)-dy*(p.x-s.x))/L
            if cr(c.GetStart())>50 or cr(c.GetEnd())>50: continue
            pr=lambda p:((p.x-s.x)*dx+(p.y-s.y)*dy)/L2
            pts=sorted([(0.0,s),(1.0,e),(pr(c.GetStart()),c.GetStart()),(pr(c.GetEnd()),c.GetEnd())],key=lambda q:q[0])
            u=sorted([pr(c.GetStart()),pr(c.GetEnd())])
            if (min(1,u[1])-max(0,u[0]))*L<=1000: continue
            print(a.GetNetname(),b.GetLayerName(a.GetLayer()),[(mm(q.x),mm(q.y)) for q in (s,e,c.GetStart(),c.GetEnd())])
            a.SetStart(pcbnew.VECTOR2I(pts[0][1].x,pts[0][1].y)); a.SetEnd(pcbnew.VECTOR2I(pts[3][1].x,pts[3][1].y)); b.RemoveNative(c); n+=1; done=True; break
        if done: break
    if not done: break
print('merged',n)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(PCB,b)
# まとめた結果DRCに現れたBATの行き止まり(10.425→12.225, y=60.075)を除去
e=Ed(); e.setend('BAT',(10.0,60.075),(12.225,60.075),(10.425,60.075)); e.save()
