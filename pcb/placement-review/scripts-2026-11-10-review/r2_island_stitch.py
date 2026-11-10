"""B.Cu GNDのうち、表面との接続がビア1個以下で面積5 mm2以上の島へ、2個目のGNDビアを追加する。
候補点は島とF.Cu GNDの両方を0.6 mm内側へ縮めた領域内で、既存ビアから最も遠い格子点。"""
import sys,os,math
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','scripts-2026-11-10'))
from lib import *
e=Ed(); b=e.b
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
z=[z for z in b.Zones() if not z.GetIsRuleArea()][0]
gv=[t.GetPosition() for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND']
thp=[p.GetPosition() for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname()=='GND' and p.HasHole()]
pads=[(p.GetPosition(),max(p.GetSize().x,p.GetSize().y)/2) for fp in b.GetFootprints() for p in fp.Pads()]
F=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(pcbnew.F_Cu)); F.Deflate(FM(0.6),pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,FM(0.01))
ps=z.GetFilledPolysList(pcbnew.B_Cu); added=[]
for i in range(ps.OutlineCount()):
    poly=pcbnew.SHAPE_POLY_SET(); poly.AddOutline(ps.Outline(i))
    for h in range(ps.HoleCount(i)): poly.AddHole(ps.Hole(i,h))
    a=poly.Area()/1e12
    if a<5: continue
    infl=pcbnew.SHAPE_POLY_SET(poly); infl.Inflate(FM(0.31),pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,FM(0.01))
    have=[v for v in gv+thp if infl.Contains(v)]
    if len(have)>=2: continue
    d=pcbnew.SHAPE_POLY_SET(poly); d.Deflate(FM(0.6),pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,FM(0.01))
    bb=poly.BBox(); best=None
    x=bb.GetLeft()
    while x<bb.GetRight():
        y=bb.GetTop()
        while y<bb.GetBottom():
            p=pcbnew.VECTOR2I(int(x),int(y))
            if d.Contains(p) and F.Contains(p) and all(math.hypot(p.x-q.x,p.y-q.y)>r+FM(1.0) for q,r in pads):
                s=min([math.hypot(p.x-v.x,p.y-v.y) for v in have] or [1e12])
                if best is None or s>best[0]: best=(s,p)
            y+=FM(0.25)
        x+=FM(0.25)
    if best is None or best[0]<FM(2.0): print('skip island area %.1f at (%.1f,%.1f): no spot'%(a,mm(bb.GetCenter().x),mm(bb.GetCenter().y))); continue
    pt=(round(mm(best[1].x),2),round(mm(best[1].y),2)); added.append((round(a,2),[ (round(mm(v.x),2),round(mm(v.y),2)) for v in have],pt,round(mm(best[0]),1)))
for a in added: e.via('GND',a[2]); print('island %.2f mm2 existing %s -> add %s (%.1f mm apart)'%a)
e.save(); print(stats())
