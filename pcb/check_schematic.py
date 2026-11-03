"""Validate the wireless schematic against its BOM, pin plan and previous matrix."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from check_libraries import children, field, properties, read


PCB = Path(__file__).resolve().parent
ROOT = PCB.parent
BASELINE = 'a82fe3d'


def export_netlist(cli, schematic, dest):
    subprocess.run([str(cli), 'sch', 'export', 'netlist', str(schematic), '--format', 'kicadxml', '-o', str(dest)], check=True, capture_output=True, text=True)
    return ET.parse(dest).getroot()


def netsets(xml):
    return {n.attrib['name']: {(p.attrib['ref'], p.attrib['pin']) for p in n.findall('node')} for n in xml.find('nets').findall('net')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PCB / 'schematic-review')
    parser.add_argument('--kicad-cli', type=Path, default=Path(sys.executable).with_name('kicad-cli.exe'))
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cli = args.kicad_cli
    netfile = out / 'ts52k-wireless.net'
    xml = export_netlist(cli, PCB / 'ts52k.kicad_sch', netfile)
    nets = netsets(xml)
    node_net = {node: name for name, nodes in nets.items() for node in nodes}
    comp = {c.attrib['ref']: c for c in xml.find('components').findall('comp')}
    assert len(comp) == 135

    def N(*pairs):
        return {(ref, str(pin)) for ref, pin in pairs}

    required = {
        'USB_VBUS': N(('J1','A4'), ('J1','A9'), ('J1','B4'), ('J1','B9'), ('D91',1), ('R20',1), ('C22',1), ('U6',13)),
        'MCU_VBUS': N(('R20',2), ('C26',1), ('U5',32)),
        'VDDH': N(('U6',10), ('U6',11), ('C23',1), ('C25',1), ('U5',30)),
        'BAT': N(('U6',2), ('U6',3), ('C24',1), ('J3',1)),
        'nRF_VDD': N(('L1',1), ('U5',28), ('J2',1), *[(f'C{i}',1) for i in range(27,32)]),
        'DCCH': N(('L1',2), ('U5',31)),
        'D+': N(('J1','A6'), ('J1','B6'), ('D90',1), ('U5',35)),
        'D-': N(('J1','A7'), ('J1','B7'), ('D89',1), ('U5',34)),
        'SWDIO': N(('J2',2), ('U5',51)),
        'SWCLK': N(('J2',4), ('U5',53)),
        'nRESET': N(('J2',3), ('SW1',2), ('U5',40)),
        'rpg1': N(('SW2','A'), ('U5',45)),
        'rpg2': N(('SW2','B'), ('U5',46)),
    }
    for name, expected in required.items():
        assert nets[name] == expected, (name, nets[name] ^ expected)
    ground = N(*[('U5', p) for p in [1,2,15,33,55]], *[('U6',p) for p in [4,5,6,8,15,17]], ('J2',5), ('J3',2), ('SW1',1), ('SW2','C'), ('SW2','MP'))
    ground |= N(*[(f'C{i}',2) for i in range(22,34)], *[(f'R{i}',2) for i in [17,18,19]], ('R5',1), ('R6',1))
    ground |= N(*[(f'D{i}',2) for i in [89,90,91]], *[('J1',p) for p in ['A1','A12','B1','B12','SH']])
    assert nets['GND'] == ground, ('GND', nets['GND'] ^ ground)
    for ref, pin in [('R17',16), ('R18',12), ('R19',1)]:
        assert nets[node_net[(ref,'1')]] == N((ref,1), ('U6',pin))
    for cc, resistor in [('A5','R5'), ('B5','R6')]:
        assert nets[node_net[('J1',cc)]] == N(('J1',cc), (resistor,2))
    for mcu_pin, cap, crystal_pin in [(17,'C32',2), (18,'C33',1)]:
        assert nets[node_net[('U5',str(mcu_pin))]] == N(('U5',mcu_pin), (cap,1), ('X3',crystal_pin))
    for ref, pin in [('J2',6), ('J1','A8'), ('J1','B8'), ('U6',7), ('U6',9), ('U6',14), ('U5',39)]:
        assert len(nets[node_net[(ref,str(pin))]]) == 1, (ref,pin)

    gpio = dict(zip([f'col{i}' for i in range(1,7)], [22,23,20,21,19,16]))
    gpio.update(zip([f'row{i}' for i in range(1,11)], [24,25,27,29,36,37,41,42,43,44]))
    gpio.update(rpg1=45, rpg2=46)
    for name, pin in gpio.items():
        assert ('U5',str(pin)) in nets[name]
        assert sum(ref=='U5' for ref,p in nets[name]) == 1

    with (ROOT / 'notes/wireless-bom-draft.csv').open(encoding='utf-8', newline='') as f:
        bom = {r['LCSC']:r for r in csv.DictReader(f)}
    with (PCB / 'wireless-library.csv').open(encoding='utf-8', newline='') as f:
        registered = {r['LCSC']:r for r in csv.DictReader(f)}
    actual = Counter()
    refs = {}
    for ref, component in comp.items():
        metadata = {p.attrib['name']:p.attrib.get('value','') for p in component.findall('property')}
        lcsc = metadata.get('LCSC')
        if not lcsc:
            assert ref.startswith('MX') or ref in ['SW2','J2'], ref
            continue
        row = bom[lcsc]
        actual[lcsc] += 1
        refs.setdefault(lcsc, []).append(ref)
        assert all(metadata[k] == row[k] for k in ['MPN','Manufacturer','JLCClass']), ref
        assert component.findtext('footprint') == registered[lcsc]['Footprint'], ref
        lib = component.find('libsource')
        assert lib.attrib['lib']+':'+lib.attrib['part'] == registered[lcsc]['Symbol'], ref
    assert actual == Counter({k:int(v['Quantity']) for k,v in bom.items()})
    assert sum(actual.values()) == 81
    with (out/'bom.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f)
        w.writerow(['MPN','LCSC','Quantity','References','JLCClass','Footprint'])
        for lcsc,row in bom.items():
            w.writerow([row['MPN'],lcsc,actual[lcsc],','.join(sorted(refs[lcsc])),row['JLCClass'],registered[lcsc]['Footprint']])

    root = read(PCB/'ts52k.kicad_sch')
    current = {properties(s)['Reference']:s for s in children(root,'symbol')}
    # A pin lying inside a redundant overlapping segment can lose its branch on save.
    # All four USB data contacts must therefore be explicit wire endpoints.
    wire_ends = {tuple(map(float, point[1:])) for w in children(root,'wire') for point in field(w,'pts')}
    assert {(44.45,y) for y in [165.1,167.64,170.18,172.72]} <= wire_ends, 'USB data contact without explicit wire endpoint'
    with tempfile.TemporaryDirectory(prefix='ts52k-matrix-baseline-') as tmp:
        tmp = Path(tmp)
        for filename in ['ts52k.kicad_sch','rp2040.kicad_sch']:
            (tmp/filename).write_bytes(subprocess.check_output(['git','show',BASELINE+':pcb/'+filename],cwd=ROOT))
        old = read(tmp/'ts52k.kicad_sch')
        prior = {properties(s)['Reference']:s for s in children(old,'symbol')}
        matrix = {ref for ref in current if ref.startswith('MX') or ref.startswith('D') and ref not in ['D89','D90','D91']}
        assert len(matrix) == 105
        retained = matrix | {'J1','J2','SW1','SW2','D89','D90','D91','R5','R6'}
        for ref in retained:
            assert field(current[ref],'at') == field(prior[ref],'at'), ref
            assert field(current[ref],'uuid') == field(prior[ref],'uuid'), ref
        assert field(children(root,'sheet')[0],'at') == field(children(old,'sheet')[0],'at')
        oldnets = netsets(export_netlist(cli,tmp/'ts52k.kicad_sch',tmp/'before.net'))
        def matrix_graph(net_dict):
            domain=lambda ref,pin: ref in matrix or ref=='SW2' and pin in ['S1','S2']
            return {frozenset(n for n in nodes if domain(*n)) for nodes in net_dict.values()}-{frozenset()}
        assert matrix_graph(oldnets) == matrix_graph(nets), 'Matrix connectivity changed'
        # PCB placement has its own review; schematic checks do not freeze it.

    ercfile = out/'erc.json'
    subprocess.run([str(cli),'sch','erc',str(PCB/'ts52k.kicad_sch'),'--format','json','--severity-all','--exit-code-violations','-o',str(ercfile)],check=True,capture_output=True,text=True)
    erc=json.loads(ercfile.read_text(encoding='utf-8'))
    assert not [v for s in erc['sheets'] for v in s['violations']]
    sources = [PCB/'ts52k.kicad_sch',PCB/'mdbt50q.kicad_sch',PCB/'ts52k.kicad_pro',PCB/'ts52k.kicad_sym',PCB/'tag-connect.kicad_sym',ROOT/'notes/wireless-bom-draft.csv',PCB/'wireless-library.csv',Path(__file__)]
    result = {'result':'pass','kicad_version':subprocess.check_output([str(cli),'--version'],text=True).strip(), 'erc_errors':0,'erc_warnings':0,'assembly_part_types':19,'assembly_quantity':81,'retained_matrix_parts':105,'retained_component_coordinates':len(retained),'matrix_connectivity':'unchanged','baseline_commit':BASELINE,'pcb':'checked_separately_in_placement_review','physical_boot':'not_tested','checks':['power_nets_exact_membership','usb_data_and_cc','usb_data_contacts_explicit_wire_endpoints','all_module_ground_pads','charger_control_and_ep','fixed_usb100','swd_and_reset','lf_crystal_and_loads','18_gpio_assignments','nc_pins','selected_parts_metadata_and_footprints','old_matrix_graph_and_coordinates','kicad_erc'], 'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (out/'validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: ERC 0 errors / 0 warnings; 19 types / 81 parts; original matrix and coordinates preserved; PCB checked separately')


if __name__=='__main__':
    main()
