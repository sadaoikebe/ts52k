#!/usr/bin/env python3
"""Generate the TC52 wireless schematic.

  ts52k.kicad_sch    root: two sheets, notes
  mdbt50q.kicad_sch  MDBT50Q-1MV2 module, LF crystal, REG0 inductor, decoupling, BQ24072 charger, battery connector
                     with reverse-polarity FET, USB-C with ESD, SWD contacts, reset switch, encoder
  ec.kicad_sch       capacitive matrix, MUX x2, analog front end (wired TC52 circuit, see docs/tc52-build-log.md)
  tc52.kicad_sym     project symbols generated here

All connections are made with global labels (no wires), the same way the wired TC52 `ec` sheet was generated.
Symbols for the module and the power parts are taken from the TS52K wireless schematic (origin/wireless),
passives from the Rev 0.2 schematic.  The pin assignment lives in PINS below and is the single source for
the board builder and the firmware table (docs/tc52w-build-log.md).

Run from anywhere:  python3 gen_sch.py
"""
import os
import subprocess
import uuid
from sx import Q, parse, dump, find, first, prop
import matrix as M

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.dirname(HERE)
REV02 = 'c672d06'           # Rev 0.2 (Device:R / Device:C symbols)
WL = 'origin/wireless'      # TS52K wireless (module, charger, connectors)
ROOT_UUID = 'a46aaf04-b440-466e-8b21-108f618a37ed'
NS = uuid.UUID('7c520000-0000-4000-8000-0000000000aa')


def uid(name):
    return str(uuid.uuid5(NS, name))


EC_UUID = uid('sheet-ec')
MCU_UUID = uid('sheet-mcu')


def git_show(rev, path):
    return subprocess.check_output(['git', '-C', PCB, 'show', f'{rev}:pcb/{path}'], text=True)


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
    return ['symbol', Q(name), ['pin_names', ['offset', '0.508']],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'], ['on_board', 'yes'],
            P('Reference', ref, 0, h + 1.5), P('Value', short, 0, -h - 1.5),
            P('Footprint', fp, 0, 0, hide=True), P('Datasheet', '', 0, 0, hide=True),
            P('Description', desc, 0, 0, hide=True),
            ['symbol', Q(short + '_0_1')] + g,
            ['symbol', Q(short + '_1_1')] + pl]


def pins_of(symdef):
    out = {}
    for sub in find(symdef, 'symbol'):
        for p in find(sub, 'pin'):
            x, y, a = (float(v) for v in first(p, 'at')[1:4])
            out[first(p, 'number')[1]] = (x, -y, {0: 180, 180: 0, 90: 270, 270: 90}[int(a)])
    return out


SYMS = {}


def define_symbols():
    S = SYMS
    rp = parse(git_show(REV02, 'rp2040.kicad_sch'))
    rl = first(rp, 'lib_symbols')
    S['Device:R'] = next(s for s in find(rl, 'symbol') if s[1] == 'Device:R')
    S['Device:C'] = next(s for s in find(rl, 'symbol') if s[1] == 'Device:C')
    for f in ('ts52k.kicad_sch', 'mdbt50q.kicad_sch'):
        t = parse(git_show(WL, f))
        for s in find(first(t, 'lib_symbols'), 'symbol'):
            if s[1].startswith('ts52k:MX') or s[1] == 'power:GND':
                continue
            S.setdefault(s[1], s)
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
    S['tc52:TestPoint'] = box_symbol('tc52:TestPoint', 'TP', [('1', '1', 'passive', 'b', 0)], 1.27, 1.27,
                                     'TestPoint:TestPoint_Pad_D1.0mm', 'Test pad', in_bom=False, body='circle')
    S['tc52:Hole_Pad'] = box_symbol('tc52:Hole_Pad', 'H', [('1', '1', 'passive', 'b', 0)], 2.54, 2.54,
                                    'tc52:Hole_M2_Pad', 'M2 fixing hole with land', in_bom=False, body='circle')
    S['tc52:Hole'] = box_symbol('tc52:Hole', 'H', [], 2.54, 2.54, 'MountingHole:MountingHole_2.1mm',
                                'M2 fixing hole, NPTH', in_bom=False, body='circle')


