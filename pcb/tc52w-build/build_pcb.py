#!/usr/bin/env python3
"""Build the TC52 wireless board.

  python3 build_pcb.py            # full build -> ../ts52k.kicad_pcb

Base: the Rev 0.2 board (git c672d06) for the outline, the zones and the board setup, exactly as the wired TC52
build did.  Everything else is generated: all footprints come from the generated schematic (gen_sch.py), the
matrix / MUX / lower band / upper band / east bundle are the wired TC52 routing (layout.py, east.py), and the
module, power and analog front end on the west side are new (module.py).
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
from brd import B, V, MM, mm, L1, L2, L3, L4

PCB = os.path.dirname(HERE)
BASE = 'c672d06'
OUT = os.path.join(PCB, 'ts52k.kicad_pcb')
KEYS = json.load(open(os.path.join(HERE, 'keys.json')))
FPDIR = '/usr/share/kicad/footprints'


def load_fp(libid):
    lib, name = libid.split(':')
    d = os.path.join(PCB, lib + '.pretty') if os.path.isdir(os.path.join(PCB, lib + '.pretty')) else os.path.join(FPDIR, lib + '.pretty')
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None:
        raise RuntimeError(libid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def strip(bd):
    """keep the outline, the board setup and the main ground zone; drop every footprint, track and local zone"""
    b = bd.b
    b.SetCopperLayerCount(4)
    b.SetLayerName(L2, 'In1.Cu')
    b.SetLayerName(L3, 'In2.Cu')
    for f in list(b.GetFootprints()):
        b.RemoveNative(f)
    for t in list(b.GetTracks()):
        b.RemoveNative(t)
    for z in list(b.Zones()):
        if z.GetIsRuleArea() or z.GetAssignedPriority() == 1:
            b.RemoveNative(z)
    for d in list(b.GetDrawings()):
        if d.GetClass() == 'PCB_TEXT' and 'TS52K' in d.GetText():
            d.SetText('TC52 Wireless R0.1')


def apply_netlist(bd, comps, nets):
    b = bd.b
    padnet = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            padnet[(ref, pin)] = name
    park = 0
    for ref, c in sorted(comps.items()):
        f = load_fp(c['footprint'])
        f.SetReference(ref)
        b.Add(f)
        f.SetPosition(V(284 + (park % 8) * 2.2, 90 + (park // 8) * 1.6))
        park += 1
        f.SetValue(c['value'])
        if c.get('descr'):
            f.SetField('Description', c['descr'])
            for x in f.GetFields():
                if x.GetName() == 'Description':
                    x.SetVisible(False)
        f.SetPath(pcbnew.KIID_PATH(c['path'] + c['uuid']))
        for k in ('LCSC', 'MPN'):
            if c['props'].get(k):
                f.SetField(k, c['props'][k])
                for x in f.GetFields():
                    if x.GetName() == k:
                        x.SetVisible(False)
        if ref.startswith(('MX', 'H', 'TP')) or ref in ('J2', 'SW2'):
            f.SetExcludedFromBOM(True)
            f.SetExcludedFromPosFiles(ref != 'SW2' and True)
        if 'DNP' in c['value']:
            f.SetDNP(True)
            f.SetExcludedFromBOM(True)
            f.SetExcludedFromPosFiles(True)
        for p in f.Pads():
            name = padnet.get((ref, p.GetNumber()))
            if name is None:
                p.SetNetCode(0)
            else:
                p.SetNet(bd.net(name))
    b.FindFootprintByReference('SW1').SetDuplicatePadNumbersAreJumpers(True)


# JLC04161H-7628 (design-spec section 1): the electrode-to-L2 capacitance and the column loading are computed for
# 0.2104 mm of 7628 prepreg between L1 and L2.  The base board still carries KiCad's default two-layer description;
# the board file is given the real stack so that it cannot be ordered or analysed against the wrong one.
STACK = (('F.Cu', 'copper', 0.035), ('dielectric 1', 'prepreg', 0.2104), ('In1.Cu', 'copper', 0.0152),
         ('dielectric 2', 'core', 1.065), ('In2.Cu', 'copper', 0.0152), ('dielectric 3', 'prepreg', 0.2104),
         ('B.Cu', 'copper', 0.035))


def write_stackup(path):
    """replace the copper / dielectric part of the (stackup ...) block (pcbnew's Python API does not expose it)"""
    s = open(path).read()
    i = s.index('\t\t\t(layer "F.Cu"\n\t\t\t\t(type "copper")')
    j = s.index('\t\t\t(layer "B.Mask"', i)
    out = []
    for name, typ, th in STACK:
        out.append(f'\t\t\t(layer "{name}"\n\t\t\t\t(type "{typ}")\n\t\t\t\t(thickness {th:g})\n')
        if typ != 'copper':
            out.append('\t\t\t\t(material "%s")\n\t\t\t\t(epsilon_r %s)\n\t\t\t\t(loss_tangent 0.02)\n' % (('7628', '4.4') if typ == 'prepreg' else ('FR4', '4.6')))
        out.append('\t\t\t)\n')
    s = s[:i] + ''.join(out) + s[j:]
    open(path, 'w').write(s)
    chk = pcbnew.LoadBoard(path)                 # must still load, with four copper layers
    assert chk.GetCopperLayerCount() == 4


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    tmp = '/tmp/tc52w_base.kicad_pcb'
    open(tmp, 'w').write(subprocess.check_output(['git', '-C', PCB, 'show', f'{BASE}:pcb/ts52k.kicad_pcb'], text=True))
    board = pcbnew.LoadBoard(tmp)
    bd = B(board)
    comps, nets = netlist.export(PCB, '/tmp/tc52w.net')
    strip(bd)
    apply_netlist(bd, comps, nets)
    import layout
    layout.run(bd, KEYS, stage)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = MM(0.1)          # 0.1 mm necks between the module's pads only (check_spec item)
    pcbnew.SaveBoard(OUT, board)
    write_stackup(OUT)
    print('saved', OUT)


if __name__ == '__main__':
    main()
