"""West side of the island: row drive resistors and feeds, PURGE/ADC/+3V3 through the MX3 gate, AFE."""
import pcbnew
from brd import L1, L2, L3, L4
from east import place1, fix_vertical, pads
import layout


def at(bd, ref, n, x, y, rot):
    """place ref (back side) with rotation rot so that pad n is at (x, y)"""
    f = bd.place(ref, x, y, rot)
    f.Reference().SetVisible(False)
    p = bd.pad(ref, n)
    f.SetPosition(pcbnew.VECTOR2I(f.GetPosition().x + pcbnew.FromMM(x - p[0]), f.GetPosition().y + pcbnew.FromMM(y - p[1])))
    return f


def two(bd, ref, x, y, d):
    """2-pad part with pad 1 at (x, y) and pad 2 in direction d ('n','s','e','w')"""
    want = {'e': (1, 0), 'w': (-1, 0), 's': (0, 1), 'n': (0, -1)}[d]
    for rot in (0, 90, 180, 270):
        at(bd, ref, 1, x, y, rot)
        p1, p2 = bd.pad(ref, 1), bd.pad(ref, 2)
        if (p2[0] - p1[0]) * want[0] + (p2[1] - p1[1]) * want[1] > 0.3:
            return bd.pad(ref, 1), bd.pad(ref, 2)
    raise RuntimeError(ref)


