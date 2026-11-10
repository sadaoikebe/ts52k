BOX=(-4,44,48,90)
PW=0.3
# ---------- stage 2: crystal + power cluster ----------
if STAGE>=2:
    X1='Net-(U5-P0.00)'; X2='Net-(U5-P0.01)'
    e.seg(X1,'B',(11.6,60.2),(12.3,60.2),(13.35,59.15),(15.97,59.15))
    e.seg(X2,'B',(11.6,61.0),(12.6,61.0),(12.95,60.65),(15.97,60.65))
    e.seg('GND','B',(16.93,59.15),(16.93,60.65),w=0.25); e.via('GND',(16.93,59.9))
    e.seg('DCCH','B',(11.6,66.6),(13.3,66.6),w=PW)
    e.seg('nRF_VDD','B',(11.6,65.0),(13.3,65.0),w=PW)
    e.seg('nRF_VDD','B',(13.5,64.75),(22.05,64.75),w=PW)
    for x,y in ((15.075,63.75),(19.685,63.75),(18.95,65.3),(20.5,65.3),(22.05,65.3)): e.seg('nRF_VDD','B',(x,y),(x,64.75),w=PW)
    e.seg('VDDH','B',(11.6,65.8),(12.3,65.8),(12.5,65.6),(15.05,65.6),w=0.2)
    e.via('VDDH',(22.3,67.8))
    e.seg('VDDH','B',(22.3,67.8),(22.15,67.65),(17.75,67.65),(17.05,66.95),(15.45,66.95),(15.45,66.3),w=0.2)
    e.seg('MCU_VBUS','B',(11.6,67.4),(12.3,67.4),(12.45,67.25),(15.1,67.25),(16.3,68.45),(16.9,68.45),w=0.25)
    e.seg('MCU_VBUS','B',(20.25,68.8),(19.75,69.3),(16.9,69.3),(16.9,68.45),w=0.25)
    e.via('USB_VBUS',(23.0,68.8)); e.seg('USB_VBUS','B',(23.0,68.8),(21.9,68.8),w=0.3)
    for p in ((17.38,63.75),(19.725,66.85),(21.275,66.85),(19.25,68.45)): e.via('GND',p)
    e.seg('GND','B',(16.625,63.75),(18.135,63.75),w=0.25)
    e.seg('GND','B',(18.95,66.85),(22.05,66.85),w=0.25)
    e.seg('GND','B',(16.95,66.5),(18.95,66.5),w=0.25); e.seg('GND','B',(18.45,68.45),(19.25,68.45),w=0.25)
    e.via('GND',(14.35,52.825)); e.seg('GND','B',(13.5,52.825),(14.35,52.825),w=0.25)
    e.via('GND',(18.85,54.3)); e.seg('GND','B',(17.775,54.3),(18.85,54.3),w=0.25)
# ---------- stage 3: north side, band, bus head ----------
def lane(net,start,*jogs,end=None,layer='B'):
    pts=[start]; x,y=start
    for xs,ny in jogs:
        if abs(xs-x)>1e-6: pts.append((xs,y))
        d=abs(ny-y); pts.append((round(xs+d,6),ny)); x,y=xs+d,ny
    if end is not None and abs(end-x)>1e-6: pts.append((end,y))
    e.seg(net,layer,*pts); return pts[-1]
