"""Fetch the SVG endpoint used by JLCPCB's public footprint viewer (GET only)."""
import hashlib, json, subprocess
from fetch import PARTS, OUT
results = []
for p in PARTS:
    url = f"https://easyeda.com/api/products/{p}/svgs"
    target = OUT / f"{p}-svgs.json"
    r = subprocess.run(["curl", "-L", "--max-time", "40", "-sS", "-w", "%{http_code}", url, "-o", str(target)], capture_output=True, text=True)
    results.append(dict(part=p,url=url,file=target.name,status=r.stdout,sha256=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,error=r.stderr))
    print(p, r.stdout, r.stderr, flush=True)
    if r.returncode or r.stdout != "200": break
(OUT.parent / "fetch-svg-log.json").write_text(json.dumps(results, indent=2) + "\n")
