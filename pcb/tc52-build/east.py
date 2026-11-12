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
      'INHB': 35.175, 'PA': 35.92}
XQ = {'+3V3': 36.0, 'ENC_B': 35.7, 'ENC_A': 35.4, 'ENC_SW': 35.1, 'S3B': 34.8, 'S2B': 34.5, 'S1B': 34.2, 'PB': 33.85,
      'INHB': 33.5, 'PA': 33.15, 'S3A': 32.65, 'S2A': 32.35, 'S1A': 32.05, 'INHA': 31.75}
PB_VIA = (30.9, 30.9 + 34.432)
PA_VIA = (31.25, 31.25 + 35.92)
V0 = (28.1, 73.6)
# after the gate
POST = {'ENC_B': 74.3, 'ENC_A': 74.6, 'ENC_SW': 74.9, 'S3B': 75.2, 'S2B': 75.5, 'S1B': 75.8, 'PB': 76.1, 'INHB': 76.4,
        'PA': 76.7, 'S3A': 77.0, 'S2A': 77.3, 'S1A': 77.6, 'INHA': 77.9}
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
    va, vb = (34.2, 64.95), (40.55, 63.3)
    bd.via('+3V3', *va); bd.via('+3V3', *vb)
    T('+3V3', [va, (34.2, 65.9), (38.5, 65.9), (40.55, 63.85), vb], 0.25, L3)
    T('+3V3', [(39.86, 63.29), vb], 0.25)
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
        c2 = c1 - 0.42
        ys = 68.0 + 0.3 * j
        x0 = max(p[1] - c1, p[0] + 0.3)
        T(n, [p, (x0, p[1]), (x0, x0 + c1)] if x0 > p[1] - c1 + 1e-6 else [p, (x0, p[1])])
        T(n, [(x0, x0 + c1), (ys - c1, ys), (ys - c2, ys), (XQ[n], XQ[n] + c2), (XQ[n], XQ[n] + cg[n]), (xg[n], yg[n]), (gx + 0.9, yg[n])])
    # grounds that lost their pour connection when L1 became electrodes: C15 (pocket between QSPI_SS and the +3V3 feed)
    # and the flash ground pin (under the MX7 electrode, so no via there: L4 track to the via in the U4 belly)
    c15 = bd.pad('C15', 2)
    T('GND', [c15, (30.95, 61.05)], 0.25)
    bd.via('GND', 30.95, 61.05)
    u44 = bd.pad('U4', 4)
    qspi_north(bd)                                   # frees the pocket around the flash ground pin
    T('GND', [u44, (34.3, u44[1]), (35.3, 59.4), (37.0, 61.1), (38.12, 62.91)], 0.25)
    c14 = bd.pad('C14', 2)                           # C14 ground is fenced in by the MUX A lines: own via
    T('GND', [c14, (c14[0], 70.45)], 0.25)
    bd.via('GND', c14[0], 70.45)
    # ---- +3V3M: R26 / C37 south of X2, L3 under the bundle, vias inside the bundle
    place1(bd, 'R26', 30.1, 72.6, 0)
    place1(bd, 'C37', 28.1, 72.6, 0)
    T('+3V3', [(30.8, 71.2), (30.8, 72.2), (30.4, 72.6), bd.pad('R26', 1)], 0.25)
    vj = (29.0, 73.9)                              # +3V3 on to J2 / R4 over L3 (old via sat on the MX8 guard ring)
    T('+3V3', [bd.pad('R26', 1), (30.1, 72.9), (29.3, 73.7), vj], 0.25)
    bd.via('+3V3', *vj)
    T('+3V3', [vj, (28.07, 74.83), (28.07, 78.88)], 0.25, L3)
    T('PA', [bd.pad('R26', 2), bd.pad('C37', 1), V0], 0.25)
    bd.via('+3V3M', *V0)
    c37 = bd.pad('C37', 2)
    T('GND', [c37, (c37[0] - 0.85, c37[1])], 0.25)
    bd.via('GND', c37[0] - 0.85, c37[1])
    bd.via('+3V3M', *PA_VIA)
    bd.via('+3V3M', *PB_VIA)
    T('PA', [V0, (29.3, 72.4), (30.3, 71.4), (30.3, 69.0), (PA_VIA[0], 69.0 - (PA_VIA[0] - 30.3)), PA_VIA, (31.6, PA_VIA[1] - 0.35), (31.6, 66.01), PB_VIA],
      0.2, L3)
    for n, v in (('PA', PA_VIA), ('PB', PB_VIA)):
        ca = 35.90 if n == 'PA' else CA[n]
        T(n, [v, (v[0] + 0.3, v[0] + 0.3 + ca), (XQ[n], XQ[n] + ca), (XQ[n], XQ[n] + cg[n]), (xg[n], yg[n]), (gx + 0.9, yg[n])])
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
        T(n, [end[n], (xn - 0.15, post[n]), (xn, post[n] - 0.15), (xn, yb + 0.3), (xn + 0.3, yb), (xn + 1.0, yb)])
        band[n] = (xn + 1.0, yb)
    # ---- MUX A group: under SW1, through the MX12 gate, down between c3 and c4
    g12 = SV('MX12', 0)[0]
    xdown = {'INHA': 70.4, 'S1A': 70.7, 'S2A': 71.0, 'S3A': 71.3, 'PA': 71.6}
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
    decap(bd, 'C34', a16)
    # MUX A ground pins: 7, 8 (VEE, VSS), 1 (X4, unused), 15 (X2, unused)
    a7, a8 = A[7], A[8]
    vx = a8[0] - 1.9
    T('GND', [a8, (vx + 0.6, a8[1]), (vx, (a7[1] + a8[1]) / 2), (vx + 0.6, a7[1]), a7], 0.25)
    bd.via('GND', vx, (a7[1] + a8[1]) / 2)
    a5 = A[5]
    T('GND', [a5, (bx - 0.3, a5[1] + 0.4)], 0.25); bd.via('GND', bx - 0.3, a5[1] + 0.4)
    T('GND', [a12, (a12[0] + 2.1, a12[1])], 0.25); bd.via('GND', a12[0] + 2.1, a12[1])
    return band