if STAGE>=3:
    A2='Net-(D2-A)'
    e.seg('rpg1','B',(4.2,58.75),(4.2,56.75),(5.65,55.3),(5.65,54.3),(7.86,52.09),(11.73,52.09),(12.375,52.735),(12.375,55.745),(12.955,56.325))
    e.seg('rpg2','B',(5.0,58.75),(5.0,57.0),(6.0,56.0),(6.0,54.445),(8.005,52.44),(11.585,52.44),(12.025,52.88),(12.025,55.89),(12.81,56.675))
    e.seg(A2,'B',(5.715,52.229),(6.204,51.74),(11.875,51.74),(12.725,52.59),(12.725,55.6),(13.1,55.975),(21.0,55.975))
    e.seg('row1','B',(5.8,58.75),(5.8,57.475),(9.9,57.475),(10.3,57.075))
    e.seg('row6','B',(6.6,58.75),(6.6,57.825),(10.05,57.825),(10.45,57.425))
    e.seg('row2','B',(7.4,58.75),(7.4,58.175),(10.2,58.175),(10.6,57.775))
    e.seg('row7','B',(8.2,58.75),(9.0,58.75),(9.225,58.525),(10.35,58.525),(10.75,58.125))
    e.seg('col6','B',(11.6,59.4),(12.2,59.4),(13.125,58.475))
    e.seg('col5','B',(11.6,61.8),(12.3,61.8),(12.5,61.6))
    e.seg('col4','B',(11.6,62.6),(12.3,62.6),(12.95,61.95))
    e.seg('col3','B',(11.6,63.4),(12.3,63.4),(13.4,62.3))
    e.seg('col2','B',(11.6,64.2),(12.3,64.2),(13.85,62.65))
    p=lane('rpg1',(12.955,56.325),(19.3,56.825),(29.15,57.09),(35.85,56.92),(45.89,57.15),end=46.53)
    p=lane('rpg2',(12.81,56.675),(19.15,57.175),(29.0,57.44),(36.0,57.27),(45.73,57.6),end=46.28)
    p=lane('row1',(10.3,57.075),(19.0,57.525),end=21.3); e.seg('row1','B',p,(21.3,59.4))
    p=lane('row1',(21.3,59.4),(24.3,57.79),(36.15,57.62),(45.5,58.05),end=48.34)
    p=lane('row6',(10.45,57.425),(17.7,60.125),(24.4,58.14),(37.8,58.362),(44.9,58.5),end=48.34)
    p=lane('row2',(10.6,57.775),(17.55,60.475),end=23.675); e.seg('row2','B',p,(24.05,60.85))
    p=lane('row2',(24.05,60.85),(24.8,58.49),(37.65,59.09),(45.75,58.89),end=48.15); e.seg('row2','B',p,(48.21,58.95),(48.28,58.95))
    p=lane('row7',(10.75,58.125),(17.4,60.825),(22.5,61.575),(24.95,58.84),(37.5,59.44),end=47.04); e.seg('row7','B',p,(47.244,59.644),(47.488,59.4),(47.53,59.4))
    p=lane('col6',(13.125,58.475),(17.25,61.175),(22.35,61.925),(25.1,59.19),(37.35,59.79),(45.94,60.45),end=46.7)
    p=lane('col5',(12.5,61.6),(22.2,62.275),(25.25,59.54),(37.2,60.14),(45.795,60.8),end=46.9)
    p=lane('col4',(12.95,61.95),(22.05,62.625),(25.4,59.89),(37.05,60.49),(45.65,61.15),end=47.15)
    p=lane('col3',(13.4,62.3),(21.9,62.975),(25.55,60.24),(36.9,60.84),(45.505,61.5),end=109.79); e.seg('col3','B',p,(110.49,62.2))
    p=lane('col2',(13.85,62.65),(21.75,63.325),(25.7,60.59),end=36.5)
    e.seg('col2','B',p,(36.5,69.0),(37.8,70.3),(52.361,70.3),(53.34,71.279))

