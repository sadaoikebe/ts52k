"""One-time RP2040 -> wireless rough placement; run with KiCad's Python.

Requires the original PCB from 530e849. Does not route any new connections.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
import pcbnew as p

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / 'pcb'
OUT = Path(__file__).resolve().parent
path = PCB / 'ts52k.kicad_pcb'
baseline = subprocess.check_output(['git', 'show', '530e849:pcb/ts52k.kicad_pcb'], cwd=ROOT)
assert path.read_bytes().replace(b'\r\n', b'\n') == baseline.replace(b'\r\n', b'\n'), 'Already migrated; do not overwrite later work'
b = p.LoadBoard(str(path))
xml = ET.parse(PCB / 'schematic-review/ts52k-wireless.net').getroot()
components = {c.get('ref'): c for c in xml.findall('./components/comp')}
node_net = {(n.get('ref'), n.get('pin')): net.get('name')
            for net in xml.findall('./nets/net') for n in net.findall('node')}
old = {f.GetReference(): f for f in b.GetFootprints()}
new_refs = set(components) - set(old) | {'U5'}
replaced = {'U5', 'J2', 'D89', 'D90', 'D91'}
retained = set(components) & set(old) - {'U5'}
def sch_path(c):
    return c.find('sheetpath').get('tstamps') + c.findtext('tstamps')
for ref in retained:
    assert old[ref].GetPath().AsString() == sch_path(components[ref]), ref
anchors = {ref: [old[ref].GetPosition().x, old[ref].GetPosition().y,
                  old[ref].GetOrientationDegrees(), old[ref].GetLayer()]
           for ref in retained}
net_map = {}
for ref in retained:
    for pad in old[ref].Pads():
        target = node_net.get((ref, pad.GetNumber()))
        if target and pad.GetNetCode():
            net_map.setdefault(pad.GetNetCode(), set()).add(target)
assert all(len(names) == 1 for names in net_map.values()), net_map
net_map = {code: next(iter(names)) for code, names in net_map.items()}
nets = {}
for name in sorted(set(node_net.values())):
    net = b.FindNet(name)
    if net is None:
        net = p.NETINFO_ITEM(b, name)
        b.Add(net)
    nets[name] = net
removed_objects = []
def remove(item):
    b.Remove(item)
    item.thisown = False
    removed_objects.append(item)

# Delete obsolete circuits; preserve matrix trunks outside this local island.
# Liang-Barsky clipping retains only the original segment portions outside it.
clear_box = (15.3, 56.5, 41.5, 72.0)
def outside(a, z):
    x0, y0, x1, y1 = clear_box
    dx, dy = z[0]-a[0], z[1]-a[1]
    lo, hi = 0., 1.
    for v, q in [(-dx, a[0]-x0), (dx, x1-a[0]), (-dy, a[1]-y0), (dy, y1-a[1])]:
        if abs(v) < 1e-12:
            if q < 0: return [(a, z)]
        elif v < 0: lo = max(lo, q/v)
        else: hi = min(hi, q/v)
    if lo > hi: return [(a, z)]
    lerp = lambda t: (a[0]+t*dx, a[1]+t*dy)
    return ([(a, lerp(lo))] if lo > 1e-9 else []) + ([(lerp(hi), z)] if hi < 1-1e-9 else [])
tracks_before = len(list(b.GetTracks()))
deleted_tracks, clipped_tracks = 0, 0
always_clear = {'+3V3', '+5V', 'D+', 'D-', 'SWDIO', 'SWCLK', '~{RST}', 'nRESET'}
for t in list(b.GetTracks()):
    name = net_map.get(t.GetNetCode())
    if name is None or t.GetNetname() in always_clear:
        remove(t); deleted_tracks += 1; continue
    t.SetNet(nets[name])
    if isinstance(t, p.PCB_VIA):
        pos = t.GetPosition(); x, y = p.ToMM(pos.x), p.ToMM(pos.y)
        if clear_box[0] <= x <= clear_box[2] and clear_box[1] <= y <= clear_box[3]:
            remove(t); deleted_tracks += 1
        continue
    a, z = t.GetStart(), t.GetEnd()
    aa, zz = (p.ToMM(a.x), p.ToMM(a.y)), (p.ToMM(z.x), p.ToMM(z.y))
    segments = outside(aa, zz)
    if segments == [(aa, zz)]: continue
    if not segments:
        remove(t); deleted_tracks += 1; continue
    clipped_tracks += 1
    for i, (start, end) in enumerate(segments):
        target = t if i == 0 else t.Duplicate()
        if i: b.Add(target)
        target.SetStart(p.VECTOR2I(p.FromMM(start[0]), p.FromMM(start[1])))
        target.SetEnd(p.VECTOR2I(p.FromMM(end[0]), p.FromMM(end[1])))
for zone in list(b.Zones()):
    box = zone.GetBoundingBox()
    # Old MCU priority pours, its local rule area, and duplicate SWD keepout.
    if zone.GetAssignedPriority() > 0 or zone.GetIsRuleArea():
        remove(zone)
    else:
        zone.SetNet(nets['GND'])
        zone.UnFill()

positions = {
    'U5': (23.5,63.0,-90), 'U6': (17.0,51.0,0),
    'C22': (17.0,48.5,0), 'C23': (17.0,54.0,0), 'C24': (13.5,52.6,90),
    'R17': (19.5,54.0,0), 'R18': (19.5,52.5,0), 'R19': (14.0,51.0,0),
    'R20': (30.5,49.0,0), 'X3': (33.5,60.2,90),
    'C32': (33.5,58.6,0), 'C33': (35.5,59.7,0),
    'C27': (33.2,64.6,0), 'C28': (35.4,64.6,0),
    'C29': (32.6,62.8,0), 'C30': (34.8,62.8,0), 'C31': (37.0,62.8,0),
    'L1': (33.2,66.2,0), 'C25': (35.6,66.4,0), 'C26': (32.6,68.8,0),
    'J3': (16.0,82.0,0),
}
assert set(positions) == new_refs
for ref, f in old.items():
    if ref not in components or ref in replaced:
        remove(f)
for ref, c in components.items():
    fpid = c.findtext('footprint')
    if ref in new_refs or ref in replaced:
        lib, fpname = fpid.split(':', 1)
        f = p.FootprintLoad(str(PCB / (lib+'.pretty')), fpname)
        assert f is not None, fpid
        b.Add(f)
        f.SetFPID(p.LIB_ID(*fpid.split(':', 1)))
        if ref in new_refs:
            x, y, angle = positions[ref]
            f.SetLayerAndFlip(p.B_Cu)
            f.SetOrientationDegrees(angle)
            f.SetPosition(p.VECTOR2I(p.FromMM(x), p.FromMM(y)))
        else:
            x, y, angle, layer = anchors[ref]
            f.SetLayerAndFlip(layer)
            f.SetOrientationDegrees(angle)
            f.SetPosition(p.VECTOR2I(x, y))
        f.SetReference(ref)
    else:
        f = old[ref]
        f.SetFPID(p.LIB_ID(*fpid.split(':', 1)))
    f.SetPath(p.KIID_PATH(sch_path(c)))
    f.SetValue(c.findtext('value'))
    props = {v.get('name'):v.get('value','') for v in c.findall('property')}
    for key in ['MPN','Manufacturer','LCSC','JLCClass']:
        if key in props:
            f.SetField(key, props[key]); f.GetField(key).SetVisible(False)
    for field in c.findall('./fields/field'):
        key = field.get('name')
        if key not in ['Footprint', 'Reference', 'Value']:
            f.SetField(key, field.text or '')
            f.GetField(key).SetVisible(False)
    f.SetSheetname(props['Sheetname']); f.SetSheetfile(props['Sheetfile'])
    f.SetExcludedFromBOM('exclude_from_bom' in props)
    f.SetExcludedFromPosFiles('exclude_from_pos_files' in props)
    if ref in new_refs or ref in replaced:
        f.Value().SetVisible(False)
        f.Reference().SetTextSize(p.VECTOR2I(p.FromMM(.65),p.FromMM(.65)))
        f.Reference().SetTextThickness(p.FromMM(.1))
    for pad in f.Pads():
        name = node_net.get((ref, pad.GetNumber()))
        pad.SetNet(nets[name] if name else b.FindNet(0))

fps = {f.GetReference():f for f in b.GetFootprints()}
assert set(fps) == set(components)
for ref in retained:
    f = fps[ref]
    assert anchors[ref] == [f.GetPosition().x,f.GetPosition().y,f.GetOrientationDegrees(),f.GetLayer()], ref
for ref, f in fps.items():
    for pad in f.Pads():
        assert pad.GetNetname() == node_net.get((ref,pad.GetNumber()), ''), (ref,pad.GetNumber())
b.BuildConnectivity()
p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(path), b)
report = {
    'stage':'rough placement, no new routing', 'baseline_commit':'530e849',
    'footprints_before':len(old), 'footprints_after':len(fps),
    'removed_references':sorted(set(old)-set(components)),
    'replaced_references':sorted(replaced),
    'tracks_and_vias_before':tracks_before, 'tracks_and_vias_after':len(list(b.GetTracks())),
    'tracks_and_vias_removed':deleted_tracks, 'old_tracks_clipped':clipped_tracks,
    'new_routed_connections':0, 'routing_clear_rectangle_mm':clear_box,
    'retained_positions_and_orientations_checked':len(retained),
    'schematic_paths_and_pad_nets':'match XML netlist',
    'rough_positions_mm_deg':positions,
    'board_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
}
(OUT/'placement.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
