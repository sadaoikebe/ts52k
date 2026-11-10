"""アンテナ先端側・側方のGNDベタだけを抜くルールエリアを追加する（配線・ビア・パッドは許可）。
範囲 x=33.45..40.0, y=54.0..71.0。範囲内で孤立するGNDビアは除去する。"""
import sys,os
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..','scripts-2026-11-10'))
from lib import *
X0,Y0,X1,Y1=33.45,54.0,40.0,71.0
e=Ed(); b=e.b
z=pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName('ANT_NO_FILL')
ls=pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)
z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
o=z.Outline(); o.NewOutline()
for x,y in [(X0,Y0),(X1,Y0),(X1,Y1),(X0,Y1)]: o.Append(FM(x),FM(y))
b.Add(z)
for t in list(e.T):
    if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND':
        p=t.GetPosition()
        if X0-0.3<mm(p.x)<X1+0.3 and Y0-0.3<mm(p.y)<Y1+0.3: print('remove GND via',mm(p.x),mm(p.y)); b.RemoveNative(t)
e.save(); print(stats())