# ---------- stage 4: south side ----------
if STAGE>=4:
    ob=pcbnew.LoadBoard('/tmp/w/orig.kicad_pcb'); nrest=0
    for t in ob.GetTracks():
        if t.GetClass()!='PCB_TRACK' or t.GetNetname() not in('row3','row8','row4','row9','row5','row10'): continue
        a=(mm(t.GetStart().x),mm(t.GetStart().y)); c=(mm(t.GetEnd().x),mm(t.GetEnd().y))
        if (min(a[0],c[0])>=31.5 and max(a[0],c[0])<=39.01 and min(a[1],c[1])>80) or (t.GetNetname()=='row3' and min(a[0],c[0])>40):
            if not any(x.GetClass()=='PCB_TRACK' and x.GetNetname()==t.GetNetname() and x.GetStart()==t.GetStart() and x.GetEnd()==t.GetEnd() for x in e.T):
                n=pcbnew.PCB_TRACK(b); n.SetStart(t.GetStart()); n.SetEnd(t.GetEnd()); n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer()); n.SetNet(e.net(t.GetNetname())); b.Add(n); e.T.append(n); nrest+=1
    print('restored lower head segs',nrest)
    def west_end(net):
        best=None
        for t in e.tracks(net):
            if t.GetClass()!='PCB_TRACK': continue
            for q in (t.GetStart(),t.GetEnd()):
                if 31.4<mm(q.x)<32.0 and 81<mm(q.y)<83.2 and (best is None or mm(q.x)<best[0]): best=(mm(q.x),mm(q.y))
        return best
    # fan from the south pad row, around MX3, east, down to the lower bus head
    fan={'row3':[(9.0,68.05),(9.0,68.2),(5.625,71.575)],'row8':[(7.4,68.05),(5.275,70.175)],
         'row4':[(6.2,67.15),(6.5,67.45),(6.5,68.25),(4.925,69.825)],'row9':[(5.8,68.05),(5.8,68.3),(4.575,69.525)],
         'row5':[(5.0,68.05),(5.0,68.6),(4.225,69.375)],'row10':[(4.2,68.05),(4.2,68.9),(3.875,69.225)]}
    order=['row3','row8','row4','row9','row5','row10']
    tgt={'row3':(32.7,80.527)}
    for i,nm in enumerate(order):
        xl=5.625-0.35*i; ye=76.15+0.35*i
        pts=fan[nm]+[(xl,ye-0.35),(xl+0.35,ye)]
        e.seg(nm,'B',*pts)
        we=tgt.get(nm) or west_end(nm); assert we,nm
        xs=20.75-0.15*i
        p=lane(nm,(xl+0.35,ye),(xs,we[1]),end=we[0])
    e.seg('col1','B',(3.8,67.15),(3.5,67.45),(3.5,77.9),(3.85,78.25),(17.45,78.25),(17.8,78.6),(17.8,85.39),(12.861,90.329))
    # col1 through the module to MX2.2
    e.seg('col1','B',(3.8,67.15),(3.8,66.5),(3.4,66.1),(3.4,57.9),(3.2,57.7),(3.2,51.6),(4.37,50.43),(11.3,50.43),(12.065,49.689)) if False else None
    # SWD
    e.seg('SWDIO','B',(2.6,68.05),(2.6,80.2),(3.13,80.73),(10.365,80.73))
    e.seg('SWCLK','B',(1.8,68.05),(1.8,81.47),(2.33,82.0),(10.365,82.0))
    # USB
    e.seg('D-','B',(21.85,52.6),(25.2,55.95),(25.2,56.2),w=0.2); e.via('D-',(25.2,56.2))
    e.seg('D+','B',(22.65,52.6),(25.45,55.4),(26.6,55.4),w=0.2); e.via('D+',(26.6,55.4))
    e.seg('D-','F',(25.2,56.2),(25.2,57.0),(27.3,59.1),(27.3,62.55),w=0.2); e.via('D-',(27.3,62.55))
    e.seg('D+','F',(26.6,55.4),(26.6,56.3),(28.0,57.7),(28.0,61.9),w=0.2); e.via('D+',(28.0,61.9))
    e.seg('D-','B',(27.3,62.55),(29.85,62.55),(30.4,63.1),(30.4,69.8),(30.035,70.165),(11.765,70.165),(10.6,69.0),(10.6,68.05),w=0.2)
    e.seg('D+','B',(28.0,61.9),(30.2,61.9),(30.8,62.5),(30.8,70.2),(30.435,70.565),(11.365,70.565),(9.8,69.0),(9.8,68.05),w=0.2)
    # nRESET
    e.seg('nRESET','B',(7.8,67.15),(7.8,65.9)); e.via('nRESET',(7.8,65.9))
    e.seg('nRESET','F',(7.8,65.9),(9.15,67.25),(9.15,69.3)); e.via('nRESET',(9.15,69.3))
    e.seg('nRESET','B',(9.15,69.3),(9.15,69.895),(10.195,70.94),(31.25,70.94),(31.65,70.54)); e.via('nRESET',(31.65,70.54))
    e.seg('nRESET','F',(31.65,70.54),(31.65,72.4)); e.via('nRESET',(31.65,72.4))
    # col1 link MX3.1 - MX8.1 - x=41
    e.rmif(lambda k,n,l,a,c: n=='col1' and k=='T' and abs(a[0]-41.0)<.01 and abs(c[0]-41.0)<.01 and min(a[1],c[1])<70.8)
    e.seg('col1','B',(8.6,71.29),(41.0,71.29),(41.0,81.18))
    # D3 anode
    e.seg('Net-(D3-A)','B',(14.446,68.739),(15.457,69.75),(24.4,69.75),(24.4,64.4))
    # col1: through the module to MX2.2, and MX8.1 -> MX7.1
    e.seg('col1','B',(3.8,67.15),(3.8,66.5),(3.4,66.1),(3.4,57.9),(3.2,57.7),(3.2,51.4),(4.2,50.4),(6.9,50.4),(7.5,51.0),(11.0,51.0),(11.6,50.4))
    e.seg('col1','B',(34.29,71.279),(35.9,69.669),(35.9,61.3)); e.via('col1',(35.9,61.3))
    e.seg('col1','F',(35.9,61.3),(35.9,56.8),(36.4,56.3)); e.via('col1',(36.4,56.3))
    e.seg('col1','B',(36.4,56.3),(36.4,52.4),(35.8,51.8),(30.4,51.8),(30.0,52.2))
    # power from the north pocket (F.Cu)
    for t in ob.GetTracks():
        if t.GetNetname()!='USB_VBUS': continue
        if t.GetClass()=='PCB_VIA':
            p=t.GetPosition()
            if abs(mm(p.x)-20.6)<.02 and abs(mm(p.y)-50.5)<.02: e.via('USB_VBUS',(mm(p.x),mm(p.y)))
        elif t.GetLayer()==pcbnew.B_Cu and 19.9<min(mm(t.GetStart().x),mm(t.GetEnd().x)) and max(mm(t.GetStart().x),mm(t.GetEnd().x))<20.7 and 49.7<min(mm(t.GetStart().y),mm(t.GetEnd().y)):
            n=pcbnew.PCB_TRACK(b); n.SetStart(t.GetStart()); n.SetEnd(t.GetEnd()); n.SetWidth(t.GetWidth()); n.SetLayer(t.GetLayer()); n.SetNet(e.net('USB_VBUS')); b.Add(n); e.T.append(n)
    e.seg('USB_VBUS','F',(20.6,50.5),(20.9,50.8),(20.9,52.8),(23.0,54.9),(23.0,68.8),w=0.3)
    e.seg('VDDH','F',(18.6,52.3),(22.3,56.0),(22.3,67.8),w=0.3)
    e.seg('BAT','B',(16.225,54.3),(16.225,55.25),(23.6,55.25),(23.8,55.45),w=0.3); e.via('BAT',(23.8,55.45))
    e.seg('BAT','F',(23.8,55.45),(23.8,61.45),(26.35,64.0),w=0.3); e.via('BAT',(26.35,64.0))