def decap(bd, ref, p16):
    """100n at MUX pin 16: below the pad, ground via further south"""
    place1(bd, ref, p16[0], p16[1] + 1.3, 90)
    p1, p2 = bd.pad(ref, 1), bd.pad(ref, 2)
    if p2[1] < p1[1]:
        f = bd.fp(ref); f.SetOrientationDegrees(270)
        import pcbnew
        q = bd.pad(ref, 1)
        f.SetPosition(pcbnew.VECTOR2I(f.GetPosition().x + pcbnew.FromMM(p16[0] - q[0]), f.GetPosition().y + pcbnew.FromMM(p16[1] + 1.3 - q[1])))
        p1, p2 = bd.pad(ref, 1), bd.pad(ref, 2)
    bd.track('+3V3M', [p16, p1], L4, 0.25)
    bd.track('GND', [p2, (p2[0], p2[1] + 0.95)], L4, 0.25)
    bd.via('GND', p2[0], p2[1] + 0.95)


def band_run(bd, band, Bp, K, SV, DV):
    """upper band -> MUX B (between c10 and c11) and -> encoder SW2"""
    T = lambda name, pts, w=W, layer=L4: bd.track(NET.get(name, name), pts, layer, w)
    # ---- MUX B group: S3B, S2B, S1B, PB, INHB turn south; INHB is the westmost
    c10 = SV('MX42'), SV('MX43'), SV('MX48')
    b6, b9, b10, b11, b16 = (Bp[i] for i in (6, 9, 10, 11, 16))
    bx = (b6[0] + b11[0]) / 2
    grp = ['INHB', 'PB', 'S1B', 'S2B', 'S3B']                       # west -> east
    x1 = c10[1][0] + 2.61                                           # beside the c10 leg MX42 -> MX43 (2 mm from the MX43 via)
    x2 = c10[2][0] + 2.3                                            # beside the leg MX43 -> MX48
    x3 = 211.0                                                      # east of the mounting hole at (209.55, 92.87)
    xv0 = SV('MX82')[0] + 2.2                                       # through the gap between c10 (MX82 leg) and the MX52 row via
    yeast = {'S3B': 103.2, 'S2B': 103.5, 'S1B': 103.8, 'PB': 104.1, 'INHB': 104.4}
    xbelly = {'INHB': bx - 1.1, 'PB': bx - 0.6, 'S1B': bx, 'S2B': bx + 0.4, 'S3B': bx + 0.8}
    for i, n in enumerate(grp):
        p = band[n]
        xa = x1 + P * i
        xb = x2 + P * i
        xc = x3 + P * i
        xv = xv0 + P * i
        ya = c10[1][1] - 0.5 - 0.1243 * i                           # shift x1 -> x2 starts above the MX43 via
        yb = 84.3 - 0.1243 * i                                      # shift x2 -> x3 below the row-2 bus
        yc = 96.7 - 0.1243 * i                                      # SE diagonal, 2 mm clear of the c10 corner above MX82
        pts = [p, (xa - 0.3, p[1]), (xa, p[1] + 0.3), (xa, ya), (xb, ya + xb - xa), (xb, yb), (xc, yb + xc - xb), (xc, yc),
               (xv, yc + xv - xc), (xv, yeast[n]), (xbelly[n], yeast[n])]
        if n == 'INHB':
            pts += [(xbelly[n], b6[1]), b6]
        elif n == 'PB':
            yg = b11[1] + 0.9
            pts += [(xbelly[n], yg), (bx + 1.0, yg + bx + 1.0 - xbelly[n]), (bx + 1.0, b16[1]), b16]
        else:
            pad = {'S1B': b11, 'S2B': b10, 'S3B': b9}[n]
            pts += [(xbelly[n], pad[1]), pad]
        T(n, pts)
    decap(bd, 'C35', b16)
    b7, b8 = Bp[7], Bp[8]
    vx = b8[0] - 1.9
    bd.track('GND', [b8, (vx + 0.6, b8[1]), (vx, (b7[1] + b8[1]) / 2), (vx + 0.6, b7[1]), b7], L4, 0.25)
    bd.via('GND', vx, (b7[1] + b8[1]) / 2)
    # ---- encoder: pull-ups R15 (ENC_A, straddles ENC_B) and R16 (ENC_B) next to SW2
    y1 = 49.1
    xr = 287.5
    place1(bd, 'R15', xr, y1, 90); fix_vertical(bd, 'R15', xr, y1)
    place1(bd, 'R16', xr + 1.5, y1 - 0.51, 90); fix_vertical(bd, 'R16', xr + 1.5, y1 - 0.51)
    lane = {'+3V3': y1, 'ENC_B': y1 + 0.51, 'ENC_A': y1 + 1.02}
    for n in ('+3V3', 'ENC_B', 'ENC_A'):
        p = band[n]
        d = p[1] - lane[n]
        T(n, [p, (xr - 3.0 - d, p[1]), (xr - 3.0, lane[n]), (xr, lane[n])])
    T('+3V3', [(xr, y1), (xr + 0.9, y1), bd.pad('R16', 1)])
    c20, c19 = bd.pad('C20', 2), bd.pad('C19', 1)
    T('ENC_B', [(xr, lane['ENC_B']), (c20[0] - 0.8, lane['ENC_B']), c20])
    T('ENC_A', [(xr, lane['ENC_A']), (291.4, lane['ENC_A']), (292.38, 51.1), (296.6, 51.1), (296.6, c19[1] + 0.3), (296.9, c19[1]), c19])
    c20g = bd.pad('C20', 1); pc = pads(bd, 'SW2', 'C')[0]
    bd.track('GND', [c20g, (294.3, c20g[1]), (pc[0], 49.4), pc], L4, 0.3)
    p = band['ENC_SW']
    s1 = [q for q in pads(bd, 'SW2', 'S1')][0]
    T('ENC_SW', [p, (xr + 0.2, p[1]), (xr + 0.5, p[1] + 0.3), (xr + 0.5, s1[1] - 1.8), (xr + 2.3, s1[1]), s1])


