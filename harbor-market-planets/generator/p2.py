"""Planets 2-5: Coralune, Verdantide, Dunewake, Frostharbor."""
import math
from mathutils import Vector, Matrix
from core import (TAU, DEG, RW, MB, Planet, Plateau, clamp, smooth, lerp, sph, ang, adist, dirs, nz, fbm, onz,
                  frame, basis, outward, ico, lathe, tube, ribbon, rock)
from prefabs import *  # noqa
from planets import (coast_profile, mound, seabed, std_terraces, place_up, land, off_build)


def wrapd(a):
    return (a + math.pi) % TAU - math.pi


def strip(mb, pts, side, width, mat):
    """Flat strip through pts with a fixed side direction (or one per point)."""
    v, f = [], []
    for i, p in enumerate(pts):
        s = side[i] if isinstance(side, list) else side
        w = width[i] if isinstance(width, list) else width
        v += [p + s * w, p - s * w]
    for i in range(len(pts) - 1):
        f.append([2 * i + 1, 2 * i, 2 * i + 2, 2 * i + 3])
    mb.add(v, f, mat)


def disc(mb, centre_dir, r_abs, rad, mat, n=12, rng=None):
    """Flat low-poly pool on the sphere, centred on centre_dir at radius r_abs."""
    up = centre_dir.normalized()
    v, f = lathe([(rad, 0.0), (0.0, 0.0)], n, rng.uniform(0, TAU) if rng else 0.0, cap0=False, cap1=False,
                 jit=0.12 if rng else 0.0, rng=rng)
    mb.add(v, f, mat, frame(up * r_abs, up))


def ring_around(p, n, lo, hi, jitter=0.35):
    """Evenly spaced probes in a band lo..hi degrees outside the plateau rim."""
    out = []
    for i in range(n):
        phi = TAU * (i + p.rng.uniform(-jitter, jitter)) / n
        a = p.plat.alpha(phi) + p.rng.uniform(lo, hi) * DEG
        pr = p.probe(sph(a, phi))
        if pr:
            out.append(pr)
    return out


