"""Verify regenerated outputs, unchanged source geometry, and every CPL angle."""
import collections,csv,hashlib,io,json,subprocess,zipfile,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
JLC=ROOT/'pcb/jlcpcb'
BASE='6e3c3ec'
def blob(path):return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT)
def sha(data):return hashlib.sha256(data).hexdigest()
manifest=json.loads((JLC/'assembly/manifest.json').read_text())
for path,h in manifest['source_sha256'].items():
    data=(ROOT/'pcb'/path).read_bytes()
    assert sha(data)==h
    assert data==blob('pcb/'+path),path
for path,h in manifest['output_sha256'].items():assert sha((JLC/path).read_bytes())==h,path
oldmanifest=json.loads(blob('pcb/jlcpcb/assembly/manifest.json'))
baseline_mismatches={p:dict(recorded=h,actual=sha(blob('pcb/jlcpcb/'+p))) for p,h in oldmanifest['output_sha256'].items() if h!=sha(blob('pcb/jlcpcb/'+p))}
readcsv=lambda b:list(csv.DictReader(io.StringIO(b.decode())))
cpl=readcsv((JLC/'assembly/ts52k-cpl.csv').read_bytes())
oldcpl=readcsv(blob('pcb/jlcpcb/assembly/ts52k-cpl.csv'))
assert cpl==oldcpl
assert (JLC/'assembly/ts52k-bom.csv').read_bytes()==blob('pcb/jlcpcb/assembly/ts52k-bom.csv')
positions={r['Designator']:r for r in cpl}
assert len(positions)==len(cpl)==82
geom=json.loads((HERE/'geometry.json').read_text())
nonpolar={'C15849','C19666','C15850','C14663','C1547','C713281','C23186','C25981','C22843','C25804','C22939','C96341'}
audit=[]
for row in geom:
    part=row['bom']['LCSC Part #'];status='補正あり（既存+180°維持）' if part=='C15127' else '回転無意味（180°）' if part in nonpolar else '補正不要（確認済み）'
    for inst in row['instances']:
        ref=inst['ref'];r=positions[ref]
        assert r['Layer']=='Bottom' and inst['bottom']
        assert abs(float(r['Mid X'])-inst['x'])<.000002
        assert abs(float(r['Mid Y'])+inst['y'])<.000002
        correction=180 if part=='C15127' else 0
        assert abs((float(r['Rotation'])-inst['angle']-correction+180)%360-180)<1e-6
        audit.append(dict(Designator=ref,LCSC=part,Footprint=row['bom']['Footprint'],Layer='Bottom',KiCad_raw_rotation=inst['angle'],Correction=correction,Before_CPL_rotation=r['Rotation'],After_CPL_rotation=r['Rotation'],Status=status))
assert len(audit)==82 and {r['Designator'] for r in audit}==set(positions)
with (HERE/'instance-audit.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(audit[0]),lineterminator='\n');w.writeheader();w.writerows(audit)
a=zipfile.ZipFile(io.BytesIO(blob('pcb/jlcpcb/gerber/ts52k-gerbers.zip')))
b=zipfile.ZipFile(JLC/'gerber/ts52k-gerbers.zip')
assert a.namelist()==b.namelist()
def without_dates(raw):
    return '\n'.join(l for l in raw.decode().splitlines() if not any(t in l for t in ['CreationDate','G04 Created by KiCad','; DRILL file KiCad']))
for name in a.namelist():assert without_dates(a.read(name))==without_dates(b.read(name)),name
drc=json.loads((JLC/'assembly/drc.json').read_text());erc=json.loads((JLC/'assembly/erc.json').read_text())
assert len(drc['violations'])==9 and not drc['unconnected_items'] and not drc['schematic_parity']
assert all(v['severity']=='warning' and v['type'] in {'silk_overlap','silk_edge_clearance'} for v in drc['violations'])
assert not [v for s in erc['sheets'] for v in s['violations']]
assert (JLC/'assembly/export-status.txt').read_text().startswith('EXPORT COMPLETED')
result=dict(base=BASE,kicad_version=subprocess.check_output(['kicad-cli','--version'],text=True).strip(),assembly_references=82,bom_rows=21,lcsc_parts=20,source_files_byte_identical=True,bom_and_cpl_byte_identical=True,cpl_angles_verified=82,gerber_members_equal_except_dates=len(a.namelist()),drc=dict(errors=0,unconnected=0,parity=0,warnings=dict(collections.Counter(v['type'] for v in drc['violations']))),erc_violations=0,manifest_hashes_verified=True,baseline_manifest_mismatches=baseline_mismatches,output_sha256=manifest['output_sha256'],decisions=dict(collections.Counter(r['Status'] for r in audit)))
(HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for name in ['drc.json','erc.json']:shutil.copyfile(JLC/'assembly'/name,HERE/name)
print(json.dumps(result,ensure_ascii=False,indent=2))
