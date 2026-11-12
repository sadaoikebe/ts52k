import sys,re,numpy as np
sys.path.insert(0,'/home/hatch/workspace/ts52k-ec/tools')
from sexp import *
b=parse(open('ref/ts52k-main/pcb/ts52k.kicad_pcb').read())
keys=[]
for fp in find(b,'footprint'):
    ref=[p[2] for p in find(fp,'property') if p[1]=='Reference'][0]
    if ref.startswith('MX'):
        at=first(fp,'at'); u=re.search(r'MXOnly-([\d.]+)U',fp[1]).group(1)
        keys.append((ref,float(at[1]),float(at[2]),float(u)))
keys.sort(key=lambda k:(round(k[2]/19),k[1]))
import json; json.dump(keys,open('ref/out/ts52k_keys.json','w'))
X0,X1,Y0,Y1=-3.57,303.61,45.24,121.44
res=0.25
xs=np.arange(X0,X1,res);ys=np.arange(Y0,Y1,res)
XX,YY=np.meshgrid(xs,ys)
def freemask(r):
    m=np.ones(XX.shape,bool)
    for _,x,y,u in keys: m&=((XX-x)**2+(YY-y)**2)>r*r
    return m
from scipy import ndimage
for r in (6.0,8.5):
    m=freemask(r)
    print('r',r,'free area mm2',round(m.sum()*res*res),'of',round((X1-X0)*(Y1-Y0)))
    # distance transform: largest inscribed circles (distance to nearest pad or board edge)
    mp=np.pad(m,1,constant_values=False)
    d=ndimage.distance_transform_edt(mp)[1:-1,1:-1]*res
    dd=d.copy();out=[]
    for i in range(14):
        j=np.unravel_index(dd.argmax(),dd.shape); rr=dd[j]
        if rr<3.4: break
        out.append((round(xs[j[1]],1),round(ys[j[0]],1),round(rr,1)))
        dd[((XX-xs[j[1]])**2+(YY-ys[j[0]])**2)<(rr*1.2)**2]=0
    print('  largest free circles (x,y,radius):',out)
