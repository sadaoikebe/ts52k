"""Draw the J2 area from pcbnew data (red=F.Cu, blue=B.Cu, green=via, grey=holes,
orange dashed = 15.6 mm switch body squares, black = J2 courtyard, magenta = ANT_EDGE)."""
import sys
import pcbnew
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
b = pcbnew.LoadBoard(sys.argv[1]); m = lambda v: v / 1e6
X0, X1, Y0, Y1 = -5, 22, 76, 104
fig, ax = plt.subplots(figsize=(8, 8.3))
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        ax.add_patch(Circle((m(t.GetPosition().x), m(t.GetPosition().y)), m(t.GetWidth(pcbnew.F_Cu)) / 2, color='green'))
    else:
        c = 'red' if t.GetLayer() == pcbnew.F_Cu else 'blue'
        hl = t.GetNetname() in ('SWDIO', 'SWCLK', 'nRESET', 'nRF_VDD', 'GND')
        ax.plot([m(t.GetStart().x), m(t.GetEnd().x)], [m(t.GetStart().y), m(t.GetEnd().y)], color=c,
                lw=2.2 if hl else 0.8, alpha=1 if hl else 0.4, solid_capstyle='round')
for f in b.GetFootprints():
    for p in f.Pads():
        x, y = m(p.GetPosition().x), m(p.GetPosition().y)
        if not (X0 < x < X1 and Y0 < y < Y1): continue
        if p.GetDrillSizeX() > 0:
            ax.add_patch(Circle((x, y), m(p.GetDrillSizeX()) / 2, color='grey', alpha=0.7))
        elif f.GetReference() == 'J2':
            ax.add_patch(Circle((x, y), m(p.GetSizeX()) / 2, color='gold', ec='k'))
            ax.text(x, y, p.GetNumber(), ha='center', va='center', fontsize=6)
    if f.GetReference().startswith('MX'):
        x, y = m(f.GetPosition().x), m(f.GetPosition().y)
        ax.add_patch(Rectangle((x - 7.8, y - 7.8), 15.6, 15.6, fill=False, ec='orange', ls='--'))
        if X0 < x < X1 + 8 and Y0 < y < Y1 + 8: ax.text(min(x, X1 - 3), max(y - 3, Y0 + 1), f.GetReference(), ha='center', color='orange', clip_on=True)
cy = b.FindFootprintByReference('J2').GetCourtyard(pcbnew.B_CrtYd).BBox()
ax.add_patch(Rectangle((m(cy.GetLeft()), m(cy.GetTop())), m(cy.GetWidth()), m(cy.GetHeight()), fill=False, ec='k'))
ax.add_patch(Rectangle((-3.8, 45), 4.03, 37, fill=False, ec='magenta', hatch='//'))
ax.axvline(-3.572, color='k', lw=1.5)
ax.set_xlim(X0, X1); ax.set_ylim(Y1, Y0); ax.set_aspect('equal'); ax.grid(alpha=0.3)
ax.set_title('J2 west strip (seen from front, 2026-11-13)')
fig.savefig(sys.argv[2], dpi=110, bbox_inches='tight')
