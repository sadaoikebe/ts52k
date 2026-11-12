#!/bin/bash
# drc.sh : run DRC, print a summary (counts by type, then details filtered by an optional grep pattern)
P=$(dirname $(dirname $(realpath $0)))
kicad-cli pcb drc --schematic-parity --all-track-errors --refill-zones --severity-all --format json -o /tmp/tc52-drc.json $P/ts52k.kicad_pcb >/dev/null 2>&1
git -C $P checkout ts52k.kicad_pro 2>/dev/null
python3 - "$@" <<'PY'
import json,sys,collections
d=json.load(open('/tmp/tc52-drc.json'))
pat=sys.argv[1] if len(sys.argv)>1 else None
lim=int(sys.argv[2]) if len(sys.argv)>2 else 40
for key in ('violations','unconnected_items','schematic_parity'):
    v=d.get(key,[])
    c=collections.Counter(x['type'] for x in v)
    print(key,len(v),dict(c))
    n=0
    for x in v:
        line=x['type']+' | '+x['description'][:60]+' | '+' ; '.join(f"{i['description'][:70]} @({i['pos']['x']:.2f},{i['pos']['y']:.2f})" for i in x.get('items',[]))
        if pat and __import__('re').search(pat,line) and n<lim:
            print('  ',line); n+=1
PY