# ================================================================ 2 CORALUNE
def coralune():
    p = Planet(2, "Coralune", "Coralune", 202)
    P = p.P
    P.add('water', '#0E8F96', rough=0.07, alpha=0.7, spec=0.7, label='Petrolwasser')
    P.add('sea_sand', '#BFE0CF', show=False)
    P.add('sea_coral', '#F3A487', show=False)
    P.add('sea_coral2', '#F2B46E', show=False)
    P.add('sea_mid', '#147F87', show=False)
    P.add('sea_deep', '#06525E', label='Tiefes Petrol')
    P.add('sand', '#F0E1C3', label='Korallensand')
    P.add('reef', '#CDB596', label='Riffgestein')
    P.add('reef2', '#B89F80', show=False)
    P.add('build', '#EEE8D9', label='Heller Kalkstein (Baufläche)')
    P.add('build2', '#E6E0CE', show=False)
    P.add('edge', '#D0C6AC', label='Kalksteinkante')
    P.add('terr', '#E2D9C1', show=False)
    P.add('cliff', '#C8BB9D', show=False)
    P.add('cliff2', '#B7A988', show=False)
    P.add('c_orange', '#F28A36', label='Koralle Orange')
    P.add('c_pink', '#EF7BA3', label='Koralle Rosa')
    P.add('c_red', '#D9473F', label='Koralle Warmrot')
    P.add('c_peach', '#F7B07C', show=False)
    P.add('shell', '#F8EADA', label='Muschel')
    P.add('shell2', '#F1BDAE', show=False)

    p.plat = Plateau(zp=1.035, rho0=0.5, var=0.09, seed=2.2)
    std_terraces(p, [dict(r=1.096, width=5.8, wvar=1.6, top=P['terr'], rim=P['edge'], cliffs=[P['cliff'], P['cliff2']], drop=0.085)])
    reef_c = [dirs(a, f) for a, f in ((84, -60), (90, -125), (78, -152), (100, -90), (100, 80), (120, 160), (128, -30), (150, 40))]

    def reef_h(d):
        a, phi = ang(d)
        ring = 1 - abs(a - (62 + 4 * onz(phi, 1.8, 3)) * DEG) / (5 * DEG)
        seg = smooth(-0.1, 0.2, fbm(d, 3.4, 3, 8))
        h = 0.022 * max(0.0, ring) * seg - 0.02 * (1 - max(0.0, ring))
        for k, c in enumerate(reef_c):
            h = max(h, mound(d, c, (5.5 if k < 4 else 8) * DEG, 0.016, 30 + k, shelf=-0.022, deep=-0.13, wobble=0.4))
        return h

    def hfun(d):
        a, phi = ang(d)
        x = a - p.outer_alpha(phi)
        h = coast_profile(x, 0.066, (6.5 + 1.5 * onz(phi, 2.2, 4)) * DEG, 8 * DEG, 10 * DEG, hs=-0.026)
        h = max(h, reef_h(d) + 0.004 * fbm(d, 12, 2, 5))
        h = max(h, seabed(d, -0.14, 0.035, 2))
        return h

    def paint(dc, h, slope, c):
        a, phi = ang(dc)
        if h > 0.004:
            if a - p.outer_alpha(phi) > 14 * DEG or slope > 0.25:
                return P['reef'] if fbm(dc, 8, 2, 1) > -0.1 else P['reef2']
            return P['sand']
        if h > -0.03:
            n = fbm(dc, 7.5, 2, 6)
            if n > 0.36:
                return P['sea_coral']
            if n < -0.4:
                return P['sea_coral2']
            return P['sea_sand']
        if h > -0.075:
            return P['sea_mid']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['cliff'], P['cliff2'], P['cliff2']])
    p.build_bvh()
    rng = p.rng
    corals = [P['c_orange'], P['c_pink'], P['c_red'], P['c_peach']]
    # reef arches: chunky, on the reef in the side view and at the front corners
    for (a, f, span, hh) in ((64, -150, 0.2, 0.11), (66, -32, 0.18, 0.1), (74, -96, 0.22, 0.1)):
        d = dirs(a, f)
        pr = p.probe(d)
        M = basis(pr['d'] * (RW - 0.006), pr['d'], outward(pr['d'])) @ Rz(rng.uniform(-0.5, 0.5))
        pts = pf_arch(p.d('ReefArches'), M, rng, [P['reef'], P['reef2']], span=span, height=hh, r0=0.05, r1=0.03,
                      n=7, jit=0.18, bands=True, sink=0.06)
        for i in (3, 5, 6, 8):
            pf_coral_round(p.d('ReefArches'), M @ T(pts[i] + Vector((0, 0, 0.026))), rng, corals[i % 4], r=0.017)
        pf_coral_branch(p.d('ReefArches'), M @ T(pts[6] + Vector((0, 0, 0.028))), rng, P['c_orange'], h=0.05, depth=1)
        p.claim(d, 6 * DEG)
        p.count('Riffbogen')

    # low coral hem around the build area
    for k, pr in enumerate(ring_around(p, 40, 1.4, 3.6)):
        s = p.frontal(pr['d'], 0.7)
        M = frame(pr['loc'], pr['d'], rng.uniform(0, TAU))
        kind = k % 3
        if kind == 0:
            pf_coral_round(p.d('CoralsLow'), M, rng, corals[k % 4], r=rng.uniform(0.013, 0.02) * s, mat2=corals[(k + 1) % 4])
        elif kind == 1:
            pf_coral_branch(p.d('CoralsLow'), M, rng, corals[(k + 2) % 4], h=rng.uniform(0.03, 0.045) * s, depth=1)
        else:
            pf_coral_round(p.d('CoralsLow'), M, rng, corals[(k + 3) % 4], r=rng.uniform(0.012, 0.017) * s, squash=0.9)
        p.claim(pr['d'], 0.8 * DEG)
        p.count('Niedrige Koralle')

    # large shells on the beach
    for (f, s) in ((205, 0.095), (-28, 0.08), (98, 0.09)):
        phi = f * DEG
        a = p.outer_alpha(phi) + 3.2 * DEG
        pr = p.probe(sph(a, phi))
        M = frame(pr['loc'] - pr['d'] * 0.006, place_up(p, pr, 0.5), rng.uniform(0, TAU)) @ Ry(-0.22)
        pf_shell(p.d('Shells'), M, rng, P['shell'], P['shell2'], s=s * p.frontal(pr['d'], 0.75))
        p.claim(pr['d'], 3.5 * DEG)
        p.count('Riesenmuschel')

    reef_ok = lambda pr: pr['h'] > -0.02 and off_build(pr, 14)
    # sea fans on the back reef, facing the camera
    for pr in p.scatter(6, reef_ok, 2.6 * DEG, a=(50, 80), phis=[(30, 160)]):
        M = basis(pr['loc'], pr['d'], Vector((1, 0, 0)))
        pf_fan(p.d('FanCorals'), M @ Rz(rng.uniform(-0.4, 0.4)), rng, corals[rng.randrange(3)], h=rng.uniform(0.1, 0.15), ribs=P['c_red'])
        p.count('Fächerkoralle')
    # big branching corals back & sides, smaller ones on the front reefs
    for pr in p.scatter(14, reef_ok, 2.4 * DEG, a=(48, 120)):
        s = p.frontal(pr['d'], 0.5)
        pf_coral_branch(p.d('BranchCorals'), frame(pr['loc'], pr['d'], rng.uniform(0, TAU)), rng, corals[rng.randrange(4)],
                        h=rng.uniform(0.08, 0.12) * s, depth=2)
        p.count('Astkoralle')
    # round corals everywhere on the reef
    for pr in p.scatter(30, lambda pr: pr['h'] > -0.024 and off_build(pr, 12), 1.5 * DEG, a=(40, 160)):
        s = p.frontal(pr['d'], 0.6)
        pf_coral_round(p.d('RoundCorals'), frame(pr['loc'], place_up(p, pr, 0.5), rng.uniform(0, TAU)), rng,
                       corals[rng.randrange(4)], r=rng.uniform(0.022, 0.04) * s, mat2=P['shell'])
        p.count('Hirnkoralle')
    # submerged corals in the lagoon (seen through the water)
    for pr in p.scatter(22, lambda pr: -0.03 < pr['h'] < -0.006 and off_build(pr, 8), 1.4 * DEG, a=(30, 120)):
        M = frame(pr['loc'], pr['d'], rng.uniform(0, TAU))
        if rng.random() < 0.5:
            pf_coral_branch(p.d('LagoonCorals'), M, rng, corals[rng.randrange(4)], h=rng.uniform(0.035, 0.05), depth=1)
        else:
            pf_coral_round(p.d('LagoonCorals'), M, rng, corals[rng.randrange(4)], r=rng.uniform(0.014, 0.022))
        p.count('Lagunenkoralle')

    p.meta.update(tagline="Die lebendige Korallenwelt",
                  features=["Helle Kalkstein-Baufläche, gesäumt von 40 niedrigen Korallen",
                            "Breite Lagune mit sichtbaren Korallenflecken unter Wasser",
                            "Drei Riffbögen auf dem äußeren Riffring",
                            "Ast-, Hirn- und Fächerkorallen, drei große Muscheln am Strand"])
    p.finalize()
    return p


