"""Rebuild the left-edge module layout on top of commit 6b41900 (stripped board). Deterministic: always starts from that commit."""
import sys,subprocess; sys.path.insert(0,'/home/hatch/workspace/ts52k-fable/pcb/placement-review/scripts-2026-11-10-antenna')
from lib import *
import drc
BASE='6b41900'
subprocess.run(f'git -C /home/hatch/workspace/ts52k-fable show {BASE}:pcb/ts52k.kicad_pcb > {PCB}',shell=True,check=True)
e=Ed(); b=e.b
STAGE=int(sys.argv[1]) if len(sys.argv)>1 else 99
# ---------- stage 1: cleanup + placement ----------
def inbox(a,c,x0,y0,x1,y1): return x0<=min(a[0],c[0]) and max(a[0],c[0])<=x1 and y0<=min(a[1],c[1]) and max(a[1],c[1])<=y1
n=e.rmif(lambda k,n,l,a,c: n=='GND' and inbox(a,c,12.0,56.0,22.0,70.0))        # old cap stubs/vias
n+=e.rmif(lambda k,n,l,a,c: n=='col3' and max(a[0],c[0])<34)
n+=e.rmif(lambda k,n,l,a,c: n=='VDDH' and k=='V' and abs(a[0]-18.2)<.02 and abs(a[1]-52.7)<.02)
n+=e.rmif(lambda k,n,l,a,c: n=='VDDH' and l=='F' and abs(max(a[1],c[1])-52.7)<.02 and min(a[1],c[1])>52.2)
n+=e.rmif(lambda k,n,l,a,c: n=='col1' and inbox(a,c,40.9,70.6,41.1,71.3) and False)
n+=e.rmif(lambda k,n,l,a,c: inbox(a,c,19.8,54.8,20.7,56.0))
n+=e.rmif(lambda k,n,l,a,c: n=='GND' and (inbox(a,c,12.6,52.7,13.6,52.95) or inbox(a,c,17.6,54.2,17.9,56.0)))
n+=e.rmif(lambda k,n,l,a,c: n=='GND' and (inbox(a,c,-3.6,68.45,36.5,79.9) or inbox(a,c,-3.6,45,8,58.4) or inbox(a,c,9,79,31.4,83.3) or inbox(a,c,22,53,37,62.5) or inbox(a,c,-3.6,79,9,84)))
n+=e.rmif(lambda k,n,l,a,c: n=='row3' and k=='T' and abs(a[0]-32.7)<.02 and abs(c[0]-32.7)<.02 and min(a[1],c[1])<80.4)
print('stage1 removed',n)
P={ 'L1':(13.5,65.6,270),'C31':(15.85,63.75,0),'C27':(18.91,63.75,180),
    'C28':(18.95,66.075,270),'C29':(20.5,66.075,270),'C30':(22.05,66.075,270),'C25':(16.0,65.9,0),'C26':(17.675,68.45,0),
    'C32':(16.45,59.15,0),'C33':(16.45,60.65,0),
    'J3':(30.6,65.0,270),'D2':(21.3,57.75,90),'D3':(24.05,62.5,270),'R20':(21.075,68.8,180),'J2':(11.0,82.0,270),'SW1':(27.5,74.6,0)}
for r,(x,y,rot) in P.items(): e.move(r,x,y,rot)
if STAGE>=1 and '-p' in sys.argv:
    for r in list(P)+['X3','C32','C33']:
        f=b.FindFootprintByReference(r); print(r,[(p.GetNumber(),p.GetNetname()[-8:],round(mm(p.GetPosition().x),3),round(mm(p.GetPosition().y),3),round(mm(p.GetBoundingBox().GetWidth()),2),round(mm(p.GetBoundingBox().GetHeight()),2)) for p in f.Pads()])
exec(open('/home/hatch/workspace/ts52k-fable/pcb/placement-review/scripts-2026-11-10-antenna/route.py').read())
e.save()
d=drc.run(); drc.show(d,box=BOX if 'BOX' in dir() else None)
if '-u' in sys.argv: drc.unconn(d)
