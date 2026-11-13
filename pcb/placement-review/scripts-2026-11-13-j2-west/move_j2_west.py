"""2026-11-13: move J2 (Tag-Connect TC2030-IDC-NL) to the west-edge strip (run once against wireless 4cbad9f).

At (12.0, 83.3), between the front-side bodies of MX3 (1.75U) and MX4 (2.25U), there was
no room for the TC2030-CLIP once the real switch body (~15.6 mm at its base) is fitted.
New position: (-0.6, 86.5), -90 deg (bottom side), between the west board edge (x = -3.572)
and the MX4 west stabilizer, south of the ANT_EDGE keep-out (y < 82).

The VTref / nRESET / SWDIO / SWCLK / GND tails near the old J2 are removed and re-routed on B.Cu.
The two GND stitching vias (1.5, 84.0) and (1.5, 86.5) that sit on the new routes are removed.
"""
import sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
near = lambda p, x, y: abs(p.x - mm(x)) < 2000 and abs(p.y - mm(y)) < 2000

REMOVE = {
    'nRF_VDD': [((11.6, 79.0), (10.73, 79.87)), ((10.73, 79.87), (10.73, 82.665))],
    'nRESET': [((14.3, 81.0), (12.4, 81.0)), ((12.4, 81.0), (12.0, 81.4)), ((12.0, 81.4), (12.0, 82.665))],
    'SWDIO': [((2.6, 80.2), (3.13, 80.73)), ((3.13, 80.73), (4.33, 80.73)), ((4.33, 80.73), (7.8, 84.2)),
              ((7.8, 84.2), (10.465, 84.2)), ((10.465, 84.2), (10.73, 83.935))],
    'SWCLK': [((1.8, 81.47), (2.33, 82.0)), ((2.33, 82.0), (4.7, 82.0)), ((4.7, 82.0), (7.65, 84.95)),
              ((7.65, 84.95), (11.47, 84.95)), ((11.47, 84.95), (12.0, 84.42)), ((12.0, 84.42), (12.0, 83.935))],
    'GND': [((13.27, 82.665), (13.27, 81.85)), ((13.27, 81.85), (13.72, 81.4)), ((13.72, 81.4), (16.4, 81.4)),
            ((16.4, 81.4), (16.5, 81.5))],
}
VIAS = [(1.5, 84.0), (1.5, 86.5)]
todo = sum(len(v) for v in REMOVE.values()) + len(VIAS)
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        if t.GetNetname() == 'GND' and any(near(t.GetPosition(), *v) for v in VIAS):
            b.RemoveNative(t); todo -= 1
        continue
    for a, c in REMOVE.get(t.GetNetname(), []):
        s, e = t.GetStart(), t.GetEnd()
        if t.GetLayerName() == 'B.Cu' and ((near(s, *a) and near(e, *c)) or (near(s, *c) and near(e, *a))):
            b.RemoveNative(t); todo -= 1
assert todo == 0, todo

j2 = b.FindFootprintByReference('J2')
j2.SetPosition(V(-0.6, 86.5))
j2.SetOrientationDegrees(-90)
pads = {p.GetNumber(): p.GetPosition() for p in j2.Pads() if p.GetNumber()}
P = lambda n: (pads[n].x / 1e6, pads[n].y / 1e6)
assert P('1') == (0.035, 85.23) and P('2') == (-1.235, 85.23) and P('3') == (0.035, 86.5), pads
assert P('4') == (-1.235, 86.5) and P('5') == (0.035, 87.77), pads
j2.Reference().SetPosition(V(-0.6, 91.6))
j2.Reference().SetTextAngleDegrees(0)

def route(net, width, pts):
    code = b.GetNetcodeFromNetname(net)
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(width))
        t.SetLayer(pcbnew.B_Cu); t.SetNetCode(code); b.Add(t)

# East side of J2: VTref (outer) and nRESET (inner) come from the old J2 area, pass north of the
# MX4 stabilizer hole (4.763, 85.884, d 3.048) and enter pads 1 / 3 from the east.
route('nRF_VDD', 0.2, [(11.6, 79.0), (7.3, 83.3), (1.6, 83.3), (1.6, 84.6), (0.97, 85.23), P('1')])
route('nRESET', 0.15, [(14.3, 81.0), (12.4, 81.0), (9.6, 83.8), (2.2, 83.8), (2.2, 86.5), P('3')])
# West side: SWDIO / SWCLK come down from the module at x = 2.6 / 1.8, cross west below ANT_EDGE
# (y > 82) and north of the single alignment hole, and enter pads 2 / 4 from the west.
route('SWCLK', 0.15, [(1.8, 81.47), (1.8, 81.8), (1.45, 82.35), (-1.75, 82.35), (-2.3, 82.9), (-2.3, 86.5), P('4')])
route('SWDIO', 0.15, [(2.6, 80.2), (2.6, 82.15), (1.9, 82.85), (-1.3, 82.85), (-1.8, 83.35), (-1.8, 85.23), P('2')])
route('GND', 0.15, [P('5'), (1.5, 87.77), (1.5, 89.0)])   # existing GND via (1.5, 89.0)

for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'SWD' and near(d.GetPosition(), 16.3, 82.75):
        d.SetPosition(V(-0.6, 80.9 + 0.0))
        break
else:
    raise SystemExit('SWD silk not found')

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('saved')
