# s2_south_exit.py 実行後の手直し（記録用）
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from lib import *
e=Ed()
# rpg1 の曲げを南へ寄せる
e.rm('rpg1',(31.35,67.65),(31.35,68.6),(32.035,69.285),(37.3,69.285))
e.seg('rpg1','B',e.pad('U5',3),(31.35,68.9),(31.735,69.285),(37.3,69.285))
# U5.2(GND) は rpg1 でベタのスポークが減るため直結に変更（ビアへの配線は従来どおり）
for p in e.b.FindFootprintByReference('U5').Pads():
    if p.GetNumber()=='2': p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
e.save()
