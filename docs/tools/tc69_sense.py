import pcbnew,sys,collections,math
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
T=[t for t in b.GetTracks() if t.GetClass()!='PCB_VIA']
def pts(t,step=0.5):
    s=t.GetStart();e=t.GetEnd();L=mm(t.GetLength());n=max(1,int(L/step))
    return [(mm(s.x)+(mm(e.x)-mm(s.x))*(i+.5)/n, mm(s.y)+(mm(e.y)-mm(s.y))*(i+.5)/n, L/n) for i in range(n)]
import numpy as np
for target in ('SENSE','ADC','Net-(R3-Pad1)','Net-(R1-Pad1)'):
    for layer in (pcbnew.F_Cu,pcbnew.B_Cu):
        P=[p for t in T if t.GetNetname()==target and t.GetLayer()==layer for p in pts(t)]
        if not P: continue
        P=np.array(P)
        out={}
        for n in sorted({t.GetNetname() for t in T}):
            if n in (target,'GND'): continue
            Q=[p for t in T if t.GetNetname()==n and t.GetLayer()==layer for p in pts(t)]
            if not Q: continue
            Q=np.array(Q)
            d=np.sqrt(((P[:,None,:2]-Q[None,:,:2])**2).sum(-1)).min(1)
            close=[ (P[d<g,2].sum()) for g in (0.6,1.0,2.0,4.0)]
            if close[3]>2: out[n]=(round(d.min(),2),[round(c,1) for c in close])
        print(target,b.GetLayerName(layer),'len',round(P[:,2].sum(),1)); 
        for n,v in out.items(): print('    vs',n,'min dist',v[0],'len within 0.6/1/2/4 mm:',v[1])
# XIAO pads and nearest sense-side copper
u1=[f for f in b.GetFootprints() if f.GetReference()=='U1'][0]
bb=u1.GetBoundingBox(False,False); print('U1 bbox',mm(bb.GetX()),mm(bb.GetY()),mm(bb.GetRight()),mm(bb.GetBottom()))
for r in ('U3','C2','U4','U5'):
    f=[f for f in b.GetFootprints() if f.GetReference()==r][0]; print(r,mm(f.GetPosition().x),mm(f.GetPosition().y))
# under-pad foreign traces: for each SW, B.Cu track length within r<6 of centre by net
tot=collections.Counter(); foreign=collections.Counter(); ex=[]
for f in b.GetFootprints():
    if not f.GetReference().startswith('SW'): continue
    c=f.GetPosition(); own={p.GetNetname() for p in f.Pads()}
    for t in T:
        if t.GetLayer()!=pcbnew.B_Cu: continue
        for x,y,l in pts(t,0.25):
            if math.hypot(x-mm(c.x),y-mm(c.y))<6.0:
                n=t.GetNetname(); k='own' if n in own else ('foreign-col' if n.startswith('col') else 'foreign-row' if n.startswith('row') else 'foreign-'+n)
                tot[k]+=l
                if k!='own': foreign[(f.GetReference(),n)]+=l
print('B.Cu track length under electrodes (r<6):',{k:round(v,1) for k,v in tot.items()})
print('foreign examples:',sorted(((k,round(v,1)) for k,v in foreign.items()),key=lambda x:-x[1])[:25])
