#!/usr/bin/env python3
"""check_spec.py : checks from design-spec.md that the KiCad DRC does not cover (or that the rule areas exempt).

Prints one line per check; exits 1 if a hard check fails. The 'review' lists are for reading, not pass/fail.
"""
import json, math, os, sys, collections
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import matrix as M
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(os.path.join(os.path.dirname(HERE), 'ts52k.kicad_pcb'))
K = json.load(open(os.path.join(HERE, 'keys.json')))
L1, L2, L3, L4 = pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu
ASYNC = ('USB', 'D+', 'D-', 'QSPI', 'XIN', 'SWCLK', 'SWDIO', 'ENC_')
fail = []

def seg(t):
    s, e = t.GetStart(), t.GetEnd()
    return mm(s.x), mm(s.y), mm(e.x), mm(e.y)

def dist_ss(a, c):
    """distance between two segments (x1,y1,x2,y2)"""
    def pd(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
        return math.hypot(px - x1 - t * dx, py - y1 - t * dy)
    def ccw(ax, ay, bx, by, cx, cy):
        return (cx - ax) * (by - ay) - (bx - ax) * (cy - ay)
    x1, y1, x2, y2 = a; x3, y3, x4, y4 = c
    if ccw(x1, y1, x2, y2, x3, y3) * ccw(x1, y1, x2, y2, x4, y4) < 0 and ccw(x3, y3, x4, y4, x1, y1) * ccw(x3, y3, x4, y4, x2, y2) < 0:
        return 0.0
    return min(pd(x1, y1, *c), pd(x2, y2, *c), pd(x3, y3, *a), pd(x4, y4, *a))

tracks = [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T]
vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]

def report(name, bad, hard=True):
    print(('ok   ' if not bad else ('FAIL ' if hard else 'note ')) + name + ('' if not bad else f' : {len(bad)}'))
    for x in bad[:12]:
        print('       ', x)
    if bad and hard:
        fail.append(name)

# 1. L2: no tracks at all; L3: tracks only inside the island
report('L2 carries no tracks (5-1)', [(t.GetNetname(), seg(t)) for t in tracks if t.GetLayer() == L2])
isl = lambda x, y: 14.0 <= x <= 45.5 and 41.0 <= y <= 84.5
report('L3 tracks only inside the digital island', [(t.GetNetname(), seg(t)) for t in tracks if t.GetLayer() == L3 and not (isl(*seg(t)[:2]) and isl(*seg(t)[2:]))])
# 2. L1: only rows, electrodes, ground
report('L1 tracks are row buses only (5-8)', [(t.GetNetname(), seg(t)) for t in tracks if t.GetLayer() == L1 and not t.GetNetname().startswith('ROW')])
# 3. HIZ widths
hiz = lambda n: n.startswith('COL') or n in ('SENSE', 'AMP_IN', 'AMP_FB')
report('HIZ track width 0.2 mm (5-4)', [(t.GetNetname(), mm(t.GetWidth())) for t in tracks if hiz(t.GetNetname()) and abs(mm(t.GetWidth()) - 0.2) > 1e-6])
# 4. L3 above HIZ tracks is ground (no L3 track within 1 mm of a COL/SENSE track)
l3 = [t for t in tracks if t.GetLayer() == L3]
bad = []
for t in tracks:
    if t.GetLayer() == L4 and (t.GetNetname().startswith('COL') or t.GetNetname() == 'SENSE'):
        for u in l3:
            d = dist_ss(seg(t), seg(u))
            if d < 1.0:
                bad.append((t.GetNetname(), u.GetNetname(), round(d, 2), [round(v, 1) for v in seg(u)]))
report('no L3 wiring over column / SENSE tracks (5-5)', bad)
# 5. HIZ (L4 tracks) to every foreign L4 track, including the exempted areas: list the close ones
bad = collections.defaultdict(lambda: 9.9)
for t in tracks:
    n = t.GetNetname()
    if t.GetLayer() != L4 or not (n.startswith('COL') or n == 'SENSE'):
        continue
    for u in tracks:
        m = u.GetNetname()
        if u.GetLayer() != L4 or m.startswith(('COL', 'ROW')) or m in ('SENSE', 'GND', 'AMP_IN'):
            continue
        d = dist_ss(seg(t), seg(u)) - mm(t.GetWidth()) / 2 - mm(u.GetWidth()) / 2
        if d < 2.0:
            bad[(n, m)] = min(bad[(n, m)], round(d, 2))
