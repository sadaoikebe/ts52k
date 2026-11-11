"""Follow PDF links in the LCSC HTML document wrappers already fetched."""
import hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
log=[]
for path in sorted((HERE/'raw').glob('*-datasheet.pdf')):
    if path.read_bytes().startswith(b'%PDF'):continue
    part=path.name.split('-')[0]
    url=re.search(r'https://datasheet\.lcsc\.com/datasheet/pdf/[^\s\"\'<>]+',path.read_text()).group()
    wrapper=path.with_suffix('.html');path.rename(wrapper)
    p=subprocess.run(['curl','-L','--max-time','40','-sS','-w','%{http_code}',url,'-o',str(path)],capture_output=True,text=True)
    log.append(dict(part=part,url=url,status=p.stdout,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pdf=path.read_bytes().startswith(b'%PDF')))
    print(part,p.stdout,log[-1]['pdf'],flush=True)
(HERE/'fetch-pdf-log.json').write_text(json.dumps(log,indent=2)+'\n')
