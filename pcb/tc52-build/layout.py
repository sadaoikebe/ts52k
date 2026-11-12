"""TC52 placement and routing (all coordinates in board mm, y down).

The reasoning (L4 topology, electrode gates, lane order) is in ~/workspace/ts52k-ec/tc52-build-log.md.
Layers: L1 electrodes + row buses, L2 GND, L3 GND, L4 everything else.
"""
import math
import pcbnew
import matrix as M
from brd import B, V, MM, mm, L1, L2, L3, L4, offset

KN = M.key_net()
ROW_OF = {k: int(KN[k][0][3:]) for k in KN}
COL_OF = {k: int(KN[k][1][3:]) for k in KN}

# ---------------------------------------------------------------- electrodes
# via offsets from the key centre. Default is the TC69 position (+-1.19, 0).
# Two sense vias = an "electrode gate": the column enters at the first and leaves at the second,
# other L4 wiring passes between them (the electrode on L1 is the connection).
SENSE_VIAS = {
    'MX3': [(1.6, -5.2), (1.6, 5.2)],       # gate for +3V3 / ADC / PURGE going west to the AFE
    'MX8': [(1.6, -5.2), (1.6, 5.2)],       # gate for the east bundle (BOOTSEL, ENC x3, MUX A and MUX B control)
    'MX12': [(1.6, -5.2), (1.6, 5.2)],      # gate for the MUX A control lines
    'MX7': [(5.0, -1.5)],                   # c2 leaves MX7 away from the flash (U4) and QSPI
}
DRIVE_VIA = {
    'MX3': (-1.19, 5.2),                    # below the gate lanes
    'MX8': (-1.19, 5.0),                    # below the bundle
    'MX12': (-1.19, 5.0),
}
BUS = {1: 64.29, 2: 83.34, 3: 102.04, 4: 102.74}   # L1 row buses (rows 3 and 4 share one gap)
GAP_Y = {'MX74': 88.1}                             # MX74 sits 4.76 mm lower than row 2

# lower band lanes (L4)
LANE1, LANE2, LANE3, TRUNK = 113.9, 115.4, 116.9, 118.4
C1_LANE = 116.4

MUXA = (76.0, 108.5)
MUXB = (222.5, 110.5)

K = {}


def SV(k, i=0):
    dx, dy = SENSE_VIAS.get(k, [(1.19, 0.0)])[i]
    return (K[k][0] + dx, K[k][1] + dy)


def DV(k):
    dx, dy = DRIVE_VIA.get(k, (-1.19, 0.0))
    return (K[k][0] + dx, K[k][1] + dy)


def keys_stage(bd):
    for k, (x, y) in K.items():
        f = bd.fp(k)
        f.SetPosition(V(x, y))
        f.SetOrientationDegrees(0)
        f.Reference().SetVisible(False)
        row, col = KN[k]
        bd.via(row, *DV(k), 0.8, 0.4)
        for i in range(len(SENSE_VIAS.get(k, [0]))):
            bd.via(col, *SV(k, i), 0.8, 0.4)


# ---------------------------------------------------------------- rows
ROW_FEED = {1: (18.8, 64.29), 2: (19.4, 83.34), 3: (20.3, 102.04), 4: (21.4, 102.74)}


def rows_stage(bd):
    xs = {r: [] for r in BUS}
    for k in K:
        r = ROW_OF[k]
        net = f'ROW{r}'
        dx, dy = DV(k)
        gy = GAP_Y.get(k, BUS[r])
        if k == 'MX7':      # the flash (U4) is below: lead-in on L3 inside the island, up to the bus between R14 and the bundle
            bd.via(net, 35.1, 64.9, 0.6, 0.3)
            bd.track(net, [(dx, dy), (35.1, dy + 35.1 - dx), (35.1, 64.9)], L3, 0.25)
            bd.track(net, [(35.1, gy), (35.1, 64.9)], L1, 0.25)
            xs[r].append(dx)
            continue
        if r == 4 and any(abs(dx - DV(q)[0]) < 0.9 for q in K if ROW_OF[q] == 3):
            # a row-3 key right above uses the same x: step the row-4 bus via aside
            bd.via(net, dx + 0.9, gy, 0.6, 0.3)
            bd.track(net, [(dx, dy), (dx, gy + 1.7), (dx + 0.9, gy + 0.8), (dx + 0.9, gy)], L4, 0.25)
            xs[r].append(dx + 0.9)
            continue
        bd.via(net, dx, gy, 0.6, 0.3)
        bd.track(net, [(dx, dy), (dx, gy)], L4, 0.25)        # lead-in on L4
        if k not in GAP_Y:
            xs[r].append(dx)
    for r in BUS:
        xs[r].append(ROW_FEED[r][0])
    y = BUS[1]
    bd.track('ROW1', [(min(xs[1]), y), (22.9, y), (23.19, 64.0), (26.2, 64.0), (26.49, y), (max(xs[1]), y)], L1, 0.25)
    y = BUS[2]      # jog under the Tag-Connect holes; right end drops to MX74
    bd.track('ROW2', [(min(xs[2]), y), (23.4, y), (23.76, 83.7), (30.9, 83.7), (31.26, y), (285.0, y),
                      (289.76, 88.1), (DV('MX74')[0], 88.1)], L1, 0.25)
    bd.track('ROW3', [(min(xs[3]), BUS[3]), (max(xs[3]), BUS[3])], L1, 0.25)
    bd.track('ROW4', [(min(xs[4]), BUS[4]), (max(xs[4]), BUS[4])], L1, 0.25)