report('review: HIZ track to foreign track gaps under 2.0 mm (inside the exempt areas)', sorted(bad.items()), hard=False)
# 6. column / SENSE to row lead-ins on L4 (5-9: not closer than the 2.38 mm via spacing)
bad = collections.defaultdict(lambda: 9.9)
for t in tracks:
    n = t.GetNetname()
    if t.GetLayer() != L4 or not (n.startswith('COL') or n == 'SENSE'):
        continue
    for u in tracks:
        m = u.GetNetname()
        if u.GetLayer() == L4 and m.startswith('ROW') and not m.endswith('DRV'):
            d = dist_ss(seg(t), seg(u))
            if d < 2.38 - 0.01:
                bad[(n, m)] = min(bad[(n, m)], round(d, 2))
report('review: column / SENSE to row lead-in centre distance under 2.38 mm (5-9)', sorted(bad.items()), hard=False)
# 7. guard rings: >= 2 ground vias on each ring
bad = []
for k, (x, y) in K.items():
    n = sum(1 for v in vias if v.GetNetname() == 'GND' and 7.0 <= math.hypot(mm(v.GetPosition().x) - x, mm(v.GetPosition().y) - y) <= 8.5)
    if n < 2:
        bad.append((k, n))
report('two or more ground vias per guard ring (5-10)', bad)
# 8. foreign vias through electrodes / rings
bad = []
for v in vias:
    x, y = mm(v.GetPosition().x), mm(v.GetPosition().y)
    for k, (kx, ky) in K.items():
        r = math.hypot(x - kx, y - ky)
        if r < 8.5 + 0.3 + 0.2:
            n = v.GetNetname()
            row, col = M.key_net()[k]
            if n not in (row, col, 'GND'):
                bad.append((k, n, round(x, 2), round(y, 2)))
            if n == 'GND' and r < 6.6:
                bad.append((k, 'GND via in electrode', round(x, 2), round(y, 2)))
report('no foreign via inside an electrode or ring', bad)
# 9. matrix nets: each key's pads
bad = []
kn = M.key_net()
for k in K:
    f = b.FindFootprintByReference(k)
    nets = {p.GetNumber(): p.GetNetname() for p in f.Pads()}
    if (nets['1'], nets['2'], nets['3']) != (kn[k][0], kn[k][1], 'GND'):
        bad.append((k, nets))
    q = f.GetPosition()
    if abs(mm(q.x) - K[k][0]) > 1e-3 or abs(mm(q.y) - K[k][1]) > 1e-3 or f.GetOrientationDegrees() != 0:
        bad.append((k, 'moved'))
report('52 electrodes on the Rev 0.2 key positions, 0 degrees, nets per design-spec 3', bad if len(K) == 52 else [len(K)])
# 10. MUX inputs
bad = []
for col, (mux, xn) in M.MUX_INPUT.items():
    ref = 'U7' if mux == 'A' else 'U8'
    pin = M.X_PIN[xn]
    net = [p.GetNetname() for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == str(pin)][0]
    if net != f'COL{col}':
        bad.append((col, ref, pin, net))
report('MUX inputs match matrix.MUX_INPUT', bad)
# 11. lengths
L = collections.Counter()
for t in tracks:
    L[t.GetNetname()] += mm(t.GetLength())
print('     SENSE track length %.0f mm (spec 5-13: about 230)' % L['SENSE'])
print('     AMP_IN %.1f mm (5-7: <= 3)   AMP_FB %.1f mm' % (L['AMP_IN'], L['AMP_FB']))
print('     columns: ' + ' '.join('%s=%.0f' % (f'c{i}', L[f'COL{i}']) for i in range(1, 15)))
# 12. outline unchanged against Rev 0.2
import subprocess
base = '/tmp/tc52_base_check.kicad_pcb'
open(base, 'w').write(subprocess.check_output(['git', '-C', HERE, 'show', 'c672d06:pcb/ts52k.kicad_pcb'], text=True))
bb = pcbnew.LoadBoard(base)
def edges(x):
    return sorted((d.ShowShape(), d.GetStart().x, d.GetStart().y, d.GetEnd().x, d.GetEnd().y) for d in x.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts)
report('Edge.Cuts identical to Rev 0.2', [] if edges(b) == edges(bb) else ['outline differs'])
basek = {f.GetReference(): (round(mm(f.GetPosition().x), 3), round(mm(f.GetPosition().y), 3)) for f in bb.GetFootprints() if f.GetReference().startswith('MX')}
bad = [(k, basek.get(k), K[k]) for k in K if k not in basek or abs(basek[k][0] - K[k][0]) > 2e-3 or abs(basek[k][1] - K[k][1]) > 2e-3]
report('key centres identical to Rev 0.2 (52 of %d MX footprints there)' % len(basek), bad)
for ref in ('SW2', 'J1', 'J2', 'SW1'):
    f1, f2 = b.FindFootprintByReference(ref), bb.FindFootprintByReference(ref)
    if f1.GetPosition() != f2.GetPosition():
        print('     note:', ref, 'moved from Rev 0.2')
sys.exit(1 if fail else 0)
