#!/usr/bin/env python3
"""check_spec.py : checks from design-spec.md (and the wireless additions, docs/tc52w-build-log.md) that the KiCad DRC
does not cover (or that the rule areas exempt).

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
# the wireless island: under / beside the module, the hops under the bundle, the VBUS jumper at the USB connector
ISL = ((0.5, 74.5, 10.0, 100.0), (20.5, 68.0, 29.5, 80.0), (22.0, 48.0, 25.8, 49.5))
isl = lambda x, y: any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in ISL)
report('L3 tracks only inside the digital island', [(t.GetNetname(), seg(t)) for t in tracks if t.GetLayer() == L3 and not (isl(*seg(t)[:2]) and isl(*seg(t)[2:]))])
# 2. L1: only rows, electrodes, ground
report('L1 tracks are row buses only (5-8)', [(t.GetNetname(), seg(t)) for t in tracks if t.GetLayer() == L1 and not t.GetNetname().startswith('ROW')])
# 3. HIZ widths
hiz = lambda n: n.startswith('COL') or n in ('SENSE', 'AMP_IN', 'AMP_FB')
report('HIZ track width 0.2 mm (5-4)', [(t.GetNetname(), mm(t.GetWidth())) for t in tracks if hiz(t.GetNetname()) and abs(mm(t.GetWidth()) - 0.2) > 1e-6])
# 4. L3 above HIZ tracks is ground (no L3 track within 1 mm of a COL/SENSE track)
l3 = [t for t in tracks if t.GetLayer() == L3]
HL = [(0.8, 93.0, 5.0, 98.6)]
bad = []
for t in tracks:
    if t.GetLayer() == L4 and (t.GetNetname().startswith('COL') or t.GetNetname() == 'SENSE'):
        for u in l3:
            if all(any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in HL) for x, y in (seg(u)[:2], seg(u)[2:])):
                continue                    # SWD via stubs beside the SENSE pad of the module (inside HIZ_LOCAL; static in use)
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
# 11b. screw heads (M2, on L4): no L4 copper within 2.6 mm of the hole centre; around H1 only PLATE
import finish as FIN
bad = []
l4z = [z for z in b.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(L4)]
for f in b.GetFootprints():
    r = f.GetReference()
    if not (r[0] == 'H' and r[1:].isdigit()):
        continue
    hx, hy = mm(f.GetPosition().x), mm(f.GetPosition().y)
    for t in b.GetTracks():
        if r == 'H1' and t.GetNetname() == 'PLATE':
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            d = math.hypot(mm(t.GetPosition().x) - hx, mm(t.GetPosition().y) - hy) - mm(t.GetWidth(L4)) / 2
        elif t.GetLayer() == L4:
            d = FIN.seg_dist(hx, hy, mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y)) - mm(t.GetWidth()) / 2
        else:
            continue
        if d < FIN.HEAD_R - 0.01:
            bad.append((r, t.GetNetname(), round(d, 2)))
    for g in b.GetFootprints():
        if g.GetReference() == r:
            continue
        for p in g.Pads():
            if p.IsOnLayer(L4):
                bbx = p.GetBoundingBox()
                d = math.hypot(mm(p.GetPosition().x) - hx, mm(p.GetPosition().y) - hy) - math.hypot(mm(bbx.GetWidth()), mm(bbx.GetHeight())) / 2
                if d < FIN.HEAD_R - 0.01:
                    bad.append((r, g.GetReference() + '.' + p.GetNumber(), round(d, 2)))
    hit = None
    for z in l4z:
        ps = z.GetFilledPolysList(L4)
        for a in range(0, 360, 5):
            for rr in (1.1, 1.5, 2.0, 2.5):
                if ps.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(hx + rr * math.cos(math.radians(a))), pcbnew.FromMM(hy + rr * math.sin(math.radians(a))))):
                    hit = (r, 'pour ' + z.GetNetname(), rr)
    if hit:
        bad.append(hit)
report('no L4 copper under the screw heads (2.6 mm around H1..H12; H1 carries PLATE only)', bad)
# W1. antenna keep-out: no copper on any layer in the module's own keep-out and in the widened strip (ANT_EDGE)
import module as MOD
u5 = b.FindFootprintByReference('U5')
boxes = [MOD.ANT]
for z in u5.Zones():
    if len(list(z.GetLayerSet().Seq())) >= 4:
        bb_ = z.GetBoundingBox()
        boxes.append((mm(bb_.GetLeft()), mm(bb_.GetTop()), mm(bb_.GetRight()), mm(bb_.GetBottom())))
bad = []
inb = lambda x, y, m=0.0: any(x0 - m < x < x1 + m and y0 - m < y < y1 + m for x0, y0, x1, y1 in boxes)
for t in tracks:
    x1, y1, x2, y2 = seg(t)
    if any(inb(x1 + (x2 - x1) * i / 20, y1 + (y2 - y1) * i / 20, mm(t.GetWidth()) / 2) for i in range(21)):
        bad.append((t.GetNetname(), b.GetLayerName(t.GetLayer()), [round(v, 2) for v in seg(t)]))
for v in vias:
    if inb(mm(v.GetPosition().x), mm(v.GetPosition().y), 0.3):
        bad.append((v.GetNetname(), 'via', round(mm(v.GetPosition().x), 2), round(mm(v.GetPosition().y), 2)))
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    for L in z.GetLayerSet().Seq():
        ps = z.GetFilledPolysList(L)
        for x0, y0, x1, y1 in boxes:
            x = x0 + 0.1
            while x < x1:
                y = y0 + 0.1
                while y < y1:
                    if ps.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))) and -3.57 < x:
                        bad.append(('pour', b.GetLayerName(L), round(x, 1), round(y, 1)))
                    y += 0.3
                x += 0.3
report('antenna keep-out free of copper on all four layers (module zone + ANT_EDGE)', bad[:20])
# W2. L2 is solid under every electrode and ring (only via / hole antipads), and the antenna void is far from them
l2 = [z for z in b.Zones() if z.GetZoneName() == 'L2_GND'][0].GetFilledPolysList(L2)
holes = [(mm(v.GetPosition().x), mm(v.GetPosition().y)) for v in vias if v.GetNetname() != 'GND']
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetDrillSize().x > 0 and p.GetNetname() != 'GND':
            holes.append((mm(p.GetPosition().x), mm(p.GetPosition().y)))
bad = []
for k, (kx, ky) in K.items():
    for i in range(-17, 18):
        for j in range(-17, 18):
            x, y = kx + i * 0.5, ky + j * 0.5
            if math.hypot(x - kx, y - ky) > 8.45 or x < -3.2 or x > 303.2 or y > 121.0:
                continue
            if not l2.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))) and min(math.hypot(x - hx, y - hy) for hx, hy in holes) > 1.0:
                bad.append((k, round(x, 1), round(y, 1)))
report('L2 ground is unbroken under all 52 electrodes and guard rings', bad)
vx = max(bx[2] for bx in boxes); vy0 = min(bx[1] for bx in boxes); vy1 = max(bx[3] for bx in boxes)
dmin = min((math.hypot(max(kx - vx, 0), max(vy0 - ky, 0, ky - vy1)) - 8.45, k) for k, (kx, ky) in K.items())
print('     antenna void (x < %.2f, y %.1f..%.1f): nearest guard ring %s at %.1f mm' % (vx, vy0, vy1, dmin[1], dmin[0]))
hz = [seg(t) for t in tracks if t.GetNetname().startswith('COL') or t.GetNetname() in ('SENSE', 'AMP_IN')]
dv = min(dist_ss(sg, (vx, vy0, vx, vy1)) for sg in hz)
print('     antenna void to the nearest column / SENSE track: %.1f mm' % dv)
# W3. tracks narrower than 0.15 mm exist only as necks at the module's pads
cxm, cym = mm(u5.GetPosition().x), mm(u5.GetPosition().y)
bad = [(t.GetNetname(), mm(t.GetWidth()), [round(v, 2) for v in seg(t)]) for t in tracks
       if mm(t.GetWidth()) < 0.149 and not all(abs(x - cxm) < 8.5 and abs(y - cym) < 6.2 for x, y in (seg(t)[:2], seg(t)[2:]))]
report('tracks under 0.15 mm only as necks between the module pads', bad)
# W4. fast lines stay off the "low frequency I/O only" pads (3..14, 50, 52, 54, 56..61); PURGE (SENSE) is exempt by design
LF = set(range(3, 15)) | {50, 52, 54} | set(range(56, 62))
bad = [(p.GetNumber(), p.GetNetname()) for p in u5.Pads() if p.GetNumber().isdigit() and int(p.GetNumber()) in LF and p.GetNetname().startswith('ROW')]
report('row strobes are not on low-frequency-only module pads', bad)
print('     low-frequency-only pads in use:', ' '.join(f'{p.GetNumber()}={p.GetNetname()}' for p in sorted(u5.Pads(), key=lambda p: int(p.GetNumber())) if int(p.GetNumber()) in LF and p.GetNetname() and not p.GetNetname().startswith('unconnected')))
# 12. outline and key positions unchanged against Rev 0.2 and against the wired TC52

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
wired = '/tmp/tc52_wired_check.kicad_pcb'
open(wired, 'w').write(subprocess.check_output(['git', '-C', HERE, 'show', '733bf7d:pcb/ts52k.kicad_pcb'], text=True))
bw = pcbnew.LoadBoard(wired)
report('Edge.Cuts identical to the wired TC52 (733bf7d)', [] if edges(b) == edges(bw) else ['outline differs'])
wk = {f.GetReference(): (f.GetPosition().x, f.GetPosition().y, f.GetOrientationDegrees()) for f in bw.GetFootprints() if f.GetReference().startswith(('MX', 'H'))}
nk = {f.GetReference(): (f.GetPosition().x, f.GetPosition().y, f.GetOrientationDegrees()) for f in b.GetFootprints() if f.GetReference().startswith(('MX', 'H'))}
report('52 key centres and 12 fixing holes identical to the wired TC52', [k for k in wk if wk[k] != nk.get(k)] + [k for k in nk if k not in wk])
for ref in ('SW2', 'J1', 'J2', 'SW1'):
    f1, f2 = b.FindFootprintByReference(ref), bw.FindFootprintByReference(ref)
    if f1.GetPosition() != f2.GetPosition():
        print('     note:', ref, 'moved from the wired TC52: (%.2f, %.2f) -> (%.2f, %.2f)' % (mm(f2.GetPosition().x), mm(f2.GetPosition().y), mm(f1.GetPosition().x), mm(f1.GetPosition().y)))
sys.exit(1 if fail else 0)
