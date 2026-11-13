"""Draw J2 and the front-side obstacle model around it (2026-11-13). Run with ~/.venv-tc52w python."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from obstacles import obstacles, m

b = pcbnew.LoadBoard(sys.argv[1])
X0, X1, Y0, Y1 = -4, 40, 80, 122
fig, ax = plt.subplots(figsize=(11, 10.5))
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition(); ax.add_patch(Circle((m(p.x), m(p.y)), m(t.GetWidth(pcbnew.F_Cu)) / 2, color='green', alpha=0.6))
        continue
    s, e = t.GetStart(), t.GetEnd(); n = t.GetNetname()
    swd = n in ('SWDIO', 'SWCLK', 'nRESET', 'nRF_VDD') or (n == 'GND' and t.GetLayerName() == 'B.Cu')
    ax.plot([m(s.x), m(e.x)], [m(s.y), m(e.y)], color=('orange' if swd and n != 'GND' else ('red' if t.GetLayerName() == 'F.Cu' else 'blue')),
            lw=1.6 if swd else 0.8, alpha=0.8)
for f in b.GetFootprints():
    for p in f.Pads():
        if not p.GetNumber():
            ax.add_patch(Circle((m(p.GetPosition().x), m(p.GetPosition().y)), m(p.GetDrillSizeX()) / 2, fill=False, ec='k', lw=0.6))
colors = {'switch': 'orange', 'stabilizer': 'purple', 'stab-wire': 'purple', 'encoder': 'brown'}
for k, r, x0, y0, x1, y1 in obstacles(b):
    if x1 < X0 or x0 > X1 or y1 < Y0 or y0 > Y1: continue
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=colors.get(k, 'gray'), ls='--' if k != 'stab-wire' else ':'))
    ax.text((x0 + x1) / 2, max(y0, Y0) + 1.2, r.split('@')[0], ha='center', fontsize=7, color=colors.get(k, 'gray'), clip_on=True)
j2 = b.FindFootprintByReference('J2')
for p in j2.Pads():
    if p.GetNumber():
        ax.add_patch(Circle((m(p.GetPosition().x), m(p.GetPosition().y)), 0.39, color='k'))
        ax.text(m(p.GetPosition().x), m(p.GetPosition().y) - 0.55, p.GetNumber(), fontsize=6, ha='center')
cy = j2.GetCourtyard(pcbnew.B_CrtYd).BBox()
ax.add_patch(Rectangle((m(cy.GetLeft()), m(cy.GetTop())), m(cy.GetWidth()), m(cy.GetHeight()), fill=False, ec='k'))
ax.add_patch(Rectangle((m(cy.GetLeft()) - 2, m(cy.GetTop()) - 2), m(cy.GetWidth()) + 4, m(cy.GetHeight()) + 4, fill=False, ec='k', ls=':'))
ax.add_patch(Rectangle((-3.8, 45), 4.03, 37, fill=False, ec='magenta', hatch='//'))
ax.axvline(-3.572, color='k', lw=1.5); ax.axhline(121.444, color='k', lw=1.5)
ax.set_xlim(X0, X1); ax.set_ylim(Y1, Y0); ax.set_aspect('equal'); ax.grid(alpha=0.3)
ax.set_title('J2 (19.05, 115.0) +90 deg, bottom side; dashed = front obstacles, dotted black = courtyard + 2 mm (2026-11-13)', fontsize=8)
fig.savefig(sys.argv[2], dpi=110, bbox_inches='tight')
