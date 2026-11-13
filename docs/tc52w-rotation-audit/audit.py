"""TC52 wireless CPL rotation audit: EasyEDA (JLCPCB) numbered lands vs the footprints on the board.

Inputs : board.json from extract_board.py; raw/<C>-components.json (GET https://easyeda.com/api/products/<C>/components),
         raw/<C>-svgs.json (GET .../svgs, the endpoint behind JLCPCB's public footprint viewer), raw/<C>-lcsc.json
         (GET https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=<C>); pcb/jlcpcb/assembly/ts52k-{bom,cpl}.csv.
Output : audit.json (per BOM line: both land sources, symbol pin names, cardinal-rotation fits) and a printed summary.
Source of the land data: JLCEDA/EasyEDA Official Library (嘉立创EDA/EasyEDA官方库), https://lceda.cn/ , https://easyeda.com/ .
Coordinates: mm, footprint front side at 0 deg, x right, y down.  EasyEDA unit = 10 mil = 0.254 mm.
This does not decide corrections by itself: the fits are evidence that a person reads together with the pin names.
"""
import csv, json, math, sys, xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
U = 0.254

def pads_from_components(part):
    p = RAW / f"{part}-components.json"
    try:
        d = json.loads(p.read_text())["result"]
    except Exception:
        return None, None, None
    pk = d["packageDetail"]["dataStr"]
    ox, oy = float(pk["head"]["x"]), float(pk["head"]["y"])
    pads = []
    for s in pk["shape"]:
        if not s.startswith("PAD~"):
            continue
        f = s.split("~")
        pads.append(dict(number=f[8], x=round((float(f[2]) - ox) * U, 4), y=round((float(f[3]) - oy) * U, 4),
                         w=round(float(f[4]) * U, 4), h=round(float(f[5]) * U, 4), shape=f[1], layer=f[6],
                         angle=float(f[11] or 0), hole_r=round(float(f[9] or 0) * U, 4)))
    pins = {}
    for s in d["dataStr"]["shape"]:
        if s.startswith("P~"):
            seg = s.split("^^")
            name = seg[3].split("~")[4]
            num = seg[4].split("~")[4]
            pins[num] = name
    meta = dict(package=pk["head"]["c_para"].get("package"), uuid=d["packageDetail"]["uuid"],
                symbol_para=d["dataStr"]["head"]["c_para"])
    return pads, pins, meta

def pads_from_svgs(part):
    d = json.loads((RAW / f"{part}-svgs.json").read_text())["result"]
    pads, pins, meta = [], {}, {}
    for r in d:
        tree = ET.fromstring(r["svg"])
        group = next(e for e in tree if "c_origin" in e.attrib)
        ox, oy = map(float, group.attrib["c_origin"].split(","))
        if r["docType"] == 4:
            meta = dict(package=dict(x.split("`")[i:i+2] for x in [group.attrib.get("c_para", "")] for i in range(0, 0)) or None,
                        c_para=group.attrib.get("c_para"))
            for e in group.iter():
                a = e.attrib
                if a.get("c_partid") != "part_pad":
                    continue
                x, y = map(float, a["c_origin"].split(","))
                pads.append(dict(number=a.get("number"), x=round((x - ox) * U, 4), y=round((y - oy) * U, 4),
                                 w=round(float(a["c_width"]) * U, 4), h=round(float(a["c_height"]) * U, 4),
                                 shape=a["c_shape"], layer=a.get("layerid"), angle=float(a.get("c_rotation", 0) or 0)))
        elif r["docType"] == 2:
            for e in group.iter():
                if e.attrib.get("c_partid") != "part_pin":
                    continue
                texts = [t.text for t in e.iter() if t.tag.endswith("text")]
                if len(texts) >= 2:
                    pins[texts[1]] = texts[0]
    return pads, pins, meta

def lcsc_meta(part):
    try:
        r = json.loads((RAW / f"{part}-lcsc.json").read_text())["result"]
        return dict(code=r.get("productCode"), model=r.get("productModel"), brand=r.get("brandNameEn"),
                    package=r.get("encapStandard"), pdf=r.get("pdfUrl"))
    except Exception as ex:
        return dict(error=str(ex))

def fits(kd, ed):
    common = sorted(set(kd) & set(ed))
    out = []
    for angle in (0, 90, 180, 270):
        c, s = round(math.cos(math.radians(angle))), round(math.sin(math.radians(angle)))
        pts = {n: (c * ed[n]["x"] - s * ed[n]["y"], s * ed[n]["x"] + c * ed[n]["y"]) for n in common}
        tx = sum(kd[n]["x"] - pts[n][0] for n in common) / len(common)
        ty = sum(kd[n]["y"] - pts[n][1] for n in common) / len(common)
        res = {n: math.hypot(kd[n]["x"] - pts[n][0] - tx, kd[n]["y"] - pts[n][1] - ty) for n in common}
        out.append(dict(rotation_easyeda_to_kicad_cw=angle, translation=[round(tx, 4), round(ty, 4)],
                        rms=round(math.sqrt(sum(v * v for v in res.values()) / len(common)), 4), max=round(max(res.values()), 4)))
    return out

