"""pcbnew helpers for the TC52 board builder."""
import math
import pcbnew

MM = pcbnew.FromMM
mm = pcbnew.ToMM
L1, L2, L3, L4 = pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


class B:
    def __init__(self, board):
        self.b = board
        self.log = []

    def net(self, name):
        n = self.b.FindNet(name)
        if n is None:
            n = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(n)
        return n

    def track(self, net, pts, layer=L4, w=0.2):
        """polyline of straight segments"""
        n = self.net(net)
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(V(x1, y1))
            t.SetEnd(V(x2, y2))
            t.SetWidth(MM(w))
            t.SetLayer(layer)
            t.SetNet(n)
            self.b.Add(t)

    def via(self, net, x, y, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(V(x, y))
        v.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, MM(d))
        v.SetDrill(MM(drill))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(L1, L4)
        v.SetNet(self.net(net))
        self.b.Add(v)
        return v

    def fp(self, ref):
        return self.b.FindFootprintByReference(ref)

    def pad(self, ref, num):
        """(x, y) of a pad centre in mm"""
        f = self.fp(ref)
        for p in f.Pads():
            if p.GetNumber() == str(num):
                q = p.GetPosition()
                return (mm(q.x), mm(q.y))
        raise KeyError((ref, num))

    def place(self, ref, x, y, rot=0.0, back=True):
        f = self.fp(ref)
        f.SetPosition(V(x, y))
        if back and f.GetLayer() != L4:
            f.Flip(V(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.SetOrientationDegrees(rot)
        return f


def dog(p, q, first='v'):
    """connect p->q with one 45-degree bend: axis-aligned leg first ('v' vertical or 'h' horizontal), then diagonal"""
    (x1, y1), (x2, y2) = p, q
    dx, dy = x2 - x1, y2 - y1
    if first == 'v':
        d = abs(dx)
        if abs(dy) < d:
            raise ValueError(f'dog v: {p}->{q}')
        ym = y2 - math.copysign(d, dy)
        return [p, (x1, ym), q]
    d = abs(dy)
    if abs(dx) < d:
        raise ValueError(f'dog h: {p}->{q}')
    xm = x2 - math.copysign(d, dx)
    return [p, (xm, y1), q]


def dog2(p, q, first='d'):
    """diagonal first, then axis-aligned leg into q. first='dv': diagonal then vertical; 'dh': diagonal then horizontal"""
    r = dog(q, p, 'v' if first == 'dv' else 'h')
    return r[::-1]
