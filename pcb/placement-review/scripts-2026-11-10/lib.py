import pcbnew, math
PCB='/home/hatch/workspace/ts52k-fable/pcb/ts52k.kicad_pcb'
mm=pcbnew.ToMM; FM=pcbnew.FromMM
L={'B':pcbnew.B_Cu,'F':pcbnew.F_Cu}
TOL=0.003
class Ed:
    def __init__(s,path=PCB):
        s.path=path; s.b=pcbnew.LoadBoard(path); s.log=[]; s.T=list(s.b.GetTracks())
    def net(s,n):
        ni=s.b.FindNet(n); assert ni, n; return ni
    def _eq(s,p,q): return abs(mm(p.x)-q[0])<TOL and abs(mm(p.y)-q[1])<TOL
    def find(s,net,a,b_,layer=None):
        r=[]
        for t in s.T:
            if t.GetClass()!='PCB_TRACK' or t.GetNetname()!=net: continue
            if layer and t.GetLayer()!=L[layer]: continue
            if (s._eq(t.GetStart(),a) and s._eq(t.GetEnd(),b_)) or (s._eq(t.GetStart(),b_) and s._eq(t.GetEnd(),a)): r.append(t)
        return r
    def rm(s,net,*pts,layer=None):
        # remove chain of segments a->b->c...
        for a,b_ in zip(pts,pts[1:]):
            r=s.find(net,a,b_,layer)
            assert len(r)==1,(net,a,b_,len(r))
            s.b.RemoveNative(r[0]); s.T=[t for t in s.T if t is not r[0]]
    def rmvia(s,net,p):
        r=[t for t in s.T if t.GetClass()=='PCB_VIA' and t.GetNetname()==net and s._eq(t.GetPosition(),p)]
        assert len(r)==1,(net,p,len(r)); s.b.RemoveNative(r[0]); s.T=[t for t in s.T if t is not r[0]]
    def setend(s,net,a,b_,newb):
        r=s.find(net,a,b_); assert len(r)==1,(net,a,b_,len(r)); t=r[0]
        if s._eq(t.GetEnd(),b_): t.SetEnd(pcbnew.VECTOR2I(FM(newb[0]),FM(newb[1])))
        else: t.SetStart(pcbnew.VECTOR2I(FM(newb[0]),FM(newb[1])))
        s._chk(mm(t.GetStart().x),mm(t.GetStart().y),mm(t.GetEnd().x),mm(t.GetEnd().y),net)
    def _chk(s,x1,y1,x2,y2,net):
        dx=abs(x2-x1);dy=abs(y2-y1)
        assert dx<1e-6 or dy<1e-6 or abs(dx-dy)<2e-6,('angle',net,(x1,y1),(x2,y2))
        assert dx+dy>1e-6,('zero',net,(x1,y1))
    def seg(s,net,layer,*pts,w=0.15):
        ni=s.net(net)
        for a,b_ in zip(pts,pts[1:]):
            s._chk(a[0],a[1],b_[0],b_[1],net)
            t=pcbnew.PCB_TRACK(s.b); t.SetStart(pcbnew.VECTOR2I(FM(a[0]),FM(a[1]))); t.SetEnd(pcbnew.VECTOR2I(FM(b_[0]),FM(b_[1])))
            t.SetWidth(FM(w)); t.SetLayer(L[layer]); t.SetNet(ni); s.b.Add(t); s.T.append(t)
    def via(s,net,p,d=0.6,drill=0.3):
        v=pcbnew.PCB_VIA(s.b); v.SetPosition(pcbnew.VECTOR2I(FM(p[0]),FM(p[1]))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(pcbnew.F_Cu,FM(d)); v.SetDrill(FM(drill)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(s.net(net)); s.b.Add(v); s.T.append(v)
    def move(s,ref,x,y,rot=None):
        fp=s.b.FindFootprintByReference(ref); fp.SetPosition(pcbnew.VECTOR2I(FM(x),FM(y)))
        if rot is not None: fp.SetOrientationDegrees(rot)
    def save(s):
        f=pcbnew.ZONE_FILLER(s.b); f.Fill(s.b.Zones())
        pcbnew.SaveBoard(s.path,s.b)
def stats(path=PCB):
    b=pcbnew.LoadBoard(path); r={}
    f=0;nv=0;gv=0
    percol={}
    for t in b.GetTracks():
        n=t.GetNetname()
        if t.GetClass()=='PCB_VIA':
            if n=='GND': gv+=1
            else: nv+=1
            if n.startswith('col'): percol.setdefault(n,[0,0])[1]+=1
        elif t.GetLayer()==pcbnew.F_Cu:
            f+=mm(t.GetLength())
            if n.startswith('col'): percol.setdefault(n,[0,0])[0]+=mm(t.GetLength())
    return dict(F_mm=round(f,3),sigvias=nv,gndvias=gv,col={k:(round(v[0],3),v[1]) for k,v in sorted(percol.items())})
if __name__=='__main__':
    print(stats())
def _pt(s,net,p,tol=0.003):
    for t in s.T:
        if t.GetNetname()!=net: continue
        if t.GetClass()=='PCB_VIA':
            q=t.GetPosition()
            if abs(mm(q.x)-p[0])<tol and abs(mm(q.y)-p[1])<tol: return (q.x/1e6,q.y/1e6)
        else:
            for q in (t.GetStart(),t.GetEnd()):
                if abs(mm(q.x)-p[0])<tol and abs(mm(q.y)-p[1])<tol: return (q.x/1e6,q.y/1e6)
    raise AssertionError(('pt',net,p))
def _pad(s,ref,num):
    for p in s.b.FindFootprintByReference(ref).Pads():
        if p.GetNumber()==str(num): q=p.GetPosition(); return (q.x/1e6,q.y/1e6)
    raise AssertionError((ref,num))
Ed.pt=_pt; Ed.pad=_pad
