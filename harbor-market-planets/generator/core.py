"""Harbor Market Tycoon – Planet generator core (Blender 5.x, bpy module).

Coordinate conventions
- Planet centre at the origin, sea level radius RW = 1.0 (1 Blender unit = 1 m).
- +Z is "up": the flat build area sits on top at z = Plateau.zp.
- The preview camera looks from -Y (front) at 45 deg elevation, so large
  decoration goes to the back (+Y) and the sides (+/-X); the front stays low.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

TAU = math.tau
RW = 1.0
DEG = math.pi / 180.0


# ---------------------------------------------------------------- math utils
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def sph(alpha, phi, r=1.0):
    s = math.sin(alpha)
    return Vector((s * math.cos(phi), s * math.sin(phi), math.cos(alpha))) * r


def ang(d):
    d = d.normalized()
    return math.acos(clamp(d.z, -1, 1)), math.atan2(d.y, d.x)


def adist(a, b):
    return math.acos(clamp(a.normalized().dot(b.normalized()), -1, 1))


def dirs(alpha_deg, phi_deg):
    return sph(alpha_deg * DEG, phi_deg * DEG)


def nz(v, s=1.0, seed=0.0):
    return noise.noise(Vector((v[0] * s + seed * 13.37 + 0.31,
                               v[1] * s - seed * 7.91 + 0.17,
                               v[2] * s + seed * 3.17 + 0.53)))


def fbm(v, s, octaves=4, seed=0.0):
    t = n = 0.0
    a = 1.0
    for i in range(octaves):
        t += a * nz(v, s * (2 ** i), seed + i * 1.7)
        n += a
        a *= 0.5
    return t / n


def onz(phi, f, seed):
    """Periodic 1D noise around a circle."""
    return noise.noise(Vector((math.cos(phi) * f + 0.37, math.sin(phi) * f + 0.11, seed * 3.1 + 0.29)))


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def frame(loc, up, spin=0.0, s=1.0):
    q = Vector((0, 0, 1)).rotation_difference(up.normalized())
    S = Matrix.Scale(s, 4) if isinstance(s, (int, float)) else Matrix.Diagonal((s[0], s[1], s[2], 1.0))
    return Matrix.Translation(loc) @ q.to_matrix().to_4x4() @ Matrix.Rotation(spin, 4, 'Z') @ S


def basis(loc, up, fwd, s=1.0):
    z = up.normalized()
    x = (fwd - z * fwd.dot(z)).normalized()
    y = z.cross(x)
    M = Matrix((x, y, z)).transposed().to_4x4()
    M.translation = loc
    return M @ Matrix.Scale(s, 4)


def outward(d):
    """Unit tangent at direction d pointing away from the top (+Z)."""
    a, phi = ang(d)
    return Vector((math.cos(a) * math.cos(phi), math.cos(a) * math.sin(phi), -math.sin(a)))


# ---------------------------------------------------------------- materials
class Palette:
    def __init__(self, prefix):
        self.prefix = prefix
        self.m = {}
        self.info = []

    def add(self, key, hexcol, rough=0.8, metal=0.0, emit=0.0, alpha=1.0, spec=0.4,
            coat=0.0, label=None, show=True, emit_hex=None):
        name = f"{self.prefix}_{key}"
        if key == 'water':
            rough = max(rough, 0.38)
            spec = min(spec, 0.5)
        m = bpy.data.materials.new(name)
        b = m.node_tree.nodes.get("Principled BSDF")
        col = srgb(hexcol)
        b.inputs["Base Color"].default_value = (*col, 1.0)
        b.inputs["Roughness"].default_value = rough
        b.inputs["Metallic"].default_value = metal
        b.inputs["Specular IOR Level"].default_value = spec
        if emit > 0:
            ec = srgb(emit_hex) if emit_hex else col
            b.inputs["Emission Color"].default_value = (*ec, 1.0)
            b.inputs["Emission Strength"].default_value = emit
        if alpha < 1.0:
            b.inputs["Alpha"].default_value = alpha
            m.surface_render_method = 'BLENDED'
            try:
                m.blend_method = 'BLEND'
            except Exception:
                pass
        if coat:
            b.inputs["Coat Weight"].default_value = coat
            b.inputs["Coat Roughness"].default_value = 0.08
        m.diffuse_color = (*col, alpha)
        m.roughness = rough
        m.metallic = metal
        self.m[key] = m
        if show:
            self.info.append({"key": key, "hex": hexcol.upper(), "label": label or key, "emissive": emit > 0})
        return m

    def __getitem__(self, k):
        return self.m[k]


# ---------------------------------------------------------------- mesh builder
class MB:
    def __init__(self):
        self.v, self.f, self.m = [], [], []

    def add(self, verts, faces, mat, M=None):
        o = len(self.v)
        if M is None:
            self.v.extend(Vector(v) for v in verts)
        else:
            self.v.extend(M @ Vector(v) for v in verts)
        for k, fc in enumerate(faces):
            self.f.append([i + o for i in fc])
            self.m.append(mat[k] if isinstance(mat, (list, tuple)) else mat)
        return o

    def vert(self, co):
        self.v.append(Vector(co))
        return len(self.v) - 1

    def face(self, idx, mat):
        self.f.append(list(idx))
        self.m.append(mat)


_ICO = {}


def ico(sub):
    if sub not in _ICO:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        bm.verts.index_update()
        _ICO[sub] = ([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces])
        bm.free()
    v, f = _ICO[sub]
    return [x.copy() for x in v], [list(x) for x in f]


def connect(rings, n, cap0=True, cap1=True):
    f = []
    for A, B in zip(rings, rings[1:]):
        la, lb = len(A), len(B)
        if la == 1 and lb == 1:
            continue
        if la == 1:
            for i in range(n):
                f.append([A[0], B[(i + 1) % n], B[i]])
        elif lb == 1:
            for i in range(n):
                f.append([A[i], A[(i + 1) % n], B[0]])
        else:
            for i in range(n):
                f.append([A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]])
    if cap0 and len(rings[0]) > 1:
        f.append(list(reversed(rings[0])))
    if cap1 and len(rings[-1]) > 1:
        f.append(list(rings[-1]))
    return f


def lathe(prof, n, phase=0.0, cap0=True, cap1=True, jit=0.0, rng=None):
    v, rings = [], []
    for (r, z) in prof:
        if r < 1e-6:
            rings.append([len(v)])
            v.append(Vector((0, 0, z)))
            continue
        ring = []
        for i in range(n):
            a = phase + TAU * i / n
            rr, zz = r, z
            if jit and rng:
                rr *= 1 + rng.uniform(-jit, jit)
                zz += rng.uniform(-jit, jit) * r * 0.5
            ring.append(len(v))
            v.append(Vector((rr * math.cos(a), rr * math.sin(a), zz)))
        rings.append(ring)
    return v, connect(rings, n, cap0, cap1)


def tube(pts, radii, n=6, cap0=True, cap1=True, jit=0.0, rng=None, phase=0.0):
    pts = [Vector(p) for p in pts]
    m = len(pts)
    T = [(pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(m)]
    ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = [(ref - T[0] * ref.dot(T[0])).normalized()]
    for i in range(1, m):
        nn = N[-1] - T[i] * N[-1].dot(T[i])
        N.append(nn.normalized() if nn.length > 1e-6 else N[-1])
    v, rings = [], []
    for i, p in enumerate(pts):
        r = radii[i]
        if r < 1e-6:
            rings.append([len(v)])
            v.append(p.copy())
            continue
        B = T[i].cross(N[i])
        ring = []
        for k in range(n):
            a = phase + TAU * k / n
            rr = r * (1 + (rng.uniform(-jit, jit) if jit and rng else 0.0))
            ring.append(len(v))
            v.append(p + (N[i] * math.cos(a) + B * math.sin(a)) * rr)
        rings.append(ring)
    return v, connect(rings, n, cap0, cap1)


def box(sx, sy, sz, base=False):
    x, y, z = sx / 2, sy / 2, sz / 2
    z0, z1 = (0, sz) if base else (-z, z)
    v = [(-x, -y, z0), (x, -y, z0), (x, y, z0), (-x, y, z0), (-x, -y, z1), (x, -y, z1), (x, y, z1), (-x, y, z1)]
    f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return v, f


def leaf(length, width, segs=5, droop=0.35, fold=0.3, base=0.12):
    v, f = [], []
    rows = []
    for i in range(segs):
        t = i / segs
        x = length * t
        z = -droop * length * t * t
        w = width * (base + (1 - base) * math.sin(math.pi * t) ** 0.8)
        rows.append((len(v), len(v) + 1, len(v) + 2))
        v += [Vector((x, w, z)), Vector((x, 0, z + fold * w)), Vector((x, -w, z))]
    tip = len(v)
    v.append(Vector((length, 0, -droop * length)))
    for i in range(segs - 1):
        L0, C0, R0 = rows[i]
        L1, C1, R1 = rows[i + 1]
        f += [[C0, C1, L1], [C0, L1, L0], [R0, R1, C1], [R0, C1, C0]]
    L0, C0, R0 = rows[-1]
    f += [[C0, tip, L0], [R0, tip, C0]]
    return v, f


def rock(rng, sub=1, jit=0.22):
    v, f = ico(sub)
    seed = rng.random() * 100
    v = [p * (1 + jit * nz(p, 1.7, seed) + rng.uniform(-jit * 0.35, jit * 0.35)) for p in v]
    return v, f


def ribbon(points, ups, width):
    """Flat strip through points (each with an up vector); returns verts, faces."""
    v, f = [], []
    m = len(points)
    for i in range(m):
        t = (points[min(i + 1, m - 1)] - points[max(i - 1, 0)]).normalized()
        side = ups[i].cross(t).normalized()
        w = width[i] if isinstance(width, (list, tuple)) else width
        v += [points[i] + side * w, points[i] - side * w]
    for i in range(m - 1):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
        f.append([a, b, c, d])
    return v, f


# ---------------------------------------------------------------- plateau
class Plateau:
    def __init__(self, zp=1.035, rho0=0.5, var=0.07, seed=1.0, poly=0, polyamt=0.0, phase=0.0, n=128):
        self.zp, self.rho0, self.var, self.seed = zp, rho0, var, seed
        self.poly, self.polyamt, self.phase, self.n = poly, polyamt, phase, n

    def rho(self, phi):
        r = self.rho0 * (1 + self.var * (0.65 * onz(phi, 1.1, self.seed) + 0.35 * onz(phi, 2.4, self.seed + 5.0)))
        if self.poly:
            k = self.poly
            sec = TAU / k
            off = ((phi - self.phase) % sec) - sec / 2
            fac = math.cos(math.pi / k) / math.cos(off)
            r *= lerp(1.0, fac / ((1 + math.cos(math.pi / k)) / 2), self.polyamt)
        return r

    def alpha(self, phi):
        return math.atan2(self.rho(phi), self.zp)

    def margin(self, d):
        a, phi = ang(d)
        return a - self.alpha(phi)


# ---------------------------------------------------------------- planet
class Planet:
    def __init__(self, idx, key, title, seed):
        self.idx, self.key, self.title, self.seed = idx, key, title, seed
        self.rng = random.Random(seed)
        self.P = Palette(key)
        sc = bpy.context.scene
        self.col = bpy.data.collections.new(f"{idx:02d}_{key}")
        sc.collection.children.link(self.col)
        self.c_body = self._sub("Planet")
        self.c_build = self._sub("BuildArea")
        self.c_deco = self._sub("Deco")
        self.root = bpy.data.objects.new(f"{key}_Root", None)
        self.root.empty_display_type = 'PLAIN_AXES'
        self.root.empty_display_size = 1.25
        self.col.objects.link(self.root)
        self.solid_v, self.solid_f = [], []
        self.deco, self.counts = {}, {}
        self.occ = []
        self.objects = []
        self.plat = None
        self.terr = []   # (r_top, a_out(phi), drop)
        self.meta = {}

    def _sub(self, name):
        c = bpy.data.collections.new(f"{self.key}_{name}")
        self.col.children.link(c)
        return c

    # ---------------------------------------------- objects
    def make_obj(self, mb, name, coll, solid=False):
        if solid:
            o = len(self.solid_v)
            self.solid_v.extend(mb.v)
            self.solid_f.extend([[i + o for i in fc] for fc in mb.f])
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in mb.v], [], mb.f)
        slots, idx, mi = [], {}, []
        for m in mb.m:
            if m.name not in idx:
                idx[m.name] = len(slots)
                slots.append(m)
            mi.append(idx[m.name])
        for m in slots:
            me.materials.append(m)
        me.polygons.foreach_set('material_index', mi)
        me.validate(clean_customdata=False)
        me.update()
        me.shade_flat()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.parent = self.root
        self.objects.append(ob)
        return ob

    def d(self, cat):
        if cat not in self.deco:
            self.deco[cat] = MB()
        return self.deco[cat]

    def count(self, cat, n=1):
        self.counts[cat] = self.counts.get(cat, 0) + n

    def finalize(self):
        for cat, mb in self.deco.items():
            if mb.f:
                self.make_obj(mb, f"{self.key}_Deco_{cat}", self.c_deco)

    # ---------------------------------------------- terrain pieces
    def clamp_island(self, d, h):
        """Keep the body below plateau and terraces, with a gentle ramp outside."""
        a, phi = ang(d)
        lim = 9.0
        pa = self.plat.alpha(phi)
        if a < pa + 0.03:
            lim = self.plat.zp / max(math.cos(a), 1e-3) - RW - 0.03
        for (r_top, a_out, drop) in self.terr:
            ao = a_out(phi)
            hu = r_top - RW - 0.03
            if a < ao + 0.004:
                lim = min(lim, hu)
            else:
                lim = min(lim, hu + 0.9 * (a - ao - 0.004))
        if not self.terr:
            hu = self.plat.zp / math.cos(pa) - RW - 0.05
            if a >= pa + 0.03:
                lim = min(lim, hu + 0.9 * (a - pa - 0.03))
        return min(h, lim)

    def outer_alpha(self, phi):
        if self.terr:
            return self.terr[-1][1](phi)
        return self.plat.alpha(phi)

    def make_body(self, hfun, paint, sub=5):
        v, f = ico(sub)
        H = [self.clamp_island(d, hfun(d)) for d in v]
        mb = MB()
        mb.v = [d * (RW + h) for d, h in zip(v, H)]
        for fc in f:
            p = [mb.v[i] for i in fc]
            c = (p[0] + p[1] + p[2]) / 3
            nrm = (p[1] - p[0]).cross(p[2] - p[0]).normalized()
            dc = c.normalized()
            slope = 1 - clamp(nrm.dot(dc), -1, 1)
            mb.f.append(fc)
            mb.m.append(paint(dc, c.length - RW, slope, c))
        return self.make_obj(mb, f"{self.key}_Body", self.c_body, solid=True)

    def make_water(self, mat, r=RW, sub=4, jit=0.0022):
        v, f = ico(sub)
        rng = random.Random(self.seed + 99)
        mb = MB()
        mb.add([p * (r + rng.uniform(-jit, jit)) for p in v], f, mat)
        return self.make_obj(mb, f"{self.key}_Ocean", self.c_body)

    def make_plateau(self, top, edge, cliffs, bev=0.016, profile=None, jit=0.010, tone_seed=3.0, tone_scale=2.4,
                     tone_thresh=0.12):
        """Truly planar build surface at z = zp with a bevelled rim and a cliff skirt.

        top: (mat_a, mat_b) – two close tones laid out in large irregular patches.
        cliffs: one material per cliff band (profile entry)."""
        pl, rng = self.plat, self.rng
        n = pl.n
        zp = pl.zp
        mb = MB()
        R = [pl.rho(TAU * i / n) for i in range(n)]
        counts = [n // 8, n // 4, n // 2, n]
        fr = [0.24, 0.5, 0.76, 1.0]
        c = mb.vert((0, 0, zp))
        rings = []
        for k, (cnt, f) in enumerate(zip(counts, fr)):
            ring = []
            for i in range(cnt):
                ph = TAU * i / cnt
                if k < len(counts) - 1:
                    ph += rng.uniform(-0.22, 0.22) * TAU / cnt
                    rr = (pl.rho(ph) - bev) * f * (1 + rng.uniform(-0.04, 0.04))
                else:
                    rr = R[i] - bev
                ring.append(mb.vert((rr * math.cos(ph), rr * math.sin(ph), zp)))
            rings.append(ring)

        def tone(ids, k):
            if k < 2:
                return top[0]
            cc = sum((mb.v[i] for i in ids), Vector()) / len(ids)
            return top[1] if fbm(cc, tone_scale, 2, tone_seed) > tone_thresh else top[0]

        r0 = rings[0]
        for i in range(len(r0)):
            ids = [c, r0[i], r0[(i + 1) % len(r0)]]
            mb.face(ids, tone(ids, 0))
        for k, (A, B) in enumerate(zip(rings, rings[1:])):
            m = len(A)
            for i in range(m):
                a0, a1 = A[i], A[(i + 1) % m]
                b0, b1, b2 = B[2 * i], B[2 * i + 1], B[(2 * i + 2) % (2 * m)]
                for ids in ([a0, b0, b1], [a0, b1, a1], [a1, b1, b2]):
                    mb.face(ids, tone(ids, k + 1))
        # rim + cliff sweep
        profile = profile or [(0.045, 0.006), (0.13, 0.016), (0.40, 0.03)]
        secs = [rings[-1]]
        ring = []
        for i in range(n):
            ph = TAU * i / n
            ring.append(mb.vert((R[i] * math.cos(ph), R[i] * math.sin(ph), zp - bev * 0.8)))
        secs.append(ring)
        for k, (dz, dr) in enumerate(profile):
            ring = []
            for i in range(n):
                ph = TAU * i / n
                j = jit if k < len(profile) - 1 else jit * 0.5
                rr = R[i] + dr + rng.uniform(0, j)
                ring.append(mb.vert((rr * math.cos(ph), rr * math.sin(ph), zp - dz + rng.uniform(-j, j))))
            secs.append(ring)
        mats = [edge] + list(cliffs)
        for k in range(len(secs) - 1):
            A, B = secs[k], secs[k + 1]
            for i in range(n):
                j = (i + 1) % n
                mb.face([A[i], B[i], B[j], A[j]], mats[k] if not callable(mats[k]) else mats[k](i, k))
        area = 0.0
        for i in range(n):
            r1, r2 = R[i] - bev, R[(i + 1) % n] - bev
            area += 0.5 * r1 * r2 * math.sin(TAU / n)
        ob = self.make_obj(mb, f"{self.key}_BuildArea", self.c_build)
        rmin, rmax = min(R) - bev, max(R) - bev
        ob["build_surface_z"] = zp
        ob["build_radius_min"] = round(rmin, 4)
        ob["build_radius_max"] = round(rmax, 4)
        ob["build_area_m2"] = round(area, 4)
        self.meta["build"] = {"z": zp, "r_min": round(rmin, 3), "r_max": round(rmax, 3), "area": round(area, 3)}
        return ob

    def make_terrace(self, mb, r_top, a_in, a_out, top, rim, cliffs, bev=0.012, drop=0.08, n=160,
                     flare=(0.006, 0.016), jit=0.006, mid=2):
        rng = self.rng
        secs = []
        for i in range(n):
            phi = TAU * i / n
            ai, ao = a_in(phi), a_out(phi)
            ba = bev / r_top
            sec = [sph(lerp(ai, ao - ba, k / mid), phi, r_top) for k in range(mid + 1)]
            sec.append(sph(ao, phi, r_top - bev * 0.8))
            sec.append(sph(ao + flare[0] + rng.uniform(0, jit), phi, r_top - drop * 0.45 + rng.uniform(-jit, jit)))
            sec.append(sph(ao + flare[1] + rng.uniform(0, jit * 0.5), phi, r_top - drop))
            secs.append([mb.vert(p) for p in sec])
        bands = [top] * mid + [rim] + list(cliffs)
        for i in range(n):
            A, B = secs[i], secs[(i + 1) % n]
            for k in range(len(A) - 1):
                m = bands[k]
                if callable(m):
                    m = m(i, k, (mb.v[A[k]] + mb.v[B[k + 1]]) / 2)
                mb.face([A[k], A[k + 1], B[k + 1], B[k]], m)
        self.terr.append((r_top, a_out, drop))

    def finish_terraces(self, mb):
        if mb.f:
            self.make_obj(mb, f"{self.key}_Terraces", self.c_body, solid=True)

    # ---------------------------------------------- surface queries
    def build_bvh(self):
        self.bvh = BVHTree.FromPolygons(self.solid_v, self.solid_f, all_triangles=False)

    def hit(self, d):
        d = d.normalized()
        loc, nrm, _, _ = self.bvh.ray_cast(d * 3.0, -d, 4.0)
        if loc is None:
            return None
        if nrm.dot(d) < 0:
            nrm = -nrm
        return loc, nrm

    def probe(self, d):
        d = d.normalized()
        h = self.hit(d)
        if not h:
            return None
        loc, nrm = h
        a, phi = ang(d)
        return {"d": d, "loc": loc, "n": nrm, "h": loc.length - RW, "a": a, "phi": phi,
                "slope": 1 - nrm.dot(d), "front": -d.y, "pm": self.plat.margin(d)}

    def sdir(self, a=(0, 180), phis=None):
        rng = self.rng
        c0, c1 = math.cos(a[0] * DEG), math.cos(a[1] * DEG)
        al = math.acos(rng.uniform(c1, c0))
        if phis:
            w = [abs(p1 - p0) for p0, p1 in phis]
            r = rng.uniform(0, sum(w))
            for (p0, p1), ww in zip(phis, w):
                if r <= ww:
                    ph = (p0 + rng.uniform(0, 1) * (p1 - p0)) * DEG
                    break
                r -= ww
            else:
                ph = rng.uniform(0, TAU)
        else:
            ph = rng.uniform(0, TAU)
        return sph(al, ph)

    def free(self, d, r):
        return all(adist(d, q) > r + rq for q, rq in self.occ)

    def claim(self, d, r):
        self.occ.append((d.normalized(), r))

    def scatter(self, n, pred, rad, a=(0, 180), phis=None, tries=4000, claim=True):
        out = []
        for _ in range(tries):
            if len(out) >= n:
                break
            d = self.sdir(a, phis)
            r = rad(d) if callable(rad) else rad
            if not self.free(d, r):
                continue
            p = self.probe(d)
            if p is None or not pred(p):
                continue
            p["r"] = r
            if claim:
                self.claim(d, r)
            out.append(p)
        return out

    def coast(self, phi, a0, a1=150 * DEG, step=0.004, level=0.004):
        a = a0
        last = None
        while a < a1:
            d = sph(a, phi)
            h = self.hit(d)
            if h and h[0].length < RW + level:
                return a, h[0], last
            last = h[0] if h else last
            a += step
        return None

    def frontal(self, d, lo=0.32):
        """Scale factor that keeps decoration low on the camera-facing front."""
        f = clamp((-d.normalized().y - 0.15) / 0.55)
        if d.normalized().z < -0.35:
            f *= 0.5
        return lerp(1.0, lo, f)


# ---------------------------------------------------------------- scene helpers
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _ICO.clear()