class Sheet:
    def __init__(self, sheet_uuid, title, paper='A2'):
        self.items = []
        self.used = []
        self.uuid = sheet_uuid
        self.title = title
        self.paper = paper
        self.flags = 0

    def place(self, lib, ref, value, x, y, nets, fp=None, lcsc=None, mpn=None, dnp=False, in_bom=True, note=None):
        sd = SYMS[lib]
        x, y = round(x / 1.27) * 1.27, round(y / 1.27) * 1.27      # connection grid
        if lib not in self.used:
            self.used.append(lib)
        fp = fp if fp is not None else (prop(sd, 'Footprint') or '')
        pp = pins_of(sd)
        top = min([v[1] for v in pp.values()] or [-2])
        if lib in ('Device:R', 'Device:C'):
            rp, vp = P('Reference', ref, x + 1.9, y - 1.0, just='left', size=1.0), P('Value', value, x + 1.9, y + 1.0, just='left', size=1.0)
        elif lib in ('tc52:ECS_PAD', 'tc52:TestPoint', 'tc52:Hole', 'tc52:Hole_Pad', 'power:PWR_FLAG'):
            rp, vp = P('Reference', ref, x, y - 5.3, size=1.0, hide=lib == 'power:PWR_FLAG'), P('Value', value, x, y, hide=True)
        else:
            rp, vp = P('Reference', ref, x - 6.0, y + top - 3.0, just='right'), P('Value', value, x - 4.0, y + top - 3.0, just='left')
        s = ['symbol', ['lib_id', Q(lib)], ['at', f'{x:.2f}', f'{y:.2f}', '0'], ['unit', '1'],
             ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'], ['on_board', 'yes'],
             ['dnp', 'yes' if dnp else 'no'], ['uuid', Q(uid('sym-' + ref))],
             rp, vp, P('Footprint', fp, x, y, hide=True), P('Datasheet', '', x, y, hide=True),
             P('Description', note or prop(sd, 'Description') or '', x, y, hide=True)]
        if lcsc:
            s.append(P('LCSC', lcsc, x, y, hide=True))
        if mpn:
            s.append(P('MPN', mpn, x, y, hide=True))
        for n in pp:
            s.append(['pin', Q(n), ['uuid', Q(uid(f'pin-{ref}-{n}'))]])
        s.append(['instances', ['project', Q('ts52k'),
                                ['path', Q(f'/{ROOT_UUID}/{self.uuid}'), ['reference', Q(ref)], ['unit', '1']]]])
        self.items.append(s)
        seen = set()
        missing = [n for n in pp if n not in nets]
        if missing:
            raise RuntimeError(f'{ref}: pins without a net entry: {missing}')
        for num, net in nets.items():
            px, py, ang = pp[num]
            key = (round(x + px, 2), round(y + py, 2), net)
            if key in seen:
                continue
            seen.add(key)
            if net is None:
                self.items.append(['no_connect', ['at', f'{x+px:.2f}', f'{y+py:.2f}'], ['uuid', Q(uid(f'nc-{ref}-{num}'))]])
            else:
                self.items.append(glabel(net, x + px, y + py, ang))

    def flag(self, net, x, y):
        self.flags += 1
        self.place('power:PWR_FLAG', f'#FLG{self.uuid[:2]}{self.flags:02d}', 'PWR_FLAG', x, y, {'1': net}, in_bom=False)

    def text(self, t, x, y, size=2.0):
        t = t.replace('"', "'")
        self.items.append(['text', Q(t), ['exclude_from_sim', 'no'], ['at', f'{x:.2f}', f'{y:.2f}', '0'],
                           ['effects', ['font', ['size', str(size), str(size)]], ['justify', 'left', 'bottom']],
                           ['uuid', Q(uid('txt-' + t))]])

    def render(self, page):
        libs = ['lib_symbols'] + [SYMS[k] for k in self.used]
        top = ['kicad_sch', ['version', '20260306'], ['generator', Q('tc52w_gen_sch')], ['generator_version', Q('10.0')],
               ['uuid', Q(self.uuid)], ['paper', Q(self.paper)],
               ['title_block', ['title', Q(self.title)], ['rev', Q('0.1')],
                ['comment', '1', Q('Generated by pcb/tc52w-build/gen_sch.py')]],
               libs] + self.items + [['sheet_instances', ['path', Q('/'), ['page', Q(str(page))]]], ['embedded_fonts', 'no']]
        return dump(top) + '\n'


R0402, C0402, C0603 = 'Resistor_SMD:R_0402_1005Metric', 'Capacitor_SMD:C_0402_1005Metric', 'Capacitor_SMD:C_0603_1608Metric'
R0603W, C0603W, C0805W = 'ts52k:R_0603_1608Metric', 'ts52k:C_0603_1608Metric', 'ts52k:C_0805_2012Metric'

