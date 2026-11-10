"""B面の参照名シルクを整理する。対象: 文字高0.8 mm未満の25個と、DRCでパッド・他シルクと重なる参照名。
0.8 mm高・0.12 mm太さで、部品の周囲に重ならない位置を探して置く。置けないものは非表示にする。"""
import sys,os,json
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','scripts-2026-11-10'))
from lib import *
drc=json.load(open(sys.argv[1]))
b=pcbnew.LoadBoard(PCB)
targets=set()
import re
for v in drc['violations']:
    if v['type'] in('silk_over_copper','silk_overlap','text_height','silk_edge_clearance'):
        for i in v['items']:
            m=re.match(r'Reference field of (\w+)',i['description'])
            if m: targets.add(m.group(1))
SILK=pcbnew.B_SilkS
def box(bb,infl=0.0):
    return (mm(bb.GetLeft())-infl,mm(bb.GetTop())-infl,mm(bb.GetRight())+infl,mm(bb.GetBottom())+infl)
def hit(a,c): return a[0]<c[2] and c[0]<a[2] and a[1]<c[3] and c[1]<a[3]
obst=[]
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.IsOnLayer(pcbnew.B_Cu) or p.HasHole(): obst.append(box(p.GetBoundingBox(),0.15))
    for g in fp.GraphicalItems():
        if g.GetLayer()==SILK: obst.append(box(g.GetBoundingBox(),0.12))
for d in b.GetDrawings():
    if d.GetLayer()==SILK: obst.append(box(d.GetBoundingBox(),0.15))
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': obst.append(box(t.GetBoundingBox(),-0.1))   # ビア穴付近は避ける
outline=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outline,True)
outline.Deflate(FM(0.7),pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS,FM(0.01))
def inside(t): return all(outline.Contains(pcbnew.VECTOR2I(FM(x),FM(y))) for x in (t[0],t[2]) for y in (t[1],t[3]))
fixed={}  # ref -> box of already-settled visible refs
for fp in b.GetFootprints():
    r=fp.Reference()
    if fp.GetLayer()==pcbnew.B_Cu and r.IsVisible() and r.GetLayer()==SILK and fp.GetReference() not in targets:
        fixed[fp.GetReference()]=box(r.GetBoundingBox(),0.12)
res={}
for ref in sorted(targets,key=lambda s:(re.sub(r'\d','',s),int(re.sub(r'\D','',s)))):
    fp=b.FindFootprintByReference(ref); r=fp.Reference()
    if r.GetLayer()!=SILK or not r.IsVisible(): continue
    r.SetTextSize(pcbnew.VECTOR2I(FM(0.8),FM(0.8))); r.SetTextThickness(FM(0.12))
    r.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); r.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    pb=None
    for p in fp.Pads():
        q=box(p.GetBoundingBox()); pb=q if pb is None else (min(pb[0],q[0]),min(pb[1],q[1]),max(pb[2],q[2]),max(pb[3],q[3]))
    cx,cy=(pb[0]+pb[2])/2,(pb[1]+pb[3])/2; best=None
    for ang in (0,90):
        r.SetTextAngleDegrees(ang); r.SetPosition(pcbnew.VECTOR2I(FM(cx),FM(cy))); tb=box(r.GetBoundingBox())
        w,h=tb[2]-tb[0],tb[3]-tb[1]
        cands=[]
        for k in range(0,9):
            g=0.3+0.15*k
            for off in (0,-0.6,0.6,-1.2,1.2,-1.8,1.8):
                cands+= [(cx+off,pb[1]-g-h/2),(cx+off,pb[3]+g+h/2),(pb[0]-g-w/2,cy+off),(pb[2]+g+w/2,cy+off)]
        for (x,y) in cands:
            t=(x-w/2,y-h/2,x+w/2,y+h/2)
            if not inside(t): continue
            if any(hit(t,o) for o in obst) or any(hit(t,o) for o in fixed.values()): continue
            d=abs(x-cx)+abs(y-cy)+(0.3 if ang else 0)
            if best is None or d<best[0]: best=(d,x,y,ang,t)
    if best and best[0]<2.2+max(pb[2]-pb[0],pb[3]-pb[1])/2:
        r.SetTextAngleDegrees(best[3]); r.SetPosition(pcbnew.VECTOR2I(FM(best[1]),FM(best[2]))); fixed[ref]=tuple(v+(-0.12 if i<2 else 0.12) for i,v in enumerate(best[4])); res[ref]='placed (%.2f,%.2f) %d deg'%best[1:4]
    else:
        r.SetVisible(False); res[ref]='hidden'
for k,v in res.items(): print(k,v)
pcbnew.SaveBoard(PCB,b)
