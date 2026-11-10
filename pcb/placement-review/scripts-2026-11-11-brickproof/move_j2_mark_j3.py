"""2026-11-11 brick-proofing edit (run once against wireless 43c3f08).

1. J2 (Tag-Connect TC2030-NL): the single alignment hole at (11.0, 79.46) sat
   under the body outline of MX3 on the front side.  Rotate J2 to lie along
   the row gap (y = 80.8 .. 85.8 is free of switch bodies) at (12.0, 83.3) and
   re-route SWDIO / SWCLK / nRESET / VTref / GND to the new pad positions.
2. J3 (battery): add "+" / "-" silkscreen in front of the plug opening.
"""
import sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(mm(x), mm(y))
near = lambda p, x, y: abs(p.x - mm(x)) < 2000 and abs(p.y - mm(y)) < 2000

REMOVE = {
    'nRF_VDD': [((14.2, 79.0), (12.47, 80.73)), ((12.47, 80.73), (11.635, 80.73))],
    'nRESET': [((14.9, 79.6), (14.9, 81.5)), ((14.9, 81.5), (14.4, 82.0)), ((14.4, 82.0), (11.635, 82.0))],
    'SWDIO': [((3.13, 80.73), (10.365, 80.73))],
    'SWCLK': [((2.33, 82.0), (10.365, 82.0))],
}
todo = sum(len(v) for v in REMOVE.values())
for t in list(b.GetTracks()):
    if t.GetClass() == 'PCB_VIA':
        if t.GetNetname() == 'GND' and near(t.GetPosition(), 14.0, 84.0):
            b.RemoveNative(t); todo -= 0; print('removed GND via 14.0,84.0')
        continue
    for a, c in REMOVE.get(t.GetNetname(), []):
        s, e = t.GetStart(), t.GetEnd()
        if t.GetLayerName() == 'B.Cu' and ((near(s, *a) and near(e, *c)) or (near(s, *c) and near(e, *a))):
            b.RemoveNative(t); todo -= 1
assert todo == 0, todo

j2 = b.FindFootprintByReference('J2')
j2.SetPosition(V(12.0, 83.3))
j2.SetOrientationDegrees(0)
pads = {p.GetNumber(): p.GetPosition() for p in j2.Pads() if p.GetNumber()}
P = lambda n: (pads[n].x / 1e6, pads[n].y / 1e6)
assert P('1') == (10.73, 82.665) and P('2') == (10.73, 83.935) and P('5') == (13.27, 82.665), pads
j2.Reference().SetPosition(V(12.0, 80.1))
j2.Reference().SetTextAngleDegrees(0)

def route(net, width, pts):
    code = b.GetNetcodeFromNetname(net)
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(mm(width))
        t.SetLayer(pcbnew.B_Cu); t.SetNetCode(code); b.Add(t)

route('nRF_VDD', 0.2, [(14.2, 79.0), (11.6, 79.0), (10.73, 79.87), P('1')])
route('nRESET', 0.15, [(14.9, 79.6), (14.9, 80.4), (14.3, 81.0), (12.4, 81.0), (12.0, 81.4), P('3')])
route('GND', 0.15, [P('5'), (13.27, 81.85), (13.72, 81.4), (16.4, 81.4), (16.5, 81.5)])
route('SWDIO', 0.15, [(3.13, 80.73), (4.33, 80.73), (7.8, 84.2), (10.465, 84.2), P('2')])
route('SWCLK', 0.15, [(2.33, 82.0), (4.7, 82.0), (7.65, 84.95), (11.47, 84.95), (12.0, 84.42), P('4')])

def silk(text, x, y, size=1.5):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(text); t.SetLayer(pcbnew.B_SilkS); t.SetPosition(V(x, y))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(0.25))
    t.SetMirrored(True); b.Add(t)

silk('+', 37.0, 64.0)   # J3 pad 1 = BAT (y = 64.0)
silk('-', 37.0, 66.0)   # J3 pad 2 = GND (y = 66.0)
silk('SWD', 16.3, 82.75, 0.8)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('saved')
