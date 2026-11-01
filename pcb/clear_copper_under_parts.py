#!/usr/bin/env python3
"""
Clear tracks/vias that sit under selected footprints on a KiCad PCB.

Designed for the RP2040 re-layout of ts52k: after you move B.Cu MCU-side
parts onto the old ATmega island, matrix/power copper still runs through
those footprints. This clips B.Cu segments to the footprint outline and
deletes vias under the body — without a global "delete dangling tracks"
pass that would eat the matrix stubs.

Usage (from repo root or pcb/):

  python pcb/clear_copper_under_parts.py              # default MCU-side refs
  python pcb/clear_copper_under_parts.py --dry-run    # report only
  python pcb/clear_copper_under_parts.py --refs U5,U4,C8,C9,C10
  python pcb/clear_copper_under_parts.py --margin 0.3

Default targets are the RP2040-side parts listed in PLACEMENT.md (the ones
that started life off-board). Pass --refs after you settle final placement.

Safety:
  - Only B.Cu segments are clipped (parts live on the back).
  - Segments that merely pass near a part are shortened, not deleted whole,
    so matrix stub tips outside the body stay for later fanout.
  - Writes a timestamped .bak_* next to the PCB unless --no-backup.
  - Does NOT run Cleanup Tracks & Vias.
"""
from __future__ import annotations

import argparse
import math
import re
import shutil
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# RP2040-side refs from PLACEMENT.md (off-board set during the port).
DEFAULT_REFS = """
U5 U4 U3 X2 J2 SW1
R2 R3 R4 R7 R8 R9 R10 R11 R12 R13 R14
C2 C3 C4 C5 C6 C7 C8 C9 C10 C11 C12 C13 C14 C15 C16 C17 C18 C21
""".split()

DEFAULT_MARGIN_MM = 0.25
SAMPLE_STEP_MM = 0.15
MIN_SEGMENT_MM = 0.05


@dataclass
class AABB:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def expand(self, m: float) -> "AABB":
        return AABB(self.xmin - m, self.ymin - m, self.xmax + m, self.ymax + m)

    def contains(self, x: float, y: float, pad: float = 0.0) -> bool:
        return (
            self.xmin - pad <= x <= self.xmax + pad
            and self.ymin - pad <= y <= self.ymax + pad
        )

    def overlaps(self, other: "AABB") -> bool:
        return not (
            self.xmax < other.xmin
            or self.xmin > other.xmax
            or self.ymax < other.ymin
            or self.ymin > other.ymax
        )

    def union(self, other: "AABB") -> "AABB":
        return AABB(
            min(self.xmin, other.xmin),
            min(self.ymin, other.ymin),
            max(self.xmax, other.xmax),
            max(self.ymax, other.ymax),
        )


def find_footprint_span(text: str, ref: str) -> tuple[int, int]:
    m = re.search(rf'\(property\s+"Reference"\s+"{re.escape(ref)}"', text)
    if not m:
        raise KeyError(ref)
    start = text.rfind("(footprint", 0, m.start())
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return start, j + 1
    raise KeyError(ref)


def parse_at(block: str) -> tuple[float, float, float]:
    m = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", block)
    if not m:
        raise ValueError("footprint missing (at ...)")
    return float(m.group(1)), float(m.group(2)), float(m.group(3) or 0)


def world_xy(lx: float, ly: float, cx: float, cy: float, rot: float) -> tuple[float, float]:
    # Pad coords on B.Cu footprints in the file are already layer-mirrored.
    r = math.radians(rot)
    cos, sin = math.cos(r), math.sin(r)
    return cx + lx * cos - ly * sin, cy + lx * sin + ly * cos


def footprint_aabb(block: str, margin: float) -> AABB:
    cx, cy, rot = parse_at(block)
    boxes: list[AABB] = []
    seen: set[str] = set()

    for m in re.finditer(r'\(pad\s+"([^"]+)"\s+\w+\s+\w+', block):
        pad = m.group(1)
        if pad in seen:
            continue
        start = m.start()
        depth = 0
        chunk = ""
        for j in range(start, min(len(block), start + 5000)):
            if block[j] == "(":
                depth += 1
            elif block[j] == ")":
                depth -= 1
                if depth == 0:
                    chunk = block[start : j + 1]
                    break
        if not chunk:
            continue
        seen.add(pad)
        at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", chunk)
        size = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)\)", chunk)
        if not at or not size:
            continue
        lx, ly = float(at.group(1)), float(at.group(2))
        sx, sy = float(size.group(1)), float(size.group(2))
        hx, hy = sx / 2, sy / 2
        corners = [
            (lx - hx, ly - hy),
            (lx - hx, ly + hy),
            (lx + hx, ly - hy),
            (lx + hx, ly + hy),
        ]
        ws = [world_xy(x, y, cx, cy, rot) for x, y in corners]
        xs = [p[0] for p in ws]
        ys = [p[1] for p in ws]
        boxes.append(AABB(min(xs), min(ys), max(xs), max(ys)))

    for m in re.finditer(
        r"\(fp_line\s*\n\s*\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\n\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)"
        r'[\s\S]*?\(layer\s+"(?:B|F)\.CrtYd"\)',
        block,
    ):
        for lx, ly in (
            (float(m.group(1)), float(m.group(2))),
            (float(m.group(3)), float(m.group(4))),
        ):
            wx, wy = world_xy(lx, ly, cx, cy, rot)
            boxes.append(AABB(wx, wy, wx, wy))

    if not boxes:
        return AABB(cx - 3, cy - 3, cx + 3, cy + 3).expand(margin)

    u = boxes[0]
    for b in boxes[1:]:
        u = u.union(b)
    return u.expand(margin)


