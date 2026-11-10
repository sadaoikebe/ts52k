import sys; sys.path.insert(0,'/tmp/fb')
from lib import *
e=Ed(); R=lambda v: round(v,6)
# ---- clear old stubs ----
e.rmvia('nRF_VDD',(24.1,61.875)); e.rm('nRF_VDD',(24.1,61.875),(24.1,64.4))
e.rm('nRESET',(25.3,67.0),(23.1,69.2),layer='F'); e.rmvia('nRESET',(23.1,69.2)); e.rm('nRESET',(23.1,69.2),(23.1,70.4))
e.setend('SWCLK',(32.15,60.2),(32.15,64.8),(32.15,63.0)); e.rm('SWCLK',(32.15,64.8),(32.0,64.95),(32.0,66.0)); e.rmvia('SWCLK',(32.0,66.0))
e.rmvia('GND',(23.5,77.675)); e.via('GND',(20.3,77.7),d=0.8,drill=0.4)
e.rm('GND',(28.042,81.22),(28.352,81.53),(29.0,81.53)); e.rmvia('GND',(29.058,82.499)); e.via('GND',(28.042,81.22))
# D4 anode: make room for two lanes south of the J2 holes
e.setend('Net-(D4-A)',(20.2,87.25),(23.5,83.95),(23.43,84.02))
e.rm('Net-(D4-A)',(23.5,83.95),(29.2,83.95),(29.5,84.25))
e.seg('Net-(D4-A)','B',(23.43,84.02),(29.27,84.02),(29.5,84.25))
# ---- F.Cu lead-outs from under the module ----
p=e.pt('nRF_VDD',(24.1,61.875))
e.seg('nRF_VDD','F',p,(24.1,68.2),(22.0,70.3),(22.0,75.15),(21.55,75.6),w=0.25); e.via('nRF_VDD',(21.55,75.6))
e.setend('nRESET',(25.3,64.7),(25.3,67.0),(25.3,67.6))
e.seg('nRESET','F',(25.3,67.6),(22.45,70.45),(22.45,75.6)); e.via('nRESET',(22.45,75.6))
e.via('SWCLK',(32.15,63.0))
j4=e.pad('J2',4); j2=e.pad('J2',2); j1=e.pad('J2',1); j3=e.pad('J2',3)
e.seg('SWCLK','F',(32.15,63.0),(31.15,63.0),(22.8,71.35),(22.8,R(j4[1]-1.65)),(24.45,j4[1])); e.via('SWCLK',(24.45,j4[1]))
e.seg('SWCLK','B',(24.45,j4[1]),j4)
e.seg('SWDIO','F',(31.35,64.8),(29.95,64.8),(23.15,71.6),(23.15,R(j2[1]-1.3)),(24.45,j2[1])); e.via('SWDIO',(24.45,j2[1]))
e.seg('SWDIO','B',(24.45,j2[1]),j2)
# ---- B.Cu loop round the south of J2 to its east column ----
e.seg('nRESET','B',(22.45,75.6),(22.45,82.17),(23.6,83.32),(27.98,83.32),(28.7,82.6),(28.7,j3[1]),j3)
e.seg('nRF_VDD','B',(21.55,75.6),(21.55,82.37),(22.85,83.67),(28.57,83.67),(29.3,82.94),(29.3,j1[1]),j1)
# ---- nRESET to SW1: hop the row wall, then col1 ----
s=e.pad('SW1',2)   # first pad 2 found
sw=e.pt('nRESET',(45.725,79.2))
e.via('nRESET',(28.7,j3[1])); e.seg('nRESET','F',(28.7,j3[1]),(29.25,R(j3[1]-0.55)),(33.5,R(j3[1]-0.55))); e.via('nRESET',(33.5,R(j3[1]-0.55)))
y=R(j3[1]-0.55)
e.seg('nRESET','B',(33.5,y),(40.2,y)); e.via('nRESET',(40.2,y)); e.seg('nRESET','F',(40.2,y),(41.8,y)); e.via('nRESET',(41.8,y))
e.seg('nRESET','B',(41.8,y),(R(sw[0]-(y-sw[1])),y),sw)
e.save()
