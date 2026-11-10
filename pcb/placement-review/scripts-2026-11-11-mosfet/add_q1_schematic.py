"""Add Q1 (AO3401A, reverse-battery protection) to the project library and schematic.

Run once on wireless b730700:  python3 add_q1_schematic.py <repo root> [rot] [mirror]
- copies KiCad's Package_TO_SOT_SMD:SOT-23 into pcb/ts52k.pretty
- adds a standalone ts52k:AO3401A symbol (graphics/pins of Transistor_FET:TP0610T,
  which Transistor_FET:AO3401A extends) to pcb/ts52k.kicad_sym and the schematic
- moves J3 into a new block: BAT -> Q1 source, Q1 drain -> BAT_CONN -> J3 pin 1, Q1 gate -> GND
"""
import hashlib, json, re, shutil, sys, uuid
from pathlib import Path

ROOT = Path(sys.argv[1])
ROT = sys.argv[2] if len(sys.argv) > 2 else '90'
MIRROR = sys.argv[3] if len(sys.argv) > 3 else 'y'
PCB = ROOT / 'pcb'
KICAD_SYM = Path('/usr/share/kicad/symbols/Transistor_FET.kicad_sym')
KICAD_FP = Path('/usr/share/kicad/footprints/Package_TO_SOT_SMD.pretty/SOT-23.kicad_mod')
SHEET = '/a46aaf04-b440-466e-8b21-108f618a37ed'
DS = 'https://www.aosmd.com/pdfs/datasheet/AO3401A.pdf'
DESC = 'AO3401A P-channel MOSFET, -30 V, SOT-23; 1 G, 2 S, 3 D; reverse-battery protection'
EXTRA = [('MPN', 'AO3401A'), ('Manufacturer', 'Alpha & Omega Semiconductor'), ('LCSC', 'C15127'), ('JLCClass', 'Basic')]


def block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError('unbalanced')


def uid():
    return str(uuid.uuid4())


def prop(name, value, at, hide, indent, size='1.27 1.27', justify=None):
    t = '\t' * indent
    j = f'\n{t}\t\t(justify {justify})' if justify else ''
    h = f'\n{t}\t(hide yes)' if hide else ''
    return (f'{t}(property "{name}" "{value}"\n{t}\t(at {at})\n{t}\t(show_name no)\n{t}\t(do_not_autoplace no){h}\n'
            f'{t}\t(effects\n{t}\t\t(font\n{t}\t\t\t(size {size})\n{t}\t\t)' + j + f'\n{t}\t)\n{t})\n')


def lib_symbol(name, indent):
    """Standalone symbol text; name is 'AO3401A' (library) or 'ts52k:AO3401A' (schematic cache)."""
    src = KICAD_SYM.read_text(encoding='utf-8')
    base = block(src, src.index('\t(symbol "TP0610T"'))
    units = ''.join(block(base, base.index(f'(symbol "TP0610T_{u}"')).replace('TP0610T_', 'AO3401A_') for u in ('0_1', '1_1'))
    units = '\n'.join(('\t\t' + block(base, base.index(f'(symbol "TP0610T_{u}"'))).replace('TP0610T_', 'AO3401A_') for u in ('0_1', '1_1'))
    t = '\t' * indent
    body = (f'(symbol "{name}"\n\t(pin_names\n\t\t(hide yes)\n\t)\n\t(exclude_from_sim no)\n\t(in_bom yes)\n\t(on_board yes)\n'
            '\t(in_pos_files yes)\n\t(duplicate_pin_numbers_are_jumpers no)\n'
            + prop('Reference', 'Q', '5.08 1.905 0', False, 1, justify='left')
            + prop('Value', 'AO3401A', '5.08 0 0', False, 1, justify='left')
            + prop('Footprint', 'ts52k:SOT-23', '5.08 -1.905 0', True, 1, justify='left')
            + prop('Datasheet', DS, '5.08 -3.81 0', True, 1, justify='left')
            + prop('Description', DESC, '0 0 0', True, 1)
            + prop('ki_fp_filters', 'SOT?23*', '0 0 0', True, 1)
            + ''.join(prop(k, v, '0 0 0', True, 1) for k, v in EXTRA)
            + re.sub(r'(?m)^\t\t', '\t', units) + '\n\t(embedded_fonts no)\n)')
    return '\n'.join(t + line if line else line for line in body.split('\n'))