def extract_blocks(text: str, head: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for m in re.finditer(rf"(?m)^[\t ]*\({re.escape(head)}\b", text):
        start = text.index("(", m.start())
        depth = 0
        for j in range(start, len(text)):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    out.append((start, j + 1, text[start : j + 1]))
                    break
    return out


def point_forbidden(x: float, y: float, boxes: list[AABB], pad: float) -> bool:
    return any(b.contains(x, y, pad) for b in boxes)


def clip_segment(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    width: float,
    boxes: list[AABB],
    sample_step: float,
) -> list[tuple[float, float, float, float]]:
    """Outside-only sub-segments after removing runs under boxes."""
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 1e-9:
        if point_forbidden(x1, y1, boxes, width / 2):
            return []
        return [(x1, y1, x2, y2)]

    sa = AABB(
        min(x1, x2) - width / 2,
        min(y1, y2) - width / 2,
        max(x1, x2) + width / 2,
        max(y1, y2) + width / 2,
    )
    if not any(sa.overlaps(b) for b in boxes):
        return [(x1, y1, x2, y2)]

    n = max(2, int(math.ceil(length / sample_step)))
    pad = width / 2 + 0.05
    pts: list[tuple[float, float]] = []
    keep: list[bool] = []
    for i in range(n + 1):
        t = i / n
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        pts.append((x, y))
        keep.append(not point_forbidden(x, y, boxes, pad))

    runs: list[tuple[int, int]] = []
    i = 0
    while i <= n:
        if not keep[i]:
            i += 1
            continue
        j = i
        while j <= n and keep[j]:
            j += 1
        runs.append((i, j - 1))
        i = j

    out: list[tuple[float, float, float, float]] = []
    for a, b in runs:
        ax, ay = pts[a]
        bx, by = pts[b]
        if math.hypot(bx - ax, by - ay) < MIN_SEGMENT_MM:
            continue
        out.append((ax, ay, bx, by))
    return out


def fmt_num(v: float) -> str:
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s if s else "0"


def rewrite_segment_block(block: str, x1: float, y1: float, x2: float, y2: float) -> str:
    block = re.sub(
        r"\(start\s+[-\d.]+\s+[-\d.]+\)",
        f"(start {fmt_num(x1)} {fmt_num(y1)})",
        block,
        count=1,
    )
    block = re.sub(
        r"\(end\s+[-\d.]+\s+[-\d.]+\)",
        f"(end {fmt_num(x2)} {fmt_num(y2)})",
        block,
        count=1,
    )
    return block


def clone_segment(block: str, x1: float, y1: float, x2: float, y2: float) -> str:
    b = rewrite_segment_block(block, x1, y1, x2, y2)
    return re.sub(
        r'\(uuid\s+"[^"]+"\)',
        f'(uuid "{uuid.uuid4()}")',
        b,
        count=1,
    )


def parse_refs(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_REFS)
    parts = re.split(r"[\s,;]+", raw.strip())
    return [p for p in parts if p]


def run(
    pcb_path: Path,
    refs: list[str],
    margin: float,
    layer: str,
    dry_run: bool,
    no_backup: bool,
    sample_step: float,
) -> int:
    text = pcb_path.read_text(encoding="utf-8")

    boxes: list[AABB] = []
    missing: list[str] = []
    print(f"PCB: {pcb_path}")
    print(f"refs ({len(refs)}): {' '.join(refs)}")
    print(f"layer={layer}  margin={margin} mm  dry_run={dry_run}")
    for ref in refs:
        try:
            s, e = find_footprint_span(text, ref)
        except KeyError:
            missing.append(ref)
            continue
        bb = footprint_aabb(text[s:e], margin)
        boxes.append(bb)
        print(
            f"  {ref:4s} AABB "
            f"({bb.xmin:7.2f},{bb.ymin:7.2f})-({bb.xmax:7.2f},{bb.ymax:7.2f})"
        )
    if missing:
        print("MISSING footprints:", ", ".join(missing))
    if not boxes:
        print("no target boxes; nothing to do")
        return 1

    segs = extract_blocks(text, "segment")
    vias = extract_blocks(text, "via")
    print(f"\nboard has {len(segs)} segments, {len(vias)} vias")

    edits: list[tuple[int, int, str | None]] = []
    n_deleted = n_clipped = n_split = 0
    net_del: Counter[str] = Counter()
    net_clip: Counter[str] = Counter()

    for s, e, block in segs:
        layer_m = re.search(r'\(layer\s+"([^"]+)"\)', block)
        if not layer_m or layer_m.group(1) != layer:
            continue
        sm = re.search(
            r"\(start\s+([-\d.]+)\s+([-\d.]+)\)\s*\n\s*\(end\s+([-\d.]+)\s+([-\d.]+)\)",
            block,
        )
        wm = re.search(r"\(width\s+([-\d.]+)\)", block)
        nm = re.search(r'\(net\s+"([^"]*)"\)', block)
        if not sm or not wm:
            continue
        x1, y1, x2, y2 = map(float, sm.groups())
        w = float(wm.group(1))
        net = nm.group(1) if nm else "?"
        pieces = clip_segment(x1, y1, x2, y2, w, boxes, sample_step)
        if len(pieces) == 1 and pieces[0] == (x1, y1, x2, y2):
            continue
        if not pieces:
            edits.append((s, e, None))
            n_deleted += 1
            net_del[net] += 1
            continue
        if len(pieces) == 1:
            edits.append((s, e, rewrite_segment_block(block, *pieces[0])))
            n_clipped += 1
            net_clip[net] += 1
        else:
            edits.append((s, e, "\n".join(clone_segment(block, *p) for p in pieces)))
            n_split += 1
            n_clipped += 1
            net_clip[net] += 1

    n_via_del = 0
    via_nets: Counter[str] = Counter()
    for s, e, block in vias:
        am = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)\)", block)
        nm = re.search(r'\(net\s+"([^"]*)"\)', block)
        size_m = re.search(r"\(size\s+([-\d.]+)\)", block)
        if not am:
            continue
        x, y = float(am.group(1)), float(am.group(2))
        r = float(size_m.group(1)) / 2 if size_m else 0.4
        if point_forbidden(x, y, boxes, r):
            edits.append((s, e, None))
            n_via_del += 1
            via_nets[nm.group(1) if nm else "?"] += 1

    print(f"\nsegment fully removed: {n_deleted}")
    print(f"segment clipped/split:  {n_clipped} (of which splits: {n_split})")
    print(f"vias removed:           {n_via_del}")
    if net_del:
        print("  deleted segs by net:", net_del.most_common(15))
    if net_clip:
        print("  clipped segs by net:", net_clip.most_common(15))
    if via_nets:
        print("  deleted vias by net:", via_nets.most_common(15))

    if dry_run:
        print("\ndry-run: PCB not modified")
        return 0

    if not edits:
        print("\nnothing to change")
        return 0

    if not no_backup:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = pcb_path.with_name(f"{pcb_path.name}.bak_clear_{stamp}")
        shutil.copy2(pcb_path, backup)
        print(f"\nbackup: {backup.name}")

    edits.sort(key=lambda t: t[0], reverse=True)
    new_text = text
    for s, e, rep in edits:
        if rep is None:
            s2 = s - 1 if s > 0 and new_text[s - 1] == "\n" else s
            new_text = new_text[:s2] + new_text[e:]
        else:
            new_text = new_text[:s] + rep + new_text[e:]

    pcb_path.write_text(new_text, encoding="utf-8")
    print(
        f"done. segments {new_text.count('(segment')} "
        f"(was {text.count('(segment')}), "
        f"vias {new_text.count('(via')} (was {text.count('(via')})"
    )
    return 0


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(
        description="Clip B.Cu tracks and delete vias under selected footprints."
    )
    ap.add_argument(
        "--pcb",
        type=Path,
        default=here / "ts52k.kicad_pcb",
        help="path to .kicad_pcb (default: ts52k.kicad_pcb next to this script)",
    )
    ap.add_argument(
        "--refs",
        type=str,
        default=None,
        help="comma/space separated refs (default: RP2040-side set from PLACEMENT.md)",
    )
    ap.add_argument(
        "--margin",
        type=float,
        default=DEFAULT_MARGIN_MM,
        help=f"extra mm around pad/courtyard AABB (default {DEFAULT_MARGIN_MM})",
    )
    ap.add_argument(
        "--layer",
        default="B.Cu",
        help="copper layer to clip (default B.Cu)",
    )
    ap.add_argument(
        "--sample-step",
        type=float,
        default=SAMPLE_STEP_MM,
        help=f"sampling step along tracks in mm (default {SAMPLE_STEP_MM})",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would change without writing the PCB",
    )
    ap.add_argument(
        "--no-backup",
        action="store_true",
        help="do not write a .bak_clear_* copy before modifying",
    )
    args = ap.parse_args()
    raise SystemExit(
        run(
            pcb_path=args.pcb,
            refs=parse_refs(args.refs),
            margin=args.margin,
            layer=args.layer,
            dry_run=args.dry_run,
            no_backup=args.no_backup,
            sample_step=args.sample_step,
        )
    )


if __name__ == "__main__":
    main()
