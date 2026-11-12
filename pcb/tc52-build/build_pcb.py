#!/usr/bin/env python3
"""Build the TC52 board from the Rev 0.2 board (git main) and the generated schematic.

  python3 build_pcb.py            # full build -> ../ts52k.kicad_pcb
Stages: strip Rev 0.2 matrix -> 4 layers -> footprints from netlist -> placement -> routing -> zones.
All geometry decisions live in layout.py.
"""
import json
import math
import os
import subprocess
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netlist
import matrix as M
from brd import B, V, MM, mm, L1, L2, L3, L4

PCB = os.path.dirname(HERE)
BASE = 'c672d06'
OUT = os.path.join(PCB, 'ts52k.kicad_pcb')
KEYS = json.load(open(os.path.join(HERE, 'keys.json')))
FPDIR = '/usr/share/kicad/footprints'


def island_keep(x, y):
    """region whose Rev 0.2 routing is kept"""
    return 14.0 <= x <= 52.0 and y <= 84.5


def near_key(x, y):
    k = min(KEYS, key=lambda k: math.hypot(KEYS[k][0] - x, KEYS[k][1] - y))
    return k, math.hypot(KEYS[k][0] - x, KEYS[k][1] - y)


def load_fp(libid):
    lib, name = libid.split(':')
    d = os.path.join(PCB, lib + '.pretty') if os.path.isdir(os.path.join(PCB, lib + '.pretty')) else os.path.join(FPDIR, lib + '.pretty')
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None:
        raise RuntimeError(libid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def strip(bd):
    b = bd.b
    b.SetCopperLayerCount(4)
    b.SetLayerName(L2, 'In1.Cu')
    b.SetLayerName(L3, 'In2.Cu')
    removed = 0
    for f in list(b.GetFootprints()):
        r = f.GetReference()
        if r.startswith('MX') or (r.startswith('D') and r not in ('D89', 'D90', 'D91')):
            b.RemoveNative(f)
            removed += 1
    kept_gnd = 0
    for t in list(b.GetTracks()):
        n = t.GetNetname()
        if n.startswith(('row', 'col', 'Net-(D')):
            b.RemoveNative(t)
            continue
        if n in ('rpg1', 'rpg2', 'Net-(R14-Pad2)'):
            # encoder and BOOTSEL lines are rerouted (upper band / electrode gate); keep only the stubs at C19/C20
            s, e = t.GetStart(), t.GetEnd()
            if not (t.Type() != pcbnew.PCB_VIA_T and abs(s.x - e.x) < MM(0.02) and mm(s.x) > 290 and max(mm(s.y), mm(e.y)) < 49.5):
                b.RemoveNative(t)
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            x, y = mm(p.x), mm(p.y)
            k, d = near_key(x, y)
            if n == 'GND' and min(math.hypot(x - a, y - c) for a, c in ((18.4, 63.65), (18.4, 65.1), (19.98, 60.17))) < 0.1:
                b.RemoveNative(t)      # in the way of the west fan-out (rows, S0-S3, PURGE, ADC); restitched in layout.py
                continue
            if n == 'GND':
                # stitching is regenerated; keep only island vias that do not hit an electrode on L1
                if not island_keep(x, y) or d < 8.9:
                    b.RemoveNative(t)
                else:
                    kept_gnd += 1
        elif t.GetLayer() == L1:
            # island jumpers that used the front side move to L3 (L1 carries electrodes only)
            t.SetLayer(L3)
    for d in list(b.GetDrawings()):
        if d.GetClass() == 'PCB_TEXT' and 'TS52K' in d.GetText():
            d.SetText('TC52 Keyboard R0.1')
    return removed, kept_gnd


def apply_netlist(bd, comps, nets):
    b = bd.b
    padnet = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            padnet[(ref, pin)] = name
    # new footprints
    park = [0]
    for ref, c in sorted(comps.items()):
        f = b.FindFootprintByReference(ref)
        if f is None:
            f = load_fp(c['footprint'])
            f.SetReference(ref)
            b.Add(f)
            f.SetPosition(V(284 + (park[0] % 8) * 2.2, 90 + (park[0] // 8) * 1.6))
            park[0] += 1
        f.SetValue(c['value'])
        f.SetPath(pcbnew.KIID_PATH(c['path'] + c['uuid']))
        for k in ('LCSC', 'MPN'):
            if c['props'].get(k):
                f.SetField(k, c['props'][k])
                fld = [x for x in f.GetFields() if x.GetName() == k]
                for x in fld:
                    x.SetVisible(False)
        if ref.startswith(('MX', 'H', 'TP')):
            f.SetExcludedFromBOM(True)
            f.SetExcludedFromPosFiles(True)
        if 'DNP' in c['value']:
            f.SetDNP(True)
            f.SetExcludedFromBOM(True)
            f.SetExcludedFromPosFiles(True)
    for f in b.GetFootprints():
        ref = f.GetReference()
        if ref not in comps:
            raise RuntimeError(f'footprint {ref} not in schematic')
        for p in f.Pads():
            name = padnet.get((ref, p.GetNumber()))
            if name is None:
                if p.GetNumber() and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    name = None
                p.SetNetCode(0) if name is None else p.SetNet(bd.net(name))
            else:
                p.SetNet(bd.net(name))
    # kept Rev 0.2 tracks: rename nets that changed name
    ren = {'rpg1': 'ENC_A', 'rpg2': 'ENC_B'}
    for t in b.GetTracks():
        if t.GetNetname() in ren:
            t.SetNet(bd.net(ren[t.GetNetname()]))


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    tmp = '/tmp/tc52_base.kicad_pcb'
    open(tmp, 'w').write(subprocess.check_output(['git', '-C', PCB, 'show', f'{BASE}:pcb/ts52k.kicad_pcb'], text=True))
    board = pcbnew.LoadBoard(tmp)
    bd = B(board)
    comps, nets = netlist.export(PCB)
    print('strip:', strip(bd))
    apply_netlist(bd, comps, nets)
    import layout
    layout.run(bd, KEYS, stage)
    pcbnew.SaveBoard(OUT, board)
    print('saved', OUT)


if __name__ == '__main__':
    main()
