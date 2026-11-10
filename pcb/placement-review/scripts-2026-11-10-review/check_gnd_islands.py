import pcbnew,sys
mm=pcbnew.ToMM
b=pcbnew.LoadBoard(sys.argv[1] if len(sys.argv)>1 else 'pcb/ts52k.kicad_pcb')
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
z=[z for z in b.Zones() if not z.GetIsRuleArea()][0]
conn=[]
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND': conn.append(('via',t.GetPosition()))
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname()=='GND': conn.append((fp.GetReference()+'.'+p.GetNumber()+('T' if p.HasHole() else ''),p.GetPosition(),p))
for lay in (pcbnew.F_Cu,pcbnew.B_Cu):
    ps=z.GetFilledPolysList(lay)
    rows=[];tot=0
    for i in range(ps.OutlineCount()):
        poly=pcbnew.SHAPE_POLY_SET(); poly.AddOutline(ps.Outline(i))
        for h in range(ps.HoleCount(i)): poly.AddHole(ps.Hole(i,h))
        a=poly.Area()/1e12; tot+=a
        bb=poly.BBox()
        vs=[c[0] for c in conn if poly.Contains(c[1]) and (c[0]=='via' or c[0].endswith('T') or c[2].IsOnLayer(lay))]
        nv=sum(1 for v in vs if v=='via'); others=[v for v in vs if v!='via']
        rows.append((a,mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom()),nv,others))
    print(b.GetLayerName(lay),ps.OutlineCount(),'total %.2f'%tot)
    for r in sorted(rows,reverse=True): print('  area %.2f bbox (%.1f,%.1f)-(%.1f,%.1f) vias %d pads '%r[:6]+str(r[6][:8]))
