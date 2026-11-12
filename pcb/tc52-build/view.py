#!/usr/bin/env python3
"""view.py x0 y0 w h out.png [layers=B,F,3] [labels=1]  -- quick region render with mm grid (board coords)"""
import sys, os, pcbnew
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon
mm = pcbnew.ToMM
x0, y0, w, h = map(float, sys.argv[1:5]); out = sys.argv[5]
layers = (sys.argv[6] if len(sys.argv) > 6 else 'B,F,3').split(',')
labels = (sys.argv[7] if len(sys.argv) > 7 else '1') == '1'
b = pcbnew.LoadBoard(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ts52k.kicad_pcb'))
LID = {'B': pcbnew.B_Cu, 'F': pcbnew.F_Cu, '3': pcbnew.In2_Cu, '2': pcbnew.In1_Cu}
COL = {'B': '#1f5fd0', 'F': '#d03030', '3': '#20a040', '2': '#b0b000'}
sc = 1500 / w / 100
fig = plt.figure(figsize=(w * sc, h * sc), dpi=100); ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(x0, x0 + w); ax.set_ylim(y0 + h, y0); ax.set_aspect('equal')
inb = lambda x, y, m=8: x0 - m < x < x0 + w + m and y0 - m < y < y0 + h + m
lw = lambda wmm: wmm * sc * 100 / 72 * 72 / 100 * 72 / 72 * (72 / 100) * 100 / 72  # mm -> points
def pts(wmm): return wmm * sc * 72
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts and d.GetClass() == 'PCB_SHAPE':
        try:
            s, e = d.GetStart(), d.GetEnd(); ax.plot([mm(s.x), mm(e.x)], [mm(s.y), mm(e.y)], 'k-', lw=1)
        except Exception: pass
for f in b.GetFootprints():
    for p in f.Pads():
        q = p.GetPosition(); x, y = mm(q.x), mm(q.y)
        if not inb(x, y): continue
        for L in layers:
            if L not in LID or not p.IsOnLayer(LID[L]): continue
            poly = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(poly, LID[L], 0, 5000, pcbnew.ERROR_INSIDE)
            for i in range(poly.OutlineCount()):
                o = poly.Outline(i)
                ax.add_patch(Polygon([(mm(o.CPoint(j).x), mm(o.CPoint(j).y)) for j in range(o.PointCount())], fc=COL[L], ec='none', alpha=0.35))
        if p.GetDrillSize().x > 0:
            ax.add_patch(Circle((x, y), mm(p.GetDrillSize().x) / 2, fc='w', ec='k', lw=0.5))
        if labels and f.GetReference()[:2] != 'MX' and p.GetSize(pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu).x > 0:
            ax.text(x, y, p.GetNumber(), fontsize=5, ha='center', va='center', color='k')
    q = f.GetPosition()
    if inb(mm(q.x), mm(q.y), 0):
        ax.text(mm(q.x), mm(q.y), f.GetReference(), fontsize=7, color='#804000', ha='center', va='bottom', weight='bold')
seen = {}
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        q = t.GetPosition(); x, y = mm(q.x), mm(q.y)
        if inb(x, y):
            ax.add_patch(Circle((x, y), mm(t.GetWidth(pcbnew.F_Cu)) / 2, fc='#909090' if t.GetNetname() == 'GND' else '#e0a000', ec='k', lw=0.3))
            if labels and t.GetNetname() != 'GND': ax.text(x, y - 0.5, t.GetNetname(), fontsize=4.5, ha='center')
        continue
    for L in layers:
        if L in LID and t.GetLayer() == LID[L]:
            s, e = t.GetStart(), t.GetEnd()
            if inb(mm(s.x), mm(s.y)) or inb(mm(e.x), mm(e.y)):
                ax.plot([mm(s.x), mm(e.x)], [mm(s.y), mm(e.y)], '-', color=COL[L], lw=pts(mm(t.GetWidth())), solid_capstyle='round', alpha=0.8)
                k = (t.GetNetname(), L)
                mx, my = (mm(s.x) + mm(e.x)) / 2, (mm(s.y) + mm(e.y)) / 2
                if labels and inb(mx, my, 0) and all(abs(mx - a) + abs(my - c) > w / 6 for a, c in seen.get(k, [])) and t.GetLength() > pcbnew.FromMM(1.5):
                    seen.setdefault(k, []).append((mx, my)); ax.text(mx, my, t.GetNetname().replace('/rp2040/', '').replace('Net-', ''), fontsize=5, color='k')
step = 1 if w <= 40 else (5 if w <= 160 else 10)
import numpy as np
ax.set_xticks(np.arange(np.ceil(x0 / step) * step, x0 + w, step)); ax.set_yticks(np.arange(np.ceil(y0 / step) * step, y0 + h, step))
ax.grid(True, lw=0.3, color='#888', alpha=0.5); ax.tick_params(direction='in', pad=-14, labelsize=6)
fig.savefig(out)
