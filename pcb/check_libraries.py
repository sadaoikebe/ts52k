"""Check selected parts without modifying schematics or PCB. Run with KiCad Python."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import pcbnew


PCB = Path(__file__).resolve().parent
ROOT = PCB.parent


def parse(text):
    stack = [[]]
    for match in re.finditer(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text):
        token = match.group()
        if token == '(':
            stack.append([])
        elif token == ')':
            value = stack.pop()
            stack[-1].append(value)
        else:
            stack[-1].append(token[1:-1] if token.startswith('"') else token)
    assert len(stack) == 1 and len(stack[0]) == 1, 'Invalid expression'
    return stack[0][0]


def children(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def field(node, key):
    return children(node, key)[0][1:]


def properties(node):
    return {x[1]: x[2] for x in children(node, 'property')}


def walk(node, key):
    for value in node:
        if isinstance(value, list):
            if value and value[0] == key:
                yield value
            yield from walk(value, key)


def read(path):
    return parse(path.read_text(encoding='utf-8'))


def run_cli(cli, args):
    result = subprocess.run([str(cli), *map(str, args)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Error creating' not in result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--kicad-cli', type=Path, default=Path(sys.executable).with_name('kicad-cli.exe'))
    args = parser.parse_args()
    libs = {}
    inputs = [ROOT / 'notes/wireless-bom-draft.csv', PCB / 'wireless-library.csv', PCB / 'ts52k.kicad_pro']
    for table, kind in [('sym-lib-table', 'symbol'), ('fp-lib-table', 'footprint')]:
        inputs.append(PCB / table)
        for entry in children(read(PCB / table), 'lib'):
            name = field(entry, 'name')[0]
            assert name != 'rp2040', 'Obsolete library registered'
            path = Path(field(entry, 'uri')[0].replace('${KIPRJMOD}', str(PCB)))
            assert path.exists(), str(path)
            if kind == 'symbol':
                inputs.append(path)
                libs[name] = {x[1]: x for x in children(read(path), 'symbol')}
            else:
                inputs.extend(sorted(path.glob('*.kicad_mod')))
    assert set(libs['ts52k']) == {r['Symbol'].split(':')[1] for r in csv.DictReader((PCB / 'wireless-library.csv').open(encoding='utf-8'))} | {'MX-NoLED-MX_Alps_Hybrid'}
    assert not (PCB / 'rp2040.kicad_sym').exists()
    assert not (PCB / 'rp2040.pretty').exists()
    assert not (PCB / 'tag-connect.pretty').exists()

    with (ROOT / 'notes/wireless-bom-draft.csv').open(encoding='utf-8', newline='') as f:
        bom = list(csv.DictReader(f))
    with (PCB / 'wireless-library.csv').open(encoding='utf-8', newline='') as f:
        manifest = list(csv.DictReader(f))
    assert len(bom) == len(manifest) == 20
    assert len({r['MPN'] for r in bom}) == 20
    assert sum(int(r['Quantity']) for r in bom) == 82
    basic = [r for r in bom if r['JLCClass'] == 'Basic']
    assert (len(basic), sum(int(r['Quantity']) for r in basic)) == (13, 73)

    fps = {}
    for path in sorted((PCB / 'ts52k.pretty').glob('*.kicad_mod')):
        fp = read(path)
        assert fp[1] == path.stem
        assert pcbnew.FootprintLoad(str(path.parent), path.stem) is not None
        fps[path.stem] = fp
    assert len(fps) == 15
    for row, selected in zip(manifest, bom):
        assert all(row[k] == selected[k] for k in ['MPN', 'LCSC', 'Quantity'])
        lib, name = row['Symbol'].split(':')
        symbol = libs[lib][name]
        props = properties(symbol)
        assert all(props[k] == selected[k] for k in ['MPN', 'LCSC', 'Manufacturer', 'JLCClass'])
        assert props['Footprint'] == row['Footprint']
        fp = fps[row['Footprint'].split(':')[1]]
        pins = {field(p, 'number')[0] for p in walk(symbol, 'pin')}
        pads = {p[1] for p in children(fp, 'pad') if p[1] and p[1] != 'MP'}
        assert pins == pads, (name, pins - pads, pads - pins)
    used = {r['Footprint'].split(':')[1] for r in manifest}
    swd = properties(libs['tag-connect']['TC2030_IDC_NL'])['Footprint'].split(':')[1]
    assert set(fps) == used | {swd}, 'Unused or missing footprint'

    pinmap = {field(p, 'number')[0]: field(p, 'name')[0] for p in walk(libs['ts52k']['MDBT50Q-1MV2'], 'pin')}
    expected = {'1':'GND', '2':'GND', '15':'GND', '17':'P0.00', '18':'P0.01', '28':'VDD', '30':'VDDH', '31':'DCCH', '32':'VBUS', '33':'GND', '34':'D-', '35':'D+', '40':'P0.18', '51':'SWDIO', '53':'SWDCLK', '55':'GND'}
    assert all(pinmap[k] == v for k, v in expected.items())
    for name, size, positions in [
        ('Crystal_Epson_FC-12M_2.05x1.2mm', [0.7, 1.4], [-0.75, 0.75]),
        ('H5VU10U_DFN1006-2L', [0.55, 0.60], [-0.425, 0.425]),
    ]:
        pads = children(fps[name], 'pad')
        assert len(pads) == 2
        for pad, x in zip(pads, positions):
            assert list(map(float, field(pad, 'size'))) == size
            assert list(map(float, field(pad, 'at')[:2])) == [x, 0]
    zones = children(fps['Raytac_MDBT50Q'], 'zone')
    antenna = next(z for z in zones if children(z, 'layers'))
    assert len(field(antenna, 'layers')) == 32
    pts = field(field(antenna, 'polygon'), 'pts')
    ys = [float(p[2]) for p in pts]
    assert abs(max(ys) - min(ys) - 3.8) < 1e-9
    ep = next(p for p in children(fps['VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm'], 'pad') if p[1] == '17')
    assert list(map(float, field(ep, 'size'))) == [1.68, 1.68]
    for pad in children(fps[swd], 'pad'):
        if pad[1]:
            assert field(pad, 'layers') == ['F.Cu', 'F.Mask']
    swd_symbol = libs['tag-connect']['TC2030_IDC_NL']
    assert field(swd_symbol, 'in_bom') == ['no']
    assert field(swd_symbol, 'in_pos_files') == ['no']

    with tempfile.TemporaryDirectory(prefix='ts52k-library-check-') as tmp:
        out = Path(tmp)
        for lib in libs:
            dest = out / lib
            dest.mkdir()
            run_cli(args.kicad_cli, ['sym', 'export', 'svg', PCB / (lib + '.kicad_sym'), '-o', dest])
            assert len(list(dest.glob('*.svg'))) == len(libs[lib])
        dest = out / 'footprints'
        dest.mkdir()
        run_cli(args.kicad_cli, ['fp', 'export', 'svg', PCB / 'ts52k.pretty', '-o', dest])
        assert len(list(dest.glob('*.svg'))) == 15
    result = {
        'result': 'pass',
        'kicad_version': subprocess.check_output([str(args.kicad_cli), '--version'], text=True).strip(),
        'part_types': 20, 'assembly_quantity': 82,
        'basic_types': 13, 'basic_quantity': 73,
        'extended_types': 7, 'extended_quantity': 9,
        'ts52k_symbols': 21, 'swd_symbols': 1, 'ts52k_footprints': 15,
        'checks': ['registered_paths', 'obsolete_libraries_removed', 'bom_fields_and_quantities', 'symbol_pin_to_pad_numbers', 'module_critical_pin_names', 'crystal_and_esd_pad_dimensions', 'antenna_3_8mm_all_copper_keepout', 'charger_ep_size', 'swd_no_paste_and_no_assembly', 'kicad_read_and_svg_export'],
        'schematic_erc': 'separate_check_see_pcb/schematic-review/validation.json',
        'pcb_drc_and_parity': 'not_run_for_wireless_revision',
        'physical_boot': 'not_tested',
        'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(inputs))},
    }
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('PASS: 20 selected types / 82 parts; 21 symbols + SWD; 15 footprints')


if __name__ == '__main__':
    main()
