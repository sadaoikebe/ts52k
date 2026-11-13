"""Measure J2 clearances (2026-11-13). Writes JSON to argv[2]."""
import sys, json, math
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
m = lambda v: v / 1e6
j2 = b.FindFootprintByReference('J2')
cy = j2.GetCourtyard(pcbnew.B_CrtYd).BBox()
crt = (m(cy.GetLeft()), m(cy.GetTop()), m(cy.GetRight()), m(cy.GetBottom()))
holes = [(m(p.GetPosition().x), m(p.GetPosition().y), m(p.GetDrillSizeX()) / 2) for p in j2.Pads() if not p.GetNumber()]
def rd(a, c):
    dx = max(c[0] - a[2], a[0] - c[2], 0); dy = max(c[1] - a[3], a[1] - c[3], 0); return math.hypot(dx, dy)
sw = []
for f in b.GetFootprints():
    r = f.GetReference()
    if r.startswith('MX'):
        x, y = m(f.GetPosition().x), m(f.GetPosition().y)
        sw.append((rd(crt, (x - 7.8, y - 7.8, x + 7.8, y + 7.8)), r, x, y))
sw.sort()
mx4 = b.FindFootprintByReference('MX4')
stab = [(m(p.GetPosition().x), m(p.GetPosition().y), m(p.GetDrillSizeX()) / 2) for p in mx4.Pads() if not p.GetNumber() and m(p.GetPosition().x) < 10]
lengths = {}
for t in b.GetTracks():
    if t.GetClass() != 'PCB_VIA' and t.GetNetname() in ('SWDIO', 'SWCLK', 'nRESET', 'nRF_VDD'):
        lengths.setdefault(t.GetNetname(), {}).setdefault(t.GetLayerName(), 0)
        lengths[t.GetNetname()][t.GetLayerName()] += m(t.GetLength())
out = {
    'J2': {'pos': [m(j2.GetPosition().x), m(j2.GetPosition().y)], 'orientation': j2.GetOrientationDegrees(), 'layer': j2.GetLayerName(),
           'courtyard_bbox': crt,
           'pads': {p.GetNumber(): [m(p.GetPosition().x), m(p.GetPosition().y), p.GetNetname()] for p in j2.Pads() if p.GetNumber()},
           'holes': holes},
    'switch_body_15.6mm_nearest': [{'ref': r, 'center': [x, y], 'gap_from_courtyard_mm': round(d, 3)} for d, r, x, y in sw[:4]],
    'board_edge_x': -3.572, 'courtyard_to_edge_mm': round(crt[0] + 3.572, 3),
    'hole_edge_to_board_edge_mm': round(min(h[0] - h[2] for h in holes) + 3.572, 3),
    'ANT_EDGE_bottom_y': 82.0, 'pad_or_hole_to_ANT_EDGE_mm': round(min(min(h[1] - h[2] for h in holes), 85.23 - 0.3937) - 82.0, 3),
    'MX4_west_stab_holes': stab,
    'nearest_J2_hole_edge_to_MX4_stab_x_mm': round(stab[0][0] - max(h[0] + h[2] for h in holes), 3),
    'track_lengths_mm': {k: {l: round(v, 2) for l, v in d.items()} for k, d in lengths.items()},
}
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1))
