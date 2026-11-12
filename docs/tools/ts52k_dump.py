import sys,collections,math
sys.path.insert(0,'/home/hatch/workspace/ts52k-ec/tools')
from sexp import *
b=parse(open(sys.argv[1]).read())
# edge cuts
xs=[];ys=[]
for k in ('gr_line','gr_arc','gr_rect','gr_circle','gr_poly'):
    for g in find(b,k):
        if first(g,'layer')[1]!='Edge.Cuts': continue
        pts=[]
        for kk in ('start','end','mid','center'):
            p=first(g,kk)
            if p: pts.append((float(p[1]),float(p[2])))
        print(k,pts)
        for p in pts: xs.append(p[0]);ys.append(p[1])
print('edge bbox',min(xs),max(xs),min(ys),max(ys))
for fp in find(b,'footprint'):
    at=first(fp,'at'); ref=[p[2] for p in find(fp,'property') if p[1]=='Reference'][0]
    val=[p[2] for p in find(fp,'property') if p[1]=='Value'][0]
    lay=first(fp,'layer')[1]
    if ref.startswith('D') and not ref.startswith('D8') and not ref.startswith('D9'): continue
    print(ref,val,fp[1],at[1],at[2],at[3] if len(at)>3 else 0,lay)