def instance(lib_id, ref, value, at, rot, mirror, props, pins, ref_at, val_at, fp=''):
    m = f'\n\t\t(mirror {mirror})' if mirror else ''
    out = (f'\t(symbol\n\t\t(lib_id "{lib_id}")\n\t\t(at {at[0]} {at[1]} {rot}){m}\n\t\t(unit 1)\n\t\t(body_style 1)\n'
           '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n'
           f'\t\t(uuid "{uid()}")\n')
    here = f'{at[0]} {at[1]} 0'
    out += prop('Reference', ref, ref_at, ref.startswith('#'), 2, '1 1', 'left' if not ref.startswith('#') else None)
    out += prop('Value', value, val_at, False, 2, '1 1', 'left' if not ref.startswith('#') else None)
    out += prop('Footprint', fp, here, True, 2, '1 1')
    for k, v in props:
        out += prop(k, v, here, True, 2, '1 1')
    for p in pins:
        out += f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)\n'
    out += (f'\t\t(instances\n\t\t\t(project "ts52k"\n\t\t\t\t(path "{SHEET}"\n\t\t\t\t\t(reference "{ref}")\n'
            '\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
    return out


def wire(a, b):
    return (f'\t(wire\n\t\t(pts\n\t\t\t(xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n'
            f'\t\t\t(type default)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)\n')


def main():
    # footprint
    dst = PCB / 'ts52k.pretty' / 'SOT-23.kicad_mod'
    shutil.copyfile(KICAD_FP, dst)
    # library symbol
    libp = PCB / 'ts52k.kicad_sym'
    lib = libp.read_text(encoding='utf-8')
    assert '(symbol "AO3401A"' not in lib
    marker = '(symbol "MX-NoLED-MX_Alps_Hybrid"'
    lib = lib.replace(marker, lib_symbol('AO3401A', 0) + '\n' + marker, 1)
    libp.write_text(lib, encoding='utf-8')
    # provenance
    srcp = PCB / 'library-sources.json'
    src = json.loads(srcp.read_text(encoding='utf-8'))
    src['assets'] += [
        {'asset': 'ts52k:SOT-23', 'source': 'Package_TO_SOT_SMD:SOT-23', 'source_sha256': hashlib.sha256(KICAD_FP.read_bytes()).hexdigest(),
         'source_kicad_version': '10.0.8'},
        {'asset': 'ts52k:AO3401A', 'source': 'Transistor_FET:AO3401A', 'source_sha256': hashlib.sha256(KICAD_SYM.read_bytes()).hexdigest(),
         'source_kicad_version': '10.0.8'},
    ]
    srcp.write_text(json.dumps(src, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    schp = PCB / 'ts52k.kicad_sch'
    s = schp.read_text(encoding='utf-8')
    assert '"ts52k:AO3401A"' not in s
    # cache symbol
    marker = '\t\t(symbol "ts52k:S2B-PH-SM4-TB(LF)(SN)"'
    s = s.replace(marker, lib_symbol('ts52k:AO3401A', 2) + '\n' + marker, 1)

    # --- J3 moves from (130.81,135.89) to (170.18,167.64); its GND symbol follows
    j0 = s.index('(reference "J3")')
    a = s.rfind('\n\t(symbol\n', 0, j0) + 1
    j3 = block(s, a)
    new = j3.replace('(at 130.81 135.89 0)', '(at 170.18 167.64 0)').replace('(at 130.81 130.81 0)', '(at 170.18 163.83 0)') \
            .replace('(at 119.38 133.35 0)', '(at 170.18 161.925 0)')
    assert new.count('170.18 167.64') >= 6
    s = s.replace(j3, new, 1)
    g0 = s.index('(reference "#PWR0318")')
    a = s.rfind('\n\t(symbol\n', 0, g0) + 1
    gnd = block(s, a)
    s = s.replace(gnd, gnd.replace('125.73 146.05', '165.1 175.26').replace('125.73 149.86', '165.1 179.07'), 1)
    # old wires: BAT run now ends at the C24 junction; J3 pin 2 drop moves with J3
    old = '(xy 95.25 135.89) (xy 125.73 135.89)'
    assert s.count(old) == 1
    s = s.replace(old, '(xy 95.25 135.89) (xy 119.38 135.89)')
    old = '(xy 125.73 138.43) (xy 125.73 146.05)'
    assert s.count(old) == 1
    s = s.replace(old, '(xy 165.1 170.18) (xy 165.1 175.26)')
    k = s.index('\t(junction\n\t\t(at 119.38 135.89)')
    s = s.replace(block(s, k + 1) + '\n\t', '', 1) if False else s[:k] + s[k:].replace('\t' + block(s, k + 1) + '\n', '', 1)

    # --- new items
    add = ''
    add += instance('ts52k:AO3401A', 'Q1', 'AO3401A', (152.4, 170.18), ROT, MIRROR,
                    [('Datasheet', DS), ('Description', DESC)] + EXTRA, ['1', '2', '3'],
                    '154.94 171.45 90', '154.94 173.355 90', 'ts52k:SOT-23')
    gnd_new = gnd.replace('125.73 146.05', '152.4 175.26').replace('125.73 149.86', '152.4 179.07').replace('#PWR0318', '#PWR0319')
    gnd_new = re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{uid()}")', gnd_new)
    add += '\t' + gnd_new + '\n'
    add += wire((142.24, 167.64), (147.32, 167.64))      # BAT label -> Q1 S
    add += wire((157.48, 167.64), (165.1, 167.64))      # Q1 D -> J3 pin 1 (BAT_CONN)
    gl = block(s, s.index('(global_label "BAT"'))
    gl = gl.replace('116.84 135.89', '142.24 167.64').replace('(at 142.24 167.64 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t)\n\t\t\t(justify left)',
                                                              '(at 142.24 167.64 180)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t)\n\t\t\t(justify right)', 1)
    gl = re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{uid()}")', gl)
    add += '\t' + gl + '\n'
    add += (f'\t(label "BAT_CONN"\n\t\t(at 157.48 167.64 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t)\n'
            f'\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)\n')
    for text, y in (('Reverse-battery protection', 157.48), ('Q1 body diode conducts J3 -> BAT; gate at GND', 159.385)):
        add += (f'\t(text "{text}"\n\t\t(exclude_from_sim no)\n\t\t(at 139.7 {y} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n\t\t\t)\n'
                f'\t\t\t(justify left)\n\t\t)\n\t\t(uuid "{uid()}")\n\t)\n')
    k = s.index('\t(text "USB100 fixed charging')
    s = s[:k] + add + s[k:]
    schp.write_text(s, encoding='utf-8')


main()
