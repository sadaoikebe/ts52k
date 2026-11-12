#!/usr/bin/env python3
"""Generate the TC52 schematic from the Rev 0.2 (git main) schematic.

  - ts52k.kicad_sch : matrix (MX switches, diodes) removed, sheet pins/labels renamed, 'ec' sheet added
  - rp2040.kicad_sch: GPIO hierarchical labels changed to the EC pin assignment
  - ec.kicad_sch    : generated from scratch (electrodes, MUX x2, AFE, row/column resistors, holes)
  - tc52.kicad_sym  : project symbols used by ec.kicad_sch

Run from anywhere:  python3 gen_sch.py
"""
import os
import subprocess
import uuid
from sx import Q, parse, dump, find, first, prop
import matrix as M

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.dirname(HERE)
BASE = 'c672d06'  # Rev 0.2
ROOT_UUID = 'a46aaf04-b440-466e-8b21-108f618a37ed'
NS = uuid.UUID('7c520000-0000-4000-8000-000000000000')


def uid(name):
    return str(uuid.uuid5(NS, name))


EC_UUID = uid('sheet-ec')


def git_show(path):
    return subprocess.check_output(['git', '-C', PCB, 'show', f'{BASE}:pcb/{path}'], text=True)


def font(size=1.27):
    return ['effects', ['font', ['size', str(size), str(size)]]]


def P(key, val, x, y, hide=False, just=None, size=1.27):
    e = font(size)
    if just:
        e.append(['justify', just])
    p = ['property', Q(key), Q(val), ['at', f'{x:.2f}', f'{y:.2f}', '0']]
    if hide:
        p.append(['hide', 'yes'])
    p.append(e)
    return p


def glabel(name, x, y, ang, shape='passive'):
    just = {0: 'left', 180: 'right', 90: 'left', 270: 'right'}[ang]
    return ['global_label', Q(name), ['shape', shape], ['at', f'{x:.2f}', f'{y:.2f}', str(ang)],
            ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just]],
            ['uuid', Q(uid(f'gl-{name}-{x:.2f}-{y:.2f}'))],
            ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', f'{x:.2f}', f'{y:.2f}', '0'],
             ['hide', 'yes'], font()]]


# ---------------------------------------------------------------- symbols
def box_symbol(name, ref, pins, w, h, fp='', desc='', in_bom=True, body='rect'):
    """pins: list of (number, pname, type, side, pos) ; side l/r/t/b ; pos = coordinate along side"""
    g = []
    if body == 'rect':
        g.append(['rectangle', ['start', f'{-w}', f'{h}'], ['end', f'{w}', f'{-h}'],
                  ['stroke', ['width', '0.254'], ['type', 'default']], ['fill', ['type', 'background']]])
    elif body == 'circle':
        g.append(['circle', ['center', '0', '0'], ['radius', f'{w}'],
                  ['stroke', ['width', '0.254'], ['type', 'default']], ['fill', ['type', 'none']]])
    elif body == 'ecs':
        g.append(['circle', ['center', '0', '0'], ['radius', f'{w}'],
                  ['stroke', ['width', '0.3'], ['type', 'default']], ['fill', ['type', 'none']]])
        for sgn in (-1, 1):
            g.append(['arc', ['start', f'{sgn*0.5}', '2.2'], ['mid', f'{sgn*2.3}', '0'], ['end', f'{sgn*0.5}', '-2.2'],
                      ['stroke', ['width', '0.5'], ['type', 'default']], ['fill', ['type', 'none']]])
        g.append(['polyline', ['pts', ['xy', '0', f'{w}'], ['xy', '0', f'{-w}']],
                  ['stroke', ['width', '0.15'], ['type', 'default']], ['fill', ['type', 'none']]])
    pl = []
    for num, pname, typ, side, pos in pins:
        L = 2.54
        at = {'l': (-w - L, pos, 0), 'r': (w + L, pos, 180), 't': (pos, h + L, 270), 'b': (pos, -h - L, 90)}[side]
        pl.append(['pin', typ, 'line', ['at', f'{at[0]}', f'{at[1]}', f'{at[2]}'], ['length', f'{L}'],
                   ['name', Q(pname), font(1.0)], ['number', Q(num), font(1.0)]])
    short = name.split(':')[-1]
    s = ['symbol', Q(name), ['pin_names', ['offset', '0.508']],
         ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'], ['on_board', 'yes'],
         P('Reference', ref, 0, h + 1.5), P('Value', short, 0, -h - 1.5),
         P('Footprint', fp, 0, 0, hide=True), P('Datasheet', '', 0, 0, hide=True),
         P('Description', desc, 0, 0, hide=True),
         ['symbol', Q(short + '_0_1')] + g,
         ['symbol', Q(short + '_1_1')] + pl]
    return s


