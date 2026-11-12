import sys,json,math,collections
sys.path.insert(0,'/home/hatch/workspace/ts52k-ec/tools')
from sexp import *
b=parse(open('ref/ts52k-main/pcb/ts52k.kicad_pcb').read())
keys=json.load(open('ref/out/ts52k_keys.json'))
def near(x,y):
    d,k=min((math.hypot(x-k[1],y-k[2]),k[0]) for k in keys); return d,k
print('== bottom-side parts vs EC electrode positions (dist to nearest key centre)')
for fp in find(b,'footprint'):
    ref=[p[2] for p in find(fp,'property') if p[1]=='Reference'][0]
    if ref.startswith('MX') or (ref.startswith('D') and ref not in('D89','D90','D91')): continue
    at=first(fp,'at'); x,y=float(at[1]),float(at[2]); d,k=near(x,y)
    cls='UNDER ELECTRODE' if d<6 else 'under guard ring' if d<8.5 else 'free'
    print(f'  {ref:5s} ({x:6.1f},{y:6.1f}) nearest {k} {d:5.1f} mm  {cls}')
# net lengths under electrodes
L=collections.defaultdict(lambda:[0,0,0])
for s in find(b,'segment'):
    st=first(s,'start');en=first(s,'end');net=first(s,'net')
    name=net[1] if len(net)==2 else net[2]
    x0,y0,x1,y1=map(float,(st[1],st[2],en[1],en[2])); ln=math.hypot(x1-x0,y1-y0); n=max(1,int(ln/0.25))
    for i in range(n):
        x=x0+(x1-x0)*(i+.5)/n;y=y0+(y1-y0)*(i+.5)/n; d,_=near(x,y)
        L[name][0]+=ln/n
        if d<6: L[name][1]+=ln/n
        elif d<8.5: L[name][2]+=ln/n
print('== track length: total / under electrode r<6 / under ring')
for n,v in sorted(L.items()):
    if n.startswith(('row','col','Net-(D')) : continue
    print(f'  {n:28s} {v[0]:7.1f} {v[1]:6.1f} {v[2]:6.1f}')
