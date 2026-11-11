"""Export JLCPCB fabrication and bottom-side assembly files from the current KiCad project.

Run this after saving the project. It does not read the old JLCPCB project database.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path


PCB_DIR = Path(__file__).resolve().parent.parent
JLC_DIR = PCB_DIR / "jlcpcb"
BOARD = PCB_DIR / "ts52k.kicad_pcb"
SCHEMATIC = PCB_DIR / "ts52k.kicad_sch"
PROJECT = PCB_DIR / "ts52k.kicad_pro"

# CPL rotation offsets (degrees) keyed by LCSC part number, for parts whose
# JLCPCB library orientation has been verified against the EasyEDA/manufacturer
# data and differs from KiCad's footprint orientation. Only add an entry with
# that evidence; everything else keeps the raw KiCad rotation and relies on
# the order-time placement preview.
# - C15127 (AO3401A, SOT-23): the EasyEDA land definition is rotated 180
#   degrees vs KiCad's SOT-23, with identical pin numbering (1=G, 2=S, 3=D).
#   A 180 degree offset is unaffected by the bottom-side board flip.
ROTATION_CORRECTIONS = {"C15127": 180.0}


def cli_path(override):
    if override:
        return override
    found = shutil.which("kicad-cli")
    if found:
        return found
    if os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "KiCad" / "10.0" / "bin" / "kicad-cli.exe"
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("kicad-cli was not found; pass its path with --kicad-cli")


def run(cli, *args):
    subprocess.run([cli, *map(str, args)], cwd=PCB_DIR, check=True)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", help="path to kicad-cli")
    args = parser.parse_args()
    assembly_dir = JLC_DIR / "assembly"
    gerber_dir = JLC_DIR / "gerber"
    assembly_dir.mkdir(parents=True, exist_ok=True)
    gerber_dir.mkdir(parents=True, exist_ok=True)
    status_file = assembly_dir / "export-status.txt"
    status_file.write_text(
        "EXPORT IN PROGRESS OR FAILED. Previous output files may be stale; do not order from them.\n",
        encoding="utf-8",
    )
    cli = cli_path(args.kicad_cli)
    settings = json.loads(PROJECT.read_text(encoding="utf-8"))
    edge_clearance = settings["board"]["design_settings"]["rules"]["min_copper_edge_clearance"]
    if edge_clearance < 0.2:
        raise RuntimeError(f"Copper-to-edge rule is only {edge_clearance} mm; JLCPCB requires at least 0.2 mm")

    with tempfile.TemporaryDirectory(prefix="ts52k-jlc-") as temp_dir:
        temp = Path(temp_dir)
        drc_file = temp / "drc.json"
        erc_file = temp / "erc.json"
        raw_bom = temp / "bom.csv"
        raw_positions = temp / "positions.csv"
        plotted = temp / "gerbers"
        plotted.mkdir()

        run(cli, "pcb", "drc", "--all-track-errors", "--schematic-parity", "--refill-zones", "--format", "json", "-o", drc_file, BOARD)
        drc = json.loads(drc_file.read_text(encoding="utf-8"))
        shutil.copyfile(drc_file, assembly_dir / "drc.json")
        drc_errors = [item for item in drc["violations"] if item["severity"] == "error"]
        if drc_errors or drc["unconnected_items"] or drc["schematic_parity"]:
            raise RuntimeError("DRC errors, unconnected items or schematic parity issues: inspect " + str(assembly_dir / "drc.json"))

        run(cli, "sch", "erc", "--format", "json", "-o", erc_file, SCHEMATIC)
        erc = json.loads(erc_file.read_text(encoding="utf-8"))
        shutil.copyfile(erc_file, assembly_dir / "erc.json")
        erc_errors = [v for sheet in erc["sheets"] for v in sheet["violations"] if v["severity"] == "error"]
        if erc_errors:
            raise RuntimeError("ERC errors: inspect " + str(assembly_dir / "erc.json"))

        run(cli, "sch", "export", "bom", "--fields", "Reference,Value,Footprint,LCSC,MPN",
            "--labels", "Reference,Value,Footprint,LCSC,MPN", "-o", raw_bom, SCHEMATIC)
        # Include mixed SMD/PTH J1 regardless of the footprint assembly attribute.
        run(cli, "pcb", "export", "pos", "--side", "back", "--format", "csv", "--units", "mm",
            "-o", raw_positions, BOARD)
        with raw_bom.open(encoding="utf-8-sig", newline="") as source:
            bom_rows = list(csv.DictReader(source))
        with raw_positions.open(encoding="utf-8-sig", newline="") as source:
            positions = list(csv.DictReader(source))

        bom = {row["Reference"]: row for row in bom_rows}
        pos = {row["Ref"]: row for row in positions}
        if len(bom) != len(bom_rows) or len(pos) != len(positions):
            raise RuntimeError("Duplicate component references in BOM or position file")
        hand_soldered = {ref for ref in bom if re.fullmatch(r"MX\d+", ref)} | {"SW2", "J2"}
        expected = set(bom) - hand_soldered
        if set(pos) != expected:
            raise RuntimeError(f"BOM/CPL mismatch: missing positions {sorted(expected - set(pos))}; "
                               f"unexpected positions {sorted(set(pos) - expected)}")
        if not {"J1", "SW1"}.issubset(pos):
            raise RuntimeError("The USB connector J1 and BOOTSEL switch SW1 must both be assembled")
        if any(row["Side"].lower() != "bottom" for row in positions):
            raise RuntimeError("Every assembled component must be on the bottom side")
        missing_parts = [ref for ref in sorted(expected) if not re.fullmatch(r"C\d+", bom[ref]["LCSC"])]
        if missing_parts:
            raise RuntimeError("Missing LCSC part numbers: " + ", ".join(missing_parts))

        grouped = defaultdict(list)
        for ref in sorted(expected, key=lambda x: (re.sub(r"\d+$", "", x), int(re.search(r"\d+$", x).group()))):
            row = bom[ref]
            grouped[(row["Value"], row["Footprint"], row["LCSC"])].append(ref)
        jlc_bom = [
            {"Comment": value, "Designator": ",".join(refs), "Footprint": footprint, "LCSC Part #": lcsc}
            for (value, footprint, lcsc), refs in grouped.items()
        ]
        jlc_cpl = []
        for row in positions:
            rotation = row["Rot"]
            offset = ROTATION_CORRECTIONS.get(bom[row["Ref"]]["LCSC"])
            if offset:
                rotation = f"{(float(rotation) + offset) % 360:.6f}"
            jlc_cpl.append(
                {"Designator": row["Ref"], "Mid X": row["PosX"], "Mid Y": row["PosY"],
                 "Layer": "Bottom", "Rotation": rotation}
            )

        run(cli, "pcb", "export", "gerbers", "--layers",
            "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts",
            "--subtract-soldermask", "--check-zones", "-o", plotted, BOARD)
        run(cli, "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "absolute",
            "--excellon-separate-th", "--excellon-units", "mm", "-o", plotted, BOARD)

        output_bom = assembly_dir / "ts52k-bom.csv"
        output_cpl = assembly_dir / "ts52k-cpl.csv"
        output_zip = gerber_dir / "ts52k-gerbers.zip"
        write_csv(output_bom, ["Comment", "Designator", "Footprint", "LCSC Part #"], jlc_bom)
        write_csv(output_cpl, ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"], jlc_cpl)
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(plotted.iterdir()):
                if path.is_file():
                    archive.write(path, path.name)
        sources = [BOARD, PROJECT, SCHEMATIC, PCB_DIR / "mdbt50q.kicad_sch", PCB_DIR / "ts52k.kicad_dru",
                   PCB_DIR / "ts52k.kicad_sym", PCB_DIR / "sym-lib-table", PCB_DIR / "fp-lib-table",
                   PCB_DIR / "tag-connect.kicad_sym"]
        manifest = {
            "source_sha256": {str(path.relative_to(PCB_DIR)): sha256(path) for path in sources},
            "output_sha256": {str(path.relative_to(JLC_DIR)): sha256(path) for path in [output_zip, output_bom, output_cpl]},
            "assembly_references": len(expected),
            "bom_line_items": len(jlc_bom),
            "drc_warnings": sum(v["severity"] == "warning" for v in drc["violations"]),
            "erc_warnings": sum(v["severity"] == "warning" for sheet in erc["sheets"] for v in sheet["violations"]),
        }
        (assembly_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        status_file.write_text(
            "EXPORT COMPLETED. Review the source hashes, live stock, component rotations and JLCPCB DFM before ordering.\n",
            encoding="utf-8",
        )
        print(f"Exported {len(expected)} bottom-side parts in {len(jlc_bom)} BOM groups.")
        print(f"Gerbers: {output_zip}\nBOM: {output_bom}\nCPL: {output_cpl}")
        print("Review live stock, component rotations and JLCPCB DFM before ordering.")


if __name__ == "__main__":
    main()