def pin_xy(symdef, num):
    """connection point and outward label angle of a pin, for a symbol placed at rot 0"""
    for sub in find(symdef, 'symbol'):
        for p in find(sub, 'pin'):
            if first(p, 'number')[1] == num:
                x, y, a = (float(v) for v in first(p, 'at')[1:4])
                return x, -y, {0: 180, 180: 0, 90: 270, 270: 90}[int(a)]
    raise KeyError(num)


SYMS = {}


def define_symbols(dev_r, dev_c, pwr_flag):
    S = SYMS
    S['tc52:ECS_PAD'] = box_symbol(
        'tc52:ECS_PAD', 'MX',
        [('1', 'ROW', 'passive', 'l', 0), ('2', 'COL', 'passive', 'r', 0), ('3', 'GND', 'passive', 'b', 0)],
        3.81, 3.81, 'tc52:ecs_pad', 'Capacitive key electrode (TC69 ecs_pad): 1=drive, 2=sense, 3=guard ring',
        in_bom=False, body='ecs')
    xs = [('13', 'X0'), ('14', 'X1'), ('15', 'X2'), ('12', 'X3'), ('1', 'X4'), ('5', 'X5'), ('2', 'X6'), ('4', 'X7')]
    S['tc52:CD4051B'] = box_symbol(
        'tc52:CD4051B', 'U',
        [('11', 'A', 'input', 'l', 7.62), ('10', 'B', 'input', 'l', 5.08), ('9', 'C', 'input', 'l', 2.54),
         ('6', 'INH', 'input', 'l', -2.54), ('3', 'X', 'passive', 'l', -7.62)] +
        [(n, nm, 'passive', 'r', 8.89 - 2.54 * i) for i, (n, nm) in enumerate(xs)] +
        [('16', 'VDD', 'power_in', 't', 0), ('7', 'VEE', 'power_in', 'b', -2.54), ('8', 'VSS', 'power_in', 'b', 2.54)],
        7.62, 11.43, 'Package_SO:SOIC-16_3.9x9.9mm_P1.27mm', 'CMOS 8-channel analog multiplexer')
    S['tc52:AD8601'] = box_symbol(
        'tc52:AD8601', 'U',
        [('3', '+', 'input', 'l', 2.54), ('4', '-', 'input', 'l', -2.54), ('1', 'OUT', 'output', 'r', 0),
         ('5', 'V+', 'power_in', 't', 0), ('2', 'V-', 'power_in', 'b', 0)],
        5.08, 5.08, 'Package_TO_SOT_SMD:SOT-23-5', 'Rail-to-rail CMOS op amp, 8.2 MHz')
    S['tc52:74AHC1G04'] = box_symbol(
        'tc52:74AHC1G04', 'U',
        [('2', 'A', 'input', 'l', 0), ('1', 'NC', 'no_connect', 'l', -2.54), ('4', 'Y', 'output', 'r', 0),
         ('5', 'VCC', 'power_in', 't', 0), ('3', 'GND', 'power_in', 'b', 0)],
        5.08, 5.08, 'Package_TO_SOT_SMD:SOT-23-5', 'Single inverter')
    S['tc52:TestPoint'] = box_symbol('tc52:TestPoint', 'TP', [('1', '1', 'passive', 'b', 0)], 1.27, 1.27,
                                     'TestPoint:TestPoint_Pad_D1.0mm', 'Test pad', in_bom=False, body='circle')
    S['tc52:Hole_Pad'] = box_symbol('tc52:Hole_Pad', 'H', [('1', '1', 'passive', 'b', 0)], 2.54, 2.54,
                                    'tc52:Hole_M2_Pad', 'M2 fixing hole with land', in_bom=False, body='circle')
    S['tc52:Hole'] = box_symbol('tc52:Hole', 'H', [], 2.54, 2.54, 'MountingHole:MountingHole_2.1mm',
                                'M2 fixing hole, NPTH', in_bom=False, body='circle')
    S['Device:R'] = dev_r
    S['Device:C'] = dev_c
    S['power:PWR_FLAG'] = pwr_flag


