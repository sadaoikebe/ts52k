#!/bin/bash
# crop.sh in.svg out.png x y w h [pxwidth]  (svg user units)
in=$(realpath "$1"); out=$(realpath -m "$2"); x=$3; y=$4; w=$5; h=$6; pw=${7:-1800}
ph=$(python3 -c "print(int($pw*$h/$w))")
tmp=$(mktemp --suffix=.svg)
python3 - "$in" "$tmp" $x $y $w $h <<'PY'
import re,sys
s=open(sys.argv[1]).read()
x,y,w,h=sys.argv[3:7]
s=re.sub(r'width="[^"]+" height="[^"]+" viewBox="[^"]+"',f'width="100%" height="100%" viewBox="{x} {y} {w} {h}"',s,1)
open(sys.argv[2],'w').write(s)
PY
C=$(ls ~/.cache/puppeteer/chrome/linux-*/chrome-linux64/chrome | head -1)
timeout 90 $C --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=$pw,$ph --screenshot=$out file://$tmp 2>&1 | tail -1
rm -f $tmp
