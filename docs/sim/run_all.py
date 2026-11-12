"""Run the axisymmetric sweep: board configs x spring scenarios x (unpressed, pressed),
reduce to half-electrode quantities, convert to ADC counts. Writes results/axisym.json and prints tables.

usage: .venv/bin/python run_all.py [--quick]
"""
import json, math, os, sys, time
import numpy as np
import axisym, afe

REF = 1.5 if "--quick" in sys.argv else 1.0
os.makedirs("results", exist_ok=True)

# ----------------------------------------------------------------- board configurations
CFGS = {
    "a_tc69":        {"kind": "tc69"},                                   # 2-layer, B.Cu cut 13 mm sq under pad
    "b_tc52":        {"kind": "tc52"},                                   # L2 solid, 0.2104 mm below
    "c_tc52_l2cut":  {"kind": "tc52", "l2_hole_r": 6.5},                 # L2 cut under pad (r 6.5), L3 solid
    "c2_tc52_l23cut": {"kind": "tc52", "l2_hole_r": 6.5, "l3_hole_r": 6.5},  # L2+L3 cut, L4 = GND (worst)
    "b_h-10%":       {"kind": "tc52", "h12": 0.2104 * 0.9},
    "b_h+10%":       {"kind": "tc52", "h12": 0.2104 * 1.1},
    "b_3313":        {"kind": "tc52", "h12": 0.0994},                    # thin prepreg stack (forbidden in spec)
}

# ----------------------------------------------------------------- spring scenarios (ASSUMED, see md §2)
# rb/rt: mean coil radius at bottom/top turn, n turns, d wire dia, H0/H1 spring top height unpressed/pressed
D = 0.3
FLAT = axisym.T_CU1 + axisym.T_MASK + D + 0.005  # top height when all turns lie on the mask (flat spiral)
SPRINGS = {
    "S1_pad":   dict(rb=5.0, rt=2.5, n=5, d=D, H0=5.0, H1=FLAT),   # base over electrode, flattens fully
    "S2_gap":   dict(rb=6.4, rt=2.25, n=6, d=D, H0=5.0, H1=1.0),   # base in the 6-7 mm gap, 4 mm travel
    "S3_pad1":  dict(rb=5.0, rt=2.5, n=5, d=D, H0=5.0, H1=1.0),    # base over electrode, 4 mm travel
    "S4_gapflat": dict(rb=6.4, rt=2.25, n=6, d=D, H0=5.0, H1=FLAT),
}
KAPPA = 46.27 / (math.pi * (6.0**2 - 2.25**2) / 2)   # real half-pad area / axisym half-annulus area

C_TRACE = {"tc69": None, "tc52": 24.0}   # non-electrode part of a column [pF]; tc69 derived from Fable's 20 pF
CS = 410.0                               # SENSE node with C2 = 330 pF (Fable)


def reduce(C):
    """C = 2x2 Maxwell [[EE, ES],[ES, SS]] of full annulus E and spring S -> half-electrode quantities."""
    cee, ces, css = C[0, 0], -C[0, 1], C[1, 1]
    cas = ces / 2                      # exact by A<->B mirror symmetry
    cm_spring = cas * cas / css        # drive->sense coupling through the floating spring
    cb = KAPPA * cee / 2 - cas * cas / css   # sense half: load to AC ground with spring floating (drive at 0)
    return dict(C_EE=cee, C_ES=ces, C_SS=css, C_AS=cas, Cm=cm_spring, C_B=cb)


def spr(s, h):
    return dict(rb=s["rb"], rt=s["rt"], n=s["n"], d=s["d"], htop=h)


def main():
    out = {}
    t0 = time.time()
    for sk, s in SPRINGS.items():
        for ck, cfg in CFGS.items():
            if sk != "S1_pad" and sk != "S2_gap" and ck not in ("a_tc69", "b_tc52", "c_tc52_l2cut"):
                continue
            row = {}
            for state, h in (("up", s["H0"]), ("down", s["H1"])):
                names, C, info = axisym.capmatrix(cfg, spr(s, h), refine=REF)
                row[state] = reduce(C) | info
            out[f"{sk}|{ck}"] = row
            print(f"[{time.time()-t0:6.0f}s] {sk:10s} {ck:16s} Cm up {row['up']['Cm']:.3f} down {row['down']['Cm']:.3f} "
                  f"C_B {row['up']['C_B']:.2f}", flush=True)
    # travel curves for S1 / S2 on a, b, c
    curves = {}
    for sk in ("S1_pad", "S2_gap"):
        s = SPRINGS[sk]
        hs = list(np.linspace(s["H0"], s["H1"], 6))
        for ck in ("a_tc69", "b_tc52", "c_tc52_l2cut"):
            vals = []
            for h in hs:
                names, C, info = axisym.capmatrix(CFGS[ck], spr(s, h), refine=REF)
                vals.append(reduce(C)["Cm"])
            curves[f"{sk}|{ck}"] = dict(travel=[s["H0"] - h for h in hs], Cm=vals)
            print(f"[{time.time()-t0:6.0f}s] curve {sk} {ck}", [round(v, 3) for v in vals], flush=True)
    # no-spring electrode capacitance (for hand-calc check)
    nospring = {}
    for ck in ("a_tc69", "b_tc52", "c_tc52_l2cut", "b_3313"):
        names, C, info = axisym.capmatrix(CFGS[ck], None, refine=REF)
        nospring[ck] = C[0, 0]
    json.dump(dict(springs=SPRINGS, cfgs=CFGS, res=out, curves=curves, nospring=nospring, refine=REF),
              open("results/axisym.json", "w"), indent=1)
    print("done", time.time() - t0)


if __name__ == "__main__":
    main()
