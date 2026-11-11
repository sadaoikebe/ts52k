"""Fetch read-only public product metadata for the BOM (no order APIs)."""
import concurrent.futures, csv, hashlib, json, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "raw"
PARTS = sorted({r["LCSC Part #"] for r in csv.DictReader((ROOT / "pcb/jlcpcb/assembly/ts52k-bom.csv").open())})
def fetch(item):
    part, kind, url = item
    target = OUT / f"{part}-{kind}"
    try:
        with urllib.request.urlopen(url, timeout=40) as response:
            data = response.read()
            status = response.status
        target.write_bytes(data)
        return dict(part=part, file=target.name, url=url, status=status, sha256=hashlib.sha256(data).hexdigest())
    except Exception as e:
        return dict(part=part, url=url, error=str(e))
if __name__ == "__main__":
    items = [(p, "lcsc.json", f"https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={p}") for p in PARTS]
    items += [(p, "jlc.html", f"https://jlcpcb.com/partdetail/{p}") for p in PARTS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, items))
    (OUT.parent / "fetch-log.json").write_text(json.dumps(results, indent=2) + "\n")
    for r in results: print(r["part"], r.get("file"), r.get("status", r.get("error")))
