"""Compare numbered pad topology at cardinal rotations, allowing origin offsets.

This is evidence extraction, not an automatic correction generator. Different
recommended pad lengths and origins are not in themselves rotation errors.
"""
import json, math
from pathlib import Path
HERE=Path(__file__).resolve().parent
rows=json.loads((HERE/'geometry.json').read_text())
results=[]
for row in rows:
    part=row['bom']['LCSC Part #']
    if any(r['part']==part for r in results):continue
    k=[p for p in row['kicad_lib_pads'] if p['number']]
    assert len(row['easyeda'])==1, part
    e=row['easyeda'][0]['pads']
    # Explicit aliases for combined USB pins, shield tabs, and switch contacts.
    if part=='C165948':
        aliases={'A1B12':'A1','B1A12':'B1','A4B9':'A4','B4A9':'B4',
                 '1':'SH_R_rear','2':'SH_R_front','3':'SH_L_front','4':'SH_L_rear'}
        e=[dict(p,number=aliases.get(p['number'],p['number'])) for p in e]
        k=[p for p in k if p['number'] not in {'B12','A12','B9','A9'}]
        k=[dict(p,number=('SH_'+('R' if p['x']>0 else 'L')+'_'+('front' if p['y']>0 else 'rear')) if p['number']=='SH' else p['number']) for p in k]
    elif part=='C295747':
        k=[dict(p,number=('3' if p['x']>0 else '4') if p['number']=='MP' else p['number']) for p in k]
    elif part=='C318884':
        # KiCad names each internally connected row as a single electrical pad.
        k=[dict(p,number=str(1+(p['x']>0)+2*(p['y']>0))) for p in k]
    kd={p['number']:p for p in k};ed={p['number']:p for p in e}
    assert set(kd)==set(ed), (part,set(kd)^set(ed))
    fits=[]
    for angle in [0,90,180,270]:
        c=round(math.cos(math.radians(angle)));s=round(math.sin(math.radians(angle)))
        pts={n:(c*p['x']-s*p['y'],s*p['x']+c*p['y']) for n,p in ed.items()}
        tx=sum(kd[n]['x']-p[0] for n,p in pts.items())/len(pts)
        ty=sum(kd[n]['y']-p[1] for n,p in pts.items())/len(pts)
        residuals={n:math.hypot(kd[n]['x']-p[0]-tx,kd[n]['y']-p[1]-ty) for n,p in pts.items()}
        fits.append(dict(clockwise_rotation_svg_to_kicad=angle,translation_mm=[tx,ty],rms_mm=math.sqrt(sum(v*v for v in residuals.values())/len(pts)),max_mm=max(residuals.values())))
    best=min(fits,key=lambda f:f['rms_mm'])
    result=dict(part=part,matched_numbered_pads=len(kd),best=best,all_cardinal_fits=fits)
    results.append(result)
    print(part,len(kd),'rotation',best['clockwise_rotation_svg_to_kicad'],'translation',*[round(t,4) for t in best['translation_mm']],'max',round(best['max_mm'],4))
(HERE/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')
# Check every board instance, not only a representative footprint.
count=0;worst=0
for row in rows:
    for inst in row['instances']:
        assert inst['bottom']
        lib=row['kicad_lib_pads']; norm=inst['normalized_pads']
        key=lambda p:(p['number'],p['x'],p['y'])
        assert len(lib)==len(norm)
        for a,b in zip(sorted(lib,key=key), sorted(norm,key=key)):
            assert (a['number'],a['shape'])==(b['number'],b['shape'])
            assert abs((a['angle']-b['angle']+90)%180-90)<1e-8
            delta=max(abs(a[t]-b[t]) for t in ['x','y','w','h'])
            worst=max(worst,delta)
            assert delta<=.000002,(inst['ref'],a,b)
        count+=1
print('Board/library instances:',count,'max rounding error mm:',worst)
(HERE/'board-library-check.json').write_text(json.dumps(dict(instances=count,all_bottom=True,max_pad_difference_mm=worst,tolerance_mm=.000002),indent=2)+'\n')
