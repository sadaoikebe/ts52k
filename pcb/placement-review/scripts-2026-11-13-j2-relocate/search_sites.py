"""Scan the whole board for J2 sites whose courtyard is >= 2 mm from every front-side obstacle (2026-11-13).

For each y (0.1 mm step) and orientation the forbidden x-intervals of the J2 centre are computed exactly
(Euclidean distance rectangle-to-rectangle), so narrow gaps (e.g. between two 1.25U keys, ~2.06 mm margin)
are not missed by a coarse x grid. Back-side courtyard overlap is reported separately (J2 lands are on B.Cu).
usage: python3 search_sites.py ts52k.kicad_pcb [out.json]
"""
import sys, json, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from obstacles import obstacles, rd, m

CLR = 2.0
b = pcbnew.LoadBoard(sys.argv[1])
OBS = obstacles(b)
BACK = []
for f in b.GetFootprints():
    if f.GetLayer() == pcbnew.B_Cu and f.GetReference() != 'J2':
        bb = f.GetCourtyard(pcbnew.B_CrtYd).BBox()
        if bb.GetWidth() > 0:
            BACK.append((f.GetReference(), m(bb.GetLeft()), m(bb.GetTop()), m(bb.GetRight()), m(bb.GetBottom())))
EDGE = (-3.572, 45.252, 303.611, 121.444)  # straight edges of the outline (corners R1.19)
EDGE_MIN = 0.5
ANT = (-3.8, 45.0, 0.23, 82.0)
U5_SWD = (2.2, 68.05)  # between SWDIO(51) and SWCLK(53)


def free_intervals(y, hx, hy):
    lo, hi = EDGE[0] + EDGE_MIN + hx, EDGE[2] - EDGE_MIN - hx
    bad = []
    for o in OBS + [('ant', 'ANT_EDGE') + ANT]:
        s = CLR if o[0] != 'ant' else 0.0
        dy = max(o[3] - (y + hy), (y - hy) - o[5], 0)
        if dy >= s and o[0] != 'ant':
            continue
        if o[0] == 'ant' and dy > 0:
            continue
        w = math.sqrt(max(s * s - dy * dy, 0))
        bad.append((o[2] - hx - w, o[4] + hx + w))
    bad.sort()
    out, x = [], lo
    for a, c in bad:
        if a > x and x < hi:
            out.append((x, min(a, hi)))
        x = max(x, c)
    if x < hi:
        out.append((x, hi))
    return out


res = []
for rot, (hx, hy) in ((0, (3.545, 2.045)), (90, (2.045, 3.545))):
    y = EDGE[1] + EDGE_MIN + hy
    while y <= EDGE[3] - EDGE_MIN - hy + 1e-9:
        for a, c in free_intervals(y, hx, hy):
            x = (a + c) / 2  # centre of the free interval = most room left/right
            env = (x - hx, y - hy, x + hx, y + hy)
            d = min((rd(env, o[2:]), o[0], o[1]) for o in OBS)
            bk = min((rd(env, o[1:]), o[0]) for o in BACK)
            res.append(dict(x=round(x, 3), y=round(y, 2), rot=rot, front_min=round(d[0], 3), nearest=d[1:],
                            back_min=round(bk[0], 3), back_nearest=bk[1],
                            dist_U5=round(math.hypot(x - U5_SWD[0], y - U5_SWD[1]), 1)))
        y = round(y + 0.1, 4)
print(len(res), 'free (x-interval centres)')
ok = [r for r in res if r['back_min'] >= 0.3]
print(len(ok), 'without back-side courtyard conflict (>=0.3 mm)')
best = {}
for r in ok:
    k = (int(r['x'] // 6), int(r['y'] // 6))
    if k not in best or r['front_min'] > best[k]['front_min']:
        best[k] = r
for r in sorted(best.values(), key=lambda r: r['dist_U5'])[:40]:
    print(r)
if len(sys.argv) > 2:
    json.dump({'clearance_mm': CLR, 'n_free': len(res), 'n_no_back_conflict': len(ok),
               'per_6mm_cell_best': sorted(best.values(), key=lambda r: r['dist_U5']),
               'obstacles': OBS}, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
