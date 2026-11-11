"""Download selected manufacturer documents linked by JLCPCB (GET only)."""
import json,subprocess,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
parts={'C81598','C5118826','C165948','C318884','C22395519','C295747','C140288','C15127'}
log=[]
for r in json.loads((HERE/'jlc-metadata.json').read_text()):
    if r['part'] not in parts:continue
    url=r['metadata']['dataManualUrl'];path=HERE/'raw'/f"{r['part']}-datasheet.pdf"
    proc=subprocess.run(['curl','-L','--max-time','40','-sS','-w','%{http_code}',url,'-o',str(path)],capture_output=True,text=True)
    log.append(dict(part=r['part'],url=url,status=proc.stdout,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pdf=path.read_bytes().startswith(b'%PDF')))
    print(r['part'],proc.stdout,log[-1]['pdf'],flush=True)
(HERE/'fetch-datasheet-log.json').write_text(json.dumps(log,indent=2)+'\n')
