"""Axisymmetric (r,z) electrostatic FEM of one TC69/TC52 EC key cell.

Conductors (all as thin/solid bodies removed from the mesh, Dirichlet on their boundary):
  E : the electrode annulus (drive half + sense half tied together; see README in tc52-sim.md
      for how the half-electrode quantities are derived exactly from E by symmetry)
  S : conical spring, modelled as N coaxial toroidal rings (one per turn), all tied (one floating body)
  G : everything grounded (guard ring, neighbour rings / top pour, back GND, L2/L3 planes)

Output: Maxwell capacitance matrix [[C_EE, C_ES],[C_SE, C_SS]] in pF (C_ES < 0).

Units: mm. eps0 = 8.8541878e-3 pF/mm.
"""
import sys, json, math
import numpy as np
import gmsh
from skfem import MeshTri, Basis, ElementTriP2, BilinearForm, asm, condense, solve
from skfem.helpers import dot, grad

EPS0 = 8.8541878e-3  # pF/mm

# ---------------------------------------------------------------- geometry
ELEC_RI, ELEC_RO = 2.25, 6.0         # ecs_pad half-annuli (TC69 original, checked)
RING_RI, RING_RO = 7.0, 8.5          # guard ring (pad 3, width 1.5 around r=7.75)
CELL_R = 19.05 / math.sqrt(math.pi)  # equal-area radius of a 19.05 mm key cell (10.75)
TOP_POUR_R = 9.525                   # beyond the cell edge: neighbour guard ring / L1 pour (GND)
T_CU1 = 0.035                        # outer copper 1 oz
T_CU_IN = 0.0152                     # inner copper 0.5 oz (JLC04161H-7628)
T_MASK = 0.020                       # solder mask over copper (assumption)
ER_MASK = 3.8
ER_FR4 = 4.4
Z_TOP = 14.0                         # top of model (Neumann; ~plate height, see md)


