import pcbnew, math, re
PCB='/home/hatch/workspace/ts52k-fable/pcb/ts52k.kicad_pcb'
mm=pcbnew.ToMM; FM=pcbnew.FromMM
L={'B':pcbnew.B_Cu,'F':pcbnew.F_Cu}
TOL=0.004
def V(x,y): return pcbnew.VECTOR2I(FM(x),FM(y))
class Ed:
    def __init__(s,path=PCB):
        s.path=path; s.b=pcbnew.LoadBoard(path); s.T=list(s.b.GetTracks())
    def net(s,n):
        ni=s.b.FindNet(n); assert ni, n; return ni
    def tracks(s,net=None):
        return [t for t in s.T if (net is None or t.GetNetname()==net)]
    def rmif(s,pred):
        """remove tracks/vias for which pred(kind,net,layer,(x1,y1),(x2,y2)) is true"""
        n=0
        for t in list(s.T):
            if t.GetClass()=='PCB_VIA':
                p=t.GetPosition(); a=(mm(p.x),mm(p.y)); k=('V',t.GetNetname(),None,a,a)
            else:
                k=('T',t.GetNetname(),'F' if t.GetLayer()==pcbnew.F_Cu else 'B',(mm(t.GetStart().x),mm(t.GetStart().y)),(mm(t.GetEnd().x),mm(t.GetEnd().y)))
            if pred(*k):
                s.b.RemoveNative(t); s.T.remove(t); n+=1
        return n
    def _chk(s,x1,y1,x2,y2,net):
        dx=abs(x2-x1);dy=abs(y2-y1)
        assert dx<1e-6 or dy<1e-6 or abs(dx-dy)<2e-6,('angle',net,(x1,y1),(x2,y2))
        assert dx+dy>1e-6,('zero',net,(x1,y1))
    def seg(s,net,layer,*pts,w=0.15):
        ni=s.net(net)
        for a,b_ in zip(pts,pts[1:]):
            s._chk(a[0],a[1],b_[0],b_[1],net)
            t=pcbnew.PCB_TRACK(s.b); t.SetStart(V(*a)); t.SetEnd(V(*b_))
            t.SetWidth(FM(w)); t.SetLayer(L[layer]); t.SetNet(ni); s.b.Add(t); s.T.append(t)
    def path(s,net,layer,start,*moves,w=0.15):
        """moves: ('x',X) horizontal to X; ('y',Y) vertical to Y; ('d',X) 45deg to x=X keeping current y trend given by sign: ('d',X,+1/-1 for y dir); ('dy',Y,+1/-1 for x dir)"""
        pts=[start]; x,y=start
        for m in moves:
            if m[0]=='x': x=m[1]
            elif m[0]=='y': y=m[1]
            elif m[0]=='d':
                dx=m[1]-x; y=y+abs(dx)*m[2]; x=m[1]
            elif m[0]=='dy':
                dy=m[1]-y; x=x+abs(dy)*m[2]; y=m[1]
            elif m[0]=='to': x,y=m[1],m[2]
            pts.append((round(x,6),round(y,6)))
        s.seg(net,layer,*pts,w=w); return pts[-1]
    def via(s,net,p,d=0.6,drill=0.3):
        v=pcbnew.PCB_VIA(s.b); v.SetPosition(V(*p)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetWidth(pcbnew.F_Cu,FM(d)); v.SetDrill(FM(drill)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(s.net(net)); s.b.Add(v); s.T.append(v)
    def move(s,ref,x,y,rot=None):
        fp=s.b.FindFootprintByReference(ref); fp.SetPosition(V(x,y))
        if rot is not None: fp.SetOrientationDegrees(rot)
        return fp
    def pad(s,ref,num):
        for p in s.b.FindFootprintByReference(ref).Pads():
            if p.GetNumber()==str(num): q=p.GetPosition(); return (round(mm(q.x),4),round(mm(q.y),4))
        raise AssertionError((ref,num))
    def save(s,fill=True):
        if fill:
            f=pcbnew.ZONE_FILLER(s.b); f.Fill(s.b.Zones())
        pcbnew.SaveBoard(s.path,s.b)
def netlist(path):
    t=open(path).read(); i=t.find('(nets'); r={}
    for n in re.split(r'\n\s*\(net\s',t[i:])[1:]:
        name=re.search(r'\(name "([^"]*)"\)',n).group(1)
        for m in re.finditer(r'\(node\s*\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)',n):
            r[(m.group(1),m.group(2))]=name
    return r
