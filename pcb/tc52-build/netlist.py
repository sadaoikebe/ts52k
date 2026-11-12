"""Read a KiCad netlist (kicadsexpr) exported by kicad-cli."""
import os, subprocess
from sx import parse, find, first

def export(pcbdir, out='/tmp/tc52.net'):
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', out, os.path.join(pcbdir, 'ts52k.kicad_sch')],
                   check=True, capture_output=True)
    return load(out)

def load(path):
    t = parse(open(path).read())
    comps = {}
    for c in find(first(t, 'components'), 'comp'):
        ref = first(c, 'ref')[1]
        d = {'value': first(c, 'value')[1], 'footprint': (first(c, 'footprint') or [0, ''])[1],
             'path': first(c, 'sheetpath') and first(first(c, 'sheetpath'), 'tstamps')[1],
             'uuid': first(c, 'tstamps')[1], 'props': {}}
        for p in find(c, 'property'):
            d['props'][first(p, 'name')[1]] = (first(p, 'value') or [0, ''])[1]
        comps[ref] = d
    nets = {}
    for n in find(first(t, 'nets'), 'net'):
        name = first(n, 'name')[1]
        nets[name] = [(first(x, 'ref')[1], first(x, 'pin')[1]) for x in find(n, 'node')]
    return comps, nets