# ---------- stage 5: reset switch, SWD pads, VTref ----------
if STAGE>=5:
    e.seg('nRESET','B',(31.65,72.4),(31.325,72.725),(24.5,72.725),(20.2,72.725),(17.475,75.45),(14.9,75.45)); e.via('nRESET',(14.9,75.45))
    e.seg('nRESET','F',(14.9,75.45),(14.9,79.6)); e.via('nRESET',(14.9,79.6))
    e.seg('nRESET','B',(14.9,79.6),(14.9,81.5),(14.4,82.0),(11.635,82.0))
    e.seg('nRF_VDD','B',(17.95,64.75),(17.95,65.35),w=0.3); e.via('nRF_VDD',(17.95,65.35))
    e.seg('nRF_VDD','F',(17.95,65.35),(17.95,66.3),(15.9,68.35),(15.9,71.5),(15.75,71.65),(15.75,79.0),w=0.2); e.via('nRF_VDD',(15.75,79.0))
    e.seg('nRF_VDD','B',(15.75,79.0),(14.2,79.0),(12.47,80.73),(11.635,80.73),w=0.2)
# ---------- stage 6: module ground, antenna edge strip ----------
if STAGE>=6:
    G='GND'
    e.seg(G,'B',(0.7,58.75),(1.8,58.75),w=0.25); e.seg(G,'B',(1.3,58.75),(1.3,57.75),w=0.25); e.via(G,(1.3,57.75))
    e.seg(G,'B',(0.7,68.05),(0.7,68.8),(1.0,69.1),w=0.25); e.via(G,(1.0,69.1))
    e.seg(G,'B',(11.6,58.6),(11.0,58.6),(10.7,58.9),(10.7,59.3),w=0.25); e.via(G,(10.7,59.3))
    e.seg(G,'B',(11.6,68.2),(12.3,68.2),(12.55,68.45),w=0.25); e.via(G,(12.55,68.45))
    for p in ((7.0,61.5),(9.0,61.5),(7.0,63.4),(9.0,63.4),(9.0,65.2),(6.6,65.3),(2.3,60.2),(2.3,64.6)): e.via(G,p)
    # antenna edge strip: no copper at all within 3.8 mm of the board edge beside the antenna
    z=pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName('ANT_EDGE')
    ls=pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)
    z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o=z.Outline(); o.NewOutline()
    for x,y in ((-3.8,45.0),(0.23,45.0),(0.23,82.0),(-3.8,82.0)): o.Append(FM(x),FM(y))
    b.Add(z)