class Sheet:
    def __init__(self):
        self.items = []
        self.used = []

    def place(self, lib, ref, value, x, y, nets, fp=None, lcsc=None, mpn=None, dnp=False, in_bom=True, note=None):
        sd = SYMS[lib]
        if lib not in self.used:
            self.used.append(lib)
        fp = fp if fp is not None else (prop(sd, 'Footprint') or '')
        hx = 5.5 if lib in ('Device:R', 'Device:C') else 0
        top = min([pin_xy(sd, first(p, 'number')[1])[1] for sub in find(sd, 'symbol') for p in find(sub, 'pin')] or [-2])
        if lib in ('Device:R', 'Device:C'):
            rp, vp = P('Reference', ref, x + 1.9, y - 1.0, just='left', size=1.0), P('Value', value, x + 1.9, y + 1.0, just='left', size=1.0)
        elif lib in ('tc52:ECS_PAD', 'tc52:TestPoint', 'tc52:Hole', 'tc52:Hole_Pad'):
            rp, vp = P('Reference', ref, x, y - 5.3, size=1.0), P('Value', value, x, y, hide=True)
        else:
            rp, vp = P('Reference', ref, x - 6.0, y + top - 1.0, just='right'), P('Value', value, x + 2.0, y + top - 1.0, just='left')
        s = ['symbol', ['lib_id', Q(lib)], ['at', f'{x:.2f}', f'{y:.2f}', '0'], ['unit', '1'],
             ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'], ['on_board', 'yes'],
             ['dnp', 'yes' if dnp else 'no'], ['uuid', Q(uid('sym-' + ref))],
             rp, vp, P('Footprint', fp, x, y, hide=True), P('Datasheet', '', x, y, hide=True),
             P('Description', note or prop(sd, 'Description') or '', x, y, hide=True)]
        if lcsc:
            s.append(P('LCSC', lcsc, x, y, hide=True))
        if mpn:
            s.append(P('MPN', mpn, x, y, hide=True))
        for sub in find(sd, 'symbol'):
            for p in find(sub, 'pin'):
                n = first(p, 'number')[1]
                s.append(['pin', Q(n), ['uuid', Q(uid(f'pin-{ref}-{n}'))]])
        s.append(['instances', ['project', Q('ts52k'),
                                ['path', Q(f'/{ROOT_UUID}/{EC_UUID}'), ['reference', Q(ref)], ['unit', '1']]]])
        self.items.append(s)
        for num, net in nets.items():
            px, py, ang = pin_xy(sd, num)
            if net is None:
                self.items.append(['no_connect', ['at', f'{x+px:.2f}', f'{y+py:.2f}'], ['uuid', Q(uid(f'nc-{ref}-{num}'))]])
            else:
                self.items.append(glabel(net, x + px, y + py, ang))

    def text(self, t, x, y, size=2.0):
        self.items.append(['text', Q(t), ['exclude_from_sim', 'no'], ['at', f'{x:.2f}', f'{y:.2f}', '0'],
                           ['effects', ['font', ['size', str(size), str(size)]], ['justify', 'left', 'bottom']],
                           ['uuid', Q(uid('txt-' + t))]])

    def render(self):
        libs = ['lib_symbols'] + [SYMS[k] for k in self.used]
        top = ['kicad_sch', ['version', '20260306'], ['generator', Q('tc52_gen_sch')], ['generator_version', Q('10.0')],
               ['uuid', Q(EC_UUID)], ['paper', Q('A2')],
               ['title_block', ['title', Q('TC52 capacitive matrix and analog front end')], ['rev', Q('0.1')],
                ['comment', '1', Q('Generated by pcb/tc52-build/gen_sch.py from design-spec.md')]],
               libs] + self.items + [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]], ['embedded_fonts', 'no']]
        return dump(top) + '\n'


