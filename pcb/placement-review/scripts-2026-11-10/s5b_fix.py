import sys; sys.path.insert(0,'/tmp/fb')
from lib import *
e=Ed(); R=lambda v: round(v,6)
j4=e.pad('J2',4); j2=e.pad('J2',2)
e.rm('SWCLK',(31.15,63.0),(22.8,71.35),(22.8,R(j4[1]-1.65)),(24.45,j4[1]),layer='F')
e.seg('SWCLK','F',(31.15,63.0),(23.05,71.1),(23.05,R(j4[1]-1.4)),(24.45,j4[1]))
e.rm('SWDIO',(29.95,64.8),(23.15,71.6),(23.15,R(j2[1]-1.3)),(24.45,j2[1]),layer='F')
e.seg('SWDIO','F',(29.95,64.8),(23.4,71.35),(23.4,R(j2[1]-1.05)),(24.45,j2[1]))
for p in e.b.FindFootprintByReference('J2').Pads():
    if p.GetNumber()=='5': p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
e.save()