# ================================================================ 3 VERDANTIDE
def verdantide():
    p = Planet(3, "Verdantide", "Verdantide", 303)
    P = p.P
    P.add('water', '#3EB0CE', rough=0.07, alpha=0.64, spec=0.7, label='Küstenwasser')
    P.add('sea_sand', '#CBD7A2', show=False)
    P.add('sea_mid', '#379CB3', show=False)
    P.add('sea_deep', '#196987', label='Tiefes Wasser')
    P.add('build', '#BBDA80', label='Lichtung (Baufläche)')
    P.add('build2', '#B3D376', show=False)
    P.add('edge', '#CEC7B1', label='Heller Steinrand')
    P.add('grass', '#6CC04A', label='Sattes Gras')
    P.add('grass2', '#5BAF40', show=False)
    P.add('grass3', '#4C9B3A', show=False)
    P.add('stone', '#B8B09D', label='Terrassenstein')
    P.add('stone2', '#9D9584', show=False)
    P.add('stone3', '#857D6E', show=False)
    P.add('beach', '#E2DAAF', show=False)
    P.add('trunk', '#7A5236', show=False)
    P.add('crown', '#4E9E3D', label='Baumkrone')
    P.add('crown2', '#78BF49', show=False)
    P.add('crown3', '#3A8434', show=False)
    P.add('broad', '#3E9D3F', label='Breitblatt')
    P.add('broad2', '#2E8237', show=False)
    P.add('stream', '#5FCBEA', rough=0.08, emit=0.35, label='Wasserlauf')
    P.add('fall', '#EAF8FC', rough=0.2, emit=0.7, label='Wasserfall')

    p.plat = Plateau(zp=1.035, rho0=0.5, var=0.06, seed=3.3)

    def gtop(i, k, c):
        return P['grass'] if fbm(c, 5, 2, 2) > -0.1 else P['grass2']
    std_terraces(p, [dict(r=1.1, width=5.0, wvar=1.5, top=gtop, rim=P['stone'], cliffs=[P['stone2'], P['stone3']], drop=0.088),
                     dict(r=1.058, width=5.5, wvar=1.8, top=gtop, rim=P['stone'], cliffs=[P['stone2'], P['stone3']], drop=0.08, seed=9)])
    hills = [(dirs(57, 95), 22 * DEG, 0.11), (dirs(60, 160), 17 * DEG, 0.08), (dirs(62, 22), 16 * DEG, 0.075),
             (dirs(118, 40), 20 * DEG, 0.07), (dirs(130, -140), 18 * DEG, 0.06)]
    isl = [(dirs(a, f), r * DEG, h) for a, f, r, h in ((96, -60, 8, 0.03), (104, 150, 10, 0.035), (150, 60, 12, 0.04))]

    def hfun(d):
        a, phi = ang(d)
        x = a - p.outer_alpha(phi)
        wb = (17 + 7 * onz(phi, 1.3, 5) + 3 * onz(phi, 3.3, 1)) * DEG
        h = coast_profile(x, 0.026, wb, 5 * DEG, 11 * DEG)
        hill = 0.0
        for c, r, hh in hills:
            t = max(0.0, 1 - adist(d, c) / r)
            hill += hh * t ** 1.6
        h = h + (hill + 0.012 * fbm(d, 6, 3, 2)) * smooth(-0.005, 0.02, h)
        h = max(h, seabed(d, -0.14, 0.035, 3))
        for k, (c, r, hh) in enumerate(isl):
            h = max(h, mound(d, c, r, hh, 40 + k))
        return h

    def paint(dc, h, slope, c):
        if h > 0.004:
            if slope > 0.3:
                return P['stone3']
            if slope > 0.17:
                return P['stone2'] if fbm(dc, 9, 2, 3) > 0 else P['stone']
            if h < 0.011:
                return P['beach']
            n = fbm(dc, 5, 3, 7)
            return P['grass3'] if n < -0.2 else P['grass2'] if n < 0.05 else P['grass']
        if h > -0.034:
            return P['sea_sand']
        if h > -0.08:
            return P['sea_mid']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['stone2'], P['stone3'], P['stone3']])
    p.build_bvh()
    rng = p.rng
    (r1, a1f, _), (r2, a2f, _) = p.terr

    # waterfalls: spring on the upper terrace -> fall -> lower terrace -> fall -> stream to the sea
    falls = p.d('Waterfalls')
    for fdeg in (180, -4, 128):
        phi = fdeg * DEG
        side = Vector((-math.sin(phi), math.cos(phi), 0))
        ap, a1, a2 = p.plat.alpha(phi), a1f(phi), a2f(phi)
        w = 0.011
        river1 = [sph(lerp(ap + 0.016, a1 - 0.004, t / 5), phi, r1 + 0.0035) for t in range(6)]
        strip(falls, river1, side, w, P['stream'])
        fall1 = [sph(a1 - 0.004, phi, r1 + 0.0035), sph(a1 + 0.002, phi, r1 - 0.004), sph(a1 + 0.008, phi, r1 - 0.025),
                 sph(a1 + 0.013, phi, r2 + 0.003)]
        strip(falls, fall1, side, [w, w * 1.05, w * 1.15, w * 1.25], P['fall'])
        river2 = [sph(lerp(a1 + 0.013, a2 - 0.004, t / 4), phi, r2 + 0.0035) for t in range(5)]
        strip(falls, river2, side, w * 1.1, P['stream'])
        land_pt = p.probe(sph(a2 + 0.022, phi))
        fall2 = [sph(a2 - 0.004, phi, r2 + 0.0035), sph(a2 + 0.002, phi, r2 - 0.004), sph(a2 + 0.01, phi, r2 - 0.022),
                 land_pt['loc'] + land_pt['d'] * 0.004]
        strip(falls, fall2, side, [w * 1.1, w * 1.15, w * 1.25, w * 1.35], P['fall'])
        # stream across the lowland to the coast
        pts = [land_pt['loc'] + land_pt['d'] * 0.004]
        a = a2 + 0.022
        wig = rng.uniform(0, 10)
        while a < 120 * DEG:
            a += 0.012
            ph = phi + 0.05 * math.sin(a * 40 + wig)
            pr = p.probe(sph(a, ph))
            pts.append(pr['loc'] + pr['d'] * 0.004)
            if pr['h'] < -0.004:
                break
        sides = [Vector((-math.sin(phi), math.cos(phi), 0))] * len(pts)
        strip(falls, pts, sides, [w * (1.3 + 0.6 * i / len(pts)) for i in range(len(pts))], P['stream'])
        # pools, splash and the spring rock
        disc(falls, sph(a1 + 0.02, phi), r2 + 0.003, 0.02, P['stream'], rng=rng)
        disc(falls, land_pt['d'], land_pt['loc'].length + 0.003, 0.024, P['stream'], rng=rng)
        for q in (sph(a1 + 0.016, phi, r2 + 0.006), land_pt['loc'] + land_pt['d'] * 0.008):
            for k in range(3):
                vv, ff = ico(1)
                off = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * 0.008
                falls.add(vv, ff, P['fall'], Matrix.Translation(q + off) @ Matrix.Scale(rng.uniform(0.005, 0.008), 4))
        spring = sph(ap + 0.012, phi, r1)
        pf_rock(p.d('Rocks'), frame(spring, spring.normalized(), rng.uniform(0, TAU), (0.022, 0.018, 0.02)), rng, P['stone2'], squash=0.8)
        p.claim(sph(a2 + 0.03, phi), 3.5 * DEG)
        p.claim(sph(a1, phi), 2.5 * DEG)
        p.count('Wasserfall', 2)

    # compact trees on the back and the sides
    tree_ok = lambda pr: land(pr, 0.01) and off_build(pr, 1.5) and pr['slope'] < 0.22 and pr['front'] < 0.3
    for pr in p.scatter(34, tree_ok, 2.3 * DEG, a=(28, 150)):
        s = rng.uniform(0.11, 0.17) * p.frontal(pr['d'], 0.5)
        pf_tree(p.d('Trees'), frame(pr['loc'] - pr['d'] * 0.004, pr['d'], rng.uniform(0, TAU)), rng, P['trunk'],
                [P['crown'], P['crown2'], P['crown3']], h=s)
        p.count('Baum')
    # bushes at the front
    for pr in p.scatter(10, lambda pr: land(pr, 0.012) and off_build(pr, 11) and pr['front'] >= 0.3, 1.8 * DEG, a=(35, 120)):
        pf_tree(p.d('Trees'), frame(pr['loc'] - pr['d'] * 0.003, pr['d'], rng.uniform(0, TAU)), rng, P['trunk'],
                [P['crown2'], P['crown']], h=rng.uniform(0.045, 0.06))
        p.count('Busch')
    # broad-leaf plants
    for pr in p.scatter(20, lambda pr: land(pr, 0.008) and off_build(pr, 1.5) and pr['slope'] < 0.25, 1.4 * DEG, a=(27, 140)):
        s = rng.uniform(0.045, 0.075) * p.frontal(pr['d'], 0.7)
        pf_broadleaf(p.d('BroadLeaves'), frame(pr['loc'], pr['d'], rng.uniform(0, TAU)), rng, [P['broad'], P['broad2']], s=s)
        p.count('Breitblattpflanze')
    for pr in p.scatter(10, lambda pr: land(pr, 0.006) and off_build(pr, 9), 2 * DEG, a=(35, 150)):
        s = rng.uniform(0.02, 0.035) * p.frontal(pr['d'], 0.7)
        pf_rock(p.d('Rocks'), frame(pr['loc'], place_up(p, pr, 0.5), rng.uniform(0, TAU), (s, s * 0.9, s)), rng,
                P['stone'] if rng.random() < 0.5 else P['stone2'], squash=0.7)
        p.count('Findling')

    p.meta.update(tagline="Der grüne Inselgarten",
                  features=["Weitläufige, ebene Lichtung auf zwei geschichteten Steinterrassen",
                            "Drei Wasserläufe mit je zwei kleinen Wasserfällen bis zur Küste",
                            "Kompakte Baumkronen auf Hügeln hinten und seitlich",
                            "Breitblattpflanzen und niedrige Büsche an der Vorderseite"])
    p.finalize()
    return p