R0402, C0402, C0603 = 'Resistor_SMD:R_0402_1005Metric', 'Capacitor_SMD:C_0402_1005Metric', 'Capacitor_SMD:C_0603_1608Metric'


def build_ec():
    sh = Sheet()
    G = 2.54
    # --- keys -------------------------------------------------------------
    x0, y0, dx, dy = 40.64, 40.64, 35.56, 22.86
    sh.text('Key electrodes: 14 columns x 4 rows (design-spec 3). Pad 1 = drive (ROW), pad 2 = sense (COL), pad 3 = guard ring', 25.4, 22.86, 2.5)
    for ci, col in enumerate(M.COLUMNS, 1):
        for ri, k in enumerate(col, 1):
            if not k:
                continue
            sh.place('tc52:ECS_PAD', k, 'ECS_PAD', x0 + (ci - 1) * dx, y0 + (ri - 1) * dy,
                     {'1': f'ROW{ri}', '2': f'COL{ci}', '3': 'GND'}, in_bom=False,
                     fp='tc52:ecs_pad_edge' if k == 'MX74' else None)
    # --- column pull-downs --------------------------------------------------
    yb = 142.24
    sh.text('Column discharge resistors (at the MUX inputs)', 25.4, yb - 10.16, 2.5)
    for ci in range(1, 15):
        sh.place('Device:R', f'R{40+ci}', '100k', x0 + (ci - 1) * dx, yb, {'1': f'COL{ci}', '2': 'GND'},
                 fp=R0402, lcsc='C25741', mpn='0402WGF1003TCE')
    # --- row series resistors ----------------------------------------------
    yr = 182.88
    sh.text('Row drive: GPIO18..21 -> 100R -> ROW1..4', 25.4, yr - 12.7, 2.5)
    for ri in range(1, 5):
        sh.place('Device:R', f'R{30+ri}', '100', 40.64 + (ri - 1) * 30.48, yr, {'1': f'ROW{ri}_DRV', '2': f'ROW{ri}'},
                 fp=R0402, lcsc='C25076', mpn='0402WGF1000TCE')
    sh.place('tc52:TestPoint', 'TP3', 'ROW1', 40.64 + 4 * 30.48, yr, {'1': 'ROW1'}, in_bom=False)
    # --- MUX ---------------------------------------------------------------
    ym = 236.22
    sh.text('Column select: each MUX has its own lines. INHA / INHB low = that MUX on (never both low). S1x/S2x/S3x = address A/B/C. No inverter: see build log', 25.4, ym - 22.86, 2.5)
    for name, ref, xm, dec in (('A', 'U7', 60.96, 'C34'), ('B', 'U8', 152.4, 'C35')):
        nets = {'11': 'S1' + name, '10': 'S2' + name, '9': 'S3' + name, '6': 'INH' + name, '3': 'SENSE', '16': '+3V3M', '7': 'GND', '8': 'GND'}
        for xn, pin in M.X_PIN.items():
            nets[str(pin)] = 'GND'
        for c, (mx, xn) in M.MUX_INPUT.items():
            if mx == name:
                nets[str(M.X_PIN[xn])] = f'COL{c}'
        sh.place('tc52:CD4051B', ref, 'CD4051BM96', xm, ym, nets, lcsc='C21379', mpn='CD4051BM96')
        sh.place('Device:C', dec, '0.1u', xm + 38.1, ym, {'1': '+3V3M', '2': 'GND'}, fp=C0402, lcsc='C1525', mpn='CL05B104KO5NNNC')
    # --- AFE ---------------------------------------------------------------
    ya = 304.8
    sh.text('Analog front end (TC69 circuit): SENSE node (C30 reference cap, purge by GPIO26) -> R22 -> non-inverting x44 -> ADC2', 25.4, ya - 25.4, 2.5)
    sh.place('Device:C', 'C30', '300p C0G', 40.64, ya, {'1': 'SENSE', '2': 'GND'}, fp=C0603, lcsc='C52152', mpn='0603CG301J500NT',
             note='design-spec C2: SENSE reference capacitor (alt. 330p C1664)')
    sh.place('Device:C', 'C31', 'DNP', 63.5, ya, {'1': 'SENSE', '2': 'GND'}, fp=C0603, dnp=True, in_bom=False,
             note='design-spec C2B: trim seat in parallel with C30, not fitted')
    sh.place('Device:R', 'R22', '100', 86.36, ya, {'1': 'SENSE', '2': 'AMP_IN'}, fp=R0402, lcsc='C25076', mpn='0402WGF1000TCE', note='design-spec R3')
    sh.place('tc52:AD8601', 'U6', 'AD8601ARTZ', 121.92, ya, {'3': 'AMP_IN', '4': 'AMP_FB', '1': 'AMP_OUT', '5': '+3V3A', '2': 'GND'},
             lcsc='C41249', mpn='AD8601ARTZ-REEL7')
    sh.place('Device:R', 'R21', '43k 1%', 154.94, ya, {'1': 'AMP_OUT', '2': 'AMP_FB'}, fp=R0402, lcsc='C881384', mpn='CR0402F43K0Q10Z', note='design-spec R2 (gain trim seat)')
    sh.place('Device:R', 'R20', '1k', 177.8, ya, {'1': 'AMP_FB', '2': 'GND'}, fp=R0402, lcsc='C11702', mpn='0402WGF1001TCE', note='design-spec R1')
    sh.place('Device:R', 'R23', '0', 200.66, ya, {'1': 'AMP_OUT', '2': 'ADC'}, fp=R0402, lcsc='C17168', mpn='0402WGF0000TCE', note='design-spec R_ADC')
    sh.place('Device:C', 'C33', '0.1u', 223.52, ya, {'1': '+3V3A', '2': 'GND'}, fp=C0402, lcsc='C1525', mpn='CL05B104KO5NNNC')
    sh.place('tc52:TestPoint', 'TP1', 'SENSE', 246.38, ya, {'1': 'SENSE'}, in_bom=False)
    sh.place('tc52:TestPoint', 'TP2', 'ADC', 261.62, ya, {'1': 'AMP_OUT'}, in_bom=False)
    sh.place('tc52:TestPoint', 'TP4', 'GND', 276.86, ya, {'1': 'GND'}, in_bom=False)
    # --- analog supply -----------------------------------------------------
    xs = 330.2
    sh.text('+3V3A (op amp) = +3V3 through 22R, 4.7u + 100n', xs - 15.24, ya - 25.4, 2.5)
    sh.place('Device:R', 'R24', '22', xs, ya, {'1': '+3V3', '2': '+3V3A'}, fp=R0402, lcsc='C25092', mpn='0402WGF220JTCE', note='design-spec R_F')
    sh.place('Device:C', 'C32', '4.7u', xs + 25.4, ya, {'1': '+3V3A', '2': 'GND'}, fp=C0402, lcsc='C23733', mpn='CL05A475MP5NRNC', note='design-spec C_F1')
    sh.place('power:PWR_FLAG', '#FLG0301', 'PWR_FLAG', xs + 48.26, ya, {'1': '+3V3A'}, in_bom=False)
    sh.text('+3V3M (MUX x2) = +3V3 through 22R, 4.7u: separate from +3V3A (op amp), see build log', xs - 15.24, ya + 20.32, 2.5)
    sh.place('Device:R', 'R26', '22', xs, ya + 38.1, {'1': '+3V3', '2': '+3V3M'}, fp=R0402, lcsc='C25092', mpn='0402WGF220JTCE', note='second R_F: MUX supply')
    sh.place('Device:C', 'C37', '4.7u', xs + 25.4, ya + 38.1, {'1': '+3V3M', '2': 'GND'}, fp=C0402, lcsc='C23733', mpn='CL05A475MP5NRNC', note='second C_F1: MUX supply')
    sh.place('power:PWR_FLAG', '#FLG0302', 'PWR_FLAG', xs + 48.26, ya + 38.1, {'1': '+3V3M'}, in_bom=False)
    # --- holes ---------------------------------------------------------------
    yh = 363.22
    sh.text('Plate fixing holes (M2). H1 has a land: PLATE -> R25 (not fitted) -> GND', 25.4, yh - 15.24, 2.5)
    sh.place('tc52:Hole_Pad', 'H1', 'PLATE', 40.64, yh, {'1': 'PLATE'}, in_bom=False)
    sh.place('Device:R', 'R25', 'DNP (0R)', 66.04, yh, {'1': 'PLATE', '2': 'GND'}, fp=R0402, dnp=True, in_bom=False, note='design-spec R_PLATE, not fitted')
    for i in range(2, N_HOLES + 1):
        sh.place('tc52:Hole', f'H{i}', 'M2', 66.04 + (i - 1) * 15.24, yh, {}, in_bom=False)
    return sh.render()


