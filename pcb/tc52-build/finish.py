"""Mounting holes, PLATE link, guard-ring ground vias (design-spec 4.2, 5-10)."""
import math
import pcbnew
from brd import L1, L2, L3, L4, mm
from west import at, two

HOLES = [(61.91, 54.77), (119.06, 54.77), (176.21, 54.77), (233.32, 54.77),
         (57.15, 92.87), (133.35, 92.87), (209.55, 92.87), (284.0, 92.87),
         (122.6, 111.92), (200.03, 111.92), (280.99, 111.92)]
PLATE_HOLE = (19.05, 111.92)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2_ = dx * dx + dy * dy
    t = 0 if L2_ == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2_))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def run(bd, K):
    b = bd.b
    # ---- holes
    for i, (x, y) in enumerate(HOLES):
        f = bd.fp(f'H{i + 2}')
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        f.Reference().SetVisible(False)
    f = bd.fp('H1')
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(PLATE_HOLE[0]), pcbnew.FromMM(PLATE_HOLE[1])))
    f.Reference().SetVisible(False)
    a, c = two(bd, 'R25', PLATE_HOLE[0], PLATE_HOLE[1] - 3.6, 'n')
    bd.track('PLATE', [PLATE_HOLE, a], L4, 0.25)
    bd.track('GND', [c, (c[0] + 0.9, c[1])], L4, 0.25)
    bd.via('GND', c[0] + 0.9, c[1])
    # ---- guard rings: two ground vias each (ring = 7.05 .. 8.45 mm from the key centre)
    segs = []       # (ax, ay, bx, by, half width) of every non-ground track, any layer
    pts = []        # (x, y, radius) of vias and non-ground pads
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            pts.append((mm(p.x), mm(p.y), mm(t.GetWidth(L1)) / 2))
        elif t.GetNetname() != 'GND':
            s, e = t.GetStart(), t.GetEnd()
            segs.append((mm(s.x), mm(s.y), mm(e.x), mm(e.y), mm(t.GetWidth()) / 2))
    for f in b.GetFootprints():
        for p in f.Pads():
            if f.GetReference().startswith('MX'):
                continue
            q = p.GetPosition()
            bb = p.GetBoundingBox()
            pts.append((mm(q.x), mm(q.y), max(mm(bb.GetWidth()), mm(bb.GetHeight())) / 2 + 0.05))
    n = 0
    for k, (kx, ky) in K.items():
        got = 0
        for ang in (45, 225, 135, 315, 20, 200, 110, 290, 70, 250, 160, 340, 0, 180, 90, 270):
            x = kx + 7.75 * math.cos(math.radians(ang))
            y = ky + 7.75 * math.sin(math.radians(ang))
            if any(seg_dist(x, y, *s[:4]) < s[4] + 0.3 + 0.35 for s in segs):
                continue
            if any(math.hypot(x - px, y - py) < r + 0.3 + 0.3 for px, py, r in pts):
                continue
            bd.via('GND', x, y)
            pts.append((x, y, 0.3))
            got += 1
            n += 1
            if got == 2:
                break
        if got < 2:
            print('ring vias', k, got)
    print('ring vias placed', n)


def island_vias(bd, K):
    """Ground the pieces of the local MCU pour on L4 that have no via of their own (they would leave C9, C15 and
    the flash ground pin floating). A via may sit on a guard ring (7.4 .. 8.1 mm from a key centre) or clear of all rings."""
    b = bd.b
    z = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetAssignedPriority() == 1][0]
    polys = z.GetFilledPolysList(L4)
    vias = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    other = [(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2)
             for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() in (L1, L3) and t.GetNetname() != 'GND']
    added = []
    for i in range(polys.OutlineCount()):
        o = pcbnew.SHAPE_POLY_SET(); o.AddOutline(polys.Outline(i))
        if any(v.GetNetname() == 'GND' and o.Contains(v.GetPosition()) for v in vias):
            continue
        bb = o.BBox()
        best = None
        y = mm(bb.GetTop())
        while y < mm(bb.GetBottom()) and best is None:
            x = mm(bb.GetLeft())
            while x < mm(bb.GetRight()):
                p = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
                ok = o.Contains(p, -1, pcbnew.FromMM(-0.001)) and all(
                    o.Contains(pcbnew.VECTOR2I(pcbnew.FromMM(x + dx), pcbnew.FromMM(y + dy))) for dx, dy in ((0.33, 0), (-0.33, 0), (0, 0.33), (0, -0.33), (0.24, 0.24), (-0.24, 0.24), (0.24, -0.24), (-0.24, -0.24)))
                if ok:
                    for kx, ky in K.values():
                        r = math.hypot(x - kx, y - ky)
                        if r < 6.5:
                            ok = False
                            break
                if ok and any(seg_dist(x, y, *s[:4]) < s[4] + 0.55 for s in other):
                    ok = False
                if ok and any(math.hypot(x - mm(v.GetPosition().x), y - mm(v.GetPosition().y)) < 0.95 for v in vias):
                    ok = False
                if ok:
                    best = (x, y)
                    break
                x += 0.1
            y += 0.1
        if best:
            bd.via('GND', *best)
            added.append((round(best[0], 2), round(best[1], 2)))
        else:
            bb2 = [round(mm(v), 1) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
            print('island without via, no legal spot:', bb2)
    print('island vias', added)
    return added