# ================================================================ 4 DUNEWAKE
def dunewake():
    p = Planet(4, "Dunewake", "Dunewake", 404)
    P = p.P
    P.add('water', '#2EB6B2', rough=0.07, alpha=0.62, spec=0.7, label='Türkisküste')
    P.add('sea_sand', '#EAD2A0', show=False)
    P.add('sea_mid', '#3AA5A5', show=False)
    P.add('sea_deep', '#16707F', label='Tiefes Meer')
    P.add('dune', '#ECBA5C', label='Goldene Düne')
    P.add('dune2', '#DEA64A', show=False)
    P.add('dune3', '#CF9442', show=False)
    P.add('wet', '#F2DEAF', label='Ausgewaschene Küste')
    P.add('terra', '#C6643B', label='Terrakottafels')
    P.add('terra2', '#A84F32', show=False)
    P.add('terra3', '#DA855A', show=False)
    P.add('build', '#EDCD97', label='Sandsteinplateau (Baufläche)')
    P.add('build2', '#E7C58C', show=False)
    P.add('edge', '#C9975C', label='Sandsteinkante')
    P.add('strata1', '#D9AA6E', show=False)
    P.add('strata2', '#C68C57', show=False)
    P.add('strata3', '#B5794A', show=False)
    P.add('oasis', '#3FD5C6', rough=0.05, alpha=0.86, spec=0.8, label='Oase')
    P.add('ograss', '#87AB46', show=False)
    P.add('leaf', '#6AA03D', show=False)
    P.add('leaf2', '#58893A', show=False)
    P.add('trunk', '#8C603C', show=False)

    p.plat = Plateau(zp=1.04, rho0=0.5, var=0.05, seed=4.4, poly=7, polyamt=0.55, phase=0.3)
    std_terraces(p, [dict(r=1.098, width=4.8, wvar=1.4, top=P['strata1'], rim=P['edge'], cliffs=[P['strata2'], P['strata3']], drop=0.09)])
    oasis_c = dirs(54, -104)
    wind = Vector((1.0, 0.35, 0.2)).normalized()

    def coast_a(phi):
        return (70 + 12 * onz(phi, 1.5, 9) + 5 * onz(phi, 3.6, 2)) * DEG

    def dunes(d):
        u = d.dot(wind) * 11 + 1.3 * fbm(d, 2.2, 2, 4)
        t = u % 1.0
        prof = t / 0.78 if t < 0.78 else (1 - t) / 0.22
        return 0.042 * prof * (0.65 + 0.35 * fbm(d, 3, 2, 6))

    def hfun(d):
        a, phi = ang(d)
        ca = coast_a(phi)
        wb = 3.5 * DEG
        inland = smooth(0, 7 * DEG, ca - wb - a)
        hu = 0.024 + dunes(d) * inland + 0.008 * fbm(d, 8, 2, 1)
        h = coast_profile(a - (ca - wb), hu, wb, 6 * DEG, 10 * DEG)
        do = adist(d, oasis_c)
        if do < 7.5 * DEG:
            h = lerp(0.009, h, smooth(4.2 * DEG, 7.5 * DEG, do))
        h = max(h, seabed(d, -0.14, 0.035, 5))
        for k, (c, r, hh) in enumerate(((dirs(118, 30), 12 * DEG, 0.05), (dirs(140, -110), 14 * DEG, 0.05))):
            h = max(h, mound(d, c, r, hh, 60 + k))
        return h

    def paint(dc, h, slope, c):
        if h > 0.004:
            do = adist(dc, oasis_c)
            if do < 6.6 * DEG and slope < 0.2:
                return P['ograss']
            if slope > 0.3:
                return P['terra'] if fbm(dc, 7, 2, 3) > -0.1 else P['terra2']
            if h < 0.013:
                return P['wet']
            if slope > 0.13:
                return P['dune3']
            return P['dune'] if fbm(dc, 5, 2, 8) > -0.15 else P['dune2']
        if h > -0.034:
            return P['sea_sand']
        if h > -0.08:
            return P['sea_mid']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    strata = [(0.026, 0.004), (0.05, 0.008), (0.075, 0.012), (0.1, 0.016), (0.13, 0.02), (0.42, 0.032)]
    p.make_plateau((P['build'], P['build2']), P['edge'],
                   [P['strata1'], P['strata2'], P['strata1'], P['strata3'], P['strata2'], P['strata2']], profile=strata, jit=0.006)
    p.build_bvh()
    rng = p.rng

    # oasis pond with palms
    disc(p.d('Oasis'), oasis_c, RW + 0.0145, 3.9 * DEG, P['oasis'], n=14, rng=rng)
    p.claim(oasis_c, 6.5 * DEG)
    p.count('Oase')
    for k in range(4):
        aa = TAU * k / 4 + 0.6
        e1 = outward(oasis_c)
        e2 = oasis_c.cross(e1)
        dd = (oasis_c + (e1 * math.cos(aa) + e2 * math.sin(aa)) * 5.4 * DEG).normalized()
        pr = p.probe(dd)
        pf_palm(p.d('Palms'), frame(pr['loc'] - pr['d'] * 0.004, pr['d'], rng.uniform(0, TAU)), rng, P['trunk'],
                [P['leaf'], P['leaf2']], h=rng.uniform(0.11, 0.15), lean=0.3)
        p.count('Oasenpalme')

    # wind-carved arches
    for (a, f, span, hh, rot) in ((60, -150, 0.3, 0.18, 0.25), (62, -40, 0.28, 0.17, -0.25)):
        d = dirs(a, f)
        pr = p.probe(d)
        M = basis(pr['loc'] - pr['d'] * 0.012, pr['d'], outward(pr['d'])) @ Rz(rot)
        pf_arch(p.d('RockArches'), M, rng, [P['terra'], P['terra3'], P['terra2']], span=span, height=hh, r0=0.07,
                r1=0.042, n=8, segs=14, jit=0.14, bands=True, sink=0.06)
        p.claim(d, 8 * DEG)
        p.count('Felsbogen')
    # hoodoos / mesa pillars with strata
    for (a, f, h, r) in ((47, 98, 0.12, 0.065), (60, 62, 0.1, 0.055), (62, 128, 0.1, 0.05), (72, -32, 0.08, 0.035),
                         (67, 200, 0.11, 0.045), (84, 160, 0.09, 0.04)):
        pr = p.probe(dirs(a, f))
        if not p.free(pr['d'], 2 * DEG):
            continue
        prof = [(r * 1.15, -0.05), (r * 1.1, h * 0.25), (r * 0.9, h * 0.5), (r * 1.05, h * 0.68), (r * 0.95, h * 0.85),
                (r * 1.0, h), (r * 0.4, h * 1.02)]
        v, f_ = lathe(prof, 7, rng.uniform(0, TAU), cap0=True, cap1=True, jit=0.08, rng=rng)
        bands = [P['terra'], P['terra3'], P['terra'], P['terra2'], P['terra3'], P['terra']]
        fm = [bands[k // 7] if k // 7 < len(bands) else P['terra3'] for k in range(len(f_))]
        p.d('Hoodoos').add(v, f_, fm, frame(pr['loc'] - pr['d'] * 0.01, pr['d'], 0.0))
        p.claim(pr['d'], 3 * DEG)
        p.count('Felssäule')
    # terracotta boulders
    for pr in p.scatter(14, lambda pr: pr['h'] > 0.0 and off_build(pr, 7), 2 * DEG, a=(30, 150)):
        s = rng.uniform(0.018, 0.04) * p.frontal(pr['d'], 0.6)
        pf_rock(p.d('Rocks'), frame(pr['loc'], place_up(p, pr, 0.5), rng.uniform(0, TAU), (s, s * 0.85, s)), rng,
                [P['terra'], P['terra2'], P['terra3']][rng.randrange(3)], jit=0.25, squash=0.75)
        p.count('Terrakottafels')

    p.meta.update(tagline="Die maritime Wüstenwelt",
                  features=["Flaches Sandsteinplateau mit geschichteten Felswänden",
                            "Windgeformte Dünenkämme, ausgewaschene helle Küsten",
                            "Zwei Felsbögen und Felssäulen aus Terrakotta",
                            "Türkisfarbene Oase mit vier Palmen"])
    p.finalize()
    return p


# ================================================================ 5 FROSTHARBOR
def frostharbor():
    p = Planet(5, "Frostharbor", "Frostharbor", 505)
    P = p.P
    P.add('water', '#1B4865', rough=0.05, alpha=0.82, spec=0.8, label='Dunkle Meeresbucht')
    P.add('sea_shallow', '#3D6E89', show=False)
    P.add('sea_deep', '#0C2236', label='Tiefsee')
    P.add('snow', '#F3F7FB', label='Schnee')
    P.add('snow2', '#E3ECF4', show=False)
    P.add('snow3', '#D2E1ED', show=False)
    P.add('ice', '#C7E3F2', label='Eisfläche')
    P.add('glacier', '#A2CFEA', label='Gletscher')
    P.add('glacier2', '#7DB6DD', show=False)
    P.add('turq', '#3FD6D9', rough=0.1, emit=0.7, label='Türkisakzent')
    P.add('build', '#9EA6AF', label='Steinplateau (Baufläche)')
    P.add('build2', '#969EA8', show=False)
    P.add('edge', '#747D88', label='Steinkante')
    P.add('stone', '#68727E', show=False)
    P.add('stone2', '#545E6A', label='Dunkler Fels')

    p.plat = Plateau(zp=1.04, rho0=0.5, var=0.06, seed=5.5)

    def stop(i, k, c):
        return P['snow'] if fbm(c, 6, 2, 3) > -0.15 else P['snow2']
    std_terraces(p, [dict(r=1.1, width=5.2, wvar=1.5, top=stop, rim=P['snow3'], cliffs=[P['stone'], P['stone2']], drop=0.09)])
    bays = [(-118, 0.2, 26), (-62, 0.17, 24), (172, 0.2, 22), (32, 0.16, 18), (-12, 0.12, 14)]

    def coast_a(phi):
        a = 74 + 9 * onz(phi, 1.4, 6) + 4 * onz(phi, 3.8, 1)
        for (bf, w, depth) in bays:
            a -= depth * math.exp(-(wrapd(phi - bf * DEG) / w) ** 2)
        return a * DEG

    def hfun(d):
        a, phi = ang(d)
        ca = coast_a(phi)
        wb = 4 * DEG
        hu = 0.03 + 0.016 * fbm(d, 4, 3, 2) + 0.05 * max(0.0, 1 - adist(d, dirs(60, 95)) / (25 * DEG)) ** 1.5
        h = coast_profile(a - (ca - wb), hu, wb, 4 * DEG, 9 * DEG, hs=-0.03, hd=-0.15)
        h = max(h, seabed(d, -0.15, 0.03, 6))
        for k, (c, r, hh) in enumerate(((dirs(120, -40), 14 * DEG, 0.05), (dirs(145, 120), 18 * DEG, 0.06))):
            h = max(h, mound(d, c, r, hh, 70 + k))
        return h

    def paint(dc, h, slope, c):
        if h > 0.004:
            if slope > 0.3:
                return P['stone2'] if fbm(dc, 8, 2, 1) > 0 else P['stone']
            if slope > 0.18 or h < 0.012:
                return P['ice']
            n = fbm(dc, 6, 3, 4)
            return P['snow3'] if n < -0.25 else P['snow2'] if n < 0.0 else P['snow']
        if h > -0.034:
            return P['sea_shallow']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['stone'], P['stone2'], P['stone2']])
    p.build_bvh()
    rng = p.rng
    gm = [P['glacier'], P['ice'], P['glacier2'], P['snow3']]

    # glacier walls: back and both sides
    clusters = [(48, 92, 9, 0.3), (52, 128, 7, 0.24), (53, 58, 7, 0.24), (60, 186, 6, 0.2), (61, -2, 6, 0.19), (76, 150, 5, 0.15)]
    for ci, (a, f, n, hmax) in enumerate(clusters):
        c = dirs(a, f)
        e1 = outward(c)
        e2 = c.cross(e1)
        for k in range(n):
            u = (k - (n - 1) / 2) / max(n - 1, 1)
            dd = (c + e2 * u * 0.2 + e1 * rng.uniform(-0.03, 0.04)).normalized()
            pr = p.probe(dd)
            hh = hmax * (1 - 0.55 * abs(u) * 2) * rng.uniform(0.75, 1.05)
            pf_shard(p.d('Glaciers'), frame(pr['loc'] - pr['d'] * 0.01, place_up(p, pr, 0.15), rng.uniform(0, TAU)), rng, gm,
                     h=hh, r=rng.uniform(0.035, 0.05))
        if ci in (0, 2, 3):
            pr = p.probe((c + e1 * 0.045).normalized())
            pf_shard(p.d('IceAccents'), frame(pr['loc'] - pr['d'] * 0.01, pr['d'], 0.4), rng, [P['turq'], P['glacier']],
                     h=hmax * 0.38, r=0.02, n=5)
        p.claim(c, 9 * DEG)
        p.count('Gletscher')
    # icebergs in the dark bays and the open sea
    for pr in p.scatter(12, lambda pr: pr['h'] < -0.02 and off_build(pr, 10), 3.5 * DEG, a=(35, 160)):
        s = p.frontal(pr['d'], 0.55)
        d = pr['d']
        pf_iceberg(p.d('Icebergs'), frame(d * (RW - 0.004), d, rng.uniform(0, TAU)), rng, P['ice'], P['snow'],
                   r=rng.uniform(0.03, 0.06) * s, h=rng.uniform(0.035, 0.07) * s)
        p.count('Eisberg')
    # meltwater pools – the turquoise accents on the snow
    pools = 0
    for pr in p.scatter(6, lambda pr: land(pr, 0.02) and pr['slope'] < 0.08 and off_build(pr, 9), 4 * DEG, a=(38, 110)):
        disc(p.d('IceAccents'), pr['d'], pr['loc'].length + 0.0025, rng.uniform(0.018, 0.028), P['turq'], n=9, rng=rng)
        pools += 1
        if pools >= 4:
            break
    p.count('Schmelzwasser-Pool', pools)
    for pr in p.scatter(10, lambda pr: land(pr, 0.006) and off_build(pr, 6), 2.2 * DEG, a=(30, 150)):
        s = rng.uniform(0.02, 0.04) * p.frontal(pr['d'], 0.6)
        pf_rock(p.d('Rocks'), frame(pr['loc'], place_up(p, pr, 0.4), rng.uniform(0, TAU), (s, s * 0.9, s)), rng, P['stone2'],
                jit=0.3, squash=0.8, mat2=P['snow'])
        p.count('Schneefels')

    p.meta.update(tagline="Der gefrorene Hafen",
                  features=["Solides graues Steinplateau unter einer verschneiten Terrasse",
                            "Fünf dunkle Meeresbuchten schneiden in die Eisküste",
                            "Facettierte Gletscherwände hinten und seitlich, Eisberge im Wasser",
                            "Wenige türkisfarbene Akzente: Schmelzwasser und Eiskristalle"])
    p.finalize()
    return p