# ---------------------------------------------------------------- MUX
def place_mux(bd, ref, c):
    f = bd.place(ref, c[0], c[1], 0)
    f.Reference().SetVisible(False)
    p = {n: bd.pad(ref, n) for n in range(1, 17)}
    # expected: pins 8..1 down the west column, 9..16 down the east column
    assert p[1][0] < c[0] < p[16][0] and p[8][1] < p[1][1] and p[9][1] < p[16][1], (ref, p)
    return p


def fan(bd, net, pad, lane_y, side, xk, w=0.2):
    """pad -> horizontal out to xk -> 45 deg down to lane_y; returns the lane point. side: -1 west, +1 east"""
    px, py = pad
    xe = xk + side * (lane_y - py)
    bd.track(net, [(px, py), (xk, py), (xe, lane_y)], L4, w)
    return (xe, lane_y)


def col_r(bd, n, x, y, up=True):
    """100k column discharge resistor, vertical, pad 1 (COL) on (x, y), pad 2 (GND) above (up) or below"""
    ref = f'R{40+n}'
    f = bd.place(ref, x, y - 0.51 if up else y + 0.51, 90)
    f.Reference().SetVisible(False)
    if abs(bd.pad(ref, 1)[1] - y) > 0.01:
        f.SetOrientationDegrees(270)
    assert abs(bd.pad(ref, 1)[1] - y) < 0.01 and abs(bd.pad(ref, 1)[0] - x) < 0.01, (ref, bd.pad(ref, 1))


