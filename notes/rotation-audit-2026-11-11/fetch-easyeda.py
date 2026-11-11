"""Fetch official EasyEDA package data; stop this route at the first denial."""
import json
from fetch import fetch, PARTS, OUT
results = []
for p in PARTS:
    r = fetch((p, "easyeda.json", f"https://easyeda.com/api/products/{p}/components?version=6.4.19.6"))
    results.append(r)
    print(p, r.get("status", r.get("error")), flush=True)
    if "error" in r:
        break
(OUT.parent / "fetch-easyeda-log.json").write_text(json.dumps(results, indent=2) + "\n")
