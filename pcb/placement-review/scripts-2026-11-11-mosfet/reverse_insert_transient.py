"""Estimate of the BAT-pin voltage when a reversed cell is plugged in while USB keeps BAT at 4.2 V.

NOT a verified model: square-law MOSFET with assumed parameters, lumped lead inductance.
It only answers one question: can the BAT node (Q1 source, C24, BQ24072 BAT) be dragged
below 0 V before Q1 turns itself off?  Datasheet-derived inputs: Vgs(th) -0.5..-1.3 V,
gFS 17 S at 4 A, BVdss 30 V (AO3401A rev 3.1); C24 4.7 uF nominal.
Everything else (cell resistance, lead inductance, capacitance derating) is swept.

Circuit:  BAT node (C, charger current Ichg in) -- Q1 (S->D, gate at 0 V) -- drain node (Cd)
          -- L -- R -- reversed cell (-Vb) -- GND
"""
import itertools
import numpy as np
from scipy.integrate import solve_ivp

VB, V0, BV, CD, RS = 4.2, 4.2, 30.0, 100e-12, 0.035
TEND = 60e-6
K = 17.0 ** 2 / (2 * 4.0)          # A/V^2 from gFS at 4 A


def fet(vs, vd, vth):
    """Current source->drain (A). Gate is at 0 V, so Vsg = vs."""
    vsd = vs - vd
    if vsd < 0:                     # normal polarity: body diode / channel, not exercised here
        return -1e-3 * (np.exp(min(-vsd, 1.2) / 0.05) - 1)
    vov = vs - vth
    i = 0.0
    if vov > 0:
        i = K * (vov * vsd - vsd * vsd / 2) if vsd < vov else K / 2 * vov * vov
    if vsd > BV:                    # avalanche
        i += (vsd - BV) / 0.05
    return i


def run(vth, L, R, C, ichg):
    def f(t, y):
        vc, vd, il = y
        # source resistance RS folded in crudely by limiting the channel current
        i = fet(vc, vd, vth)
        i = min(i, max(vc - vd, 0) / RS) if i > 0 else i
        return [(ichg - i) / C, (i - il) / CD, (vd + VB - R * il) / L]
    s = solve_ivp(f, [0, TEND], [V0, V0, 0.0], method='LSODA', max_step=1e-7, rtol=1e-5, atol=1e-8)
    return s.y[0].min(), s.y[0][-1], s.y[2].max(), s.y[1].min()


print('Vth   L[nH]  R[ohm] C[uF] Ichg[mA] | min Vbat  Vbat@60us   peak I[A]  min Vdrain')
worst = 9
for vth, L, R, C, ichg in itertools.product((0.5, 1.3), (50e-9, 1e-6), (0.05, 0.3), (4.7e-6, 2.0e-6), (0.004, 0.1)):
    vmin, vend, ipk, vdmin = run(vth, L, R, C, ichg)
    worst = min(worst, vmin)
    print(f'{vth:3.1f}  {L*1e9:6.0f}  {R:5.2f}  {C*1e6:4.1f}  {ichg*1e3:6.0f}   | {vmin:7.3f}  {vend:8.3f}  {ipk:8.1f}  {vdmin:8.1f}', flush=True)
print('lowest BAT-node voltage over all cases: %.3f V' % worst)
