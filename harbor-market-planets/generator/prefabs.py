"""Low-poly decoration kits. Every prefab writes into a MeshBuilder in local
space (z up, origin on the ground) transformed by matrix M."""
import math
from mathutils import Vector, Matrix
from core import (TAU, MB, lathe, tube, box, leaf, rock, ico, nz, lerp, clamp)


def Rz(a):
    return Matrix.Rotation(a, 4, 'Z')


def Ry(a):
    return Matrix.Rotation(a, 4, 'Y')


def Rx(a):
    return Matrix.Rotation(a, 4, 'X')


def T(x, y=0.0, z=0.0):
    return Matrix.Translation(Vector((x, y, z)) if not isinstance(x, Vector) else x)


def S(x, y=None, z=None):
    if y is None:
        return Matrix.Scale(x, 4)
    return Matrix.Diagonal((x, y, z, 1.0))


def align(vec):
    return Vector((0, 0, 1)).rotation_difference(vec.normalized()).to_matrix().to_4x4()


# ------------------------------------------------------------------ rocks
def pf_rock(mb, M, rng, mat, sub=1, jit=0.22, squash=0.7, mat2=None):
    v, f = rock(rng, sub, jit)
    v = [Vector((p.x, p.y, p.z * squash)) for p in v]
    if mat2 is not None:
        mats = []
        for fc in f:
            c = sum((v[i] for i in fc), Vector()) / 3
            mats.append(mat2 if c.z > 0.35 * squash else mat)
        mb.add(v, f, mats, M)
    else:
        mb.add(v, f, mat, M)


def pf_spike(mb, M, rng, mat, h=0.12, r=0.03, n=5, lean=0.25):
    lx, ly = rng.uniform(-lean, lean), rng.uniform(-lean, lean)
    prof = [(r * 1.1, -0.03), (r, 0.0), (r * 0.62, h * 0.55), (0, h)]
    v, f = lathe(prof, n, rng.uniform(0, TAU), cap0=True, cap1=False, jit=0.18, rng=rng)
    v = [Vector((p.x + lx * p.z, p.y + ly * p.z, p.z)) for p in v]
    mb.add(v, f, mat, M)


# ------------------------------------------------------------------ plants
def pf_palm(mb, M, rng, trunk, leaves, nut=None, h=0.2, lean=0.3, fronds=7):
    segs = 6
    ld = rng.uniform(0, TAU)
    pts, rad = [], []
    for i in range(segs + 1):
        t = i / segs
        x = lean * h * t * t
        pts.append(Vector((x * math.cos(ld), x * math.sin(ld), h * t)))
        rad.append(h * 0.05 * (1 - 0.45 * t))
    v, f = tube(pts, rad, 5, cap0=True, cap1=True)
    mb.add(v, f, trunk, M)
    top = pts[-1]
    if nut is not None:
        for k in range(3):
            a = TAU * k / 3 + 0.4
            vv, ff = ico(1)
            mb.add(vv, ff, nut, M @ T(top + Vector((math.cos(a) * h * 0.04, math.sin(a) * h * 0.04, -h * 0.03))) @ S(h * 0.035))
    for k in range(fronds):
        a = TAU * k / fronds + rng.uniform(-0.2, 0.2)
        L = h * rng.uniform(0.6, 0.78)
        lv, lf = leaf(L, L * 0.17, segs=5, droop=0.6, fold=0.35)
        Rl = T(top) @ Rz(a) @ Ry(-rng.uniform(0.25, 0.55))
        mb.add(lv, lf, leaves[k % len(leaves)], M @ Rl)


def pf_grass(mb, M, rng, mat, h=0.035, blades=5):
    for k in range(blades):
        a = TAU * k / blades + rng.uniform(-0.3, 0.3)
        hh = h * rng.uniform(0.7, 1.2)
        v = [Vector((-0.004, 0, 0)), Vector((0.004, 0, 0)), Vector((0.0, 0, hh))]
        mb.add(v, [[0, 1, 2]], mat, M @ Rz(a) @ Rx(rng.uniform(-0.45, 0.45)) @ T(rng.uniform(-0.006, 0.006), rng.uniform(-0.006, 0.006)))