def columns_stage(bd):
    T = lambda n, pts: bd.track(f'COL{n}', pts, L4, 0.2)
    A = place_mux(bd, 'U7', MUXA)
    Bp = place_mux(bd, 'U8', MUXB)
    # ---- c1 (gate at MX3)
    p, g1, g2, q = SV('MX2'), SV('MX3', 0), SV('MX3', 1), SV('MX4')
    T(1, [p, (p[0], g1[1] - (g1[0] - p[0])), g1])
    T(1, [g2, (g2[0], q[1] - (q[0] - g2[0])), q, (q[0], 104.0), (14.5, 107.36), (14.5, C1_LANE)])
    e = fan(bd, 'COL1', A[1], C1_LANE, -1, 70.9)
    T(1, [SV('MX5'), (SV('MX5')[0], C1_LANE - 1.5), (SV('MX5')[0] + 1.5, C1_LANE), e])
    col_r(bd, 1, 24.0, C1_LANE)
    # ---- c2 (around the flash, gate at MX8)
    s7 = SV('MX7'); g1, g2 = SV('MX8', 0), SV('MX8', 1); s13 = SV('MX13')
    T(2, [s7, (43.6, s7[1]), (43.6, 64.5), (g1[0], 68.0), g1])
    T(2, [g2, (s13[0], g2[1] + s13[0] - g2[0]), s13])
    b2 = s13
    s9 = SV('MX9')
    T(2, [b2, (b2[0], 103.6), (b2[0] - 6.23, 109.83), (s9[0] + 2.09, 109.83), s9])
    e = fan(bd, 'COL2', A[2], LANE1, -1, 70.0)
    T(2, [s9, (s9[0], LANE1 - 1.5), (s9[0] + 1.5, LANE1), e])
    col_r(bd, 2, 45.0, LANE1)
    # ---- generic upper legs: diagonal first, then vertical into the next key
    def leg(n, k1, k2, y0=None):
        p, q = SV(k1), SV(k2)
        y0 = p[1] if y0 is None else y0
        d = q[0] - p[0]
        T(n, [p, (p[0], y0), (q[0], y0 + abs(d)), q])
    # ---- c3
    p = SV('MX11'); g1, g2 = SV('MX12', 0), SV('MX12', 1); s = SV('MX18')
    T(3, [p, (g1[0], p[1] + g1[0] - p[0]), g1])
    T(3, [g2, (s[0], g2[1] + s[0] - g2[0]), s])
    s14 = SV('MX14')
    T(3, [s, (s[0], 103.6), (s[0] - (s14[1] - 103.6), s14[1]), s14])
    T(3, [(s[0], 103.6), (s[0], A[4][1] - (A[4][0] - 1.0 - s[0])), (A[4][0] - 1.0, A[4][1]), A[4]])
    col_r(bd, 3, 57.8, s14[1])
    # ---- c4
    leg(4, 'MX16', 'MX17'); leg(4, 'MX17', 'MX22'); leg(4, 'MX22', 'MX23', 93.5)
    s = SV('MX23')
    e = fan(bd, 'COL4', A[13], LANE1, +1, 82.2)
    T(4, [s, (s[0], LANE1 - 1.5), (s[0] - 1.5, LANE1), e])
    col_r(bd, 4, 90.0, LANE1)
    # ---- c5, c6 (no row-4 key: straight down into the band)
    leg(5, 'MX20', 'MX21'); leg(5, 'MX21', 'MX27')
    s = SV('MX27'); e = fan(bd, 'COL5', A[14], LANE2, +1, 81.35)
    T(5, [s, (s[0], LANE2 - 1.5), (s[0] - 1.5, LANE2), e])
    col_r(bd, 5, 100.0, LANE2)
    leg(6, 'MX25', 'MX26'); leg(6, 'MX26', 'MX31')
    s = SV('MX31'); e = fan(bd, 'COL6', A[15], LANE3, +1, 80.5)
    T(6, [s, (s[0], LANE3 - 1.5), (s[0] - 1.5, LANE3), e])
    col_r(bd, 6, 112.0, LANE3)
    # ---- c7
    leg(7, 'MX29', 'MX30'); leg(7, 'MX30', 'MX35'); leg(7, 'MX35', 'MX60', 93.5)
    s = SV('MX60'); e = fan(bd, 'COL7', Bp[1], LANE3, -1, 218.0)
    T(7, [s, (s[0], LANE3 - 1.5), (s[0] + 1.5, LANE3), e])
    col_r(bd, 7, 160.0, LANE3)
    # ---- c8
    leg(8, 'MX33', 'MX34'); leg(8, 'MX34', 'MX39')
    s = SV('MX39'); e = fan(bd, 'COL8', Bp[2], LANE2, -1, 217.1)
    T(8, [s, (s[0], LANE2 - 1.5), (s[0] + 1.5, LANE2), e])
    col_r(bd, 8, 175.0, LANE2)
    # ---- c9
    leg(9, 'MX37', 'MX38'); leg(9, 'MX38', 'MX44'); leg(9, 'MX44', 'MX81', 93.5)
    s = SV('MX81'); e = fan(bd, 'COL9', Bp[4], LANE1, -1, 217.5)
    T(9, [s, (s[0], LANE1 - 1.5), (s[0] + 1.5, LANE1), e])
    col_r(bd, 9, 196.0, LANE1)
    # ---- c10 (passes above the MX82 row lead-in)
    leg(10, 'MX42', 'MX43'); leg(10, 'MX43', 'MX48')
    s, q = SV('MX48'), SV('MX82')
    T(10, [s, (s[0], 93.0), (s[0] + 8.1, 101.1), (q[0] - 0.82, 101.1), (q[0], 101.92), q,
           (q[0] + (q[1] - Bp[5][1]), Bp[5][1]), Bp[5]])
    col_r(bd, 10, 210.6, 101.1)
    # ---- c11 (MUX B is fed from the MX52 leg; MX58 hangs on the end)
    leg(11, 'MX46', 'MX47'); leg(11, 'MX47', 'MX52')
    s, q = SV('MX52'), SV('MX58')
    T(11, [s, (s[0] + 7.93, 100.8), (q[0] - 1.55, 100.8), (q[0], 102.35), q])
    T(11, [(228.6, 100.8), (228.6, Bp[12][1] - 2.0), (Bp[12][0] + 1.4, Bp[12][1]), Bp[12]])
    col_r(bd, 11, 231.0, 100.8)
    # ---- c12
    leg(12, 'MX51', 'MX56'); leg(12, 'MX56', 'MX75'); leg(12, 'MX75', 'MX61', 93.5)
    s = SV('MX61'); e = fan(bd, 'COL12', Bp[13], LANE1, +1, 228.7)
    T(12, [s, (s[0], LANE1 - 1.5), (s[0] - 1.5, LANE1), e])
    col_r(bd, 12, 245.0, LANE1)
    # ---- c13
    leg(13, 'MX55', 'MX65'); leg(13, 'MX65', 'MX66')
    T(13, [SV('MX66'), SV('MX67')])
    s = SV('MX67'); e = fan(bd, 'COL13', Bp[14], LANE2, +1, 227.85)
    T(13, [s, (s[0], LANE2 - 1.5), (s[0] - 1.5, LANE2), e])
    col_r(bd, 13, 262.0, LANE2)
    # ---- c14 (MX74 is offset: arrive from above, leave past its lead-in)
    s, q, z = SV('MX64'), SV('MX74'), SV('MX71')
    T(14, [s, (287.5, s[1] + 287.5 - s[0]), (q[0] - 1.97, s[1] + 287.5 - s[0]), (q[0], s[1] + 287.5 - s[0] + 1.97), q])
    T(14, [q, (q[0], 90.0), (z[0], 90.0 + q[0] - z[0]), z])
    e = fan(bd, 'COL14', Bp[15], LANE3, +1, 227.0)
    T(14, [z, (z[0], LANE3 - 1.5), (z[0] - 1.5, LANE3), e])
    col_r(bd, 14, 283.0, LANE3)
    # ---- SENSE trunk (lowest lane; MUX A hangs on a short stub under its body, MUX B is the end)
    S = lambda pts: bd.track('SENSE', pts, L4, 0.2)
    xb = MUXB[0] - 1.3
    S([(-2.0, 116.4), (0.0, TRUNK), (xb, TRUNK), (xb, Bp[3][1]), Bp[3]])
    xa = MUXA[0] - 1.3
    S([(xa, TRUNK), (xa, A[3][1]), A[3]])
    return A, Bp