# ---------------------------------------------------------------- pin assignment (MDBT50Q pad -> net)
# Pad numbers are the module's land numbers; GPIO names for reference.  None = not connected.
PINS = {
    1: 'GND', 2: 'GND', 15: 'GND', 33: 'GND', 55: 'GND',
    # north side (pads 3..14: "standard drive, low frequency I/O only"): static / slow lines only
    3: 'ENC_B',      # P1.10
    4: 'ENC_A',      # P1.11
    5: 'ENC_SW',     # P1.12
    6: 'S3B',        # P1.13
    7: 'S2B',        # P1.14
    8: 'S1B',        # P1.15
    9: 'INHB',       # P0.03
    10: 'S3A',       # P0.29
    11: 'S2A',       # P0.02
    12: 'S1A',       # P0.31
    13: 'ADC',       # P0.28 = AIN4 (analog input)
    14: 'INHA',      # P0.30
    # east end
    16: None, 17: 'XL1', 18: 'XL2', 19: None, 20: None, 21: None, 22: None, 23: None, 24: None, 25: None, 26: None, 27: None,
    28: '+3V3', 29: None, 30: 'VDDH', 31: 'DCCH', 32: 'MCU_VBUS',
    # south side
    34: 'D-', 35: 'D+', 36: None,
    37: 'AFE_EN',    # P0.13: op amp supply (through R27), static
    38: None, 39: None,
    40: 'nRESET',    # P0.18
    41: 'ROW3_DRV',  # P0.17
    42: None, 43: None,
    44: 'ROW4_DRV',  # P0.20
    45: None,
    46: 'ROW2_DRV',  # P0.22
    47: None,
    48: 'ROW1_DRV',  # P0.24
    49: None,        # P0.25: held low by the firmware (guard between the row strobe and PURGE)
    50: 'SENSE',     # P1.02 = PURGE
    51: 'SWDIO', 52: None, 53: 'SWCLK', 54: None,
    56: None, 57: None, 58: None, 59: None, 60: None, 61: None,
}
GPIO = {3: 'P1.10', 4: 'P1.11', 5: 'P1.12', 6: 'P1.13', 7: 'P1.14', 8: 'P1.15', 9: 'P0.03', 10: 'P0.29', 11: 'P0.02',
        12: 'P0.31', 13: 'P0.28', 14: 'P0.30', 37: 'P0.13', 40: 'P0.18', 41: 'P0.17', 44: 'P0.20', 46: 'P0.22',
        48: 'P0.24', 50: 'P1.02'}


