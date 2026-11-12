"""East bundle: U5 east pins -> MX8 gate -> (BOOTSEL to SW1 | encoder + MUX B control north to the upper band |
MUX A control through the MX12 gate down to MUX A).  Reasoning: tc52-build-log.md (2026-11-12, 21:15 session)."""
import math
from brd import L1, L2, L3, L4

W = 0.15
# order north -> south at the MX8 gate, lane y at the gate
GATE = [('BOOT', 71.2), ('+3V3', 71.5), ('ENC_B', 71.8), ('ENC_A', 72.1), ('ENC_SW', 72.4), ('S3B', 72.7), ('S2B', 73.0),
        ('S1B', 73.3), ('PB', 73.825), ('INHB', 74.35), ('PA', 74.875), ('S3A', 75.4), ('S2A', 75.7), ('S1A', 76.0), ('INHA', 76.3)]
NET = {'BOOT': 'Net-(R14-Pad2)', 'PB': '+3V3M', 'PA': '+3V3M'}
XG0 = 38.75
PIN = {'ENC_B': 2, 'ENC_A': 3, 'ENC_SW': 4, 'S3B': 5, 'S2B': 6, 'S1B': 7, 'INHB': 9, 'S3A': 11, 'S2A': 12, 'S1A': 13, 'INHA': 14}
CA = {'ENC_B': 31.57, 'ENC_A': 31.994, 'ENC_SW': 32.418, 'S3B': 32.842, 'S2B': 33.266, 'S1B': 33.69, 'PB': 34.432,
      'INHB': 35.175, 'PA': 35.9}
XQ = {'+3V3': 36.0, 'ENC_B': 35.7, 'ENC_A': 35.4, 'ENC_SW': 35.1, 'S3B': 34.8, 'S2B': 34.5, 'S1B': 34.2, 'PB': 33.85,
      'INHB': 33.5, 'PA': 33.15, 'S3A': 32.65, 'S2A': 32.35, 'S1A': 32.05, 'INHA': 31.75}
PB_VIA = (30.9, 30.9 + 34.432)
PA_VIA = (31.25, 31.25 + 35.9)
V0 = (28.1, 73.6)
# after the gate
POST = {'ENC_B': 74.0, 'ENC_A': 74.3, 'ENC_SW': 74.6, 'S3B': 74.9, 'S2B': 75.2, 'S1B': 75.5, 'PB': 75.8, 'INHB': 76.1,
        'PA': 76.4, 'S3A': 76.7, 'S2A': 77.0, 'S1A': 77.3, 'INHA': 77.6}
NORTH = ['+3V3', 'ENC_B', 'ENC_A', 'ENC_SW', 'S3B', 'S2B', 'S1B', 'PB', 'INHB']
ASET = ['PA', 'S3A', 'S2A', 'S1A', 'INHA']
XN0 = 46.42          # x of the westmost north-going line
BAND0 = 49.8         # y of the northmost band lane
P = 0.3