N_HOLES = 12


# ---------------------------------------------------------------- root + rp2040
GPIO_NETS = [(0, 'ENC_B'), (1, 'ENC_A'), (2, 'ENC_SW'), (18, 'ROW4_DRV'), (19, 'ROW3_DRV'), (20, 'ROW2_DRV'),
             (21, 'ROW1_DRV'), (3, 'S3B'), (4, 'S2B'), (5, 'S1B'), (7, 'INHB'), (8, 'S3A'), (9, 'S2A'), (10, 'S1A'), (11, 'INHA'), (26, 'ADC'), (28, 'SENSE')]


def pt(node):
    a = first(node, 'at')
    return (float(a[1]), float(a[2])) if a else None


def edit_root(tree):
    out = []
    inbox = lambda p: 125 <= p[0] < 247.6 and 42 <= p[1] <= 160
    for c in tree:
        if not isinstance(c, list):
            out.append(c)
            continue
        k = c[0]
        if k == 'symbol':
            ref = prop(c, 'Reference')
            lib = first(c, 'lib_id')[1]
            if lib.startswith('ts52k:MX-') or (lib == 'Device:D_Small'):
                continue
            if ref and ref.startswith('#') and inbox(pt(c)):
                continue
        elif k in ('wire',):
            pts = [(float(a[1]), float(a[2])) for a in find(first(c, 'pts'), 'xy')]
            if any(inbox(p) for p in pts):
                continue
        elif k in ('junction', 'no_connect', 'label'):
            if inbox(pt(c)):
                continue
        elif k == 'global_label':
            nm = c[1]
            p = pt(c)
            if nm.startswith(('row', 'col')) or (nm.startswith('rpg') and abs(p[0] - 106.68) < 0.01):
                continue
            if nm == 'rpg1':
                c[1] = Q('ENC_A')
            if nm == 'rpg2':
                c[1] = Q('ENC_B')
        elif k == 'sheet':
            c[:] = [e for e in c if not (isinstance(e, list) and e[0] == 'pin' and e[1].startswith('GPIO'))]
            ins = next(i for i, e in enumerate(c) if isinstance(e, list) and e[0] == 'instances')
            for i, (g, net) in enumerate(GPIO_NETS):
                y = 44.45 + 2.54 * i
                c.insert(ins + i, ['pin', Q(f'GPIO{g}'), 'bidirectional', ['at', '106.68', f'{y:.2f}', '0'],
                                   ['uuid', Q(uid(f'sheetpin-GPIO{g}'))],
                                   ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'right']]])
        elif k == 'title_block':
            continue
        out.append(c)
    # new items go before sheet_instances
    idx = next(i for i, e in enumerate(out) if isinstance(e, list) and e[0] == 'sheet_instances')
    new = []
    for i, (g, net) in enumerate(GPIO_NETS):
        new.append(glabel(net, 106.68, 44.45 + 2.54 * i, 0, 'bidirectional'))
    # encoder push switch: S1 -> ENC_SW (GPIO2, internal pull-up), S2 -> GND
    new.append(glabel('ENC_SW', 247.65, 64.77, 180))
    new.append(glabel('GND', 247.65, 59.69, 180))
    new.append(['sheet', ['at', '152.4', '60.96'], ['size', '71.12', '40.64'], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
                ['on_board', 'yes'], ['dnp', 'no'], ['stroke', ['width', '0.1524'], ['type', 'solid']],
                ['fill', ['color', '0', '0', '0', '0']], ['uuid', Q(EC_UUID)],
                ['property', Q('Sheetname'), Q('ec'), ['at', '152.4', '60.2', '0'],
                 ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left', 'bottom']]],
                ['property', Q('Sheetfile'), Q('ec.kicad_sch'), ['at', '152.4', '102.3', '0'],
                 ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left', 'top']]],
                ['instances', ['project', Q('ts52k'), ['path', Q('/' + ROOT_UUID), ['page', Q('3')]]]]])
    new.append(['text', Q('TC52: capacitive matrix (52 electrodes), column MUX x2 and analog front end\\nare on sheet ec. Nets are joined by global labels:\\nROW1..4_DRV, INHA/S1A..S3A, INHB/S1B..S3B, SENSE (purge, GPIO26), ADC (GPIO28), ENC_SW'),
                ['exclude_from_sim', 'no'], ['at', '154.94', '82.0', '0'],
                ['effects', ['font', ['size', '1.6', '1.6']], ['justify', 'left']], ['uuid', Q(uid('root-note'))]])
    out[idx:idx] = new
    # title block after paper
    pi = next(i for i, e in enumerate(out) if isinstance(e, list) and e[0] == 'paper')
    out.insert(pi + 1, ['title_block', ['title', Q('TC52 (TS52K capacitive)')], ['rev', Q('0.1')]])
    return out


def edit_rp(tree):
    keep = {g for g, _ in GPIO_NETS}
    add = {7: (130.81, 90.17, 0), 8: (130.81, 95.25, 0), 9: (130.81, 97.79, 0), 10: (130.81, 100.33, 0), 11: (130.81, 102.87, 0), 23: (130.81, 135.89, 0), 24: (77.47, 120.65, 180), 25: (77.47, 123.19, 180), 26: (77.47, 125.73, 180), 28: (77.47, 130.81, 180)}
    out = []
    for c in tree:
        if isinstance(c, list) and c[0] == 'hierarchical_label' and c[1].startswith('GPIO') and int(c[1][4:]) not in keep:
            p = pt(c)
            out.append(['no_connect', ['at', f'{p[0]}', f'{p[1]}'], ['uuid', Q(uid('rp-nc-' + c[1]))]])
            continue
        if isinstance(c, list) and c[0] == 'no_connect':
            p = pt(c)
            hit = [g for g, (x, y, a) in add.items() if g in keep and abs(p[0] - x) < 0.01 and abs(p[1] - y) < 0.01]
            if hit:
                g = hit[0]
                x, y, a = add[g]
                out.append(['hierarchical_label', Q(f'GPIO{g}'), ['shape', 'bidirectional'], ['at', f'{x}', f'{y}', str(a)],
                            ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left' if a == 0 else 'right']],
                            ['uuid', Q(uid(f'rp-hl-GPIO{g}'))]])
                continue
        out.append(c)
    return out


def main():
    root = parse(git_show('ts52k.kicad_sch'))
    rp = parse(git_show('rp2040.kicad_sch'))
    rl = first(rp, 'lib_symbols')
    dev_r = next(s for s in find(rl, 'symbol') if s[1] == 'Device:R')
    dev_c = next(s for s in find(rl, 'symbol') if s[1] == 'Device:C')
    flag = next(s for s in find(first(root, 'lib_symbols'), 'symbol') if s[1] == 'power:PWR_FLAG')
    define_symbols(dev_r, dev_c, flag)
    open(os.path.join(PCB, 'ec.kicad_sch'), 'w').write(build_ec())
    open(os.path.join(PCB, 'ts52k.kicad_sch'), 'w').write(dump(edit_root(root)) + '\n')
    open(os.path.join(PCB, 'rp2040.kicad_sch'), 'w').write(dump(edit_rp(rp)) + '\n')
    # project symbol library
    lib = ['kicad_symbol_lib', ['version', '20251024'], ['generator', Q('tc52_gen_sch')], ['generator_version', Q('10.0')]]
    for k, s in SYMS.items():
        if k.startswith('tc52:'):
            t = parse(dump(s))
            t[1] = Q(k.split(':')[1])
            lib.append(t)
    open(os.path.join(PCB, 'tc52.kicad_sym'), 'w').write(dump(lib) + '\n')
    print('schematic written')


if __name__ == '__main__':
    main()