def aliases(part, k, e):
    """Explicit pad correspondences where the two libraries name the same copper differently."""
    if part == "C165948":   # USB-C: EasyEDA merges A1/B12 etc. on one land; SH tabs are 1..4 there
        amap = {"A1B12": "A1", "B1A12": "B1", "A4B9": "A4", "B4A9": "B4"}
        e = [dict(p, number=amap.get(p["number"], p["number"])) for p in e]
        k = [p for p in k if p["number"] not in {"B12", "A12", "B9", "A9"}]
        def sh(p):
            return "SH_" + ("R" if p["x"] > 0 else "L") + ("F" if p["y"] > 0 else "B")
        k = [dict(p, number=sh(p)) if p["number"] == "SH" else p for p in k]
        e = [dict(p, number=sh(p)) if p["number"] in {"1", "2", "3", "4"} else p for p in e]
    elif part == "C295747":  # JST PH SMT: mounting tabs MP (KiCad) = 3/4 (EasyEDA)
        k = [dict(p, number="MP_R" if p["x"] > 0 else "MP_L") if p["number"] == "MP" else p for p in k]
        e = [dict(p, number="MP_R" if p["x"] > 0 else "MP_L") if p["number"] in {"3", "4"} else p for p in e]
    elif part == "C318884":  # tact switch: KiCad numbers each internally joined pair alike; EasyEDA 1..4 = A..D
        k = [dict(p, number=str(1 + (p["x"] > 0) + 2 * (p["y"] > 0))) for p in k]
    return k, e

def main():
    root = HERE.parents[1]
    board = json.loads(Path(sys.argv[1]).read_text())["board"]
    bom = list(csv.DictReader((root / "pcb/jlcpcb/assembly/ts52k-bom.csv").open()))
    cpl = {r["Designator"]: r for r in csv.DictReader((root / "pcb/jlcpcb/assembly/ts52k-cpl.csv").open())}
    result = []
    for row in bom:
        part = row["LCSC Part #"]
        refs = row["Designator"].split(",")
        inst = board[refs[0]]
        k = [p for p in inst["pads_normalized"] if p["number"]]
        cpads, cpins, cmeta = pads_from_components(part)
        spads, spins, smeta = pads_from_svgs(part)
        e = cpads if cpads is not None else spads
        src = "components" if cpads is not None else "svgs"
        agree = None
        if cpads is not None:
            sd = {p["number"]: p for p in spads}
            agree = (sorted(p["number"] for p in cpads) == sorted(sd)
                     and all(abs(p["x"] - sd[p["number"]]["x"]) < 0.005 and abs(p["y"] - sd[p["number"]]["y"]) < 0.005 for p in cpads))
        ka, ea = aliases(part, k, e)
        kd = {}
        for p in ka:
            kd.setdefault(p["number"], p)
        ed = {}
        for p in ea:
            ed.setdefault(p["number"], p)
        f = fits(kd, ed)
        best = min(f, key=lambda x: x["rms"])
        kicad_pins = {}
        for r in refs:
            for p in board[r]["pads_normalized"]:
                kicad_pins.setdefault(p["number"], set()).add(p["pinfunction"])
        rec = dict(lcsc=part, refs=refs, footprint=row["Footprint"], comment=row["Comment"], source=src,
                   components_vs_svgs_same_pads=agree, lcsc_meta=lcsc_meta(part), easyeda_meta=cmeta or smeta,
                   easyeda_symbol_pins=cpins or spins, svgs_symbol_pins=spins,
                   kicad_pin_functions={n: sorted(v) for n, v in kicad_pins.items()},
                   kicad_pads=k, easyeda_pads=e, unmatched=sorted(set(kd) ^ set(ed)), fits=f, best=best,
                   instances=[dict(ref=r, kicad_rot=board[r]["angle"], cpl_rot=float(cpl[r]["Rotation"]),
                                   x=board[r]["x"], y=board[r]["y"]) for r in refs])
        result.append(rec)
        second = sorted(f, key=lambda x: x["rms"])[1]
        print(f'{part:10} {",".join(refs)[:28]:28} src={src:10} agree={agree!s:5} n={len(kd)} best={best["rotation_easyeda_to_kicad_cw"]:3} '
              f'rms={best["rms"]:.3f} max={best["max"]:.3f} 2nd={second["rotation_easyeda_to_kicad_cw"]}/{second["rms"]:.3f} unmatched={rec["unmatched"]}')
    (HERE / "audit.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")

main()
