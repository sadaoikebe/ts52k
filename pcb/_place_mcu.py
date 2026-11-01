#!/usr/bin/env python3
"""
Coarse place RP2040-side components per pcb/PLACEMENT.md.

- Does NOT touch tracks/vias (matrix stubs stay).
- Only rewrites each footprint's top-level (at x y [rot]).
- All targets stay on B.Cu; rotations chosen for roughly correct pin sides.
- Intended as a starting point for manual fine-tuning, not a final layout.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

PCB = Path(__file__).with_name("ts52k.kicad_pcb")

# ref -> (x, y, rot_deg). Board coords: y increases south.
#
# Packing rules used here (from measured pad/courtyard AABBs):
#   U5  ~8.1mm square  | U4 ~9.3x5.8 | U3 ~4.1x3.4 | X2 ~3.7x3.3
#   SW1 ~7.8x5.5       | J2 ~7x4
#   0402 C r90 ~0.67x1.52 | r0 ~1.52x0.67
#   0402 R r90 ~0.70x1.56 | r0 ~1.56x0.70
#   Min centre pitch same-orientation 0402: ~1.3mm
#   Keep ≥0.4mm courtyard gap between all MCU-side parts.
#
# Rotation notes (B.Cu; pad locals already layer-mirrored in the PCB file):
#   U5 180 — USB/QSPI N, GPIO E, SWD/XIN S
#   U4   0 — CS# west toward U5
#   U3 180 — VOUT west, VIN east
#   X2 180 — OUT north toward XIN
#   J2   0 — SWD row faces north
#   SW1 180 — pads face east
#   0402 90 = N–S long axis; 0 = E–W long axis
#
# U5 nudged NW of old ATmega for fanout to stubs y=67.38 / x=27.13.
U5 = (22.80, 62.50, 180.0)

# Fixed B.Cu obstacles: U2 (23.57,50.36), D2 (17.74,54.41), D3 (11.19,66.22), R5/R6
PLACEMENT: dict[str, tuple[float, float, float]] = {
    # --- MCU (body ≈ 18.7–26.9 × 58.4–66.6) ---
    "U5": U5,
    # --- North strip (toward J1/U2): USB, then 1V1/QSPI — leave air from U5 y≤58.4 ---
    # USB 27Ω — 1.4mm pitch; row y=54.8 so 1V1 row above has ≥0.4mm gap
    "R7": (20.80, 54.80, 90.0),   # USB_DM
    "R8": (22.20, 54.80, 90.0),   # USB_DP
    "C13": (23.80, 54.80, 90.0),  # USB_VDD east of R8 (avoid D2 at 17.7,54.4)
    # 1V1 + north IOVDD — y=56.6, 1.5mm pitch
    "C8": (20.50, 56.60, 90.0),
    "C9": (22.00, 56.60, 90.0),
    "C11": (23.50, 56.60, 90.0),
    # QSPI 27Ω — 1.3mm pitch, east of 1V1
    "R9": (25.00, 56.60, 90.0),
    "R10": (26.30, 56.60, 90.0),
    "R11": (27.60, 56.60, 90.0),
    "R12": (28.90, 56.60, 90.0),
    "R13": (30.20, 56.60, 90.0),
    # --- Flash E of QSPI row; CS west ---
    "U4": (36.50, 60.00, 0.0),
    # SS alley U5↔U4
    "R2": (29.00, 58.80, 0.0),
    "R14": (29.00, 60.20, 0.0),
    "C15": (28.80, 62.00, 0.0),
    "C16": (28.80, 64.50, 0.0),
    # --- West of U5 (clear of D2 / SW1) ---
    "C18": (16.40, 59.80, 0.0),
    "C17": (16.40, 63.50, 0.0),
    "C6": (15.80, 57.80, 0.0),   # further from D2
    "C2": (15.00, 53.80, 0.0),   # bulk N of D2, W of SW1
    # --- South of U5 ---
    "C10": (21.50, 68.00, 90.0),
    "C12": (23.50, 68.00, 90.0),
    "C7": (17.20, 66.20, 0.0),
    "R4": (17.20, 67.70, 0.0),
    "X2": (24.50, 71.50, 180.0),
    "C14": (28.00, 70.50, 0.0),
    "R3": (28.00, 72.00, 0.0),
    # --- LDO ---
    "U3": (30.00, 51.50, 180.0),
    "C3": (33.30, 50.80, 0.0),
    "C4": (33.30, 52.20, 0.0),
    "C5": (26.70, 50.80, 0.0),
    "C21": (26.70, 52.20, 0.0),
    # --- Free / mechanical ---
    "SW1": (9.50, 56.00, 180.0),  # further west, clear of C2/D2
    "J2": (12.00, 72.50, 0.0),
}


def fmt_at(x: float, y: float, rot: float) -> str:
    # Match existing style: drop .0 on integers-ish, keep reasonable precision
    def n(v: float) -> str:
        s = f"{v:.6f}".rstrip("0").rstrip(".")
        return s if s else "0"

    if abs(rot) < 1e-9 or abs(rot - 0.0) < 1e-9:
        # Keep explicit 0 rot only if we want; many footprints omit 0.
        # Always write rot for consistency when non-zero; for 0 write without.
        return f"(at {n(x)} {n(y)})"
    # Normalize 180.0 -> 180
    rs = n(rot)
    return f"(at {n(x)} {n(y)} {rs})"


def find_footprint_span(text: str, ref: str) -> tuple[int, int]:
    m = re.search(rf'\(property\s+"Reference"\s+"{re.escape(ref)}"', text)
    if not m:
        raise KeyError(ref)
    start = text.rfind("(footprint", 0, m.start())
    if start < 0:
        raise KeyError(f"footprint start for {ref}")
    depth = 0
    for j in range(start, len(text)):
        c = text[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return start, j + 1
    raise KeyError(f"unbalanced footprint {ref}")


def replace_footprint_at(block: str, x: float, y: float, rot: float) -> str:
    """Replace only the footprint-level (at ...) — the first top-level at after header."""
    # Footprint form:
    # (footprint "..."
    #   (layer ...)
    #   (uuid ...)
    #   (at X Y [R])
    # Match the first (at ...) that appears before (property "Reference"
    ref_pos = block.find('(property "Reference"')
    head = block[:ref_pos] if ref_pos >= 0 else block[:800]
    m = re.search(r"\(at\s+[-\d.]+\s+[-\d.]+(?:\s+[-\d.]+)?\)", head)
    if not m:
        raise ValueError("no footprint-level (at ...) found")
    new_at = fmt_at(x, y, rot)
    return block[: m.start()] + new_at + block[m.end() :]


def main() -> None:
    text = PCB.read_text(encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = PCB.with_name(f"ts52k.kicad_pcb.bak_place_{stamp}")
    shutil.copy2(PCB, backup)
    print(f"backup: {backup.name}")

    missing = []
    updated = []
    for ref, (x, y, rot) in sorted(PLACEMENT.items(), key=lambda kv: kv[0]):
        try:
            s, e = find_footprint_span(text, ref)
        except KeyError:
            missing.append(ref)
            continue
        old_block = text[s:e]
        new_block = replace_footprint_at(old_block, x, y, rot)
        if new_block == old_block:
            # still count as ok (already there)
            updated.append((ref, x, y, rot, "unchanged"))
        else:
            text = text[:s] + new_block + text[e:]
            updated.append((ref, x, y, rot, "moved"))

    PCB.write_text(text, encoding="utf-8")

    print(f"updated {len(updated)} footprints:")
    for ref, x, y, rot, st in updated:
        print(f"  {ref:4s} -> ({x:7.2f}, {y:7.2f}) rot={rot:6.1f}  [{st}]")
    if missing:
        print("MISSING:", ", ".join(missing))

    # quick sanity: all should be on-board y>=41
    off = [r for r, x, y, rot, st in updated if y < 41]
    if off:
        print("WARNING still off-board:", off)
    else:
        print("all targets y>=41 (on-board band)")


if __name__ == "__main__":
    main()
