"""Front-side obstacle model for J2 placement (2026-11-13).

- MX switch body: 15.6 x 15.6 mm square centred on the switch (real body, not the courtyard).
- Cherry PCB-mount stabilizer housing (per unit = one side of a 2U/2.25U/2.75U/3U stab):
  CHERRY "Keymodule MX" catalogue p.63 (SnapSwitches_04.06.pdf, 2006-12-07, RS doc 0900766b813d1126):
    drilling pattern  Ø3.05 hole 7 mm from module centre, Ø4 hole 15.24 mm from it, "A" = 23.8 (1x2..1x2.75) / 38.1 (1x3)
    frame cutout for the housing  6.65 (+0.1) wide, widest 4.2 (+0.1) from the stab centre line,
                                  12.3 / 13.5 (+-0.15) long
  Housing envelope used here: X = stab hole centre +-4.2 mm (widest dimensioned part of the housing cutout,
  >= the ~7.0 mm housing width scaled from the same page's side view), Y = from the outer edge of one PCB hole to
  the outer edge of the other (the housing snaps into the Ø3.05 hole and hooks into the Ø4 hole; the side view
  scales to -8.4 / +10.1 mm, inside these hole edges + 0.2 mm), padded by 0.2 mm.
- Stabilizer wire yoke: band between the two housings, at the Ø4 (hook) hole row, Ø4 hole y +-2 mm.
- SW2 (EC11E encoder): front courtyard.
"""
import math
import pcbnew

m = lambda v: v / 1e6
STAB_HALF_X = 4.2
PAD = 0.2


def obstacles(b):
    out = []  # (kind, ref, x0, y0, x1, y1)
    for f in b.GetFootprints():
        r = f.GetReference()
        cx, cy = m(f.GetPosition().x), m(f.GetPosition().y)
        if r.startswith('MX'):
            out.append(('switch', r, cx - 7.8, cy - 7.8, cx + 7.8, cy + 7.8))
            holes = [(m(p.GetPosition().x), m(p.GetPosition().y), m(p.GetDrillSizeX()) / 2)
                     for p in f.Pads() if p.GetNumber() == '' and abs(m(p.GetPosition().x) - cx) > 6]
            xs = sorted(set(round(h[0], 2) for h in holes))
            for x in xs:
                hs = [h for h in holes if abs(h[0] - x) < 0.1]
                y0 = min(h[1] - h[2] for h in hs) - PAD
                y1 = max(h[1] + h[2] for h in hs) + PAD
                out.append(('stabilizer', f'{r}-stab@{x:.2f}', x - STAB_HALF_X - PAD, y0, x + STAB_HALF_X + PAD, y1))
            if xs:
                big = [h for h in holes if h[2] > 1.8]
                yh = big[0][1]
                out.append(('stab-wire', f'{r}-wire', xs[0], yh - 2.0, xs[-1], yh + 2.0))
        elif r == 'SW2':
            bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
            out.append(('encoder', r, m(bb.GetLeft()), m(bb.GetTop()), m(bb.GetRight()), m(bb.GetBottom())))
        elif f.GetLayer() == pcbnew.F_Cu:
            bb = f.GetBoundingBox(False)
            out.append(('other-front', r, m(bb.GetLeft()), m(bb.GetTop()), m(bb.GetRight()), m(bb.GetBottom())))
    return out


def rd(a, c):
    dx = max(c[0] - a[2], a[0] - c[2], 0); dy = max(c[1] - a[3], a[1] - c[3], 0)
    return math.hypot(dx, dy)