def build_mcu():
    sh = Sheet(MCU_UUID, 'TC52 wireless: MDBT50Q, power, USB, SWD, encoder')
    T = sh.text
    # --- module -------------------------------------------------------------
    T('MDBT50Q-1MV2 (nRF52840). Pads 3..14 are "standard drive, low frequency I/O only" (Raytac spec 2.6): they carry the\\n'
      'encoder and the MUX select / inhibit lines (change once per column, well under 10 kHz) and the ADC input (AIN4).\\n'
      'Row strobes are on unrestricted pads; PURGE (P1.02) only ever sees the millivolt-level SENSE node.  P0.15 (boot loader LED), NFC pins and P0.26/P0.27 (next to XL1/XL2) are unused.',
      60.0, 58.0, 2.0)
    sh.place('ts52k:MDBT50Q-1MV2', 'U5', 'MDBT50Q-1MV2', 150.0, 130.0, {str(k): v for k, v in PINS.items()},
             fp='ts52k:Raytac_MDBT50Q', lcsc='C5118826', mpn='MDBT50Q-1MV2')
    # --- LF crystal ---------------------------------------------------------
    T('32.768 kHz crystal (CL 9 pF), 12 pF x2', 215.0, 78.0)
    sh.place('ts52k:X1A0000610008', 'X1', '32.768kHz', 230.0, 90.0, {'1': 'XL2', '2': 'XL1'},
             fp='ts52k:Crystal_Epson_FC-12M_2.05x1.2mm', lcsc='C96341', mpn='X1A0000610008')
    sh.place('Device:C', 'C11', '12p', 215.0, 105.0, {'1': 'XL1', '2': 'GND'}, fp=C0402, lcsc='C1547', mpn='0402CG120J500NT')
    sh.place('Device:C', 'C12', '12p', 245.0, 105.0, {'1': 'XL2', '2': 'GND'}, fp=C0402, lcsc='C1547', mpn='0402CG120J500NT')
    # --- module supply ------------------------------------------------------
    T('Module supply (TS52K wireless): REG0 DC/DC inductor DCCH - VDD, VDD 4.7u + 1u + 100n x3, VDDH 10u, VBUS 4.7u behind 2.2R', 215.0, 125.0)
    sh.place('ts52k:LQM18DN100M70L', 'L1', '10uH', 220.0, 145.0, {'1': '+3V3', '2': 'DCCH'}, fp='ts52k:L_0603_1608Metric', lcsc='C713281', mpn='LQM18DN100M70L')
    sh.place('Device:C', 'C6', '4.7u', 240.0, 145.0, {'1': '+3V3', '2': 'GND'}, fp=C0603W, lcsc='C19666', mpn='CL10A475KO8NNNC')
    sh.place('Device:C', 'C7', '1u', 258.0, 145.0, {'1': '+3V3', '2': 'GND'}, fp=C0603W, lcsc='C15849', mpn='CL10A105KB8NNNC')
    for i, r in enumerate(('C8', 'C9', 'C10')):
        sh.place('Device:C', r, '0.1u', 276.0 + 18 * i, 145.0, {'1': '+3V3', '2': 'GND'}, fp=C0402, lcsc='C1525', mpn='CL05B104KO5NNNC')
    sh.place('Device:C', 'C4', '10u', 240.0, 170.0, {'1': 'VDDH', '2': 'GND'}, fp=C0805W, lcsc='C15850', mpn='CL21A106KAYNNNE')
    sh.place('Device:R', 'R4', '2.2', 266.0, 170.0, {'1': 'USB_VBUS', '2': 'MCU_VBUS'}, fp=R0603W, lcsc='C22939', mpn='0603WAF220KT5E')
    sh.place('Device:C', 'C5', '4.7u', 290.0, 170.0, {'1': 'MCU_VBUS', '2': 'GND'}, fp=C0603W, lcsc='C19666', mpn='CL10A475KO8NNNC')
    sh.flag('+3V3', 330.0, 150.0)
    sh.flag('MCU_VBUS', 312.0, 170.0)
    sh.flag('GND', 330.0, 170.0)
    # --- charger ------------------------------------------------------------
    T('BQ24072: USB100 fixed (EN1 = EN2 = CE = TD = GND), ISET 8.2k, ILIM 1.5k, TS 10k, TMR open.  OUT -> VDDH.\\n'
      'Q1 = battery reverse-polarity protection (drain to the connector, source to BAT, gate to GND).  J3: 1 = BAT+, 2 = GND', 360.0, 78.0)
    sh.place('ts52k:BQ24072RGTR', 'U9', 'BQ24072RGTR', 400.0, 110.0,
             {'1': 'BQ_TS', '2': 'BAT', '3': 'BAT', '4': 'GND', '5': 'GND', '6': 'GND', '7': None, '8': 'GND', '9': None,
              '10': 'VDDH', '11': 'VDDH', '12': 'BQ_ILIM', '13': 'USB_VBUS', '14': None, '15': 'GND', '16': 'BQ_ISET', '17': 'GND'},
             fp='ts52k:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm', lcsc='C140288', mpn='BQ24072RGTR')
    sh.place('Device:R', 'R1', '8.2k', 360.0, 150.0, {'1': 'BQ_ISET', '2': 'GND'}, fp=R0603W, lcsc='C25981', mpn='0603WAF8201T5E')
    sh.place('Device:R', 'R2', '1.5k', 380.0, 150.0, {'1': 'BQ_ILIM', '2': 'GND'}, fp=R0603W, lcsc='C22843', mpn='0603WAF1501T5E')
    sh.place('Device:R', 'R3', '10k', 400.0, 150.0, {'1': 'BQ_TS', '2': 'GND'}, fp=R0603W, lcsc='C25804', mpn='0603WAF1002T5E')
    sh.place('Device:C', 'C1', '1u', 420.0, 150.0, {'1': 'USB_VBUS', '2': 'GND'}, fp=C0603W, lcsc='C15849', mpn='CL10A105KB8NNNC')
    sh.place('Device:C', 'C2', '4.7u', 440.0, 150.0, {'1': 'VDDH', '2': 'GND'}, fp=C0603W, lcsc='C19666', mpn='CL10A475KO8NNNC')
    sh.place('Device:C', 'C3', '4.7u', 460.0, 150.0, {'1': 'BAT', '2': 'GND'}, fp=C0603W, lcsc='C19666', mpn='CL10A475KO8NNNC')
    sh.place('ts52k:AO3401A', 'Q1', 'AO3401A', 460.0, 110.0, {'1': 'GND', '2': 'BAT', '3': 'BAT_CONN'}, fp='ts52k:SOT-23', lcsc='C15127', mpn='AO3401A')
    sh.place('ts52k:S2B-PH-SM4-TB(LF)(SN)', 'J3', 'JST PH 2-pin', 500.0, 110.0, {'1': 'BAT_CONN', '2': 'GND'},
             fp='ts52k:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal', lcsc='C295747', mpn='S2B-PH-SM4-TB(LF)(SN)')
    sh.flag('USB_VBUS', 420.0, 172.0)
    sh.flag('BAT_CONN', 500.0, 135.0)
    # --- USB ------------------------------------------------------------------
    T('USB-C (USB 2.0 full speed, no series resistors), CC 5.1k x2, ESD H5VU10U x3 at the connector', 360.0, 205.0)
    sh.place('ts52k:USB_C_Receptacle_USB2.0', 'J1', 'TYPE-C-31-M-12', 380.0, 250.0,
             {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'SH': 'GND', 'A4': 'USB_VBUS', 'A9': 'USB_VBUS', 'B4': 'USB_VBUS',
              'B9': 'USB_VBUS', 'A5': 'CC1', 'B5': 'CC2', 'A6': 'D+', 'B6': 'D+', 'A7': 'D-', 'B7': 'D-', 'A8': None, 'B8': None},
             fp='ts52k:USB_C_Receptacle_HRO_TYPE-C-31-M-12', lcsc='C165948', mpn='TYPE-C-31-M-12')
    sh.place('Device:R', 'R5', '5.1k', 430.0, 240.0, {'1': 'GND', '2': 'CC1'}, fp=R0603W, lcsc='C23186', mpn='0603WAF5101T5E')
    sh.place('Device:R', 'R6', '5.1k', 450.0, 240.0, {'1': 'GND', '2': 'CC2'}, fp=R0603W, lcsc='C23186', mpn='0603WAF5101T5E')
    for i, (r, n) in enumerate((('D89', 'D-'), ('D90', 'D+'), ('D91', 'USB_VBUS'))):
        sh.place('ts52k:H5VU10U', r, 'H5VU10U', 475.0 + 20 * i, 240.0, {'1': n, '2': 'GND'}, fp='Diode_SMD:D_SOD-882D', lcsc='C22395519', mpn='H5VU10U')
    # --- SWD, reset -----------------------------------------------------------
    T('SWD contacts (Tag-Connect TC2030-NL, no part fitted): 1 VTref = VDD, 2 SWDIO, 3 nRESET, 4 SWCLK, 5 GND.  SW1 = reset (P0.18)', 60.0, 255.0)
    sh.place('tag-connect:TC2030_IDC_NL', 'J2', 'TC2030_IDC_NL', 90.0, 275.0,
             {'1': '+3V3', '2': 'SWDIO', '3': 'nRESET', '4': 'SWCLK', '5': 'GND', '6': None},
             fp='ts52k:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical', in_bom=False,
             note='Tag-Connect TC2030-IDC-NL, TC2030-CTX pinout (1 VTref, 2 SWDIO, 3 nRESET, 4 SWCLK, 5 GND, 6 NC). No component fitted')
    sh.place('ts52k:TS-1187A-B-A-B', 'SW1', 'RESET', 150.0, 275.0, {'1': 'GND', '2': 'nRESET'},
             fp='ts52k:SW_Tactile_XKB_TS-1187A_5.1x5.1mm', lcsc='C318884', mpn='TS-1187A-B-A-B')
    # --- encoder --------------------------------------------------------------
    T('Encoder (as wired TC52): A / B with 10k pull-ups and 100n, push switch to GND (internal pull-up)', 215.0, 255.0)
    sh.place('Device:RotaryEncoder_Switch_MP', 'SW2', 'RotaryEncoder_Switch', 240.0, 280.0,
             {'A': 'ENC_A', 'B': 'ENC_B', 'C': 'GND', 'MP': 'GND', 'S1': 'ENC_SW', 'S2': 'GND'},
             fp='Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm', in_bom=False)
    sh.place('Device:R', 'R15', '10k', 280.0, 270.0, {'1': '+3V3', '2': 'ENC_A'}, fp=R0402, lcsc='C25744', mpn='0402WGF1002TCE')
    sh.place('Device:R', 'R16', '10k', 300.0, 270.0, {'1': '+3V3', '2': 'ENC_B'}, fp=R0402, lcsc='C25744', mpn='0402WGF1002TCE')
    sh.place('Device:C', 'C19', '0.1u', 280.0, 295.0, {'1': 'ENC_A', '2': 'GND'}, fp=C0402, lcsc='C1525', mpn='CL05B104KO5NNNC')
    sh.place('Device:C', 'C20', '0.1u', 300.0, 295.0, {'1': 'GND', '2': 'ENC_B'}, fp=C0402, lcsc='C1525', mpn='CL05B104KO5NNNC')
    return sh.render(2)


