#!/usr/bin/env python3
"""viewz.py x0 y0 w h out.png [layer=B|F|2|3] -- zone fill (grey) + tracks + vias of one layer, to check pour continuity"""
import sys, os, pcbnew
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, PathPatch
from matplotlib.path import Path
mm = pcbnew.ToMM
x0, y0, w, h = map(float, sys.argv[1:5]); out = sys.argv[5]
L = {'B': pcbnew.B_Cu, 'F': pcbnew.F_Cu, '2': pcbnew.In1_Cu, '3': pcbnew.In2_Cu}[sys.argv[6] if len(sys.argv) > 6 else 'B']
b = pcbnew.LoadBoard(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ts52k.kicad_pcb'))
sc = 1500 / w / 100
fig = plt.figure(figsize=(w * sc, h * sc), dpi=100); ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(x0, x0 + w); ax.set_ylim(y0 + h, y0); ax.set_aspect('equal')
for z in b.Zones():
    if z.GetIsRuleArea() or not z.IsOnLayer(L): continue
    ps = z.GetFilledPolysList(L)
    for i in range(ps.OutlineCount()):
        verts, codes = [], []
        rings = [ps.Outline(i)] + [ps.Hole(i, j) for j in range(ps.HoleCount(i))]
        for r in rings:
            n = r.PointCount()
            for k in range(n):
                verts.append((mm(r.CPoint(k).x), mm(r.CPoint(k).y))); codes.append(Path.MOVETO if k == 0 else Path.LINETO)
            verts.append(verts[-n]); codes.append(Path.CLOSEPOLY)
        ax.add_patch(PathPatch(Path(verts, codes), fc='#b8b8b8', ec='none'))
for f in b.GetFootprints():
    for p in f.Pads():
        if not p.IsOnLayer(L): continue
        poly = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(poly, L, 0, 5000, pcbnew.ERROR_INSIDE)
        for i in range(poly.OutlineCount()):
            o = poly.Outline(i)
            ax.add_patch(Polygon([(mm(o.CPoint(j).x), mm(o.CPoint(j).y)) for j in range(o.PointCount())], fc='#d04040' if p.GetNetname() != 'GND' else '#606060', ec='none', alpha=0.8))
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        q = t.GetPosition()
        ax.add_patch(Circle((mm(q.x), mm(q.y)), mm(t.GetWidth(pcbnew.F_Cu)) / 2, fc='k' if t.GetNetname() == 'GND' else '#e0a000', ec='none'))
    elif t.GetLayer() == L:
        s, e = t.GetStart(), t.GetEnd()
        ax.plot([mm(s.x), mm(e.x)], [mm(s.y), mm(e.y)], '-', color='#1f5fd0' if t.GetNetname() != 'GND' else '#606060', lw=mm(t.GetWidth()) * sc * 72, solid_capstyle='round')
import numpy as np
step = 1 if w <= 40 else (5 if w <= 160 else 10)
ax.set_xticks(np.arange(np.ceil(x0 / step) * step, x0 + w, step)); ax.set_yticks(np.arange(np.ceil(y0 / step) * step, y0 + h, step))
ax.grid(True, lw=0.3, color='#888', alpha=0.5); ax.tick_params(direction='in', pad=-14, labelsize=6)
fig.savefig(out)