def pf_tree(mb, M, rng, trunk, crowns, h=0.16):
    prof = [(h * 0.07, -0.02), (h * 0.06, h * 0.3), (h * 0.045, h * 0.62), (0, h * 0.7)]
    v, f = lathe(prof, 5, rng.uniform(0, TAU), cap0=True, cap1=False)
    mb.add(v, f, trunk, M)
    blobs = [(Vector((0, 0, h * 0.78)), h * 0.36)]
    for k in range(rng.randint(2, 3)):
        a = rng.uniform(0, TAU)
        blobs.append((Vector((math.cos(a) * h * 0.2, math.sin(a) * h * 0.2, h * rng.uniform(0.6, 0.72))), h * rng.uniform(0.22, 0.28)))
    blobs.append((Vector((rng.uniform(-0.03, 0.03) * h, 0, h * 1.02)), h * 0.24))
    for k, (c, r) in enumerate(blobs):
        vv, ff = rock(rng, 1, 0.12)
        mb.add(vv, ff, crowns[k % len(crowns)], M @ T(c) @ S(r, r, r * 0.85))


def pf_broadleaf(mb, M, rng, mats, s=0.08, n=6):
    for k in range(n):
        a = TAU * k / n + rng.uniform(-0.25, 0.25)
        L = s * rng.uniform(0.75, 1.1)
        lv, lf = leaf(L, L * 0.42, segs=4, droop=0.55, fold=0.18, base=0.15)
        mb.add(lv, lf, mats[k % len(mats)], M @ Rz(a) @ Ry(-rng.uniform(0.7, 1.05)))


# ------------------------------------------------------------------ marine
def pf_coral_branch(mb, M, rng, mat, h=0.1, depth=2, n=5):
    def branch(p, dv, L, r, lvl):
        end = p + dv * L
        mid = p + dv * L * 0.5 + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)) * L * 0.08
        v, f = tube([p, mid, end], [r, r * 0.82, r * 0.6], n, cap0=False, cap1=True)
        mb.add(v, f, mat, M)
        if lvl < depth:
            for k in range(rng.randint(2, 3)):
                a = rng.uniform(0, TAU)
                tilt = rng.uniform(0.35, 0.75)
                side = Vector((math.cos(a), math.sin(a), 0))
                nd = (dv * math.cos(tilt) + side * math.sin(tilt)).normalized()
                branch(p + dv * L * rng.uniform(0.55, 0.95), nd, L * 0.68, r * 0.62, lvl + 1)
    branch(Vector((0, 0, -0.01)), Vector((0, 0, 1)), h * 0.5, h * 0.075, 0)


def pf_coral_round(mb, M, rng, mat, r=0.04, squash=0.62, mat2=None):
    v, f = ico(2)
    seed = rng.random() * 50
    v = [Vector((p.x, p.y, p.z * squash)) * (1 + 0.1 * math.sin(nz(p, 2.5, seed) * 9.0)) * r for p in v]
    if mat2 is not None:
        mats = [mat2 if (k * 7) % 5 == 0 else mat for k in range(len(f))]
        mb.add(v, f, mats, M)
    else:
        mb.add(v, f, mat, M)


def pf_fan(mb, M, rng, mat, h=0.12, n=11, ribs=None):
    v = [Vector((0, 0, -0.01))]
    inner = []
    outer = []
    for i in range(n):
        a = math.radians(lerp(18, 162, i / (n - 1)))
        r1 = h * 0.5 * rng.uniform(0.9, 1.05)
        r2 = h * rng.uniform(0.82, 1.0)
        wob = 0.012 * (1 if i % 2 else -1)
        inner.append(len(v))
        v.append(Vector((math.cos(a) * r1, wob, math.sin(a) * r1)))
        outer.append(len(v))
        v.append(Vector((math.cos(a) * r2, -wob, math.sin(a) * r2)))
    f = []
    for i in range(n - 1):
        f.append([0, inner[i + 1], inner[i]])
        f.append([inner[i], inner[i + 1], outer[i + 1], outer[i]])
    mb.add(v, f, mat, M)
    if ribs is not None:
        for i in range(0, n, 2):
            a = math.radians(lerp(18, 162, i / (n - 1)))
            pts = [Vector((0, 0, -0.01)), Vector((math.cos(a), 0, math.sin(a))) * h * 0.5, Vector((math.cos(a), 0, math.sin(a))) * h * 0.92]
            tv, tf = tube(pts, [h * 0.03, h * 0.02, h * 0.012], 4)
            mb.add(tv, tf, ribs, M)


