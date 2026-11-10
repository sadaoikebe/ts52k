"""Strip the routing that depends on the old module position, move U5 to the left edge and re-place the parts around it.
Applied once to commit 891e14f; not meant to be re-run."""
import sys,subprocess; sys.path.insert(0,'/home/hatch/workspace/ts52k-fable/pcb/placement-review/scripts-2026-11-10-antenna')
from lib import *
e=Ed(); b=e.b
# 1. rule area ANT_NO_FILL
for z in list(b.Zones()):
    if z.GetZoneName()=='ANT_NO_FILL': b.RemoveNative(z); print('removed ANT_NO_FILL')
# 2. tracks
ALL={'DCCH','MCU_VBUS','Net-(U5-P0.00)','Net-(U5-P0.01)','nRF_VDD','SWCLK','SWDIO','nRESET','Net-(D2-A)','Net-(D3-A)'}
def pred(k,n,lay,a,c):
    xs=(a[0],c[0]); ys=(a[1],c[1]); X=max(xs); x=min(xs); Y=max(ys); y=min(ys)
    if n in ALL: return True
    if n=='BAT': return Y>54.31
    if n in('D+','D-'): return Y>52.61
    if n=='VDDH': return Y>52.71 or (k=='V' and y>52.69)
    if n=='USB_VBUS':
        return (lay=='F' and x>16.9 and X<21.0 and y>50.4) or (k=='V' and (abs(a[0]-16.98)<.02 or abs(a[0]-20.6)<.02) and y>50) or (lay=='B' and abs(X-16.98)<.02 and y>55.4) or (lay=='B' and abs(X-20.6)<.02 and x>19.9)
    if n=='col1':
        if Y<72.36 and X<12.1: return True            # MX2.2 west path and MX3.1 feed
        if X<13.0 and 72.3<Y<90.4 and y<90.0: return True  # MX3.1 -> MX4.1 link
        if Y<70.71 and x>26.0: return not (abs(a[0]-41.0)<.01 and abs(c[0]-41.0)<.01)  # MX7 loop, x=49 hop, MX8.1 entry
        if lay=='F' and Y<71.3: return True
        return False
    if n=='col2': return y<52.0 or X<48.5
    if n=='col3': return X<=110.5 and y<52.2 and not (abs(Y-52.229)<.01 and abs(y-52.229)<.01)
    if n in('col4','col5','col6'): return X<47.2 or (k=='V' and X<47)
    if n in('row1','row2','row6','row7','rpg1','rpg2'): return X<48.36
    if n=='row3': return not (x>=32.69 and Y>=80.52) 
    if n=='row8': return X<37.14
    if n=='row4': return X<35.11 and not (x>35.09)
    if n=='row9': return X<38.51
    if n=='row5': return X<36.68
    if n=='row10': return X<39.01
    if n=='GND': return 21.0<x and X<38.5 and 56.5<y and Y<70.5
    return False
print('removed tracks/vias',e.rmif(pred))
# row3 stub (32.27,80.53)-(32.5,80.76)
print('row3 stub',e.rmif(lambda k,n,lay,a,c: n=='row3' and max(a[0],c[0])<32.6))
# 3. footprints
e.move('U5',4.45,63.4,270)
e.move('L1',13.5,65.75,90)       # pad2 DCCH south
e.move('X3',14.25,59.9,90)
e.move('C32',16.2,59.15,0)
e.move('C33',16.2,60.65,0)
# 4. U5 pad nets from schematic netlist
subprocess.run(['kicad-cli','sch','export','netlist','-o','/tmp/w/new.net','/home/hatch/workspace/ts52k-fable/pcb/ts52k.kicad_sch'],check=True,capture_output=True)
nl=netlist('/tmp/w/new.net')
fp=b.FindFootprintByReference('U5'); ch=0
for p in fp.Pads():
    want=nl.get(('U5',p.GetNumber()))
    if want is None: continue
    if p.GetNetname()!=want:
        ni=b.FindNet(want)
        if not ni:
            ni=pcbnew.NETINFO_ITEM(b,want); b.Add(ni)
        p.SetNet(ni); ch+=1
print('pad nets changed',ch)
e.save()
for r in ('U5','L1','X3','C32','C33'):
    f=b.FindFootprintByReference(r); print(r,[(p.GetNumber(),p.GetNetname(),round(mm(p.GetPosition().x),3),round(mm(p.GetPosition().y),3)) for p in f.Pads()][:70 if r!='U5' else 0])
