"""TC52 placement and routing (all coordinates in board mm, y down). See tc52-build-log.md for the reasoning."""
import math
import pcbnew
import matrix as M
from brd import B, V, MM, mm, L1, L2, L3, L4, dog, dog2

KN = M.key_net()

# electrode via offsets from the key centre: default is the TC69 position (+-1.19 mm)
DRIVE_VIA = {}
SENSE_VIA = {}
DV0, SV0 = (-1.19, 0.0), (1.19, 0.0)


def keys_stage(bd, K):
    b = bd.b
    for k, (x, y) in K.items():
        f = bd.fp(k)
        f.SetPosition(V(x, y))
        f.SetOrientationDegrees(0)
        f.Reference().SetVisible(False)
        row, col = KN[k]
        dx, dy = DRIVE_VIA.get(k, DV0)
        bd.via(row, x + dx, y + dy, 0.8, 0.4)
        dx, dy = SENSE_VIA.get(k, SV0)
        bd.via(col, x + dx, y + dy, 0.8, 0.4)




def zones_stage(bd, K):
    b = bd.b
    main = None
    for z in list(b.Zones()):
        if z.GetIsRuleArea():
            if z.GetZoneName() == 'MCU_FANOUT':
                ls = pcbnew.LSET(); ls.AddLayer(L4); z.SetLayerSet(ls)
            continue
        ls = [l for l in z.GetLayerSet().Seq()]
        if z.GetAssignedPriority() == 1 and ls == [L1]:
            b.RemoveNative(z)          # local MCU zone on the front: L1 is electrodes only now
        elif len(ls) == 2:
            main = z
    # inner planes: same outline as the main zone, small clearance (only via/hole antipads)
    for layer, name in ((L2, 'L2_GND'), (L3, 'L3_GND')):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNet(bd.net('GND'))
        z.SetZoneName(name)
        z.Outline().Append(main.Outline())
        z.SetLocalClearance(MM(0.2))
        z.SetMinThickness(MM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
        b.Add(z)
    # no pour between electrode and guard ring (keeps the TC69 electrode geometry)
    for k, (x, y) in K.items():
        z = pcbnew.ZONE(b)
        z.SetIsRuleArea(True)
        z.SetLayer(L1)
        z.SetZoneName('ELECTRODE_' + k)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        o = z.Outline()
        o.NewOutline()
        for i in range(48):
            a = 2 * math.pi * i / 48
            o.Append(MM(x + 7.05 * math.cos(a)), MM(y + 7.05 * math.sin(a)))
        b.Add(z)


def fill(bd):
    pcbnew.ZONE_FILLER(bd.b).Fill(bd.b.Zones())


def run(bd, K, stage):
    keys_stage(bd, K)
    zones_stage(bd, K)
    fill(bd)