# ---------- stage 7: ground stitching where both layers have GND fill ----------
if STAGE>=7:
    import math
    e.seg('GND','B',(26.6,66.0),(26.6,67.3),w=0.3); e.via('GND',(26.6,67.3)); e.seg('GND','B',(28.6,66.0),(28.6,67.3),w=0.3); e.via('GND',(28.6,67.3))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    def fills(layer):
        ps=pcbnew.SHAPE_POLY_SET()
        for z in b.Zones():
            if z.GetIsRuleArea() or z.GetNetname()!='GND' or not z.IsOnLayer(layer): continue
            ps.Append(z.GetFilledPolysList(layer))
        return ps
    FF=fills(pcbnew.F_Cu); FB=fills(pcbnew.B_Cu)
    def inside(ps,x,y,rr):
        if not ps.Contains(V(x,y)): return False
        return all(ps.Contains(V(x+rr*math.cos(a*math.pi/6),y+rr*math.sin(a*math.pi/6))) for a in range(12))
    pads=[]; boxes=[]
    for f in b.GetFootprints():
        for p in f.Pads():
            bb=p.GetBoundingBox(); pads.append((mm(bb.GetX())-0.55,mm(bb.GetY())-0.55,mm(bb.GetRight())+0.55,mm(bb.GetBottom())+0.55))
        if not f.GetReference().startswith('MX') and f.GetReference()!='SW2':
            bb=f.GetBoundingBox(False,False); boxes.append((mm(bb.GetX())-0.4,mm(bb.GetY())-0.4,mm(bb.GetRight())+0.4,mm(bb.GetBottom())+0.4))
    vias=[(mm(t.GetPosition().x),mm(t.GetPosition().y)) for t in e.T if t.GetClass()=='PCB_VIA']
    added=[]
    y=46.5
    while y<92:
        x=1.5
        while x<49:
            ok=inside(FF,x,y,0.55) and inside(FB,x,y,0.55)
            ok=ok and not any(a<=x<=c and b_<=y<=d for a,b_,c,d in pads+boxes)
            ok=ok and all(math.hypot(x-vx,y-vy)>=1.5 for vx,vy in vias)
            if ok: e.via('GND',(round(x,3),round(y,3))); vias.append((x,y)); added.append((x,y))
            x+=1.75
        y+=1.75
    print('stitch vias added',len(added))
