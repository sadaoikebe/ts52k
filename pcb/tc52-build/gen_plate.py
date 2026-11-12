"""gen_plate.py : TC52 plate outline = TS52K plate (case/ts52k-plate-Body.dxf, bottom face) + the 12 M2 tap holes
taken from the board's mounting holes.  Output: case/tc52-plate.dxf (2D, plate's own coordinates, mm).

The TS52K DXF is a 3D edge export (faces at z 0 and z 1.5, joined by vertical lines); only the z = 0 face is kept.
Board <-> plate alignment is derived from the 14 mm switch cut-outs against keys.json and checked (<= 0.05 mm).
"""
import json, math, os, sys
import pcbnew

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'case', 'ts52k-plate-Body.dxf')
OUT = os.path.join(ROOT, 'case', 'tc52-plate.dxf')
TAP_DRILL = 1.6      # M2 x 0.4 tap drill; the plate is tapped as on TC69
MIN_WALL = 1.5       # hole wall to nearest cut-out edge


def read(path):
    lines = [l.rstrip('\r\n') for l in open(path, errors='replace')]
    pairs = [(int(lines[i].strip()), lines[i + 1].strip()) for i in range(0, len(lines) - 1, 2)]
    ents, cur, insec = [], None, False
    i = 0
    while i < len(pairs):
        c, v = pairs[i]
        if c == 0 and v == 'SECTION' and pairs[i + 1] == (2, 'ENTITIES'):
            insec = True; i += 2; continue
        if insec:
            if c == 0:
                if cur: ents.append(cur)
                if v == 'ENDSEC': cur, insec = None, False
                else: cur = {'type': v}
            elif cur is not None and c not in cur:
                cur[c] = v
        i += 1
    return ents


def main():
    lines, arcs = set(), set()
    for e in read(SRC):
        f = lambda c: round(float(e.get(c, 0)), 3)
        if e['type'] == 'LINE' and f(30) == 0 and f(31) == 0:
            a, b = (f(10), f(20)), (f(11), f(21))
            if a != b: lines.add((min(a, b), max(a, b)))
        elif e['type'] == 'ARC' and f(30) == 0:
            arcs.add((f(10), f(20), f(40), f(50), f(51)))
    # alignment: centres of 14 mm cut-outs vs key centres (board y is down, plate y is up)
    hs = {(round((a[0] + b[0]) / 2, 3), a[1]) for a, b in lines if a[1] == b[1] and abs(abs(a[0] - b[0]) - 14) < 0.01}
    cent = [(x, round(y + 7, 3)) for x, y in hs if (x, round(y + 14, 3)) in hs]
    K = json.load(open(os.path.join(HERE, 'keys.json')))
    xs = [p[0] for s in lines for p in s]; ys = [p[1] for s in lines for p in s]
    ox = min(v[0] for v in K.values()) - min(c[0] for c in cent)
    oy = min(v[1] for v in K.values()) + max(c[1] for c in cent)
    err = sorted(min(math.hypot(c[0] + ox - v[0], oy - c[1] - v[1]) for c in cent) for v in K.values())
    matched = [x for x in err if x <= 0.05]
    assert len(matched) >= 48, 'plate / board alignment failed'
    print(f'alignment: plate x = board x - {ox:.5f}, plate y = {oy:.5f} - board y; {len(matched)} of {len(K)} plain 14 mm cut-outs match within {max(matched):.3f} mm')

    b = pcbnew.LoadBoard(os.path.join(ROOT, 'pcb', 'ts52k.kicad_pcb'))
    holes = []
    for fp in b.GetFootprints():
        r = fp.GetReference()
        if r[0] == 'H' and r[1:].isdigit():
            p = fp.GetPosition()
            holes.append((int(r[1:]), pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))
    holes.sort()
    assert len(holes) == 12

    def sd(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy
        t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    ok = True
    circles = []
    for n, x, y in holes:
        p = (x - ox, oy - y)
        d = min(sd(p, a, b_) for a, b_ in lines)
        for cx, cy, r, a0, a1 in arcs:
            d = min(d, abs(math.hypot(p[0] - cx, p[1] - cy) - r))
        wall = d - TAP_DRILL / 2
        inside = min(xs) < p[0] < max(xs) and min(ys) < p[1] < max(ys)
        flag = 'ok ' if wall >= MIN_WALL and inside else 'BAD'
        ok &= flag == 'ok '
        print(f'{flag} H{n}: board ({x:.2f}, {y:.2f}) -> plate ({p[0]:.3f}, {p[1]:.3f}), wall to nearest cut-out {wall:.2f} mm')
        circles.append(p)

    o = ['0', 'SECTION', '2', 'ENTITIES']
    for a, b_ in sorted(lines):
        o += ['0', 'LINE', '8', 'plate', '10', f'{a[0]:.4f}', '20', f'{a[1]:.4f}', '11', f'{b_[0]:.4f}', '21', f'{b_[1]:.4f}']
    for cx, cy, r, a0, a1 in sorted(arcs):
        o += ['0', 'ARC', '8', 'plate', '10', f'{cx:.4f}', '20', f'{cy:.4f}', '40', f'{r:.4f}', '50', f'{a0:.4f}', '51', f'{a1:.4f}']
    for cx, cy in circles:
        o += ['0', 'CIRCLE', '8', 'tap_M2', '10', f'{cx:.4f}', '20', f'{cy:.4f}', '40', f'{TAP_DRILL / 2:.4f}']
    o += ['0', 'ENDSEC', '0', 'EOF']
    open(OUT, 'w').write('\n'.join(o) + '\n')
    print(f'wrote {OUT}: {len(lines)} lines, {len(arcs)} arcs, {len(circles)} holes')
    # every vertex of the outline must be shared by exactly two entities (closed loops only)
    import collections
    deg = collections.Counter()
    for a, b_ in lines: deg[a] += 1; deg[b_] += 1
    for cx, cy, r, a0, a1 in arcs:
        for ang in (a0, a1):
            deg[(round(cx + r * math.cos(math.radians(ang)), 3), round(cy + r * math.sin(math.radians(ang)), 3))] += 1
    bad = {k: v for k, v in deg.items() if v != 2}
    print('open or branching vertices:', len(bad), list(bad.items())[:5])
    return 0 if ok and not bad else 1


if __name__ == '__main__':
    sys.exit(main())