def build(cfg, spring, lc=0.5, refine=1.0, msh_out=None):
    """cfg: dict(kind='tc69'|'tc52', l2_hole_r=None|float, l3_hole_r=None|float, h12=0.2104)
    spring: dict(rb, rt, n, d, htop) or None (no spring)."""
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("cell")
    occ = gmsh.model.occ
    R = CELL_R
    kind = cfg["kind"]
    if kind == "tc69":
        zbot = -1.6 - 2.4                   # 2.4 mm air gap to the case floor (report §2.6)
    else:
        h12 = cfg.get("h12", 0.2104)
        zL2 = -h12
        zL3 = zL2 - T_CU_IN - 1.065
        zbot = -1.6 - 2.4
    # dielectric slabs (as separate surfaces so we can tag eps)
    surfs = {}
    surfs["air_top"] = occ.addRectangle(0, T_CU1 + T_MASK, 0, R, Z_TOP - (T_CU1 + T_MASK))
    surfs["mask"] = occ.addRectangle(0, 0, 0, R, T_CU1 + T_MASK)
    surfs["fr4"] = occ.addRectangle(0, -1.6, 0, R, 1.6)
    surfs["air_bot"] = occ.addRectangle(0, zbot, 0, R, -1.6 - zbot)
    # conductors (tools to cut out)
    cond = {"E": [], "S": [], "G": []}
    cond["E"].append(occ.addRectangle(ELEC_RI, 0, 0, ELEC_RO - ELEC_RI, T_CU1))
    cond["G"].append(occ.addRectangle(RING_RI, 0, 0, RING_RO - RING_RI, T_CU1))
    cond["G"].append(occ.addRectangle(TOP_POUR_R, 0, 0, R - TOP_POUR_R, T_CU1))
    if kind == "tc69":
        # B.Cu GND hatch, keep-out 13 mm square under the pad -> equal-area circle r=7.33
        rk = cfg.get("back_keepout_r", 13.0 / math.sqrt(math.pi))
        cond["G"].append(occ.addRectangle(rk, -1.6 - T_CU1, 0, R - rk, T_CU1))
    else:
        h2 = cfg.get("l2_hole_r")
        r0 = h2 if h2 else 0.0
        cond["G"].append(occ.addRectangle(r0, zL2 - T_CU_IN, 0, R - r0, T_CU_IN))
        h3 = cfg.get("l3_hole_r")
        r0 = h3 if h3 else 0.0
        cond["G"].append(occ.addRectangle(r0, zL3 - T_CU_IN, 0, R - r0, T_CU_IN))
        if h3:  # L4 pour under the hole (worst case: L4 GND/traces at AC ground)
            cond["G"].append(occ.addRectangle(0, -1.6 - T_CU1, 0, R, T_CU1))
    wire_pts = []
    if spring:
        n, d = spring["n"], spring["d"]
        zc0 = T_CU1 + T_MASK + d / 2 + spring.get("gap", 0.005)  # bottom turn rests on the mask
        for k in range(n):
            f = k / (n - 1)
            r = spring["rb"] + f * (spring["rt"] - spring["rb"])
            z = zc0 + f * (spring["htop"] - d / 2 - zc0)
            cond["S"].append(occ.addDisk(r, z, 0, d / 2, d / 2))
            wire_pts.append((r, z))
    tools = [(2, t) for v in cond.values() for t in v]
    objs = [(2, s) for s in surfs.values()]
    out, outmap = occ.cut(objs, tools, removeObject=True, removeTool=True)
    occ.removeAllDuplicates()
    occ.synchronize()
    # tag dielectrics by centroid z
    ents = gmsh.model.getEntities(2)
    eps_tag = {}
    for (dim, tag) in ents:
        x, y, _ = gmsh.model.occ.getCenterOfMass(dim, tag)
        if y > T_CU1 + T_MASK - 1e-9:
            er = 1.0
        elif y > 0 - 1e-9:
            er = ER_MASK
        elif y > -1.6 - 1e-9:
            er = ER_FR4
        else:
            er = 1.0
        eps_tag.setdefault(er, []).append(tag)
    for i, (er, tags) in enumerate(eps_tag.items()):
        gmsh.model.addPhysicalGroup(2, tags, tag=100 + i, name=f"eps_{er}")
    # classify boundary curves to conductors by geometry
    def owner(cx, cy):
        # returns conductor name for a curve centroid, or None
        if spring:
            for (r, z) in wire_pts:
                if abs(math.hypot(cx - r, cy - z) - spring["d"] / 2) < 1e-3 or math.hypot(cx - r, cy - z) < spring["d"] / 2 + 1e-3:
                    return "S"
        return None
    curves = gmsh.model.getEntities(1)
    groups = {"E": [], "S": [], "G": []}
    for (dim, tag) in curves:
        bb = gmsh.model.getBoundingBox(dim, tag)
        x0, y0, _, x1, y1, _ = bb
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        o = owner(cx, cy)
        if o:
            groups[o].append(tag)
            continue
        # electrode: within [ELEC_RI, ELEC_RO] x [0, T_CU1]
        def inside(rr0, rr1, zz0, zz1):
            return x0 >= rr0 - 1e-6 and x1 <= rr1 + 1e-6 and y0 >= zz0 - 1e-6 and y1 <= zz1 + 1e-6
        if inside(ELEC_RI, ELEC_RO, 0, T_CU1) and not (abs(x0 - x1) < 1e-9 and abs(x0) < 1e-9):
            groups["E"].append(tag)
            continue
        # grounds: any curve lying on a ground conductor rectangle boundary
        gb = [(RING_RI, RING_RO, 0, T_CU1), (TOP_POUR_R, R, 0, T_CU1)]
        if kind == "tc69":
            rk = cfg.get("back_keepout_r", 13.0 / math.sqrt(math.pi))
            gb.append((rk, R, -1.6 - T_CU1, -1.6))
        else:
            r2 = cfg.get("l2_hole_r") or 0.0
            gb.append((r2, R, zL2 - T_CU_IN, zL2))
            r3 = cfg.get("l3_hole_r") or 0.0
            gb.append((r3, R, zL3 - T_CU_IN, zL3))
            if cfg.get("l3_hole_r"):
                gb.append((0, R, -1.6 - T_CU1, -1.6))
        for (a, b, c, e) in gb:
            if inside(a, b, c, e):
                # exclude the outer boundary r=R (Neumann) segments: those are at x==R exactly
                if abs(x0 - R) < 1e-9 and abs(x1 - R) < 1e-9:
                    break
                groups["G"].append(tag)
                break
    for i, (k, tags) in enumerate(groups.items()):
        if tags:
            gmsh.model.addPhysicalGroup(1, tags, tag=10 + i, name=k)
    # mesh size fields: fine near copper edges & wires
    f_d = gmsh.model.mesh.field.add("Distance")
    gmsh.model.mesh.field.setNumbers(f_d, "CurvesList", [t for v in groups.values() for t in v])
    gmsh.model.mesh.field.setNumber(f_d, "Sampling", 60)
    f_t = gmsh.model.mesh.field.add("Threshold")
    gmsh.model.mesh.field.setNumber(f_t, "InField", f_d)
    gmsh.model.mesh.field.setNumber(f_t, "SizeMin", 0.012 * refine)
    gmsh.model.mesh.field.setNumber(f_t, "SizeMax", lc * refine)
    gmsh.model.mesh.field.setNumber(f_t, "DistMin", 0.02)
    gmsh.model.mesh.field.setNumber(f_t, "DistMax", 4.0)
    gmsh.model.mesh.field.setAsBackgroundMesh(f_t)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.model.mesh.generate(2)
    nodes_tag, coords, _ = gmsh.model.mesh.getNodes()
    xy = coords.reshape(-1, 3)[:, :2]
    idx = {t: i for i, t in enumerate(nodes_tag)}
    tris, eps = [], []
    for (dim, ptag) in gmsh.model.getPhysicalGroups(2):
        er = float(gmsh.model.getPhysicalName(dim, ptag).split("_")[1])
        for ent in gmsh.model.getEntitiesForPhysicalGroup(dim, ptag):
            et, _, en = gmsh.model.mesh.getElements(dim, ent)
            for t_, nn in zip(et, en):
                assert t_ == 2
                nn = nn.reshape(-1, 3)
                for row in nn:
                    tris.append([idx[v] for v in row])
                    eps.append(er)
    bnodes = {}
    for (dim, ptag) in gmsh.model.getPhysicalGroups(1):
        name = gmsh.model.getPhysicalName(dim, ptag)
        s = set()
        for ent in gmsh.model.getEntitiesForPhysicalGroup(dim, ptag):
            nt, _, _ = gmsh.model.mesh.getNodes(dim, ent, includeBoundary=True)
            s.update(idx[v] for v in nt)
        bnodes[name] = s
    if msh_out:
        gmsh.write(msh_out)
    gmsh.finalize()
    used = np.unique(np.array(tris).ravel())
    remap = -np.ones(len(xy), dtype=int)
    remap[used] = np.arange(len(used))
    p = xy[used].T
    t = remap[np.array(tris)].T
    bnodes = {k: np.array(sorted(remap[list(v)][remap[list(v)] >= 0])) for k, v in bnodes.items()}
    return p, t, np.array(eps), bnodes


