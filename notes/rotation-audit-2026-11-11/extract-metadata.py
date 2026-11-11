"""Preserve product identity and datasheet links from JLCPCB's public SSR HTML."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
records=[]
for path in sorted((HERE/'raw').glob('*-jlc.html')):
    s=path.read_text(); part=path.name.split('-')[0]; chunks=[]
    for m in re.finditer(r'self\.__next_f\.push\((\[1,.*?\])\)</script>',s):
        chunks.append(json.loads(m.group(1))[1])
    candidates=[]
    for line in ''.join(chunks).splitlines():
        try: obj=json.loads(line.split(':',1)[1])
        except (ValueError,IndexError): continue
        if isinstance(obj,dict) and obj.get('componentCode')==part and 'dataManualUrl' in obj:
            candidates.append(obj)
    assert candidates, part
    obj=candidates[-1]
    records.append(dict(part=part,url=f'https://jlcpcb.com/partdetail/{part}',html_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),footprint_viewer=f'https://jlcpcb.com/user-center/lcsvg/svg.html?code={part}&detail=1',metadata={k:obj[k] for k in ['componentCode','componentModelEn','componentBrandEn','componentSpecificationEn','componentTypeEn','dataManualUrl'] if k in obj}))
(HERE/'jlc-metadata.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