def pf_shell(mb, M, rng, mat_a, mat_b, s=0.1, ribs=9):
    m = 2 * ribs + 1
    v = [Vector((-0.02 * s, 0, 0.03 * s))]
    mid, rim = [], []
    for i in range(m):
        a = math.radians(lerp(-72, 72, i / (m - 1)))
        ridge = (i % 2 == 0)
        r = s * (1.0 if ridge else 0.94)
        zr = 0.05 * s + (0.05 * s if ridge else 0.0)
        mid.append(len(v))
        v.append(Vector((0.55 * r * math.cos(a), 0.55 * r * math.sin(a), 0.34 * s + (0.04 * s if ridge else 0.0))))
        rim.append(len(v))
        v.append(Vector((r * math.cos(a), r * math.sin(a), zr)))
    f, mats = [], []
    for i in range(m - 1):
        mt = mat_a if (i // 2) % 2 == 0 else mat_b
        f.append([0, mid[i], mid[i + 1]])
        mats.append(mt)
        f.append([mid[i], rim[i], rim[i + 1], mid[i + 1]])
        mats.append(mt)
    f.append([0] + list(reversed(rim)))
    mats.append(mat_a)
    # side closing fans from hinge to first/last rim
    f.append([0, rim[0], mid[0]])
    mats.append(mat_a)
    f.append([0, mid[-1], rim[-1]])
    mats.append(mat_a)
    # hinge ears
    ear = [Vector((-0.05 * s, -0.12 * s, 0.01 * s)), Vector((-0.05 * s, 0.12 * s, 0.01 * s)), Vector((0.08 * s, 0, 0.12 * s))]
    mb.add(v, f, mats, M)
    mb.add(ear, [[0, 1, 2]], mat_b, M)


def pf_arch(mb, M, rng, mats, span=0.25, height=0.18, r0=0.05, r1=0.03, n=6, segs=12, jit=0.14, bands=False, sink=0.05):
    pts, rad = [], []
    for i in range(segs + 1):
        t = i / segs
        x = -math.cos(math.pi * t) * span / 2
        z = math.sin(math.pi * t) * height - sink * (1 - math.sin(math.pi * t))
        pts.append(Vector((x, rng.uniform(-0.006, 0.006), z)))
        rad.append(lerp(r0, r1, math.sin(math.pi * t)))
    v, f = tube(pts, rad, n, cap0=True, cap1=True, jit=jit, rng=rng)
    if bands and isinstance(mats, (list, tuple)):
        fm = [mats[(k // n) % len(mats)] for k in range(len(f))]
        mb.add(v, f, fm, M)
    else:
        mb.add(v, f, mats if not isinstance(mats, (list, tuple)) else mats[0], M)
    return pts


# ------------------------------------------------------------------ harbour
def pf_lighthouse(mb, M, P, h=0.24, n=8):
    base = [(0.075, -0.04), (0.08, 0.0), (0.07, 0.022), (0.0, 0.026)]
    v, f = lathe(base, n, 0.2)
    mb.add(v, f, P['rock'], M)
    bands = 5
    z0, z1 = 0.022, h * 0.72
    r0, r1 = 0.036, 0.024
    for b in range(bands):
        za, zb = lerp(z0, z1, b / bands), lerp(z0, z1, (b + 1) / bands)
        ra, rb = lerp(r0, r1, b / bands), lerp(r0, r1, (b + 1) / bands)
        v, f = lathe([(ra, za), (rb, zb)], n, 0.0, cap0=False, cap1=False)
        mb.add(v, f, P['lh_white'] if b % 2 == 0 else P['lh_red'], M)
    v, f = lathe([(0.036, z1), (0.038, z1 + 0.006), (0.0, z1 + 0.006)], n, 0.0, cap0=True, cap1=True)
    mb.add(v, f, P['lh_white'], M)
    v, f = lathe([(0.018, z1 + 0.006), (0.018, z1 + 0.034), (0.0, z1 + 0.034)], n, 0.0, cap0=False, cap1=True)
    mb.add(v, f, P['lamp'], M)
    v, f = lathe([(0.026, z1 + 0.034), (0.0, z1 + 0.066)], n, 0.0, cap0=True, cap1=False)
    mb.add(v, f, P['lh_red'], M)


def pf_pier(mb, M, rng, wood, wood_dark, length=0.2, width=0.044, plank=0.017, post_depth=0.13, end_deck=True):
    k = 0
    x = 0.0
    while x < length:
        v, f = box(plank * 0.82, width * rng.uniform(0.95, 1.05), 0.0055)
        mb.add(v, f, wood, M @ T(x, rng.uniform(-0.002, 0.002), rng.uniform(-0.0008, 0.0008)) @ Rz(rng.uniform(-0.05, 0.05)))
        if k % 3 == 0:
            for sgn in (-1, 1):
                pv, pf = lathe([(0.0042, -post_depth), (0.0042, 0.01), (0, 0.012)], 5, 0.3)
                mb.add(pv, pf, wood_dark, M @ T(x, sgn * width * 0.48, 0))
        k += 1
        x += plank
    # side stringers
    for sgn in (-1, 1):
        v, f = box(length, 0.005, 0.006)
        mb.add(v, f, wood_dark, M @ T(length / 2 - plank / 2, sgn * width * 0.46, -0.005))
    if end_deck:
        v, f = box(width * 1.4, width * 1.7, 0.0065)
        mb.add(v, f, wood, M @ T(length + width * 0.55, 0, 0.0005))
        for sx in (-1, 1):
            for sy in (-1, 1):
                pv, pf = lathe([(0.0046, -post_depth), (0.0046, 0.016), (0, 0.019)], 5, 0.3)
                mb.add(pv, pf, wood_dark, M @ T(length + width * 0.55 + sx * width * 0.6, sy * width * 0.75, 0))
    return length + width * 1.25


def pf_boat(mb, M, hull, trim, s=0.06):
    pts = list(reversed([(-0.5, 0.0), (-0.42, 0.17), (-0.1, 0.24), (0.25, 0.2), (0.5, 0.0), (0.25, -0.2), (-0.1, -0.24), (-0.42, -0.17)]))
    top = [Vector((x * s, y * s, 0.12 * s)) for x, y in pts]
    bot = [Vector((x * s * 0.78, y * s * 0.55, -0.06 * s)) for x, y in pts]
    v = top + bot
    n = len(pts)
    f = [[n + i for i in range(n - 1, -1, -1)], [i for i in range(n)]]
    for i in range(n):
        j = (i + 1) % n
        f.append([n + i, n + j, j, i])
    mb.add(v, f, [hull, trim] + [hull] * n, M)
    # seat
    bv, bf = box(0.08 * s, 0.4 * s, 0.03 * s)
    mb.add(bv, bf, trim, M @ T(0, 0, 0.13 * s))


# ------------------------------------------------------------------ minerals & ice
def pf_crystal(mb, M, rng, body, tip, h=0.15, r=None, n=6):
    r = r or h * 0.17
    tl = r * rng.uniform(1.3, 2.1)
    prof = [(r * 0.85, -0.04), (r, h * 0.12), (r * 0.94, h), (0, h + tl)]
    v, f = lathe(prof, n, rng.uniform(0, TAU), cap0=True, cap1=False, jit=0.04, rng=rng)
    mats = [body] * n + [body if k % 2 else tip for k in range(n)] + [tip] * n + [body]
    mb.add(v, f, mats, M)


def pf_crystal_cluster(mb, M, rng, body, tip, h=0.2, count=5, spread=0.5):
    pf_crystal(mb, M @ Rx(rng.uniform(-0.08, 0.08)), rng, body, tip, h=h)
    for k in range(count - 1):
        a = TAU * k / (count - 1) + rng.uniform(-0.3, 0.3)
        tilt = rng.uniform(0.3, 0.75) * spread / 0.5
        hh = h * rng.uniform(0.35, 0.72)
        off = Vector((math.cos(a), math.sin(a), 0)) * h * 0.12
        pf_crystal(mb, M @ T(off) @ Rz(a) @ Ry(tilt), rng, body, tip, h=hh)


def pf_shard(mb, M, rng, mats, h=0.25, r=0.05, n=5):
    prof = [(r * 1.05, -0.06), (r, h * 0.2), (r * 0.82, h * 0.7), (r * 0.35, h), (0, h * 1.06)]
    v, f = lathe(prof, n, rng.uniform(0, TAU), cap0=True, cap1=False, jit=0.16, rng=rng)
    lx = rng.uniform(-0.15, 0.15)
    v = [Vector((p.x + lx * p.z, p.y, p.z)) for p in v]
    fm = [mats[(k + (k // n)) % len(mats)] for k in range(len(f))]
    mb.add(v, f, fm, M)


def pf_iceberg(mb, M, rng, ice, snow, r=0.06, h=0.05, n=7):
    prof = [(r * 0.7, -0.05), (r, 0.0), (r * 0.85, h * 0.55), (r * 0.45, h), (0, h * 1.08)]
    v, f = lathe(prof, n, rng.uniform(0, TAU), cap0=True, cap1=False, jit=0.2, rng=rng)
    fm = [ice] * (2 * n) + [snow] * (2 * n) + [ice]
    mb.add(v, f, fm, M)


def pf_columns(mb, M, rng, mats, h=0.1, cell=0.022, rings=2, tops=None):
    pts = [(0, 0)]
    for q in range(-rings, rings + 1):
        for r in range(-rings, rings + 1):
            if (q, r) == (0, 0) or abs(q + r) > rings:
                continue
            pts.append((q, r))
    for (q, r) in pts:
        x = cell * 1.5 * q
        y = cell * math.sqrt(3) * (r + q / 2)
        dist = math.hypot(x, y) / (cell * 1.8 * rings + 1e-6)
        hh = h * clamp(1.05 - dist * 0.7 + rng.uniform(-0.25, 0.15), 0.12, 1.2)
        rad = cell * 0.98
        v, f = lathe([(rad, -0.05), (rad, hh)], 6, math.pi / 6, cap0=True, cap1=True)
        tilt = rng.uniform(-0.12, 0.12)
        v = [Vector((p.x, p.y, p.z + (p.x * tilt if p.z > 0 else 0))) for p in v]
        fm = [mats[(k + q) % 2] for k in range(6)] + [mats[0], tops or mats[1]]
        mb.add(v, f, fm, M @ T(x, y, 0))


# ------------------------------------------------------------------ fungi
def pf_mushroom(mb, M, rng, cap, gill, stem, glow=None, spot=None, h=0.2, R=None, bend=0.18, style='dome', gills=16):
    R = R or h * 0.5
    segs = 6
    ld = rng.uniform(0, TAU)
    pts, rad = [], []
    for i in range(segs + 1):
        t = i / segs
        x = bend * h * t * t
        pts.append(Vector((x * math.cos(ld), x * math.sin(ld), h * t)))
        rad.append(h * 0.085 * (1.2 - 0.4 * t) if t > 0 else h * 0.13)
    v, f = tube(pts, rad, 6, cap0=True, cap1=False)
    mb.add(v, f, stem, M)
    tdir = (pts[-1] - pts[-2]).normalized()
    C = M @ T(pts[-1]) @ align(tdir)
    u0 = -0.06 * R
    if style == 'dome':
        prof = [(R * 0.22, u0), (R, 0.0), (R * 0.93, R * 0.16), (R * 0.68, R * 0.36), (R * 0.32, R * 0.48), (0, R * 0.52)]
    elif style == 'flat':
        prof = [(R * 0.22, u0 * 0.6), (R, -0.02 * R), (R * 0.97, R * 0.08), (R * 0.6, R * 0.17), (0, R * 0.22)]
    else:  # bell
        prof = [(R * 0.22, u0), (R, -R * 0.14), (R * 0.82, R * 0.12), (R * 0.42, R * 0.5), (0, R * 0.78)]
    v, f = lathe(prof, 10, rng.uniform(0, TAU), cap0=True, cap1=False)
    mb.add(v, f, [gill] * 10 + [cap] * (len(f) - 10), C)
    (ra0, za0), (ra1, za1) = prof[0], prof[1]

    def zu(r):
        return lerp(za0, za1, clamp((r - ra0) / (ra1 - ra0)))
    for k in range(gills):
        a = TAU * k / gills
        ca, sa = math.cos(a), math.sin(a)
        r1, r2 = R * 0.25, R * 0.93
        g = R * 0.12
        gv = [Vector((r1 * ca, r1 * sa, zu(r1) - 0.002)), Vector((r2 * ca, r2 * sa, zu(r2) - 0.002)),
              Vector((r2 * 0.9 * ca, r2 * 0.9 * sa, zu(r2) - g * 0.45)), Vector((r1 * ca, r1 * sa, zu(r1) - g))]
        mb.add(gv, [[0, 1, 2, 3]], gill, C)
    if glow is not None or spot is not None:
        m = rng.randint(4, 7)
        for k in range(m):
            a = rng.uniform(0, TAU)
            t = rng.uniform(0.25, 0.8)
            # point on cap profile (linear interp of radius)
            idx = 2 + int(t * (len(prof) - 3))
            (ra, za), (rb, zb) = prof[idx - 1], prof[idx]
            u = rng.uniform(0, 1)
            rr, zz = lerp(ra, rb, u), lerp(za, zb, u)
            vv, ff = ico(1)
            sz = R * rng.uniform(0.05, 0.09)
            mat = glow if (glow is not None and (spot is None or k % 2 == 0)) else spot
            mb.add(vv, ff, mat, C @ T(rr * math.cos(a), rr * math.sin(a), zz) @ S(sz, sz, sz * 0.6))
    return pts[-1]


# ------------------------------------------------------------------ space harbour
def pf_ring(mb, bands, n=144, tilt=None, rng=None):
    """bands: list of (r_in, r_out, thickness, mat)."""
    for (ri, ro, th, mat) in bands:
        v, f = [], []
        for i in range(n):
            a = TAU * i / n
            ca, sa = math.cos(a), math.sin(a)
            j = rng.uniform(-0.25, 0.25) * th if rng else 0.0
            v += [Vector((ri * ca, ri * sa, th / 2 + j)), Vector((ro * ca, ro * sa, th / 2 + j)),
                  Vector((ro * ca, ro * sa, -th / 2 + j)), Vector((ri * ca, ri * sa, -th / 2 + j))]
        for i in range(n):
            a0, b0 = 4 * i, 4 * ((i + 1) % n)
            f += [[a0, a0 + 1, b0 + 1, b0], [a0 + 2, a0 + 3, b0 + 3, b0 + 2], [a0 + 1, a0 + 2, b0 + 2, b0 + 1], [a0 + 3, a0, b0, b0 + 3]]
        mb.add(v, f, mat, tilt)


def pf_dock(mb, M, rng, deck, metal, metal_dark, light, length=0.22, width=0.05):
    v, f = box(length, width, 0.012)
    mb.add(v, f, deck, M @ T(length / 2, 0, 0.0))
    v, f = box(length, 0.006, 0.02)
    for sgn in (-1, 1):
        mb.add(v, f, metal, M @ T(length / 2, sgn * width * 0.5, -0.004))
    k = 0
    x = 0.02
    while x < length:
        for sgn in (-1, 1):
            pv, pf = lathe([(0.0052, -0.14), (0.0052, 0.0)], 6, 0)
            mb.add(pv, pf, metal_dark, M @ T(x, sgn * width * 0.45, 0))
        if k % 2 == 0:
            sgn = 1 if (k // 2) % 2 == 0 else -1
            pv, pf = lathe([(0.0028, 0.0), (0.0028, 0.045), (0.0, 0.045)], 5, 0)
            mb.add(pv, pf, metal, M @ T(x, sgn * width * 0.42, 0.006))
            vv, ff = ico(1)
            mb.add(vv, ff, light, M @ T(x, sgn * width * 0.42, 0.05) @ S(0.0065))
        else:
            bv, bf = lathe([(0.005, 0.0), (0.0045, 0.012), (0.006, 0.014), (0, 0.016)], 6, 0)
            mb.add(bv, bf, metal_dark, M @ T(x, -width * 0.32, 0.006))
        k += 1
        x += 0.05


def pf_crane(mb, M, metal, metal_dark, accent, h=0.16):
    v, f = box(0.04, 0.04, 0.012, base=True)
    mb.add(v, f, metal_dark, M)
    for (x, y) in ((-0.012, -0.012), (0.012, -0.012), (0.012, 0.012), (-0.012, 0.012)):
        pv, pf = tube([Vector((x, y, 0.01)), Vector((x * 0.4, y * 0.4, h))], [0.003, 0.0025], 4)
        mb.add(pv, pf, metal, M)
    v, f = box(0.13, 0.012, 0.01)
    mb.add(v, f, accent, M @ T(0.04, 0, h))
    v, f = box(0.022, 0.022, 0.018)
    mb.add(v, f, metal_dark, M @ T(-0.025, 0, h + 0.004))
    cv, cf = tube([Vector((0.1, 0, h)), Vector((0.1, 0, h * 0.55))], [0.0012, 0.0012], 3)
    mb.add(cv, cf, metal_dark, M)
    hv, hf = box(0.012, 0.012, 0.01)
    mb.add(hv, hf, accent, M @ T(0.1, 0, h * 0.53))


def pf_beacon(mb, M, metal, light, h=0.08):
    v, f = lathe([(0.012, -0.02), (0.01, 0.0), (0.004, 0.006), (0.003, h), (0, h)], 6, 0)
    mb.add(v, f, metal, M)
    vv, ff = ico(1)
    mb.add(vv, ff, light, M @ T(0, 0, h + 0.006) @ S(0.0085))
    for a in (0, TAU / 3, 2 * TAU / 3):
        sv, sf = tube([Vector((0, 0, h * 0.4)), Vector((math.cos(a) * 0.022, math.sin(a) * 0.022, -0.01))], [0.0018, 0.0018], 3)
        mb.add(sv, sf, metal, M)


# ------------------------------------------------------------------ abyss
def tentacle_path(rng, span=0.3, a=1.25, b=3.0, steps=28, lift=0.0):
    psi = 0.0
    p = Vector((0, 0, 0))
    pts = [p.copy()]
    L = 1.0
    ds = L / steps
    for i in range(1, steps + 1):
        u = i / steps
        psi = a * u + b * u ** 3
        p = p + Vector((math.sin(psi), 0, math.cos(psi))) * ds
        pts.append(p.copy())
    chord = pts[-1] - pts[0]
    ang_c = math.atan2(chord.z, chord.x)
    R = Matrix.Rotation(ang_c, 3, 'Y')
    sc = span / max(chord.length, 1e-6)
    out = []
    for q in pts:
        q2 = R @ (q - pts[0])
        out.append(Vector((q2.x * sc - span / 2, 0, q2.z * sc)))
    return out


def pf_tentacle(mb, M, rng, mat, under=None, dots=None, span=0.3, r0=0.04, r1=0.008, a=1.3, b=3.4, n=7, height=None):
    pts = tentacle_path(rng, span, a, b)
    if height:
        top = max(p.z for p in pts)
        k = height / max(top, 1e-6)
        pts = [Vector((p.x, p.y, p.z * k)) for p in pts]
    m = len(pts)
    # sink the root a bit
    pts = [pts[0] + Vector((0, 0, -0.06))] + pts
    rad = [r0 * 1.15] + [lerp(r0, r1, (i / (m - 1)) ** 0.8) for i in range(m)]
    v, f = tube(pts, rad, n, cap0=True, cap1=True, jit=0.05, rng=rng)
    if under is not None:
        fm = []
        for k in range(len(f)):
            seg = k % n
            fm.append(under if seg in (n // 2, n // 2 + 1) else mat)
        mb.add(v, f, fm, M)
    else:
        mb.add(v, f, mat, M)
    if dots is not None:
        for i in range(4, m - 2, 3):
            p = pts[i + 1]
            t = (pts[min(i + 2, m)] - pts[i]).normalized()
            side = t.cross(Vector((0, 1, 0))).normalized()
            vv, ff = ico(1)
            r = rad[i + 1] * 0.32
            mb.add(vv, ff, dots, M @ T(p + side * rad[i + 1] * 0.92) @ S(r))
    return pts
