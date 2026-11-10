import pcbnew,sys,math
mm=pcbnew.ToMM; FM=pcbnew.FromMM
b=pcbnew.LoadBoard(sys.argv[1]); pcbnew.ZONE_FILLER(b).Fill(b.Zones())
z=[z for z in b.Zones() if not z.GetIsRuleArea()][0]; F=z.GetFilledPolysList(pcbnew.F_Cu)
for net in ['D+','D-','DCCH','Net-(U5-P0.00)','Net-(U5-P0.01)']:
    n=miss=0
    for t in b.GetTracks():
        if t.GetClass()=='PCB_VIA' or t.GetNetname()!=net or t.GetLayer()!=pcbnew.B_Cu: continue
        s,e=t.GetStart(),t.GetEnd(); L=math.hypot(e.x-s.x,e.y-s.y)
        if L==0: continue
        ux,uy=(e.x-s.x)/L,(e.y-s.y)/L; k=0
        while k*FM(0.05)<=L:
            for off in (-0.25,0,0.25):
                p=pcbnew.VECTOR2I(int(s.x+ux*k*FM(0.05)-uy*FM(off)),int(s.y+uy*k*FM(0.05)+ux*FM(off)))
                n+=1; miss+=0 if F.Contains(p) else 1
            k+=1
    print(net,'samples',n,'missing',miss)
print('F polys',F.OutlineCount(),'area %.2f'%(F.Area()/1e12),'B polys',z.GetFilledPolysList(pcbnew.B_Cu).OutlineCount(),'area %.2f'%(z.GetFilledPolysList(pcbnew.B_Cu).Area()/1e12))
