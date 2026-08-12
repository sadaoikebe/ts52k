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

# ref -> (x, y, rot_deg)
# U5 kept at rot 180 (already correct). Positions in mm, board coords (y down).
#
# U5 at former ATmega area, nudged NW for fanout to stubs at y=67.38 / x=27.13.
U5 = (22.80, 62.50, 180.0)

# Fixed B.Cu obstacles in this region (do not sit on):
#   U2 (23.57, 50.36), D2 (17.74, 54.41), D3 (11.19, 66.22), R5/R6 near J1
PLACEMENT: dict[str, tuple[float, float, float]] = {
    # --- MCU ---
    "U5": U5,
    # --- 1V1 core (★★★, <2mm of VREG/DVDD) ---
    "C8": (20.80, 57.50, 90.0),   # 1V1 near VREG_VOUT P45
    "C9": (23.20, 57.50, 90.0),   # 1V1 near DVDD P50
    "C10": (21.20, 67.10, 90.0),  # 1V1 near DVDD P23 south
    # --- QSPI series 27Ω north of P51–P55 (1.2mm pitch so 0402 don't stack) ---
    "R9": (23.60, 56.90, 90.0),
    "R10": (24.80, 56.90, 90.0),
    "R11": (26.00, 56.90, 90.0),
    "R12": (27.20, 56.90, 90.0),
    "R13": (28.40, 56.90, 90.0),
    # Flash further NE; rot 0 → pin-1 side west toward SS
    "U4": (34.50, 58.50, 0.0),
    "R2": (29.20, 58.20, 0.0),    # SS pull-up
    "R14": (29.20, 59.50, 0.0),   # BOOTSEL series on SS_N (near QSPI)
    "SW1": (12.50, 58.50, 180.0),  # free; case hole TBD
    # --- USB 27Ω near P46/P47, corridor north to U2 ---
    "R7": (20.90, 55.70, 90.0),
    "R8": (21.90, 55.70, 90.0),
    # --- +3V3 bypass ---
    "C11": (24.50, 55.70, 90.0),  # near P49 north
    "C12": (24.00, 67.30, 90.0),  # near P22 south
    "C13": (19.60, 56.50, 90.0),  # near P48 USB_VDD
    "C15": (27.80, 60.50, 0.0),   # near P1 east
    "C16": (27.80, 63.80, 0.0),   # near P10 east
    "C17": (17.20, 63.50, 0.0),   # west IOVDD (easy)
    "C18": (17.20, 60.00, 0.0),
    "C6": (18.40, 58.50, 0.0),    # ADC_AVDD — lowest priority
    # --- Oscillator south of U5 ---
    "X2": (24.50, 70.00, 180.0),
    "R3": (26.60, 70.00, 0.0),
    "C14": (22.40, 70.00, 0.0),   # X2 VDD bypass (one of the +3V3 caps)
    # --- RUN RC near P26 ---
    "C7": (18.80, 66.30, 0.0),
    "R4": (18.80, 67.50, 0.0),
    # --- LDO east of USB corridor (avoids D2 at 17.7,54.4) ---
    "U3": (29.20, 53.60, 180.0),
    "C3": (31.20, 52.80, 0.0),    # VIN bulk
    "C4": (31.20, 54.20, 0.0),    # VIN
    "C5": (27.20, 52.80, 0.0),    # VOUT bulk
    "C21": (27.20, 54.20, 0.0),   # VOUT
    "C2": (18.40, 57.20, 0.0),    # bulk near U5 west
    # --- Tag-Connect: SW of MCU, clear of D3 (11.2,66.2) ---
    "J2": (14.00, 71.00, 180.0),
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
