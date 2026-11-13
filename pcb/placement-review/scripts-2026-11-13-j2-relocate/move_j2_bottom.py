"""2026-11-13: move J2 (Tag-Connect TC2030-IDC-NL) from the west strip (-0.6, 86.5) -90 deg to the bottom-row gap
between MX5 and MX9 (both 1.25U): (19.05, 115.0) +90 deg, bottom side. Run once against wireless 5f83906.

The four SWD lanes keep their west-to-east order (SWCLK, SWDIO, nRF_VDD, nRESET) down the west strip
(east of the GND stitching via (-2.262, 102.394)), turn east south of the MX5 centre hole and enter J2:
nRESET -> pad 3 and nRF_VDD -> pad 1 from the west; SWDIO / SWCLK pass south of the single alignment hole and
enter pads 2 / 4 from the east. Pad 5 (GND) goes to the existing GND via (16.074, 111.681).
Only the old J2 tails are removed; the module-side routes down to y ~ 83-86 are kept.
"""
import sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
near = lambda p, x, y: abs(p.x - mm(x)) < 2000 and abs(p.y - mm(y)) < 2000

REMOVE = {
    'nRF_VDD': [((1.6, 84.6), (0.97, 85.23)), ((0.97, 85.23), (0.035, 85.23))],
    'nRESET': [((2.2, 83.8), (2.2, 86.5)), ((2.2, 86.5), (0.035, 86.5))],
    'SWDIO': [((-1.8, 83.35), (-1.8, 85.23)), ((-1.8, 85.23), (-1.235, 85.23))],
    'SWCLK': [((-2.3, 82.9), (-2.3, 86.5)), ((-2.3, 86.5), (-1.235, 86.5))],
    'GND': [((0.035, 87.77), (1.5, 87.77)), ((1.5, 87.77), (1.5, 89.0))],
}
todo = sum(len(v) for v in REMOVE.values())
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        continue
    for a, c in REMOVE.get(t.GetNetname(), []):
        s, e = t.GetStart(), t.GetEnd()
        if t.GetLayerName() == 'B.Cu' and ((near(s, *a) and near(e, *c)) or (near(s, *c) and near(e, *a))):
            b.RemoveNative(t); todo -= 1
assert todo == 0, todo

X, Y = 19.05, 115.0
j2 = b.FindFootprintByReference('J2')
j2.SetPosition(V(X, Y))
j2.SetOrientationDegrees(90)
pads = {p.GetNumber(): p.GetPosition() for p in j2.Pads() if p.GetNumber()}
P = lambda n: (round(pads[n].x / 1e6, 4), round(pads[n].y / 1e6, 4))
exp = {'1': (18.415, 116.27), '2': (19.685, 116.27), '3': (18.415, 115.0), '4': (19.685, 115.0),
       '5': (18.415, 113.73), '6': (19.685, 113.73)}
assert all(P(k) == v for k, v in exp.items()), {k: P(k) for k in exp}
j2.Reference().SetPosition(V(23.3, 115.0))

nets = b.GetNetsByName()


def route(net, width, pts):
    code = nets[net].GetNetCode()
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(width))
        t.SetLayer(pcbnew.B_Cu); t.SetNetCode(code); b.Add(t)


# West strip lanes (west -> east): SWCLK -1.5, SWDIO -1.0, nRF_VDD -0.5, nRESET 0.0.
route('SWCLK', 0.15, [(-2.3, 82.9), (-2.3, 86.3), (-1.5, 87.1), (-1.5, 118.4), (-1.0, 118.9),
                      (21.1, 118.9), (21.6, 118.4), (21.6, 115.5), (21.1, 115.0), P('4')])
route('SWDIO', 0.15, [(-1.8, 83.35), (-1.8, 85.8), (-1.0, 86.6), (-1.0, 117.9), (-0.5, 118.4),
                      (20.3, 118.4), (20.9, 117.8), (20.9, 116.87), (20.3, 116.27), P('2')])
route('nRF_VDD', 0.2, [(1.6, 84.6), (-0.5, 86.7), (-0.5, 115.77), (0.0, 116.27), P('1')])
route('nRESET', 0.15, [(2.2, 83.8), (2.2, 85.2), (0.0, 87.4), (0.0, 114.5), (0.5, 115.0), P('3')])
route('GND', 0.15, [P('5'), (16.074, 113.73), (16.074, 111.681)])   # existing GND via (16.074, 111.681)

for d in b.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetText() == 'SWD' and near(d.GetPosition(), -0.6, 80.9):
        d.SetPosition(V(X, 110.7))
        break
else:
    raise SystemExit('SWD silk not found')

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('saved')
