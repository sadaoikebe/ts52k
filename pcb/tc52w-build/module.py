"""West side of the TC52 wireless board: MDBT50Q module, its supply parts, charger, USB, SWD, AFE, and the
lines that leave the module (bundle through the MX3 gate, supply/USB through the MX4 gate, rows on L1).
Reasoning and the floor plan: docs/tc52w-build-log.md."""
import math
import os
import subprocess
import pcbnew
from brd import L1, L2, L3, L4, mm, MM, V

HERE = os.path.dirname(os.path.abspath(__file__))
WIRED = '733bf7d'                 # finished wired TC52 board: positions of the parts that do not move
U5C = (4.45, 90.0)                # module centre; antenna end at the west board edge
HIZ_LOCAL = []                    # filled by run(): (x0, y0, x1, y1) boxes where SENSE passes its neighbours


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


def centre(bd, ref, x, y, rot):
    f = bd.place(ref, x, y, rot)
    f.Reference().SetVisible(False)
    return f


def pads(bd, ref, num):
    return [(mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in bd.fp(ref).Pads() if p.GetNumber() == str(num)]


def orient(bd, ref, x, y, test):
    """centre ref at (x, y) on the back and turn it until test(pad dict) holds"""
    for rot in (0, 90, 180, 270):
        f = bd.place(ref, x, y, rot)
        q = {}
        for p in f.Pads():
            q.setdefault(p.GetNumber(), (mm(p.GetPosition().x), mm(p.GetPosition().y)))
        if test(q):
            f.Reference().SetVisible(False)
            return q
    raise RuntimeError(ref + ' orientation')


def place(bd, K, SV, DV):
    # ---- parts that stay where the wired TC52 has them (connector, ESD, CC resistors, reset switch, encoder)
    tmp = '/tmp/tc52_wired.kicad_pcb'
    open(tmp, 'w').write(subprocess.check_output(['git', '-C', HERE, 'show', f'{WIRED}:pcb/ts52k.kicad_pcb'], text=True))
    old = pcbnew.LoadBoard(tmp)
    for ref in ('J1', 'R5', 'R6', 'D89', 'D90', 'D91', 'SW1', 'SW2', 'C19', 'C20'):
        o = old.FindFootprintByReference(ref)
        f = bd.fp(ref)
        p = o.GetPosition()
        if o.GetLayer() == L4:
            f.SetPosition(p)
            f.Flip(p, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        else:
            f.SetPosition(p)
        f.SetOrientationDegrees(o.GetOrientationDegrees())
        f.Reference().SetVisible(False)
        # same pad positions as the wired board (the libraries differ in name only for J1 / SW1 / SW2)
        if ref in ('J1', 'SW1', 'SW2', 'C19', 'C20', 'R5', 'R6'):
            a = sorted((pp.GetNumber(), round(mm(pp.GetPosition().x), 2), round(mm(pp.GetPosition().y), 2)) for pp in o.Pads())
            c = sorted((pp.GetNumber(), round(mm(pp.GetPosition().x), 2), round(mm(pp.GetPosition().y), 2)) for pp in f.Pads())
            if a != c:
                print('pad positions differ from the wired board:', ref, [x for x in zip(a, c) if x[0] != x[1]][:4])
    # ---- module: antenna west, pads 1..14 north, 15..33 east, 34..55 south
    cx, cy = U5C
    q = orient(bd, 'U5', cx, cy, lambda q: q['55'][0] < cx - 3 and q['55'][1] > cy + 3 and q['15'][0] > cx + 6 and q['15'][1] < cy - 3)
    return q



# ---------------------------------------------------------------- geometry shared by the stages
def upad(bd, n):
    return bd.pad('U5', n)


GATE_LANES = None


def run(bd, A, Bp, K, SV, DV):
    import east
    global GATE_LANES
    T = lambda net, pts, w=0.15, layer=L4: bd.track(east.NET.get(net, net), pts, layer, w)
    cx, cy = U5C
    yg = dict(east.GATE)
    # =================================================================== north side: bundle -> MX3 gate -> MX8 gate
    # pad -> lane.  Inner-row pads (5, 7, 9, 11) leave between the outer pads on 0.1 mm necks.
    nlines = [('ENC_B', 3), ('ENC_A', 4), ('ENC_SW', 5), ('S3B', 6), ('S2B', 7), ('S1B', 8), ('INHB', 9),
             ('S3A', 10), ('S2A', 11), ('S1A', 12), ('INHA', 14)]
    gx8 = SV('MX8', 0)[0]
    XE = gx8 + 0.9
    YN = cy - 5.25 - 0.45                       # necks end here (0.45 mm north of the outer pads)
    flow = [('+3V3', None, 1.0)] + [(n, pad, None) for n, pad in nlines]
    for i, (n, pad, x) in enumerate(flow):
        y = yg[n]
        xe = 10.5 - 0.15 * (len(flow) - 1 - i)  # diagonals end staggered: 0.32 mm between neighbours
        if pad is None:
            p0 = (x, 80.3)                      # +3V3 lane: comes from the bag (via in the lane, see bag()), runs west
        else:                                   # through the gate and ends at the SWD contacts as VTref
            p0 = upad(bd, pad); x = p0[0]
            if p0[1] > cy - 4.2:                # inner row: 0.1 mm neck between the outer pads
                T(n, [p0, (x, YN)], 0.1)
                p0 = (x, YN)
        T(n, [p0, (x, y + xe - x), (xe, y), (23.5 if pad is None else XE, y)])
    ecluster(bd, K, SV, DV)
    bag(bd, K, SV, DV, yg, XE)
    north(bd, K, SV, DV)
    south(bd, K, SV, DV)
    return east.after_gate(bd, A, Bp, K, SV, DV)


# lanes through the MX4 gate (y), north -> south
GL = {'+3V3': 91.45, 'VDDH': 92.4, 'MCU_VBUS': 93.05, 'GND': 93.65, 'D-': 94.15, 'D+': 94.5}
GW = {'+3V3': 0.3, 'VDDH': 0.4, 'MCU_VBUS': 0.3, 'GND': 0.3, 'D-': 0.2, 'D+': 0.2}
XB = 22.0          # the lanes are laid up to here (just east of the gate); bag() continues


def ecluster(bd, K, SV, DV):
    """crystal, REG0 inductor and the decoupling at the module's east end; six lanes on through the MX4 gate"""
    T = lambda net, pts, w=0.15, layer=L4: bd.track(net, pts, layer, w)
    P = lambda n: upad(bd, n)
    cx, cy = U5C
    # ---- 32.768 kHz crystal + load capacitors (north-east corner, clear of column c1 by > 2.5 mm)
    for rot in (0, 180):                                        # XL1 takes the west pad, XL2 the east pad
        centre(bd, 'X1', 14.3, 85.4, rot)
        q = {p.GetNetname(): (mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in bd.fp('X1').Pads()}
        if q['XL1'][0] < q['XL2'][0]:
            break
    xw, xe = q['XL1'], q['XL2']
    p17, p18 = P(17), P(18)
    T('XL1', [p17, (12.55, p17[1]), (xw[0], 86.1), xw])
    T('XL2', [p18, (12.3, 87.5), (14.25, 87.5), (xe[0], 87.0), xe])
    c11a, c11b = two(bd, 'C11', xw[0], 83.85, 'n')
    c12a, c12b = two(bd, 'C12', xe[0], 83.85, 'n')
    T('XL1', [xw, c11a]); T('XL2', [xe, c12a])
    # ground vias: the front side here is ring / row-2 bus, so one via sits in the clear lens south of the bus
    # and one on the MX3 guard ring
    VL, VR = (12.4, 84.3), (13.9, 81.3)
    T('GND', [VL, (12.4, c11b[1]), c11b, c12b, (13.9, 82.0), VR], 0.3)
    bd.via('GND', *VL); bd.via('GND', *VR)
    # ---- REG0 inductor straight on pads 28 (VDD) and 31 (DCCH); VDDH (pad 30) leaves between its pads
    p28, p30, p31, p32, p33 = P(28), P(30), P(31), P(32), P(33)
    l1, l2 = two(bd, 'L1', 13.5, p28[1], 's')
    T('+3V3', [p28, l1], 0.3)
    T('DCCH', [p31, (12.6, p31[1]), l2], 0.3)
    # ---- VDD: 100n x3 on a spur north of the bulk capacitors, 4.7u and 1u on the lane
    YS = 89.08
    T('+3V3', [l1, (13.5, YS), (16.2, YS)], 0.3)
    g = []
    for ref, x in (('C8', 14.2), ('C9', 15.2), ('C10', 16.2)):
        a, b = two(bd, ref, x, YS, 'n')
        g.append(b)
    yl = GL['+3V3']
    T('+3V3', [l1, (14.3, yl), (XB, yl)], 0.3)
    c4a, c4b = two(bd, 'C4', 15.3, p30[1], 'n')           # straddles the VDD lane
    T('VDDH', [p30, (14.4, p30[1])], 0.2)
    T('VDDH', [(14.4, p30[1]), c4a, (XB, GL['VDDH'])], 0.4)
    c6a, c6b = two(bd, 'C6', 17.45, yl, 'n')
    c7a, c7b = two(bd, 'C7', 19.0, yl, 'n')
    # ground of the cluster: one bar north of the spur, two vias on the MX4 guard ring, and the module's pad 15
    yb = g[0][1]
    T('GND', [g[0], g[2], (17.9, yb), (c7b[0], c7b[1] - 0.7), c7b], 0.4)
    T('GND', [c4b, (c4b[0] + 0.4, 90.25), (c6b[0], 90.25), c6b, c7b], 0.4)
    for v in ((16.0, 85.15), (17.0, 85.13)):
        bd.via('GND', *v)
    T('GND', [(16.0, 85.15), (17.0, 85.13)], 0.4)
    T('GND', [(16.35, 85.14), (16.35, yb)], 0.4)
    p15 = P(15)
    T('GND', [p15, (12.4, p15[1]), VL], 0.3)
    # ---- VBUS (pad 32): 4.7u, ground lane starts at pad 33
    yv = p32[1]
    c5a, c5b = two(bd, 'C5', 15.3, yv, 's')
    T('MCU_VBUS', [p32, c5a, (16.6, yv), (16.6 + yv - GL['MCU_VBUS'], GL['MCU_VBUS']), (XB, GL['MCU_VBUS'])], 0.3)
    T('GND', [p33, (14.2, p33[1]), (14.95, c5b[1]), c5b, (16.0, c5b[1]), (16.0 + c5b[1] - GL['GND'], GL['GND']), (XB, GL['GND'])], 0.3)
    # ---- USB pair: round the corner under C5, up into the gate
    p34, p35 = P(34), P(35)
    for n, p, y0, x0 in (('D-', p34, 96.45, 16.2), ('D+', p35, 96.8, 16.4)):
        T(n, [p, (p[0], y0 - 0.3), (p[0] + 0.3, y0), (x0, y0), (x0 + y0 - GL[n], GL[n]), (XB, GL[n])], 0.2)
HOP = {'VDDH': (26.0, 79.3, 69.3), 'MCU_VBUS': (26.9, 78.6, 68.6), 'D-': (27.8, 79.3, 69.3), 'D+': (28.7, 78.6, 68.6)}


def copy_usb(bd):
    """J1 break-out (CC, D+/D-, VBUS links with their L3 jumper) exactly as on the wired TC52 board"""
    old = pcbnew.LoadBoard('/tmp/tc52_wired.kicad_pcb')
    ren = {'Net-(J1-CC1)': 'CC1', 'Net-(J1-CC2)': 'CC2', 'D+': 'D+', 'D-': 'D-', '+5V': 'USB_VBUS', 'GND': 'GND',
           'ENC_A': 'ENC_A', 'ENC_B': 'ENC_B'}
    for t in old.GetTracks():
        n = t.GetNetname()
        if n not in ren:
            continue
        s_, e = t.GetStart(), t.GetEnd()
        xs = (mm(s_.x), mm(e.x)); ys = (mm(s_.y), mm(e.y))
        if n.startswith('ENC'):                       # the two stubs from the encoder pins to C19 / C20
            if not (t.Type() != pcbnew.PCB_VIA_T and abs(xs[0] - xs[1]) < 0.02 and min(xs) > 292.5 and max(ys) < 49.5):
                continue
        elif n == 'GND':                              # shield / ground pins of the connector
            if not (max(ys) < 52.0 and 18.5 < min(xs) and max(xs) < 29.2):
                continue
            if t.Type() != pcbnew.PCB_VIA_T and max(ys) > 49.2:
                continue
            if abs(xs[0] - 20.03) < 0.05 and abs(ys[0] - 51.54) < 0.05:
                continue                              # belonged to the LDO
        elif max(ys) > 56 or not (14 < xs[0] < 34):
            continue
        if n == '+5V' and min(xs) < 21.3:
            continue                                  # feed to the LDO, which is gone
        if t.Type() == pcbnew.PCB_VIA_T:
            bd.via(ren[n], xs[0], ys[0], mm(t.GetWidth(L1)), mm(t.GetDrill()))
        else:
            bd.track(ren[n], [(xs[0], ys[0]), (xs[1], ys[1])], t.GetLayer(), mm(t.GetWidth()))


def bag(bd, K, SV, DV, yg, XE):
    """between columns c1 and c2: supply and USB lanes from the MX4 gate north to the L3 hops under the bundle,
    charger and battery connector north of the bundle, MUX / pull-up supply into the bundle lanes"""
    T = lambda net, pts, w=0.15, layer=L4: bd.track(net, pts, layer, w)
    # ---- ground lane ends on the MX4 guard ring
    gv = (24.3, GL['GND'] + 0.1)
    T('GND', [(XB, GL['GND']), (24.0, GL['GND']), gv], 0.3)
    bd.via('GND', *gv)
    # ---- USB pair steps south of the ground via, then everything turns north
    T('D-', [(XB, GL['D-']), (22.6, GL['D-']), (22.9, 94.45), (HOP['D-'][0] - 0.6, 94.45)], 0.2)
    T('D+', [(XB, GL['D+']), (22.3, 94.8), (HOP['D+'][0] - 0.6, 94.8)], 0.2)
    T('D-', [(HOP['D-'][0] - 0.6, 94.45), (HOP['D-'][0], 93.85)], 0.2)
    T('D+', [(HOP['D+'][0] - 0.6, 94.8), (HOP['D+'][0], 94.2)], 0.2)
    T('VDDH', [(XB, GL['VDDH']), (HOP['VDDH'][0] - 0.6, GL['VDDH']), (HOP['VDDH'][0], GL['VDDH'] - 0.6)], 0.4)
    T('MCU_VBUS', [(XB, GL['MCU_VBUS']), (HOP['MCU_VBUS'][0] - 0.6, GL['MCU_VBUS']), (HOP['MCU_VBUS'][0], GL['MCU_VBUS'] - 0.6)], 0.3)
    ytop = {'VDDH': GL['VDDH'] - 0.6, 'MCU_VBUS': GL['MCU_VBUS'] - 0.6, 'D-': 93.85, 'D+': 94.2}
    for n, (x, ys, yn) in HOP.items():
        w = GW[n]
        T(n, [(x, ytop[n]), (x, ys)], w)
        bd.via(n, x, ys); bd.via(n, x, yn)
        T(n, [(x, ys), (x, yn)], max(w, 0.2) if n.startswith('D') else w, L3)
    # ---- +3V3 turns north west of the hops: MUX filter R26 / C37, then L3 under the bundle into its lanes
    X3 = 23.0
    T('+3V3', [(XB, GL['+3V3']), (X3 - 0.6, GL['+3V3']), (X3, GL['+3V3'] - 0.6), (X3, 80.6)], 0.3)
    r26a, r26b = two(bd, 'R26', X3, 80.6, 'w')
    c37a, c37b = two(bd, 'C37', r26b[0], 79.6, 'w')
    T('+3V3M', [r26b, c37a], 0.25)
    T('GND', [c37b, (c37b[0] - 0.9, c37b[1])], 0.25)
    bd.via('GND', c37b[0] - 0.9, c37b[1])
    # +3V3 lane (encoder pull-ups): via in the lane, the reset lane above it bulges north
    v3s, v3n = (X3, 78.9), (24.5, 71.27)
    T('+3V3', [(X3, 80.6), v3s], 0.3)
    bd.via('+3V3', *v3s); bd.via('+3V3', *v3n)
    T('+3V3', [v3s, (X3, 77.6), (24.5, 76.1), v3n], 0.25, L3)
    T('+3V3', [(23.5, yg['+3V3']), (24.0, yg['+3V3']), v3n, (25.0, yg['+3V3']), (XE, yg['+3V3'])])
    # MUX supply: one via south of the bundle, L3 to a via in each of the two +3V3M lanes
    vm = (c37a[0], 78.6)
    T('+3V3M', [c37a, vm], 0.25)
    bd.via('+3V3M', *vm)
    va, vb = (22.1, yg['PA']), (21.2, yg['PB'])
    bd.via('+3V3M', *va); bd.via('+3V3M', *vb)
    T('+3V3M', [vm, (22.1, 77.9), va, vb], 0.2, L3)
    T('+3V3M', [va, (XE, yg['PA'])]); T('+3V3M', [vb, (XE, yg['PB'])])
    # ---- north of the bundle: USB connector break-out, charger, battery connector
    copy_usb(bd)
    return X3


def north(bd, K, SV, DV):
    """north of the bundle: charger U9 with its parts, battery FET Q1, battery connector J3; the four lines that
    come up through the L3 hops (VDDH, MCU_VBUS, D-, D+)"""
    T = lambda net, pts, w=0.15, layer=L4: bd.track(net, pts, layer, w)
    ux, uy = 18.6, 56.2
    q = orient(bd, 'U9', ux, uy, lambda q: q['13'][1] < uy - 1 and q['10'][0] < ux - 1)      # IN north, OUT west, BAT east
    P = lambda n: q[str(n)]
    # ---- USB_VBUS: connector -> R4 (to the module) and -> C1 -> IN
    r4a, r4b = two(bd, 'R4', 20.95, 51.7, 's')
    r1a, r1b = two(bd, 'R1', P(16)[0], 53.3, 'n')
    T('USB_VBUS', [(21.37, 48.63), (20.7, 49.3), (20.7, 49.7), (20.4, 50.0), (17.85, 50.0), (17.85, 53.4)], 0.4)
    T('USB_VBUS', [(17.85, 53.4), P(13)], 0.25)
    T('USB_VBUS', [(20.7, 49.7), (20.95, 50.2), r4a], 0.3)
    bd.via('GND', r1b[0], 50.9)
    T('GND', [r1b, (r1b[0], 50.9)], 0.3)
    c1a, c1b = two(bd, 'C1', 17.85, 52.5, 'w')
    # ---- ISET, ILIM, TS resistors
    T('BQ_ISET', [P(16), r1a], 0.2)
    r2a, r2b = two(bd, 'R2', 15.6, 54.2, 'w')
    T('BQ_ILIM', [P(12), (16.5, P(12)[1]), (15.9, 54.85), r2a], 0.2)
    r3a, r3b = two(bd, 'R3', 21.43, 55.0, 'e')
    T('BQ_TS', [P(1), (20.9, P(1)[1]), r3a], 0.2)
    # ---- OUT -> C2 -> VDDH: west of the charger, under the battery connector, east to its hop
    c2a, c2b = two(bd, 'C2', 15.2, 56.2, 's')
    T('VDDH', [P(10), P(11)], 0.25)
    T('VDDH', [(P(10)[0], 56.2), c2a], 0.4)
    hx, _, hn = HOP['VDDH']
    T('VDDH', [c2a, (14.3, 56.2), (14.3, 58.6), (17.55, 61.85), (17.55, 65.7), (18.1, 66.25), (24.9, 66.25), (hx, 67.35), (hx, hn)], 0.4)
    # ---- BAT -> C3, Q1 (source) ; Q1 drain -> J3 pin 1 ; gate to ground
    c3a, c3b = two(bd, 'C3', 21.6, 56.5, 's')
    T('BAT', [P(2), P(3)], 0.25)
    T('BAT', [(P(2)[0], 56.2), (20.9, 56.2), (21.2, 56.5), c3a], 0.4)
    qx, qy = 24.35, 58.0
    qq = orient(bd, 'Q1', qx, qy, lambda q: q['3'][0] > qx and q['2'][1] < qy)                  # S north-west, G south-west, D east
    T('BAT', [c3a, (22.6, 56.5), (qq['2'][0] - 0.3, qq['2'][1] - 0.2), qq['2']], 0.4)
    jx, jy = 19.6, 66.2
    jq = orient(bd, 'J3', jx, jy, lambda q: q['1'][1] < jy and q['1'][0] > jx)                 # pads north, pin 1 east, opening south
    j1 = jq['1']
    T('BAT_CONN', [qq['3'], (qq['3'][0], 60.2), (qq['3'][0] - 1.8, 62.0), (j1[0] + 0.3, 62.0)], 0.4)
    gv = (22.3, 60.3)
    T('GND', [qq['1'], (qq['1'][0] - 0.5, qq['1'][1]), gv], 0.25)
    bd.via('GND', *gv)
    T('GND', [c3b, (21.6, 59.6), gv], 0.3)
    # polarity mark at pin 1 (BAT+), as on the TS52K wireless board
    t = pcbnew.PCB_TEXT(bd.b)
    t.SetText('+')
    t.SetLayer(pcbnew.B_SilkS)
    t.SetPosition(V(j1[0] + 1.25, j1[1] - 0.6))
    t.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
    t.SetTextThickness(MM(0.18))
    t.SetMirrored(True)
    bd.b.Add(t)
    # ---- MCU_VBUS: R4 -> north of R3 -> between Q1 / J3 and the USB pair -> hop
    hx, _, hn = HOP['MCU_VBUS']
    T('MCU_VBUS', [r4b, (21.6, 54.0), (23.5, 54.0), (hx, 54.0 + hx - 23.5), (hx, hn)], 0.3)
    # ---- USB pair: from the connector break-out south-east, then straight down to the hops
    for n, p0 in (('D-', (22.96, 52.67)), ('D+', (23.98, 52.57))):
        hx, _, hn = HOP[n]
        T(n, [p0, (hx, p0[1] + hx - p0[0]), (hx, hn)], 0.2)
    # ---- ground: explicit vias (the front side is guard ring or electrode almost everywhere)
    for n in (5, 6, 8):
        T('GND', [P(n), (P(n)[0], 58.6)], 0.25)
    T('GND', [(P(8)[0], 58.6), (P(5)[0], 58.6)], 0.3)
    T('GND', [P(6), (P(6)[0], 56.9)], 0.25); T('GND', [P(15), (P(15)[0], 55.6)], 0.25); T('GND', [P(4), (19.3, P(4)[1])], 0.25)
    bd.via('GND', 18.6, 59.2)
    T('GND', [(18.6, 58.6), (18.6, 59.2)], 0.3)
    g4 = (23.9, 56.0)
    T('GND', [r3b, g4], 0.25); bd.via('GND', *g4)
    return q


def south(bd, K, SV, DV):
    """south side of the module: row resistors and their vias (rows continue on L1), ADC / SWD / reset on L3 under
    the module, AFE, SWD contacts and reset switch north-west of the module"""
    import layout
    T = lambda net, pts, w=0.15, layer=L4: bd.track(net, pts, layer, w)
    P = lambda n: upad(bd, n)
    cx, cy = U5C
    BUS = layout.BUS
    # ---- rows: pad -> 100R -> via -> L1
    # ROW3 / ROW4 go south to their buses, ROW2 / ROW1 north across the module on L1
    r = {}
    for n, pad, ref, y1 in (('ROW3', 41, 'R33', 96.3), ('ROW4', 44, 'R34', 96.3), ('ROW2', 46, 'R32', 98.7), ('ROW1', 48, 'R31', 96.3)):
        p = P(pad)
        a, b = two(bd, ref, p[0], y1, 's')
        T(n + '_DRV', [p, a])
        v = (p[0], b[1] + 0.95)
        T(n, [b, v], 0.25)
        bd.via(n, *v)
        r[n] = v
    e = layout.ROW_END
    T('ROW3', [r['ROW3'], (r['ROW3'][0], BUS[3]), (e[3][0], BUS[3])], 0.25, L1)
    T('ROW4', [r['ROW4'], (r['ROW4'][0], BUS[4]), (e[4][0], BUS[4])], 0.25, L1)
    T('ROW2', [r['ROW2'], (r['ROW2'][0], BUS[2]), (e[2][0], BUS[2])], 0.25, L1)
    x1 = r['ROW1'][0]
    T('ROW1', [r['ROW1'], (x1, 82.6), (3.0, 82.6 - (x1 - 3.0)), (3.0, BUS[1]), (e[1][0], BUS[1])], 0.25, L1)
    # MX5 lead-in now starts where ROW4 reaches its bus
    # ---- AFE_EN (pad 37) -> R27 -> +3V3A, round the south of the AFE
    p = P(37)
    a, b27 = two(bd, 'R27', p[0], 96.3, 's')
    T('AFE_EN', [p, a])
    # ---- ADC: inner north pad 13 -> via under the module -> L3 -> via south of the module
    p13 = P(13)
    va = (p13[0] - 0.4, p13[1] + 1.15)
    T('ADC', [p13, (p13[0], p13[1] + 0.75), va])
    bd.via('ADC', *va)
    vb = (8.2, 98.8)
    T('ADC', [va, (8.2, va[1] + 0.8), vb], 0.15, L3)
    bd.via('ADC', *vb)
    # ---- reset: inner south pad 40 -> via under the module -> L3 west and north (with SWDIO / SWCLK) to the contacts
    p40 = P(40)
    v40 = (p40[0] - 0.4, p40[1] - 0.95)
    T('nRESET', [p40, (p40[0], p40[1] - 0.55), v40])
    bd.via('nRESET', *v40)
    p51, p53 = P(51), P(53)
    vd, vc = (2.6, 95.75), (1.75, 96.25)
    T('SWDIO', [p51, vd]); bd.via('SWDIO', *vd)
    T('SWCLK', [p53, (p53[0], 95.9), vc]); bd.via('SWCLK', *vc)
    nw = {'SWCLK': (1.4, 76.3), 'SWDIO': (2.0, 77.3), 'nRESET': (2.0, 75.0)}
    T('SWCLK', [vc, (1.45, 95.95), (1.45, 95.0), (1.4, 94.9), nw['SWCLK']], 0.15, L3)
    T('SWDIO', [vd, (1.9, 95.05), (1.9, 77.4), nw['SWDIO']], 0.15, L3)
    T('nRESET', [v40, (v40[0] - 0.4, v40[1] - 0.4), (3.2, v40[1] - 0.4), (2.8, v40[1] - 0.8), (2.8, 75.9), (2.0, 75.1), nw['nRESET']], 0.15, L3)
    for n, v in nw.items():
        bd.via(n, *v)
    # ---- AFE (wired TC52 block, moved south-west of the module).  U6 on the back: north row = pins 1, 2, 3
    ax, ay, LS = 2.2, 102.7, 98.25
    for rot in (0, 90, 180, 270):
        f = bd.place('U6', ax, ay, rot)
        q = {n: bd.pad('U6', n) for n in range(1, 6)}
        if q[1][1] < ay and q[3][1] < ay and q[1][0] < q[3][0] and q[4][1] > ay:
            break
    else:
        raise RuntimeError('U6 orientation')
    f.Reference().SetVisible(False)
    p1, p2, p3, p4, p5 = (q[n] for n in range(1, 6))
    XT = -2.9                                    # SENSE trunk down the west edge
    p50 = P(50)
    T('SENSE', [p50, (p3[0] + 0.1, p50[1] + 0.4), (p3[0] + 0.1, 96.3), (p3[0], 96.5), (p3[0], LS)], 0.2)
    T('SENSE', [(p3[0], LS), (XT + 0.6, LS), (XT, LS + 0.6), (XT, 114.6), (-2.0, 115.5), (-2.0, 116.4)], 0.2)
    a, b = two(bd, 'R22', p3[0], LS, 's')
    T('AMP_IN', [b, p3], 0.2)
    c13a, c13b = two(bd, 'C13', p3[0], LS + 1.9, 'w')            # between the + input riser and the V- riser
    c30a, c30b = two(bd, 'C30', ax - 2.65, LS, 's')
    c31a, c31b = two(bd, 'C31', ax - 4.15, LS, 's')
    yg_ = LS + 1.25
    T('GND', [c31b, c30b, (ax - 2.35, yg_), (p2[0], yg_), p2], 0.3)
    ag = (ax - 1.15, yg_ - 0.55)
    bd.via('GND', *ag)
    T('GND', [(ag[0], yg_), ag], 0.3)
    at(bd, 'TP4', 1, ax - 4.15, ay + 1.9, 0)
    T('GND', [c31b, (ax - 4.15, ay + 1.9)], 0.3)
    r23a, r23b = two(bd, 'R23', ax + 3.25, ay, 'e')
    r21a, r21b = two(bd, 'R21', ax + 2.25, ay, 's')
    T('AMP_OUT', [p1, (p1[0], ay), r21a, r23a], 0.2)
    T('ADC', [vb, (8.2, 99.5), (r23b[0], r23b[1] - 1.79), r23b])
    at(bd, 'TP2', 1, ax - 2.85, ay, 0)
    T('AMP_OUT', [(p1[0], ay), (ax - 2.85, ay)], 0.2)
    T('AMP_FB', [r21b, (p4[0], r21b[1]), p4], 0.2)
    a, b = two(bd, 'R20', p4[0], ay + 2.55, 's')
    T('AMP_FB', [p4, a], 0.2)
    gr = (2.6, 106.5)                            # on the MX5 guard ring
    T('GND', [b, gr], 0.3)
    bd.via('GND', *gr)
    c33a, c33b = two(bd, 'C33', p5[0], ay + 3.0, 'w')
    c32a, c32b = two(bd, 'C32', p5[0], ay + 4.1, 'w')
    T('+3V3A', [b27, (b27[0], 106.2), (7.0, 108.2), (p5[0] + 0.6, 108.2), (p5[0], 107.6), c32a, c33a, p5], 0.25)
    T('GND', [c32b, c33b], 0.25)
    gs = (c33b[0] - 1.5, ay + 3.55)
    T('GND', [(c33b[0], ay + 3.55), gs], 0.25)
    bd.via('GND', *gs)
    at(bd, 'TP1', 1, -2.0, 112.6, 0)
    T('SENSE', [(XT, 112.0), (-2.0, 112.6)], 0.2)
    # ROW1 test point on the MX2 lead-in
    dv = DV('MX2')
    at(bd, 'TP3', 1, dv[0] - 1.4, 62.5, 0)
    T('ROW1', [(dv[0], 62.5), (dv[0] - 1.4, 62.5)], 0.25)
    # ---- SWD contacts and reset switch north-west of the module
    centre(bd, 'J2', -0.6, 76.3, 90)
    centre(bd, 'SW1', 0.9, 67.6, 0)
    j = {p.GetNumber(): (mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in bd.fp('J2').Pads() if p.GetNumber()}
    assert j['2'][0] > j['1'][0] and j['1'][1] > j['3'][1] > j['5'][1], j      # east column 2 / 4 / 6, west column 1 / 3 / 5 (south -> north)
    T('SWDIO', [nw['SWDIO'], j['2']])
    T('SWCLK', [nw['SWCLK'], j['4']])
    T('+3V3', [(1.0, 80.3), (0.7, 80.6), (-2.0, 80.6), (-2.3, 80.3), (-2.3, j['1'][1] + 0.3), (-2.0, j['1'][1]), j['1']])
    sw2 = [q for q in pads(bd, 'SW1', '2') if q[0] < 0][0]
    sw1 = [q for q in pads(bd, 'SW1', '1') if q[0] < 0][0]
    T('nRESET', [nw['nRESET'], (2.0, 72.9), (1.4, 72.3), (-2.6, 72.3), (-2.9, 72.6), (-2.9, j['3'][1] - 0.3), (-2.6, j['3'][1]), j['3']])
    T('nRESET', [(1.4, 72.3), (0.9, 71.8), (0.9, 66.5), (0.12, sw2[1]), sw2])
    g1 = (-2.1, 70.7)
    T('GND', [sw1, g1], 0.25); bd.via('GND', *g1)
    g2 = (-2.2, j['5'][1])
    T('GND', [j['5'], g2], 0.25); bd.via('GND', *g2)
    p55 = P(55)
    g3 = (0.85, 95.5)
    T('GND', [p55, g3], 0.25); bd.via('GND', *g3)
    gu = (0.82, 86.9)                            # module ground pads 1 / 2: via under the module, west of the L3 lines
    T('GND', [P(1), (P(1)[0], 86.3), gu], 0.25); T('GND', [P(2), (P(2)[0], 86.0), (1.3, 86.5), gu], 0.25)
    bd.via('GND', *gu)
    for ref, num in (('R20', '2'), ('R3', '2'), ('J1', 'A12'), ('J1', 'B1'), ('J1', 'A1'), ('J1', 'B12'), ('J2', '5'), ('J3', '2'), ('C2', '2'), ('R1', '2'), ('U5', '55')):
        for p in bd.fp(ref).Pads():
            if p.GetNumber() == num:
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    HIZ_LOCAL.append((0.8, 93.0, 5.0, 98.6))


ANT = (-3.6, 81.0, 0.5, 97.0)        # antenna keep-out widened along the board edge (all copper layers)
BODY = (-3.4, 84.0, 12.5, 96.0)     # module body: no stitching vias under it


def fence(bd, K):
    """Ground vias in the digital island (wired TC52 rule 5-11, now: module, supply, bag between c1 and c2).  The
    front side there is electrodes, so a via can only sit on a guard ring (7.35 .. 8.15 mm from a key centre) or
    clear of every ring (>= 9.0 mm)."""
    import finish
    b = bd.b
    X0, Y0, X1, Y1 = -2.6, 46.6, 50.0, 108.0
    segs, pts, gnd = [], [], []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            (gnd if t.GetNetname() == 'GND' else pts).append((mm(p.x), mm(p.y), mm(t.GetWidth(L1)) / 2))
        else:
            s_, e = t.GetStart(), t.GetEnd()
            segs.append((mm(s_.x), mm(s_.y), mm(e.x), mm(e.y), mm(t.GetWidth()) / 2, t.GetNetname()))
    for f in b.GetFootprints():
        if f.GetReference().startswith('MX'):
            continue
        for p in f.Pads():
            q = p.GetPosition()
            bb = p.GetBoundingBox()
            pts.append((mm(q.x), mm(q.y), math.hypot(mm(bb.GetWidth()), mm(bb.GetHeight())) / 2))
    cand = []
    for k, (kx, ky) in K.items():
        if kx < X1 + 9 and ky < Y1 + 9:
            for a in range(0, 360, 15):
                cand.append((kx + 7.75 * math.cos(math.radians(a)), ky + 7.75 * math.sin(math.radians(a))))
    y = Y0
    while y <= Y1:
        x = X0
        while x <= X1:
            cand.append((x, y))
            x += 1.0
        y += 1.0
    inbox = lambda x, y, bx, m: bx[0] - m <= x <= bx[2] + m and bx[1] - m <= y <= bx[3] + m
    n = 0
    for x, y in cand:
        if not (X0 <= x <= X1 and Y0 <= y <= Y1):
            continue
        if inbox(x, y, ANT, 0.5) or inbox(x, y, BODY, 0.0):
            continue
        r = min(math.hypot(x - kx, y - ky) for kx, ky in K.values())
        if not (7.35 <= r <= 8.15 or r >= 9.0):
            continue
        # 0.6 mm to ordinary copper, 1.0 mm to high-impedance tracks, never under a connector contact / test pad
        if any(finish.seg_dist(x, y, *s_[:4]) < s_[4] + 0.3 + (1.0 if s_[5].startswith(('COL', 'SENSE', 'AMP_IN', 'XL')) else 0.3) for s_ in segs):
            continue
        if any(math.hypot(x - px, y - py) < pr + 0.3 + 0.3 for px, py, pr in pts):
            continue
        if any(math.hypot(x - px, y - py) < 2.0 for px, py, pr in gnd):
            continue
        if any(math.hypot(x - hx, y - hy) < 3.3 for hx, hy in finish.HOLES + [finish.PLATE_HOLE]):
            continue
        bd.via('GND', x, y)
        gnd.append((x, y, 0.3))
        n += 1
    print('island fence vias', n)


def zones(bd, K):
    """antenna keep-out along the board edge, beyond the one in the module footprint"""
    b = bd.b
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    for l in (L1, L2, L3, L4):
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    z.SetZoneName('ANT_EDGE')
    z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    x0, y0, x1, y1 = ANT
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(MM(px), MM(py))
    b.Add(z)