def build_ec():
    sh = Sheet(EC_UUID, 'TC52 wireless: capacitive matrix and analog front end')
    x0, y0, dx, dy = 40.64, 40.64, 35.56, 22.86
    sh.text('Key electrodes: 14 columns x 4 rows (design-spec 3). Pad 1 = drive (ROW), pad 2 = sense (COL), pad 3 = guard ring', 25.4, 22.86, 2.5)
    for ci, col in enumerate(M.COLUMNS, 1):
        for ri, k in enumerate(col, 1):
            if not k:
                continue
            sh.place('tc52:ECS_PAD', k, 'ECS_PAD', x0 + (ci - 1) * dx, y0 + (ri - 1) * dy,
                     {'1': f'ROW{ri}', '2': f'COL{ci}', '3': 'GND'}, in_bom=False,
                     fp='tc52:ecs_pad_edge' if k == 'MX74' else None)
    yb = 142.24
    sh.text('Column discharge resistors (at the MUX inputs)', 25.4, yb - 10.16, 2.5)
    for ci in range(1, 15):
        sh.place('Device:R', f'R{40+ci}', '100k', x0 + (ci - 1) * dx, yb, {'1': f'COL{ci}', '2': 'GND'},
                 fp=R0402, lcsc='C25741', mpn='0402WGF1003TCE')
    yr = 182.88
    sh.text('Row drive: module pads 48 / 46 / 41 / 44 (P0.24, P0.22, P0.17, P0.20) -> 100R -> ROW1..4', 25.4, yr - 12.7, 2.5)
    for ri in range(1, 5):
        sh.place('Device:R', f'R{30+ri}', '100', 40.64 + (ri - 1) * 30.48, yr, {'1': f'ROW{ri}_DRV', '2': f'ROW{ri}'},
                 fp=R0402, lcsc='C25076', mpn='0402WGF1000TCE')
    sh.place('tc52:TestPoint', 'TP3', 'ROW1', 40.64 + 4 * 30.48, yr, {'1': 'ROW1'}, in_bom=False)
    ym = 236.22
    sh.text('Column select: each MUX has its own lines. INHA / INHB low = that MUX on (never both low). S1x/S2x/S3x = address A/B/C', 25.4, ym - 22.86, 2.5)
    for name, ref, xm, dec in (('A', 'U7', 60.96, 'C34'), ('B', 'U8', 152.4, 'C35')):
        nets = {'11': 'S1' + name, '10': 'S2' + name, '9': 'S3' + name, '6': 'INH' + name, '3': 'SENSE', '16': '+3V3M', '7': 'GND', '8': 'GND'}
        for xn, pin in M.X_PIN.items():
            nets[str(pin)] = 'GND'
        for c, (mx, xn) in M.MUX_INPUT.items():
            if mx == name:
                nets[str(M.X_PIN[xn])] = f'COL{c}'
        sh.place('tc52:CD4051B', ref, 'CD4051BM96', xm, ym, nets, lcsc='C21379', mpn='CD4051BM96')
        sh.place('Device:C', dec, '0.1u', xm + 38.1, ym, {'1': '+3V3M', '2': 'GND'}, fp=C0402, lcsc='C1525', mpn='CL05B104KO5NNNC')
    ya = 304.8
    sh.text('Analog front end (wired TC52 circuit): SENSE node (C30 reference cap, purge by P1.02) -> R22 -> non-inverting x44 -> AIN4 (P0.28).\\n'
            'C13 (12 pF at the + input, with R22: 130 MHz low-pass) keeps 2.4 GHz from the antenna out of the op amp input', 25.4, ya - 25.4, 2.5)
    sh.place('Device:C', 'C30', '300p C0G', 40.64, ya, {'1': 'SENSE', '2': 'GND'}, fp=C0603, lcsc='C52152', mpn='0603CG301J500NT',
             note='design-spec C2: SENSE reference capacitor (alt. 330p C1664)')
    sh.place('Device:C', 'C31', 'DNP', 63.5, ya, {'1': 'SENSE', '2': 'GND'}, fp=C0603, dnp=True, in_bom=False,
             note='design-spec C2B: trim seat in parallel with C30, not fitted')
    sh.place('Device:R', 'R22', '100', 86.36, ya, {'1': 'SENSE', '2': 'AMP_IN'}, fp=R0402, lcsc='C25076', mpn='0402WGF1000TCE', note='design-spec R3')
    sh.place('Device:C', 'C13', '12p', 101.6, ya, {'1': 'AMP_IN', '2': 'GND'}, fp=C0402, lcsc='C1547', mpn='0402CG120J500NT',
             note='RF bypass at the op amp input (wireless only)')
    sh.place('tc52:AD8601', 'U6', 'AD8601ARTZ', 127.0, ya, {'3': 'AMP_IN', '4': 'AMP_FB', '1': 'AMP_OUT', '5': '+3V3A', '2': 'GND'},
             lcsc='C41249', mpn='AD8601ARTZ-REEL7')
    sh.place('Device:R', 'R21', '43k 1%', 154.94, ya, {'1': 'AMP_OUT', '2': 'AMP_FB'}, fp=R0402, lcsc='C881384', mpn='CR0402F43K0Q10Z', note='design-spec R2 (gain trim seat)')
    sh.place('Device:R', 'R20', '1k', 177.8, ya, {'1': 'AMP_FB', '2': 'GND'}, fp=R0402, lcsc='C11702', mpn='0402WGF1001TCE', note='design-spec R1')
    sh.place('Device:R', 'R23', '0', 200.66, ya, {'1': 'AMP_OUT', '2': 'ADC'}, fp=R0402, lcsc='C17168', mpn='0402WGF0000TCE', note='design-spec R_ADC')
    sh.place('Device:C', 'C33', '0.1u', 223.52, ya, {'1': '+3V3A', '2': 'GND'}, fp=C0402, lcsc='C1525', mpn='CL05B104KO5NNNC')
    sh.place('tc52:TestPoint', 'TP1', 'SENSE', 246.38, ya, {'1': 'SENSE'}, in_bom=False)
    sh.place('tc52:TestPoint', 'TP2', 'ADC', 261.62, ya, {'1': 'AMP_OUT'}, in_bom=False)
    sh.place('tc52:TestPoint', 'TP4', 'GND', 276.86, ya, {'1': 'GND'}, in_bom=False)
    xs = 330.2
    sh.text('+3V3A (op amp) = GPIO AFE_EN (P0.13, high drive, held high while scanning) through R27 22R, 4.7u + 100n.\\n'
            'The op amp draws under 1 mA; the pin also gates it for sleep.  Reason for not feeding it from +3V3: docs/tc52w-build-log.md', xs - 15.24, ya - 25.4, 2.5)
    sh.place('Device:R', 'R27', '22', xs, ya, {'1': 'AFE_EN', '2': '+3V3A'}, fp=R0402, lcsc='C25092', mpn='0402WGF220JTCE',
             note='design-spec R_F: op amp supply filter, fed from GPIO AFE_EN')
    sh.place('Device:C', 'C32', '4.7u', xs + 25.4, ya, {'1': '+3V3A', '2': 'GND'}, fp=C0402, lcsc='C23733', mpn='CL05A475MP5NRNC', note='design-spec C_F1')
    sh.flag('+3V3A', xs + 48.26, ya)
    sh.text('+3V3M (MUX x2) = +3V3 through 22R, 4.7u', xs - 15.24, ya + 20.32, 2.5)
    sh.place('Device:R', 'R26', '22', xs, ya + 38.1, {'1': '+3V3', '2': '+3V3M'}, fp=R0402, lcsc='C25092', mpn='0402WGF220JTCE', note='second R_F: MUX supply')
    sh.place('Device:C', 'C37', '4.7u', xs + 25.4, ya + 38.1, {'1': '+3V3M', '2': 'GND'}, fp=C0402, lcsc='C23733', mpn='CL05A475MP5NRNC', note='second C_F1: MUX supply')
    sh.flag('+3V3M', xs + 48.26, ya + 38.1)
    yh = 363.22
    sh.text('Plate fixing holes (M2). H1 has a land: PLATE -> R25 (not fitted) -> GND', 25.4, yh - 15.24, 2.5)
    sh.place('tc52:Hole_Pad', 'H1', 'PLATE', 40.64, yh, {'1': 'PLATE'}, in_bom=False)
    sh.place('Device:R', 'R25', 'DNP (0R)', 66.04, yh, {'1': 'PLATE', '2': 'GND'}, fp=R0402, dnp=True, in_bom=False, note='design-spec R_PLATE, not fitted')
    for i in range(2, 13):
        sh.place('tc52:Hole', f'H{i}', 'M2', 66.04 + (i - 1) * 15.24, yh, {}, in_bom=False)
    return sh.render(3)


