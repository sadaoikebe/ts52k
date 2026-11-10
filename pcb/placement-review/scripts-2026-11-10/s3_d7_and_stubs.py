import sys; sys.path.insert(0,'/tmp/fb')
from lib import *
e=Ed()
# D7 anode: MX7.2 -> D7.2
a=e.pad('MX7',2); q=e.pt('Net-(D7-A)',(44.25,54.6))
e.seg('Net-(D7-A)','B',a,(round(a[0]+(q[1]-a[1]),6),q[1]),q)
# leftover stubs
e.rm('col5',(31.586,52.719),(31.65,52.655)); e.rm('col6',(31.935,52.865),(32.0,52.8))
e.rm('col5',(34.087,52.1),(34.421,52.1))
e.rm('rpg1',(297.777,49.292),(297.777,47.281)); e.rm('rpg2',(292.772,49.292),(292.772,47.285))
e.save()
