"""For every CPL point: which CPL angle makes JLCPCB's EasyEDA land (numbered pads) land on the board copper.

Board copper: pad centres of the placed footprint (top view, mm, x right, y down, relative to the footprint origin),
read with pcbnew from pcb/ts52k.kicad_pcb.  EasyEDA pads: audit.json (raw/<C>-components.json or -svgs.json).
JLCPCB's interpretation of 'Rotation' for Layer=Bottom is not defined in its public documentation, so three models
are evaluated (R = counter-clockwise rotation seen from the top, Mx = left-right mirror, My = top-bottom mirror):
  A  copper = R(t) . My . E    -- KiCad's own bottom convention; equals feeding the raw KiCad angle (current export.py)
  B  copper = Mx . R(t) . E    -- 'mirror the angle' (t = 180 - kicad + corr): kicad-jlcpcb-tools since 2022 (#159),
                                  KiBot mirror_bottom (2023); reported to match JLCPCB's upload preview
  C  copper = R(t) . Mx . E    -- (t = kicad + 180 + corr): reported in kicad-jlcpcb-tools #636 (2025) as what JLCPCB's
                                  engineers programmed and what was assembled correctly
A and C always differ by exactly 180 deg.  B equals A for parts at +-90 deg, and equals C for parts at 0/180 deg.
Usage: python3 required_angles.py   (needs pcbnew; reads audit.json and the CPL)
"""
import csv, json, math
from pathlib import Path
import pcbnew

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
audit = {r["lcsc"]: r for r in json.loads((HERE / "audit.json").read_text())}
cpl = {r["Designator"]: r for r in csv.DictReader((ROOT / "pcb/jlcpcb/assembly/ts52k-cpl.csv").open())}
board = pcbnew.LoadBoard(str(ROOT / "pcb/ts52k.kicad_pcb"))

def R(t, p):
    c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
    return (p[0] * c + p[1] * s, -p[0] * s + p[1] * c)   # CCW on screen with y down

MODELS = {"A": lambda t, p: R(t, (p[0], -p[1])),
          "B": lambda t, p: (lambda q: (-q[0], q[1]))(R(t, p)),
          "C": lambda t, p: R(t, (-p[0], p[1]))}

def numbered(part, pads, kind):
    """Same explicit aliases as audit.py (USB-C merged pins / shield tabs, JST tabs, tact-switch rows)."""
    out = {}
    for p in pads:
        n = p["number"]
        if not n:
            continue
        if part == "C165948":
            n = {"A1B12": "A1", "B1A12": "B1", "A4B9": "A4", "B4A9": "B4"}.get(n, n)
            if kind == "k" and n in {"B12", "A12", "B9", "A9"}:
                continue
            if (kind == "k" and n == "SH") or (kind == "e" and n in {"1", "2", "3", "4"}):
                n = "SH%d" % len([k for k in out if k.startswith("SH")])
        out.setdefault(n, []).append((p["x"], p["y"]))
    return out

def score(kd, ed, f):
    """Best translation, rms over pads; SH tabs / duplicate rows compared as unordered sets."""
    pairs = []
    for n in kd:
        if n not in ed:
            continue
        ks, es = kd[n], [f(e) for e in ed[n]]
        for k in ks:
            pairs.append((k, min(es, key=lambda e: math.hypot(k[0] - e[0], k[1] - e[1]))))
    tx = sum(k[0] - e[0] for k, e in pairs) / len(pairs)
    ty = sum(k[1] - e[1] for k, e in pairs) / len(pairs)
    return math.sqrt(sum((k[0] - e[0] - tx) ** 2 + (k[1] - e[1] - ty) ** 2 for k, e in pairs) / len(pairs)), (tx, ty)

rows = []
for part, a in audit.items():
    for ref in a["refs"]:
        fp = board.FindFootprintByReference(ref)
        c = fp.GetPosition()
        kp = [dict(number=p.GetNumber(), x=(p.GetPosition().x - c.x) / 1e6, y=(p.GetPosition().y - c.y) / 1e6) for p in fp.Pads()]
        if part == "C318884":   # KiCad numbers the joined pairs alike; EasyEDA 1..4 = A..D in footprint frame
            norm = {(round(q["x"], 3), round(q["y"], 3)): q for q in a["kicad_pads"]}
            # map each board pad back to its normalized pad by order (same pad order in both lists)
            kp = [dict(k, number=str(1 + (n["x"] > 0) + 2 * (n["y"] > 0))) for k, n in zip(kp, [q for q in a["kicad_pads"]])]
        kd = numbered(part, kp, "k")
        ed = numbered(part, a["easyeda_pads"], "e")
        if part == "C165948":   # SH tabs: compare as one unordered group
            for d in (kd, ed):
                sh = [v for k in list(d) if k.startswith("SH") for v in d.pop(k)]
                d["SH"] = sh
        res = {}
        for m, fn in MODELS.items():
            fits = sorted(((score(kd, ed, lambda p, t=t, fn=fn: fn(t, p))[0], t) for t in (0, 90, 180, 270)))
            res[m] = dict(best=fits[0][1], rms=round(fits[0][0], 3), second=fits[1][1], second_rms=round(fits[1][0], 3))
        rows.append(dict(ref=ref, lcsc=part, kicad=fp.GetOrientationDegrees(), cpl=float(cpl[ref]["Rotation"]), models=res))

(HERE / "required-angles.json").write_text(json.dumps(rows, indent=1) + "\n")
norm = lambda v: round(v) % 360
for r in rows:
    m = r["models"]
    tag = "  ".join(f'{k}:{v["best"]:3}({v["rms"]:.2f}/{v["second"]}:{v["second_rms"]:.2f})' for k, v in m.items())
    print(f'{r["ref"]:4} {r["lcsc"]:9} kicad={norm(r["kicad"]):3} cpl={norm(r["cpl"]):3}  {tag}  '
          f'A_ok={norm(r["cpl"]) == m["A"]["best"]}')