def run(bd, K, SV, DV):
    T = lambda net, pts, w=0.2, layer=L4: bd.track(net, pts, layer, w)
    F = layout.ROW_FEED
    pin = {n: bd.pad('U5', p) for n, p in (('ROW1', 32), ('ROW2', 31), ('ROW3', 30), ('ROW4', 29))}
    # ---- ROW1: resistor west of the pins; bus via below it, joined to the bus by a short L1 spur
    r1, r2 = two(bd, 'R31', 19.75, 65.85, 'w')
    p = pin['ROW1']
    T('ROW1_DRV', [p, (20.75, p[1]), (20.3, r1[1]), r1], 0.15)
    v1 = (F[1][0], 66.75)
    T('ROW1', [r2, v1], 0.25)
    bd.via('ROW1', *v1)
    T('ROW1', [F[1], v1], 0.25, L1)
    # ---- ROW2..4: standing resistors, outputs run south to the buses
    for n, ref, x, y, xs in (('ROW2', 'R32', F[2][0], 68.3, 20.8), ('ROW3', 'R33', F[3][0], 71.5, 20.84)):
        r1, r2 = two(bd, ref, x, y, 's')
        p = pin[n]
        T(n + '_DRV', [p, (xs, p[1]), (x, p[1] + xs - x), r1], 0.15)
        f = F[int(n[3])]
        T(n, [r2, f], 0.25)
        bd.via(n, *f)
    r1, r2 = two(bd, 'R34', 21.2, 69.6, 's')
    p = pin['ROW4']
    T('ROW4_DRV', [p, (20.95, p[1]), (21.2, p[1] + 0.25), r1], 0.15)
    T('ROW4', [r2, (21.2, 100.0), (F[4][0], 100.2), F[4]], 0.25)
    bd.via('ROW4', *F[4])
    # ---- PURGE (SENSE, pin 40), ADC (pin 38), +3V3 (from C17) -> MX3 gate
    g = SV('MX3', 0)[0]
    ps, pa = bd.pad('U5', 40), bd.pad('U5', 38)
    c17, c17g = two(bd, 'C17', 19.98, 64.94, 'n')       # turned upright: its ground via goes north-west, +3V3 leaves west
    T('GND', [c17g, (18.9, c17g[1]), (18.6, 63.6)], 0.25)
    bd.via('GND', 18.6, 63.6)
    LS, LA, LV = 70.5, 72.7, 73.2          # lanes through the gate
    XS, XA, XV = 15.45, 17.63, 18.0
    T('SENSE', [ps, (XS + 0.4, ps[1]), (XS, ps[1] + 0.4), (XS, LS - 0.6), (XS - 0.6, LS), (-1.4, LS), (-2.0, LS + 0.6), (-2.0, 116.4)])
    T('ADC', [pa, (XA + 0.3, pa[1]), (XA, pa[1] + 0.3), (XA, LA - 0.8), (XA - 0.8, LA), (9.5, LA)], 0.15)
    T('+3V3', [c17, (XV + 0.3, c17[1]), (XV, c17[1] + 0.3), (XV, LV - 0.6), (XV - 0.6, LV), (12.5, LV), (9.2, 76.5), (6.5, 79.2), (3.2, 79.2)], 0.2)
    # ---- AFE (west of the gate). U6 on the back: north row = pins 1, 2, 3 (west -> east), south row = 5 (west), 4 (east)
    cx, cy = 3.1, 74.0
    for rot in (0, 90, 180, 270):
        f = bd.place('U6', cx, cy, rot)
        q = {n: bd.pad('U6', n) for n in range(1, 6)}
        if q[1][1] < cy and q[3][1] < cy and q[1][0] < q[3][0] and q[4][1] > cy:
            break
    else:
        raise RuntimeError('U6 orientation')
    f.Reference().SetVisible(False)
    p1, p2, p3, p4, p5 = (q[n] for n in range(1, 6))
    # SENSE -> R22 -> +IN (0.3 mm of AMP_IN)
    a, b = two(bd, 'R22', p3[0], LS, 's')
    T('AMP_IN', [b, p3], 0.2)
    # reference capacitors hang on the SENSE line; AGND island (C30, C31, V-) with a single via
    c30a, c30b = two(bd, 'C30', 0.45, LS, 's')
    c31a, c31b = two(bd, 'C31', -1.05, LS, 's')
    T('GND', [c31b, c30b, (0.75, 71.75), (1.95, 71.75), (p2[0], 71.75), p2], 0.3)
    bd.via('GND', 1.95, 71.2)
    T('GND', [(1.95, 71.75), (1.95, 71.2)], 0.3)
    at(bd, 'TP4', 1, -1.05, 74.0, 0)
    T('GND', [c31b, (-1.05, 74.0)], 0.3)
    # output: channel under the body -> east: R23 (to ADC), R21 (feedback) ; test point
    r23a, r23b = two(bd, 'R23', 6.35, cy, 'e')
    r21a, r21b = two(bd, 'R21', 5.35, cy, 's')
    T('AMP_OUT', [p1, (p1[0], cy), r21a, r23a], 0.2)
    T('ADC', [(9.5, LA), (8.2, cy), r23b], 0.15)
    at(bd, 'TP2', 1, 6.9, 76.1, 0)
    T('AMP_OUT', [r23a, (6.35, 74.6), (6.9, 75.15), (6.9, 76.1)], 0.2)
    T('AMP_FB', [r21b, (p4[0], r21b[1]), p4], 0.2)
    a, b = two(bd, 'R20', p4[0], 76.6, 's')
    T('AMP_FB', [p4, a], 0.2)
    T('GND', [b, (b[0], b[1] + 0.85)], 0.3)
    bd.via('GND', b[0], b[1] + 0.85)
    # supply: +3V3 -> R24 -> +3V3A (C32 4.7u, C33 100n) -> V+
    a, b = two(bd, 'R24', 3.2, 79.2, 'w')
    c33a, c33b = two(bd, 'C33', p5[0], 77.0, 'w')
    c32a, c32b = two(bd, 'C32', p5[0], 78.1, 'w')
    T('+3V3A', [b, (p5[0], 79.2), c32a, c33a, p5], 0.25)
    T('GND', [c32b, c33b], 0.25)
    T('GND', [(c33b[0], 77.55), (-0.3, 77.55)], 0.25)
    bd.via('GND', -0.3, 77.55)
    at(bd, 'TP1', 1, -2.0, 82.5, 0)
    # ROW1 test point on the MX2 lead-in
    d = DV('MX2')
    at(bd, 'TP3', 1, d[0] - 1.4, 62.5, 0)
    T('ROW1', [(d[0], 62.5), (d[0] - 1.4, 62.5)], 0.25)
