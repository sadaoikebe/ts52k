"""Extract numbered pad geometry from the actual board and JLC viewer SVGs.

KiCad/EasyEDA coordinates below are front-side footprint zero, x right/y down,
mm. No board is saved. EasyEDA SVG units are 10 mil = 0.254 mm.
"""
import csv, json, xml.etree.ElementTree as ET
from pathlib import Path
import pcbnew
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
board = pcbnew.LoadBoard(str(ROOT / 'pcb/ts52k.kicad_pcb'))
rows = list(csv.DictReader((ROOT/'pcb/jlcpcb/assembly/ts52k-bom.csv').open()))
board_fps = {f.GetReference(): f for f in board.GetFootprints()}
def kpad(p):
    return dict(number=p.GetNumber(), x=round(p.GetPosition().x/1e6,6), y=round(p.GetPosition().y/1e6,6),
                w=round(p.GetSize().x/1e6,6), h=round(p.GetSize().y/1e6,6), angle=p.GetOrientationDegrees(), shape=p.GetShape(), net=p.GetNetname())
result=[]
for row in rows:
    name = row['Footprint'].split(':')[1]
    fp = pcbnew.FootprintLoad(str(ROOT/'pcb/ts52k.pretty'), name)
    libpads = [kpad(p) for p in fp.Pads()]
    instances=[]
    for ref in row['Designator'].split(','):
        orig = board_fps[ref]
        f = pcbnew.FOOTPRINT(orig)
        before = dict(ref=ref,x=orig.GetPosition().x/1e6,y=orig.GetPosition().y/1e6,angle=orig.GetOrientationDegrees(),bottom=orig.IsFlipped(),pads=[kpad(p) for p in orig.Pads()])
        if f.IsFlipped(): f.Flip(f.GetPosition(), False)
        f.SetOrientationDegrees(0)
        f.SetPosition(pcbnew.VECTOR2I(0,0))
        before['normalized_pads']=[kpad(p) for p in f.Pads()]
        instances.append(before)
    part=row['LCSC Part #']; svgp=HERE/'raw'/f'{part}-svgs.json'
    ees=[]
    if svgp.exists():
        for r in json.loads(svgp.read_text()).get('result',[]):
            if r['docType'] != 4: continue
            tree=ET.fromstring(r['svg'])
            group=next(e for e in tree if 'c_origin' in e.attrib)
            ox,oy=map(float,group.attrib['c_origin'].split(','))
            pads=[]
            for e in group.iter():
                a=e.attrib
                if a.get('c_partid') != 'part_pad': continue
                x,y=map(float,a['c_origin'].split(','))
                pads.append(dict(number=a.get('number'),x=round((x-ox)*.254,6),y=round((y-oy)*.254,6),w=round(float(a['c_width'])*.254,6),h=round(float(a['c_height'])*.254,6),angle=float(a.get('c_rotation',0)),shape=a['c_shape'],svg=ET.tostring(e,encoding='unicode')))
            ees.append(dict(uuid=r['component_uuid'],updateTime=r['updateTime'],origin=[ox,oy],meta=group.attrib,pads=pads))
    result.append(dict(bom=row,kicad_lib_pads=libpads,instances=instances,easyeda=ees))
(HERE/'geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for r in result:
    print(r['bom']['LCSC Part #'],r['bom']['Designator'],r['bom']['Footprint'])
    print(' K',[(p['number'],p['x'],p['y'],p['w'],p['h'],p['angle']) for p in r['kicad_lib_pads'] if p['number']][:65])
    for e in r['easyeda']:print(' E',[(p['number'],p['x'],p['y'],p['w'],p['h'],p['angle']) for p in e['pads']][:65])
    for ins in r['instances']:
        clean=lambda ps:sorted((p['number'],p['x'],p['y'],p['w'],p['h'],p['angle']%180,p['shape']) for p in ps)
        if clean(ins['normalized_pads'])!=clean(r['kicad_lib_pads']):print(' BOARD/LIB DIFFERENCE',ins['ref'])
