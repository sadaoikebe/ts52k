import pcbnew,sys,collections
b=pcbnew.LoadBoard(sys.argv[1])
mm=pcbnew.ToMM
bb=b.GetBoardEdgesBoundingBox()
print('outline bbox',mm(bb.GetX()),mm(bb.GetY()),mm(bb.GetWidth()),mm(bb.GetHeight()))
print('copper layers',b.GetCopperLayerCount(),'thickness',mm(b.GetDesignSettings().GetBoardThickness()))
for fp in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
    r=fp.GetReference()
    if r.startswith('SW'): continue
    p=fp.GetPosition();print(r,fp.GetValue(),round(mm(p.x),2),round(mm(p.y),2),fp.GetOrientationDegrees(),'B' if fp.IsFlipped() else 'F')
sw=[f for f in b.GetFootprints() if f.GetReference().startswith('SW')]
xs=[mm(f.GetPosition().x) for f in sw];ys=[mm(f.GetPosition().y) for f in sw]
print('SW bbox',min(xs),max(xs),min(ys),max(ys))
print('SW orientations',collections.Counter(f.GetOrientationDegrees() for f in sw))
for f in sorted(sw,key=lambda f:(round(mm(f.GetPosition().y)),mm(f.GetPosition().x)))[:20]:
    print(f.GetReference(),f.GetValue(),round(mm(f.GetPosition().x),2),round(mm(f.GetPosition().y),2),f.GetOrientationDegrees(),[ (p.GetNumber(),p.GetNetname()) for p in f.Pads()])
# tracks per net
L=collections.defaultdict(lambda: collections.defaultdict(float));W=collections.defaultdict(set);vias=collections.Counter()
for t in b.GetTracks():
    n=t.GetNetname()
    if t.GetClass()=='PCB_VIA': vias[n]+=1;continue
    L[n][b.GetLayerName(t.GetLayer())]+=mm(t.GetLength());W[n].add(mm(t.GetWidth()))
for n in sorted(L): print(n,{k:round(v,1) for k,v in L[n].items()},sorted(W[n]),'vias',vias[n])
for z in b.Zones():
    print('zone',z.GetNetname(),[b.GetLayerName(l) for l in z.GetLayerSet().Seq()],'area',round(z.GetFilledArea()/1e12,1) if z.IsFilled() else 'unfilled', 'clr',mm(z.GetLocalClearance()), 'minw',mm(z.GetMinThickness()))
ds=b.GetDesignSettings()
print('min clr',mm(ds.m_MinClearance),'trackmin',mm(ds.m_TrackMinWidth))