def capmatrix(cfg, spring, refine=1.0, return_mesh=False):
    p, t, eps, bn = build(cfg, spring, refine=refine)
    m = MeshTri(p, t)
    basis = Basis(m, ElementTriP2())
    # per-element permittivity as a DG0 field
    from skfem import ElementTriP0
    b0 = basis.with_element(ElementTriP0())
    epsf = b0.interpolate(eps)

    @BilinearForm
    def a(u, v, w):
        r = w.x[0]
        return w.eps * dot(grad(u), grad(v)) * r

    K = asm(a, basis, eps=epsf) * (2 * math.pi * EPS0)  # pF
    # map conductor boundary nodes -> P2 dofs on their facets
    names = [n for n in ("E", "S") if n in bn and len(bn[n])]
    def dofs_of(node_set):
        node_set = set(node_set.tolist())
        f = np.where(np.isin(m.facets[0], list(node_set)) & np.isin(m.facets[1], list(node_set)))[0]
        return np.unique(np.concatenate([basis.get_dofs(facets=f).flatten(), np.array(sorted(node_set))]))
    D = {n: dofs_of(bn[n]) for n in list(names) + ["G"]}
    alld = np.unique(np.concatenate(list(D.values())))
    C = np.zeros((len(names), len(names)))
    for j, nj in enumerate(names):
        x = np.zeros(K.shape[0])
        x[D[nj]] = 1.0
        x = solve(*condense(K, x=x, D=alld))
        q = K @ x
        for i, ni in enumerate(names):
            C[i, j] = q[D[ni]].sum()
    C = 0.5 * (C + C.T)
    info = dict(nel=m.t.shape[1], ndof=K.shape[0])
    if return_mesh:
        return names, C, info, (m, eps, bn)
    return names, C, info


if __name__ == "__main__":
    cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"kind": "tc52"}
    sp = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    names, C, info = capmatrix(cfg, sp)
    print(names, C.tolist(), info)