def build_root():
    def sheet(u, name, fn, x, y, page):
        return ['sheet', ['at', f'{x}', f'{y}'], ['size', '71.12', '40.64'], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
                ['on_board', 'yes'], ['dnp', 'no'], ['stroke', ['width', '0.1524'], ['type', 'solid']],
                ['fill', ['color', '0', '0', '0', '0']], ['uuid', Q(u)],
                ['property', Q('Sheetname'), Q(name), ['at', f'{x}', f'{y - 0.76}', '0'],
                 ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left', 'bottom']]],
                ['property', Q('Sheetfile'), Q(fn), ['at', f'{x}', f'{y + 41.34}', '0'],
                 ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left', 'top']]],
                ['instances', ['project', Q('ts52k'), ['path', Q('/' + ROOT_UUID), ['page', Q(str(page))]]]]]
    note = ('TC52 wireless: MDBT50Q-1MV2 (nRF52840) + 1S LiPo version of the wired TC52 capacitive keyboard.\\n'
            'Sheet mdbt50q: module, charger, USB, SWD, reset, encoder.  Sheet ec: 52 electrodes, MUX x2, analog front end.\\n'
            'The sheets are joined by global labels: ROW1..4_DRV, INHA/S1A..S3A, INHB/S1B..S3B, SENSE (purge, P1.02),\\n'
            'ADC (AIN4 = P0.28), AFE_EN (P0.13), ENC_A / ENC_B / ENC_SW, +3V3 (module VDD = REG0 output), GND.\\n'
            'Pin table and firmware notes: docs/tc52w-build-log.md')
    top = ['kicad_sch', ['version', '20260306'], ['generator', Q('tc52w_gen_sch')], ['generator_version', Q('10.0')],
           ['uuid', Q(ROOT_UUID)], ['paper', Q('A4')],
           ['title_block', ['title', Q('TC52 wireless')], ['rev', Q('0.1')],
            ['comment', '1', Q('Generated by pcb/tc52w-build/gen_sch.py')]],
           ['lib_symbols'],
           ['text', Q(note), ['exclude_from_sim', 'no'], ['at', '30.0', '40.0', '0'],
            ['effects', ['font', ['size', '2.0', '2.0']], ['justify', 'left']], ['uuid', Q(uid('root-note'))]],
           sheet(MCU_UUID, 'mdbt50q', 'mdbt50q.kicad_sch', 40.64, 70.0, 2),
           sheet(EC_UUID, 'ec', 'ec.kicad_sch', 150.0, 70.0, 3),
           ['sheet_instances', ['path', Q('/'), ['page', Q('1')]]], ['embedded_fonts', 'no']]
    return dump(top) + '\n'


def main():
    define_symbols()
    open(os.path.join(PCB, 'mdbt50q.kicad_sch'), 'w').write(build_mcu())
    open(os.path.join(PCB, 'ec.kicad_sch'), 'w').write(build_ec())
    open(os.path.join(PCB, 'ts52k.kicad_sch'), 'w').write(build_root())
    lib = ['kicad_symbol_lib', ['version', '20251024'], ['generator', Q('tc52w_gen_sch')], ['generator_version', Q('10.0')]]
    for k, s in SYMS.items():
        if k.startswith('tc52:'):
            t = parse(dump(s))
            t[1] = Q(k.split(':')[1])
            lib.append(t)
    open(os.path.join(PCB, 'tc52.kicad_sym'), 'w').write(dump(lib) + '\n')
    print('schematic written')


if __name__ == '__main__':
    main()
