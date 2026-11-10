import sys; sys.path.insert(0,'/tmp/fb')
from lib import *
e=Ed(); R=lambda v: round(v,6)
# col1: MX2.2 -> west edge channel under J3 -> MX3.1
a=e.pad('MX2',2); m31=e.pad('MX3',1)
d=m31[1]-m31[0]
e.seg('col1','B',a,(R(a[0]-(a[1]-49.5)),49.5),(4.5,49.5),(2.9,51.1),(2.9,56.3),(4.0,57.4),(4.0,R(4.0+d)),m31)
# D2 anode: MX2.1 -> channel -> north of MX3.2 -> D2.2
a=e.pad('MX2',1); d22=e.pad('D2',2)
e.seg('Net-(D2-A)','B',a,(a[0],57.3),(4.6,R(57.3+(a[0]-4.6))),(4.6,66.25),(4.95,66.6),(15.0,66.6),(R(d22[1]-51.6),d22[1]),d22)
# row1 -> D2.1 : F.Cu hop over the row wall
d21=e.pad('D2',1)
e.via('row1',(29.75,68.6)); e.seg('row1','F',(29.75,68.6),(27.0,68.6),(24.1,71.5)); e.via('row1',(24.1,71.5))
e.seg('row1','B',(24.1,71.5),(d21[0],R(71.5+(d21[0]-24.1))),d21)
e.save()
