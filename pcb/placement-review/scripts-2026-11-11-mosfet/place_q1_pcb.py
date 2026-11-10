"""Place Q1 (AO3401A, SOT-23) south-west of J3 and reroute locally.

Run once on the board of wireless b730700:  python3 place_q1_pcb.py <pcb>
Coordinates are board mm (east = +x, south = +y), all new copper on B.Cu unless noted.
"""
import sys
import pcbnew

PCB = sys.argv[1]
F = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(F(x), F(y))
b = pcbnew.LoadBoard(PCB)
FCU, BCU = pcbnew.F_Cu, pcbnew.B_Cu

def net(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
    return n

def near(p, x, y, tol=0.002):
    return abs(pcbnew.ToMM(p.x) - x) < tol and abs(pcbnew.ToMM(p.y) - y) < tol

def find_track(netname, layer, a, c):
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == netname and t.GetLayer() == layer:
            if (near(t.GetStart(), *a) and near(t.GetEnd(), *c)) or (near(t.GetStart(), *c) and near(t.GetEnd(), *a)):
                return t
    raise SystemExit(f'track not found: {netname} {a} {c}')

def find_via(netname, x, y):
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == netname and near(t.GetPosition(), x, y):
            return t
    raise SystemExit(f'via not found: {netname} {x} {y}')

def track(netname, layer, width, *pts):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(F(width)); t.SetLayer(layer); t.SetNet(net(netname))
        b.Add(t)

def via(netname, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y)); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(FCU, BCU)
    v.SetWidth(FCU, F(0.6)); v.SetDrill(F(0.3)); v.SetNet(net(netname))
    b.Add(v)

assert b.FindFootprintByReference('Q1') is None, 'already applied'
CONN = '/BAT_CONN'

# --- 1. Q1 footprint, linked to the schematic symbol
import os
lib = os.path.join(os.path.dirname(os.path.abspath(PCB)), 'ts52k.pretty')
q = pcbnew.FootprintLoad(lib, 'SOT-23')
q.SetFPID(pcbnew.LIB_ID('ts52k', 'SOT-23'))
q.SetReference('Q1'); q.SetValue('AO3401A')
q.SetPath(pcbnew.KIID_PATH('/10b01f4d-a549-4121-8f70-cfe7f9401909'))
q.SetSheetname('ts52k'); q.SetSheetfile('ts52k.kicad_sch')
b.Add(q)
for k, v in (('Datasheet', 'https://www.aosmd.com/pdfs/datasheet/AO3401A.pdf'),
             ('Description', 'AO3401A P-channel MOSFET, -30 V, SOT-23; 1 G, 2 S, 3 D; reverse-battery protection'),
             ('MPN', 'AO3401A'), ('Manufacturer', 'Alpha & Omega Semiconductor'), ('LCSC', 'C15127'), ('JLCClass', 'Basic')):
    q.SetField(k, v)
q.SetPosition(V(24.97, 68.73))
q.Flip(V(24.97, 68.73), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
q.SetOrientationDegrees(0)
q.Reference().SetVisible(False); q.Value().SetVisible(False)
for f in q.GetFields():
    if f.GetName() not in ('Reference', 'Value'):
        f.SetVisible(False)
for p in q.Pads():
    p.SetNet(net({'1': 'GND', '2': 'BAT', '3': CONN}[p.GetNumber()]))
    if p.GetNumber() == '1':
        # the gate is tied to GND by its own track; no thermal spokes in this tight spot
        p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_NONE)
pos = {p.GetNumber(): (pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in q.Pads()}
print('Q1 pads', pos)
G, S, D = pos['1'], pos['2'], pos['3']
assert D[0] > 25.5 and S[1] < G[1] and S[0] < 24.5, 'unexpected orientation'

# --- 2. J3 pin 1 leaves BAT
j3 = b.FindFootprintByReference('J3')
for p in j3.Pads():
    if p.GetNumber() == '1':
        p.SetNet(net(CONN))

# --- 3. remove superseded copper (RemoveNative: BOARD.Remove breaks SWIG types in this build)
for it in (find_track('BAT', FCU, (23.8, 62.3), (25.5, 64.0)), find_via('BAT', 25.5, 64.0),
           find_track('BAT', BCU, (25.5, 64.0), (26.4, 64.0)),
           find_track('Net-(D3-A)', BCU, (24.4, 69.75), (24.4, 64.4)),
           find_track('Net-(D3-A)', BCU, (15.457, 69.75), (24.4, 69.75))):
    b.RemoveNative(it)

# --- 4. BAT: stay on F.Cu past D3, drop to B.Cu just north of Q1 source
track('BAT', FCU, 0.3, (23.8, 62.3), (23.8, 66.5))
via('BAT', 23.8, 66.5)
track('BAT', BCU, 0.3, (23.8, 66.5), (23.8, S[1] - (S[0] - 23.8)), S)

# --- 5. BAT_CONN: J3 pin 1 -> west of J3 pin 2 -> Q1 drain
track(CONN, BCU, 0.3, (26.4, 64.0), (25.55, 64.0), (25.55, D[1] - (D[0] - 25.55)), D)

# --- 6. gate -> GND at J3 pin 2 (explicit track, not only the pour)
track('GND', BCU, 0.25, G, (27.1, G[1]), (27.1, 66.0))

# --- 7. Net-(D3-A): hop over Q1 on F.Cu
track('Net-(D3-A)', BCU, 0.15, (24.4, 64.4), (24.4, 65.15), (24.75, 65.5))
via('Net-(D3-A)', 24.75, 65.5)
track('Net-(D3-A)', FCU, 0.15, (24.75, 65.5), (24.75, 67.55), (22.75, 69.55))
via('Net-(D3-A)', 22.75, 69.55)
track('Net-(D3-A)', BCU, 0.15, (15.457, 69.75), (22.55, 69.75), (22.75, 69.55))

# --- 8. D-/D+/nRESET/col1 run 0.15 mm further south under Q1 (x = 23.05..25.05)
# The 45-degree jogs are staggered 0.2 mm per track (outer tracks jog further out) so the
# diagonal segments keep at least the spacing of the straight run.
DY, XA, XB, STEP = 0.15, 22.9, 25.2, 0.2
for i, (name, y, w, x0, x1) in enumerate((('D-', 70.165, 0.2, 30.035, 11.765), ('D+', 70.565, 0.2, 30.435, 11.365),
                                          ('nRESET', 70.94, 0.15, 10.195, 31.25), ('col1', 71.29, 0.15, 8.6, 41.0))):
    old = find_track(name, BCU, (x0, y), (x1, y))
    b.RemoveNative(old)
    lo, hi = min(x0, x1), max(x0, x1)
    xa, xb = XA - i * STEP, XB + i * STEP
    track(name, BCU, w, (lo, y), (xa, y), (xa + DY, y + DY), (xb - DY, y + DY), (xb, y), (hi, y))

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('saved')
