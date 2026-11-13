"""Measure J2 clearances at its current position (2026-11-13). Writes JSON to argv[2].
Front-side obstacles are those of obstacles.py (switch body 15.6 mm, Cherry stabilizer housing, stab wire, encoder)."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from obstacles import obstacles, rd, m, STAB_HALF_X, PAD

b = pcbnew.LoadBoard(sys.argv[1])
j2 = b.FindFootprintByReference('J2')
cy = j2.GetCourtyard(pcbnew.B_CrtYd).BBox()
crt = (m(cy.GetLeft()), m(cy.GetTop()), m(cy.GetRight()), m(cy.GetBottom()))
holes = [(m(p.GetPosition().x), m(p.GetPosition().y), m(p.GetDrillSizeX()) / 2) for p in j2.Pads() if not p.GetNumber()]
OBS = obstacles(b)
near = sorted((rd(crt, o[2:]), o[0], o[1], o[2:]) for o in OBS)
by_kind = {}
for d, k, r, box in near:
    by_kind.setdefault(k, []).append({'ref': r, 'box': [round(v, 3) for v in box], 'gap_from_courtyard_mm': round(d, 3)})
EDGE = (-3.572, 45.252, 303.611, 121.444)
back = []
for f in b.GetFootprints():
    if f.GetLayer() == pcbnew.B_Cu and f.GetReference() != 'J2':
        bb = f.GetCourtyard(pcbnew.B_CrtYd).BBox()
        if bb.GetWidth() > 0:
            back.append((rd(crt, (m(bb.GetLeft()), m(bb.GetTop()), m(bb.GetRight()), m(bb.GetBottom()))), f.GetReference()))
back.sort()
lengths = {}
for t in b.GetTracks():
    if t.GetClass() != 'PCB_VIA' and t.GetNetname() in ('SWDIO', 'SWCLK', 'nRESET', 'nRF_VDD'):
        lengths.setdefault(t.GetNetname(), {}).setdefault(t.GetLayerName(), 0)
        lengths[t.GetNetname()][t.GetLayerName()] += m(t.GetLength())
out = {
    'J2': {'pos': [m(j2.GetPosition().x), m(j2.GetPosition().y)], 'orientation': j2.GetOrientationDegrees(),
           'layer': j2.GetLayerName(), 'courtyard_bbox': crt,
           'pads': {p.GetNumber(): [m(p.GetPosition().x), m(p.GetPosition().y), p.GetNetname()] for p in j2.Pads() if p.GetNumber()},
           'holes': holes},
    'obstacle_model': {'switch': '15.6 x 15.6 mm square on the switch centre',
                       'stabilizer': f'stab hole centre x +-{STAB_HALF_X} mm, y from outer edge of the 3.05 hole to outer edge of the 4.0 hole, + {PAD} mm',
                       'stab-wire': 'between the two housings, 4.0 hole row +-2 mm',
                       'encoder': 'SW2 F.CrtYd'},
    'nearest_front_obstacles_by_kind': {k: v[:3] for k, v in by_kind.items()},
    'nearest_front_obstacle': {'kind': near[0][1], 'ref': near[0][2], 'gap_mm': round(near[0][0], 3)},
    'courtyard_to_board_edge_mm': round(min(crt[0] - EDGE[0], EDGE[2] - crt[2], crt[1] - EDGE[1], EDGE[3] - crt[3]), 3),
    'hole_edge_to_board_edge_mm': round(min(EDGE[3] - (h[1] + h[2]) for h in holes), 3),
    'nearest_back_courtyards': [{'ref': r, 'gap_mm': round(d, 3)} for d, r in back[:3]],
    'track_lengths_mm': {k: {l: round(v, 2) for l, v in d.items()} for k, d in lengths.items()},
}
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ('nearest_front_obstacle', 'nearest_front_obstacles_by_kind', 'courtyard_to_board_edge_mm',
                                      'hole_edge_to_board_edge_mm', 'nearest_back_courtyards', 'track_lengths_mm')}, indent=1, ensure_ascii=False))
