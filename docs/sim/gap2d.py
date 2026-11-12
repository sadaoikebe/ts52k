"""Planar 2D cross-section across the drive/sense gap (perpendicular to the 0.4 mm GND line):
direct drive<->sense coupling per mm of gap, with/without L2. The axisymmetric model cannot see this term.
Each pad has two radial gap edges of 3.75 mm (r 2.25..6.0) -> multiply by 7.5 mm.
"""
import math
import numpy as np
import gmsh
from skfem import MeshTri, Basis, ElementTriP2, ElementTriP0, BilinearForm, asm, condense, solve
from skfem.helpers import dot, grad

E0 = 8.8541878e-3
W = 12.0


def run(kind):
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    hs = 1.6 if kind == "a" else 0.2104
    zb = -4.0 if kind == "a" else -hs - 0.0152
    s = {"air": occ.addRectangle(-W, 0.055, 0, 2 * W, 14 - 0.055), "mask": occ.addRectangle(-W, 0, 0, 2 * W, 0.055),
         "fr4": occ.addRectangle(-W, -hs, 0, 2 * W, hs)}
    if kind == "a":
        s["airb"] = occ.addRectangle(-W, zb, 0, 2 * W, -hs - zb)
    A = occ.addRectangle(-4.15, 0, 0, 3.75, 0.035)
    B = occ.addRectangle(0.4, 0, 0, 3.75, 0.035)
    G = [occ.addRectangle(-0.2, 0, 0, 0.4, 0.035)]
    if kind == "b":
        G.append(occ.addRectangle(-W, -hs - 0.0152, 0, 2 * W, 0.0152))
    occ.cut([(2, v) for v in s.values()], [(2, A), (2, B)] + [(2, g) for g in G])
    occ.removeAllDuplicates(); occ.synchronize()
    groups = {"A": [], "B": [], "G": []}
    for (d, t) in gmsh.model.getEntities(1):
        x0, y0, _, x1, y1, _ = gmsh.model.getBoundingBox(d, t)
        def ins(a, b, c, e):
            return x0 >= a - 1e-6 and x1 <= b + 1e-6 and y0 >= c - 1e-6 and y1 <= e + 1e-6
        if ins(-4.15, -0.4, 0, 0.035): groups["A"].append(t)
        elif ins(0.4, 4.15, 0, 0.035): groups["B"].append(t)
        elif ins(-0.2, 0.2, 0, 0.035): groups["G"].append(t)
        elif kind == "b" and ins(-W, W, -hs - 0.0152, -hs) and not (abs(x0 - x1) < 1e-9 and abs(abs(x0) - W) < 1e-9):
            groups["G"].append(t)
    for i, (k, v) in enumerate(groups.items()):
        gmsh.model.addPhysicalGroup(1, v, tag=10 + i, name=k)
    eps = {}
    for (d, t) in gmsh.model.getEntities(2):
        x, y, _ = occ.getCenterOfMass(d, t)
        er = 1.0 if (y > 0.055 or y < -hs) else (3.8 if y > 0 else 4.4)
        eps.setdefault(er, []).append(t)
    for i, (er, v) in enumerate(eps.items()):
        gmsh.model.addPhysicalGroup(2, v, tag=100 + i, name=f"e_{er}")
    fd = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(fd, "CurvesList", [t for v in groups.values() for t in v])
    ft = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(ft, "InField", fd)
    for k, v in (("SizeMin", 0.01), ("SizeMax", 0.6), ("DistMin", 0.02), ("DistMax", 4)):
        gmsh.model.mesh.field.setNumber(ft, k, v)
    gmsh.model.mesh.field.setAsBackgroundMesh(ft)
    for o in ("Mesh.MeshSizeExtendFromBoundary", "Mesh.MeshSizeFromPoints", "Mesh.MeshSizeFromCurvature"):
        gmsh.option.setNumber(o, 0)
    gmsh.model.mesh.generate(2)
    nt, xyz, _ = gmsh.model.mesh.getNodes(); xyz = xyz.reshape(-1, 3)[:, :2]
    idx = {t: i for i, t in enumerate(nt)}
    T, Ev = [], []
    for (d, pt) in gmsh.model.getPhysicalGroups(2):
        er = float(gmsh.model.getPhysicalName(d, pt).split("_")[1])
        for ent in gmsh.model.getEntitiesForPhysicalGroup(d, pt):
            _, _, en = gmsh.model.mesh.getElements(2, ent)
            for row in en[0].reshape(-1, 3):
                T.append([idx[v] for v in row]); Ev.append(er)
    bn = {}
    for (d, pt) in gmsh.model.getPhysicalGroups(1):
        name = gmsh.model.getPhysicalName(d, pt); ss = set()
        for ent in gmsh.model.getEntitiesForPhysicalGroup(d, pt):
            n_, _, _ = gmsh.model.mesh.getNodes(1, ent, includeBoundary=True); ss.update(idx[v] for v in n_)
        bn[name] = ss
    gmsh.finalize()
    T = np.array(T); used = np.unique(T); rm = -np.ones(len(xyz), int); rm[used] = np.arange(len(used))
    m = MeshTri(xyz[used].T, rm[T].T)
    basis = Basis(m, ElementTriP2())
    ef = basis.with_element(ElementTriP0()).interpolate(np.array(Ev))
    K = asm(BilinearForm(lambda u, v, w: w.eps * dot(grad(u), grad(v))), basis, eps=ef) * E0
    def dofs(ns):
        ns = np.array(sorted(rm[list(ns)]))
        f = np.where(np.isin(m.facets[0], ns) & np.isin(m.facets[1], ns))[0]
        return np.unique(np.concatenate([basis.get_dofs(facets=f).flatten(), ns]))
    D = {k: dofs(v) for k, v in bn.items()}
    alld = np.unique(np.concatenate(list(D.values())))
    x = np.zeros(K.shape[0]); x[D["A"]] = 1
    x = solve(*condense(K, x=x, D=alld)); q = K @ x
    return -q[D["B"]].sum(), q[D["A"]].sum()


if __name__ == "__main__":
    for k in ("a", "b"):
        cab, caa = run(k)
        print(f"{k}: direct C_AB {cab*1000:.2f} fF/mm -> x7.5 mm = {cab*7.5:.3f} pF ; C_AA {caa:.3f} pF/mm")