def fix_vertical(bd, ref, x, y):
    """vertical 2-pad part: pad 1 at (x, y), pad 2 below"""
    import pcbnew
    f = bd.fp(ref)
    for r in (90, 270):
        f.SetOrientationDegrees(r)
        p1, p2 = bd.pad(ref, 1), bd.pad(ref, 2)
        if p2[1] > p1[1]:
            break
    p1 = bd.pad(ref, 1)
    f.SetPosition(pcbnew.VECTOR2I(f.GetPosition().x + pcbnew.FromMM(x - p1[0]), f.GetPosition().y + pcbnew.FromMM(y - p1[1])))


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


def qspi_north(bd):
    """Rev 0.2 ran QSPI_SD0 south and east of the flash ground pin (U4 pin 4), whose ground came from a via to the
    front pour. The front is an electrode now (no via possible there), so SD0 / SCLK / SD3 pass north of the pin
    instead and the ground pin leaves to the south-east on L4."""
    import pcbnew
    mm = pcbnew.ToMM
    b = bd.b
    def inside(t, x0, y0, x1, y1):
        return all(x0 <= mm(p.x) <= x1 and y0 <= mm(p.y) <= y1 for p in (t.GetStart(), t.GetEnd()))
    box = {'/rp2040/QSPI_SD0': (30.7, 57.3, 39.9, 59.2), '/rp2040/QSPI_SCLK': (30.9, 57.0, 41.0, 58.1),
           '/rp2040/QSPI_SD3': (31.0, 56.6, 41.35, 57.95)}
    for t in list(b.GetTracks()):
        n = t.GetNetname()
        if n in box and t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == L4 and inside(t, *box[n]):
            b.RemoveNative(t)
    bd.track('/rp2040/QSPI_SD3', [(31.075, 56.7), (40.087, 56.7), (41.296, 57.909)], L4, 0.15)
    bd.track('/rp2040/QSPI_SCLK', [(30.925, 57.075), (39.967, 57.075), (40.946, 58.054)], L4, 0.15)
    bd.track('/rp2040/QSPI_SD0', [(30.772, 57.425), (38.6, 57.425), (39.4, 58.225), (39.859, 58.403)], L4, 0.15)