def run(bd, A, Bp, K, SV, DV):
    T = lambda name, pts, w=W, layer=L4: bd.track(NET.get(name, name), pts, layer, w)
    yg = dict(GATE)
    xg = {n: XG0 - 0.4142 * (y - 71.2) for n, y in GATE}
    cg = {n: yg[n] - xg[n] for n in yg}
    gx = SV('MX8', 0)[0]
    end = {}                                      # last point of each line east of the gate (x = gx + 0.9)
    # ---- re-laid +3V3 feed C15 -> via (32.75, 63.14) -> R2
    T('+3V3', [(29.22, 60.62), (29.8, 61.2), (30.13, 61.2), (32.6, 63.67), bd.pad('R2', 1)], 0.25)
    # +3V3 for the flash (U4 pin 8, C2): L3 jumper under the bundle; both vias clear of the guard rings
    va, vb = (34.1, 64.75), (40.0, 64.4)
    bd.via('+3V3', *va); bd.via('+3V3', *vb)
    T('+3V3', [va, (34.1, 65.9), (38.5, 65.9), vb], 0.25, L3)
    T('+3V3', [(39.35, 63.8), vb], 0.25)
    # ---- BOOTSEL and the +3V3 line for the encoder pull-ups
    r14 = bd.pad('R14', 2)
    T('BOOT', [r14, (r14[0], r14[0] + cg['BOOT']), (xg['BOOT'], yg['BOOT']), (gx + 0.9, yg['BOOT'])])
    r2 = bd.pad('R2', 1)
    T('+3V3', [r2, (r2[0], 64.4), va, (XQ['+3V3'], XQ['+3V3'] + va[1] - va[0]), (XQ['+3V3'], XQ['+3V3'] + cg['+3V3']),
               (xg['+3V3'], yg['+3V3']), (gx + 0.9, yg['+3V3'])])
    # ---- U5 pins 2..9
    for n in ('ENC_B', 'ENC_A', 'ENC_SW', 'S3B', 'S2B', 'S1B', 'INHB'):
        p = bd.pad('U5', PIN[n])
        T(n, [p, (p[1] - CA[n], p[1]), (XQ[n], XQ[n] + CA[n]), (XQ[n], XQ[n] + cg[n]), (xg[n], yg[n]), (gx + 0.9, yg[n])])
    # ---- U5 pins 11..14 (round C16, then C14)
    for j, n in enumerate(('S3A', 'S2A', 'S1A', 'INHA')):
        p = bd.pad('U5', PIN[n])
        c1 = 36.76 + 0.4243 * j
        c2 = c1 - 0.43
        ys = 68.0 + 0.3 * j
        x0 = max(p[1] - c1, p[0] + 0.3)
        T(n, [p, (x0, p[1]), (x0, x0 + c1)] if x0 > p[1] - c1 + 1e-6 else [p, (x0, p[1])])
        T(n, [(x0, x0 + c1), (ys - c1, ys), (ys - c2, ys), (XQ[n], XQ[n] + c2), (XQ[n], XQ[n] + cg[n]), (xg[n], yg[n]), (gx + 0.9, yg[n])])
    # ---- +3V3M: R26 / C37 south of X2, L3 under the bundle, vias inside the bundle
    place1(bd, 'R26', 30.1, 72.6, 0)
    place1(bd, 'C37', 28.1, 72.6, 0)
    T('+3V3', [(30.8, 71.2), (30.8, 72.2), (30.4, 72.6), bd.pad('R26', 1)], 0.25)
    vj = (29.0, 73.9)                              # +3V3 on to J2 / R4 over L3 (old via sat on the MX8 guard ring)
    T('+3V3', [bd.pad('R26', 1), (30.1, 72.9), (29.3, 73.7), vj], 0.25)
    bd.via('+3V3', *vj)
    T('+3V3', [vj, (28.1, 74.8), (28.1, 76.7)], 0.25, L3)
    T('PA', [bd.pad('R26', 2), bd.pad('C37', 1), V0], 0.25)
    bd.via('+3V3M', *V0)
    c37 = bd.pad('C37', 2)
    T('GND', [c37, (c37[0] - 0.85, c37[1])], 0.25)
    bd.via('GND', c37[0] - 0.85, c37[1])
    bd.via('+3V3M', *PA_VIA)
    bd.via('+3V3M', *PB_VIA)
    T('PA', [V0, (29.3, 72.4), (PA_VIA[0], 72.4 + 29.3 - PA_VIA[0]), PA_VIA, (31.6, PA_VIA[1] - 0.35), (31.6, 66.01), PB_VIA],
      0.2, L3)
    for n, v in (('PA', PA_VIA), ('PB', PB_VIA)):
        T(n, [v, (XQ[n], XQ[n] + CA[n]), (XQ[n], XQ[n] + cg[n]), (xg[n], yg[n]), (gx + 0.9, yg[n])])
    # ---- after the gate: BOOTSEL to SW1, the rest drops to the post-gate lanes
    sw = [q for q in pads(bd, 'SW1', '2') if q[1] < 76][0]
    T('BOOT', [(gx + 0.9, yg['BOOT']), (sw[0] - (sw[1] - yg['BOOT']), yg['BOOT']), sw])
    names = [n for n, _ in GATE if n != 'BOOT']
    xs = gx + 1.6                                  # INHA starts its 45-degree drop here
    c = yg['INHA'] - xs
    post = dict(POST); post['+3V3'] = POST['ENC_B'] - P
    for n in reversed(names):
        x1 = yg[n] - c
        x2 = x1 + post[n] - yg[n]
        T(n, [(gx + 0.9, yg[n]), (x1, yg[n]), (x2, post[n])])
        end[n] = (x2, post[n])
        c -= 0.4243
    # ---- north group: up between the SW1 pads to the upper band
    band = {}
    for i, n in enumerate(NORTH):
        xn = XN0 + P * i
        yb = BAND0 + P * i
        T(n, [end[n], (xn - 0.3, post[n]), (xn, post[n] - 0.3), (xn, yb + 0.3), (xn + 0.3, yb), (xn + 1.0, yb)])
        band[n] = (xn + 1.0, yb)
    # ---- MUX A group: under SW1, through the MX12 gate, down between c3 and c4
    g12 = SV('MX12', 0)[0]
    xdown = {'INHA': 70.1, 'S1A': 70.4, 'S2A': 70.7, 'S3A': 71.0, 'PA': 71.3}
    for j, n in enumerate(ASET):
        y1 = post[n]; y2 = 74.3 + P * j
        xa = 50.5 + 0.1243 * j
        k = 4 - j                                   # INHA turns first
        xt = g12 + 0.45 + 0.1243 * k                # start of the SE diagonal after the gate
        xd = xdown[n]
        T(n, [end[n], (xa, y1), (xa + (y1 - y2), y2), (xt, y2), (xd, y2 + xd - xt)])
        end[n] = (xd, y2 + xd - xt)
    a6, a9, a10, a11, a12, a16 = (A[i] for i in (6, 9, 10, 11, 12, 16))
    bx = (a6[0] + a11[0]) / 2                       # MUX A centre x
    tgt = {'INHA': (bx - 1.1, a6), 'S1A': (bx, a11), 'S2A': (bx + 0.4, a10), 'S3A': (bx + 0.8, a9)}
    for j, n in enumerate(('INHA', 'S1A', 'S2A', 'S3A')):
        x2, pad = tgt[n]
        y0 = 95.0 - 0.1243 * j
        T(n, [end[n], (end[n][0], y0), (x2, y0 + x2 - end[n][0]), (x2, pad[1]), pad])
    # +3V3M: outside the east pad column, in between pads 11 and 12, down the belly to pin 16
    xo = a11[0] + 1.4
    ygap = (a11[1] + a12[1]) / 2
    y0 = 95.0 - 0.1243 * 4
    T('PA', [end['PA'], (end['PA'][0], y0), (xo, y0 + xo - end['PA'][0]), (xo, ygap), (bx + 1.0, ygap), (bx + 1.0, a16[1]), a16])
    place1(bd, 'C34', xo, a9[1] - 3.5, 0, east=True)
    c34 = bd.pad('C34', 2)
    T('GND', [c34, (c34[0] + 0.9, c34[1])], 0.25)
    bd.via('GND', c34[0] + 0.9, c34[1])
    # MUX A ground pins: 7, 8 (VEE, VSS), 1 (X4, unused), 15 (X2, unused)
    a7, a8 = A[7], A[8]
    vx = a8[0] - 1.9
    T('GND', [a8, (vx + 0.6, a8[1]), (vx, (a7[1] + a8[1]) / 2), (vx + 0.6, a7[1]), a7], 0.25)
    bd.via('GND', vx, (a7[1] + a8[1]) / 2)
    a5 = A[5]
    T('GND', [a5, (bx - 0.3, a5[1] + 0.4)], 0.25); bd.via('GND', bx - 0.3, a5[1] + 0.4)
    T('GND', [a12, (a12[0] + 2.1, a12[1])], 0.25); bd.via('GND', a12[0] + 2.1, a12[1])
    return band


def pads(bd, ref, num):
    import pcbnew
    return [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in bd.fp(ref).Pads() if p.GetNumber() == str(num)]


def place1(bd, ref, x, y, rot, east=False):
    """place a 2-pad part on the back so that pad 1 is at (x, y); pad 2 lies west (default) or east / along rot"""
    f = bd.place(ref, x, y, rot)
    f.Reference().SetVisible(False)
    for r in (rot, rot + 180):
        f.SetOrientationDegrees(r)
        p1, p2 = bd.pad(ref, 1), bd.pad(ref, 2)
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        ok = (dx > 0) == east if abs(dx) > abs(dy) else True
        if ok:
            break
    import pcbnew
    p1 = bd.pad(ref, 1)
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(2 * x - p1[0]), pcbnew.FromMM(2 * y - p1[1])))
    return f
