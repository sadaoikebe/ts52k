import pcbnew,sys,collections,math,itertools
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
segs=collections.defaultdict(list)
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': continue
    n=t.GetNetname()
    if n in('GND','+3V3'): continue
    s=t.GetStart();e=t.GetEnd()
    segs[(n,t.GetLayer())].append((mm(s.x),mm(s.y),mm(e.x),mm(e.y),mm(t.GetWidth())))
def par(a,b,maxgap=2.0):
    # coupled length between two segments if nearly parallel; sample along a
    ax,ay,bx,by,_=a; L=math.hypot(bx-ax,by-ay)
    if L<0.05: return 0,0
    cx,cy,dx,dy,_=b; M=math.hypot(dx-cx,dy-cy)
    if M<0.05: return 0,0
    ux,uy=(bx-ax)/L,(by-ay)/L; vx,vy=(dx-cx)/M,(dy-cy)/M
    if abs(ux*vx+uy*vy)<0.95: return 0,0
    n=max(2,int(L/0.2)); tot=0; gs=0
    for i in range(n):
        px=ax+ux*L*(i+.5)/n; py=ay+uy*L*(i+.5)/n
        t=((px-cx)*vx+(py-cy)*vy)
        if t<0 or t>M: continue
        d=abs((px-cx)*(-vy)+(py-cy)*vx)
        if d<maxgap: tot+=L/n; gs+=d*L/n
    return tot,gs
# per-length mutual capacitance model (pF/mm) for two thin traces, centre distance d, 1.6mm FR4, weak far ground:
def cm(d,w=0.25):
    g=max(d-w,0.05)
    # empirical fit for edge-coupled traces on FR4 without near plane: ~0.045 pF/mm at g=0.25, falling ~ log
    return max(0.0,0.045*math.log(1+2.5/g)/math.log(1+2.5/0.25))
nets=sorted({k[0] for k in segs})
res={}
for (n1,l1),(n2,l2) in itertools.combinations(segs.keys(),2):
    if l1!=l2 or n1==n2: continue
    tot=0;gs=0;c=0
    for a in segs[(n1,l1)]:
        for bb in segs[(n2,l2)]:
            if min(abs(a[0]-bb[0]),abs(a[0]-bb[2]),abs(a[2]-bb[0]),abs(a[2]-bb[2]))>60 : continue
            t,g=par(a,bb)
            if t>0: tot+=t;gs+=g;c+=t*cm(g/t)
    if tot>3:
        k=tuple(sorted((n1,n2)))
        r=res.setdefault(k,[0,0,0]); r[0]+=tot;r[1]+=gs;r[2]+=c
def kind(n): return 'col' if n.startswith('col') else 'row' if n.startswith('row') else n
for k,(tot,gs,c) in sorted(res.items(),key=lambda x:-x[1][2])[:45]:
    print(f'{k[0]:>8} {k[1]:>8}  parallel {tot:6.1f} mm  mean centre dist {gs/tot:4.2f} mm  est Cm {c:5.2f} pF')
