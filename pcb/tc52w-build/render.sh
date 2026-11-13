#!/bin/bash
# render.sh <layers> <x0> <y0> <w> <h> <out.png> [pxwidth]   (board mm; origin fixed by the board bbox)
set -e
PCB=$(dirname $(dirname $(realpath $0)))/ts52k.kicad_pcb
T=$(mktemp -d)
kicad-cli pcb export svg --layers "$1" --mode-single --page-size-mode 2 --exclude-drawing-sheet -o $T/a.svg $PCB >/dev/null 2>&1
python3 - $T/a.svg $T/b.svg $2 $3 $4 $5 <<'PY'
import re,sys
s=open(sys.argv[1]).read()
x,y,w,h=map(float,sys.argv[3:7])
m=re.search(r'viewBox="([\d.\- ]+)"',s); vb=list(map(float,m.group(1).split()))
OX,OY=float(open('/tmp/tc52_origin').read().split()[0]),float(open('/tmp/tc52_origin').read().split()[1])
s=re.sub(r'width="[^"]+" height="[^"]+" viewBox="[^"]+"',f'width="100%" height="100%" viewBox="{x-OX} {y-OY} {w} {h}"',s,1)
s=s.replace('<svg ','<svg style="background:#fff" ',1)
open(sys.argv[2],'w').write(s)
PY
PW=${7:-1800}; PH=$(python3 -c "print(int($PW*$5/$4))")
C=$(ls ~/.cache/puppeteer/chrome/linux-*/chrome-linux64/chrome | head -1)
timeout 120 $C --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=$PW,$PH --screenshot=$6 file://$T/b.svg 2>&1 | tail -1
rm -rf $T