def zones_stage(bd):
    b = bd.b
    main = None
    for z in list(b.Zones()):
        if z.GetIsRuleArea():
            if z.GetZoneName() == 'MCU_FANOUT':
                ls = pcbnew.LSET(); ls.AddLayer(L4); z.SetLayerSet(ls)
            continue
        ls = [l for l in z.GetLayerSet().Seq()]
        if z.GetAssignedPriority() == 1 and ls == [L1]:
            b.RemoveNative(z)          # local MCU zone on the front: L1 is electrodes only now
        elif z.GetAssignedPriority() == 1:
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        elif len(ls) == 2:
            main = z
    # inner planes: same outline as the main zone, small clearance (only via/hole antipads)
    for layer, name in ((L2, 'L2_GND'), (L3, 'L3_GND')):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(bd.net('GND'))
        z.SetZoneName(name)
        z.Outline().Append(main.Outline())
        z.SetLocalClearance(MM(0.2))
        z.SetMinThickness(MM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER if layer == L2 else pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        b.Add(z)
    # no pour between electrode and guard ring (keeps the TC69 electrode geometry)
    for k, (x, y) in K.items():
        z = pcbnew.ZONE(b)
        z.SetIsRuleArea(True)
        z.SetLayer(L1)
        z.SetZoneName('ELECTRODE_' + k)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        o = z.Outline()
        o.NewOutline()
        for i in range(48):
            a = 2 * math.pi * i / 48
            o.Append(MM(x + 7.05 * math.cos(a)), MM(y + 7.05 * math.sin(a)))
        b.Add(z)


def fill(bd):
    pcbnew.ZONE_FILLER(bd.b).Fill(bd.b.Zones())


def run(bd, keys, stage):
    K.update(keys)
    keys_stage(bd)
    rows_stage(bd)
    A, Bp = columns_stage(bd)
    import east, west
    band = east.run(bd, A, Bp, K, SV, DV)
    east.band_run(bd, band, Bp, K, SV, DV)
    west.run(bd, K, SV, DV)
    import finish
    finish.run(bd, K)
    zones_stage(bd)
    fill(bd)
    import finish as _f
    if _f.island_vias(bd, K):
        fill(bd)
