"""西端移設後のGPIO表とアンテナ周辺を検査する（基板は保存しない）。"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import pcbnew as p


ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / 'pcb/ts52k.kicad_pcb'


def vertices(poly):
    return [[p.ToMM(poly.Outline(0).CPoint(i).x),
             p.ToMM(poly.Outline(0).CPoint(i).y)]
            for i in range(poly.Outline(0).PointCount())]


def intersection_area(a, b):
    result = p.SHAPE_POLY_SET(a)
    result.BooleanIntersection(b)
    return result.Area() / 1e12


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--netlist', required=True, type=Path,
                        help='現回路図からkicad-cliで出力したkicadxml')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    board = p.LoadBoard(str(PCB))
    u5 = board.FindFootprintByReference('U5')
    table = (ROOT / 'notes/wireless-pin-assignment.md').read_text()
    rows = re.findall(r'^\| ((?:col|row)\d+|rpg[12])(?:（[AB]）)? \| '
                      r'(P[01]\.\d+) \| (\d+) \| (P[01]\.\d+) / (\d+) \|$',
                      table, re.M)
    assert len(rows) == 18, 'GPIO表の18信号を読み取れない'
    nets = ET.parse(args.netlist).getroot().find('nets')
    schematic = {n.attrib['name']: {x.attrib['pin'] for x in n.findall('node')
                                  if x.attrib['ref'] == 'U5'} for n in nets}
    pads = {pad.GetNumber(): pad for pad in u5.Pads()}
    # GPIO名も、回路図のライブラリ端子定義と照合する。
    xml = ET.parse(args.netlist).getroot()
    component = next(c for c in xml.find('components') if c.attrib['ref'] == 'U5')
    source = component.find('libsource').attrib
    part = next(x for x in xml.find('libparts')
                if x.attrib['lib'] == source['lib'] and x.attrib['part'] == source['part'])
    pin_names = {x.attrib['num']: x.attrib['name'] for x in part.find('pins')}
    checklist = (ROOT / 'notes/zmk-pin-sync-checklist.md').read_text()
    gpio = []
    for net, name, pad, old_name, old_pad in rows:
        assert schematic[net] == {pad}, (net, schematic[net], pad)
        assert pads[pad].GetNetname() == net, (net, pad)
        assert pin_names[pad] == name, (pad, pin_names[pad], name)
        assert f'{old_name} / {old_pad} | {name} / {pad} |' in checklist, net
        controller, number = map(int, name[1:].split('.'))
        line = next(x for x in checklist.splitlines()
                    if f' / {net} |' in x)
        assert f'`&gpio{controller} {number}`' in line, net
        gpio.append({'net': net, 'gpio': name, 'pad': pad})

    # モジュール内の大きい全層keepoutがメーカーのアンテナ帯。
    copper_layers = list(board.GetEnabledLayers().CuStack())
    assert len(copper_layers) == 2
    antenna = max((z for z in u5.Zones() if z.GetIsRuleArea()),
                  key=lambda z: z.Outline().Area())
    edge = next(z for z in board.Zones() if z.GetZoneName() == 'ANT_EDGE')
    regions = {'module_antenna': antenna, 'ANT_EDGE': edge}
    for label, zone in regions.items():
        assert all(zone.IsOnLayer(layer) for layer in copper_layers), label
        assert (zone.GetDoNotAllowTracks() and zone.GetDoNotAllowVias()
                and zone.GetDoNotAllowPads() and zone.GetDoNotAllowZoneFills()), label
    bb = antenna.Outline().BBox()
    assert sorted([bb.GetWidth(), bb.GetHeight()]) == [p.FromMM(3.8), p.FromMM(12.4)]
    old_rule_count = PCB.read_text().count('ANT_NO_FILL')
    assert old_rule_count == 0

    p.ZONE_FILLER(board).Fill(board.Zones())
    items = [(track, track.GetClass()) for track in board.GetTracks()]
    for footprint in board.GetFootprints():
        items.extend((pad, 'PAD') for pad in footprint.Pads())
        items.extend((item, item.GetClass()) for item in footprint.GraphicalItems())
        items.extend((field, field.GetClass()) for field in footprint.GetFields()
                     if field.IsVisible())
    items.extend((item, item.GetClass()) for item in board.GetDrawings())
    result = {}
    checked = Counter()
    # KiCadの外接ポリゴン（最大誤差1 µm）で幅と半径を含めて検査する。
    for label, region in regions.items():
        result[label] = {'vertices_mm': vertices(region.Outline()),
                         'forbidden': {'tracks': region.GetDoNotAllowTracks(),
                                       'vias': region.GetDoNotAllowVias(),
                                       'pads': region.GetDoNotAllowPads(),
                                       'zone_fills': region.GetDoNotAllowZoneFills()},
                         'layers': {}, 'intrusions': []}
    for layer in copper_layers:
        layer_name = board.GetLayerName(layer)
        for item, kind in items:
            if not item.IsOnLayer(layer):
                continue
            shape = p.SHAPE_POLY_SET()
            item.TransformShapeToPolygon(shape, layer, 0, p.FromMM(0.001), p.ERROR_OUTSIDE)
            checked[f'{layer_name}/{kind}'] += 1
            for label, region in regions.items():
                area = intersection_area(shape, region.Outline())
                if area > 0:
                    result[label]['intrusions'].append({
                        'kind': kind, 'uuid': item.m_Uuid.AsString(),
                        'layer': layer_name, 'area_mm2': area})
        for label, region in regions.items():
            zones = []
            for zone in board.Zones():
                if zone.GetIsRuleArea() or not zone.IsOnLayer(layer):
                    continue
                area = intersection_area(zone.GetFilledPolysList(layer), region.Outline())
                zones.append({'net': zone.GetNetname(), 'intersection_mm2': area})
            result[label]['layers'][layer_name] = {'filled_zones': zones}
    problems = sum(len(x['intrusions']) for x in result.values())
    problems += sum(z['intersection_mm2'] > 0 for x in result.values()
                    for layer in x['layers'].values() for z in layer['filled_zones'])
    # 文書の検索範囲と全ヒット行も保存し、メーカーの別製品・旧版の記録を区別して読む。
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    docs = [s for s in tracked if Path(s).suffix.lower() in ('.md', '.txt', '.rst', '.csv')
            and not s.startswith(('pcb/placement-review/', 'pcb/schematic-review/'))]
    pattern = re.compile(r'gpio|P[01][._]\d+|パッド|ピン|\b(?:row|col)\d+|rpg[12]', re.I)
    hits = {s: [f'{i}: {line}' for i, line in enumerate(
        (ROOT / s).read_text(encoding='utf-8-sig').splitlines(), 1) if pattern.search(line)]
            for s in docs}
    hits = {s: lines for s, lines in hits.items() if lines}
    report = {'kicad': p.Version(), 'pcb_sha256': hashlib.sha256(PCB.read_bytes()).hexdigest(),
              'schematic_sha256': {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                                     for s in ('pcb/ts52k.kicad_sch', 'pcb/mdbt50q.kicad_sch')},
              'netlist_sha256': hashlib.sha256(args.netlist.read_bytes()).hexdigest(),
              'gpio_matches': gpio, 'old_ANT_NO_FILL_occurrences': old_rule_count,
              'U5_position_mm': [p.ToMM(u5.GetPosition().x), p.ToMM(u5.GetPosition().y)],
              'U5_orientation_degrees': u5.GetOrientationDegrees(),
              'polygon_error_mm': 0.001, 'checked_copper_objects': dict(checked),
              'antenna': result, 'antenna_problem_count': problems,
              'document_scan': {'files_scanned': docs, 'hits': hits}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'gpio_matches': len(gpio), 'antenna_problems': problems,
                      'documents_scanned': len(docs), 'documents_with_hits': len(hits)},
                     ensure_ascii=False))
    assert problems == 0, 'アンテナ禁止領域に銅箔がある'


if __name__ == '__main__':
    main()
