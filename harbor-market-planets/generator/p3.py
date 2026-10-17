"""Planets 6-10: Ember Shoal, Prismara, Sporehaven, Ringhaven, Abyssal Crown."""
import math
from mathutils import Vector, Matrix
from core import (TAU, DEG, RW, MB, Planet, Plateau, clamp, smooth, lerp, sph, ang, adist, dirs, nz, fbm, onz,
                  frame, basis, outward, ico, lathe, tube, ribbon, rock)
from prefabs import *  # noqa
from planets import (coast_profile, mound, seabed, std_terraces, place_up, land, off_build)
from p2 import strip, disc, ring_around, wrapd


def around(c, delta, theta):
    """Direction at angular distance delta from c, at bearing theta (0 = away from the top)."""
    e1 = outward(c)
    e2 = c.cross(e1)
    return (c * math.cos(delta) + (e1 * math.cos(theta) + e2 * math.sin(theta)) * math.sin(delta)).normalized()


def surface_path(p, dirs_, lift=0.003):
    pts, ups = [], []
    for d in dirs_:
        pr = p.probe(d)
        pts.append(pr['loc'] + pr['n'] * lift)
        ups.append(pr['n'])
    return pts, ups


# ================================================================ 6 EMBER SHOAL
def ember_shoal():
    p = Planet(6, "EmberShoal", "Ember Shoal", 606)
    P = p.P
    P.add('water', '#1E5462', rough=0.05, alpha=0.78, spec=0.8, label='Dunkles Meer')
    P.add('sea_shallow', '#3A393C', show=False)
    P.add('sea_deep', '#0F2730', label='Tiefsee')
    P.add('basalt', '#383438', label='Basalt')
    P.add('basalt2', '#423C3F', show=False)
    P.add('basalt3', '#4D4645', show=False)
    P.add('ash', '#615956', label='Asche')
    P.add('rust', '#9E4A2C', label='Rostrote Klippe')
    P.add('rust2', '#B65A33', show=False)
    P.add('lava', '#FF7A1C', emit=6.0, label='Lava')
    P.add('lava2', '#FFA53A', emit=7.0, show=False)
    P.add('ash2', '#7C716B', show=False)
    P.add('build', '#615A5B', label='Ruhiger Basalt (Baufläche)')
    P.add('build2', '#5B5455', show=False)
    P.add('edge', '#857A74', label='Aschekante')

    p.plat = Plateau(zp=1.04, rho0=0.5, var=0.06, seed=6.6)
    std_terraces(p, [dict(r=1.1, width=5.0, wvar=1.5, top=P['basalt3'], rim=P['edge'], cliffs=[P['rust'], P['rust2']], drop=0.09)])
    vol = dirs(56, -36)
    VR, VH, CR = 24 * DEG, 0.33, 5.0 * DEG

    def vol_h(d):
        dv = adist(d, vol)
        if dv > VR:
            return -1.0
        hv = VH * (1 - dv / VR) ** 1.35
        if dv < CR:
            rim = VH * (1 - CR / VR) ** 1.35
            hv = rim - 0.075 * (1 - (dv / CR) ** 2)
        return hv + 0.01 * fbm(d, 9, 2, 3)

    def coast_a(phi):
        return (62 + 9 * onz(phi, 1.6, 2) + 4 * onz(phi, 3.4, 7)) * DEG

    def hfun(d):
        a, phi = ang(d)
        ca = coast_a(phi)
        wb = 1.6 * DEG
        hu = 0.034 + 0.016 * fbm(d, 5, 3, 1)
        h = coast_profile(a - (ca - wb), hu, wb, 4 * DEG, 10 * DEG, hs=-0.03)
        h = max(h, seabed(d, -0.15, 0.04, 4))
        for k, (c, r, hh) in enumerate(((dirs(110, -30), 10 * DEG, 0.05), (dirs(128, 150), 13 * DEG, 0.06), (dirs(84, 120), 6 * DEG, 0.04),
                                        (dirs(86, -128), 6 * DEG, 0.04), (dirs(92, -64), 5 * DEG, 0.035))):
            h = max(h, mound(d, c, r, hh, 80 + k))
        return max(h, vol_h(d))

    def paint(dc, h, slope, c):
        dv = adist(dc, vol)
        if dv < CR * 0.85 and h < VH * (1 - CR / VR) ** 1.35 - 0.025:
            return P['lava']
        if h > 0.004:
            if dv < VR * 0.9 and h > 0.05:
                if dv < CR * 1.25 or slope > 0.4:
                    return P['rust']
                if h > 0.2:
                    return P['ash2']
                return P['ash'] if h > 0.11 or fbm(dc, 6, 2, 5) > 0.1 else P['basalt3']
            if slope > 0.28:
                return P['rust'] if fbm(dc, 6, 2, 1) > -0.2 else P['rust2']
            return P['basalt'] if fbm(dc, 3.5, 2, 9) > -0.1 else P['basalt2']
        if h > -0.034:
            return P['sea_shallow']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['basalt3'], P['rust'], P['rust']])
    p.build_bvh()
    rng = p.rng
    p.claim(vol, VR * 0.9)

    # glowing lava cracks running down the volcano's far flanks
    cracks = p.d('LavaCracks')
    for k, th0 in enumerate((-0.4, 0.35, 1.2, -1.3)):
        steps = 9 if k < 2 else 6
        ds = [around(vol, lerp(CR * 1.05, CR * 1.05 + (0.24 if k < 2 else 0.15), i / steps), th0 + 0.18 * math.sin(i * 1.7 + k)) for i in range(steps + 1)]
        pts, ups = surface_path(p, ds, 0.002)
        w = [0.0065 * (1 - 0.6 * i / steps) + 0.0015 for i in range(len(pts))]
        v, f = ribbon(pts, ups, w)
        cracks.add(v, f, P['lava'] if k % 2 else P['lava2'])
        p.count('Lavaspalte')
    # a calm lava pool in the crater
    rim = VH * (1 - CR / VR) ** 1.35
    disc(cracks, vol, RW + rim - 0.045, CR * 0.82, P['lava2'], n=10, rng=rng)
    # two small far-off cracks
    for (a, f) in ((78, 160), (84, -12)):
        c = dirs(a, f)
        ds = [around(c, 0.03 * i, 0.9 + 0.3 * math.sin(i)) for i in range(5)]
        pts, ups = surface_path(p, ds, 0.002)
        v, f_ = ribbon(pts, ups, 0.004)
        cracks.add(v, f_, P['lava'])
        p.claim(c, 3 * DEG)
        p.count('Lavaspalte')

    # basalt column clusters
    for (a, f, h, rings) in ((50, 150, 0.12, 2), (60, 118, 0.1, 2), (64, 192, 0.09, 2), (86, -128, 0.05, 1), (92, -64, 0.045, 1)):
        pr = p.probe(dirs(a, f))
        pf_columns(p.d('BasaltColumns'), frame(pr['loc'] - pr['d'] * 0.006, pr['d'], rng.uniform(0, TAU)), rng,
                   [P['basalt'], P['basalt2']], h=h, cell=0.021, rings=rings, tops=P['basalt3'])
        p.claim(pr['d'], 4 * DEG)
        p.count('Basaltsäulen')
    # sharp rocks, well outside the build area
    for pr in p.scatter(16, lambda pr: land(pr, 0.0) and off_build(pr, 9), 2.4 * DEG, a=(34, 150)):
        s = p.frontal(pr['d'], 0.45)
        pf_spike(p.d('SharpRocks'), frame(pr['loc'], place_up(p, pr, 0.3), rng.uniform(0, TAU)), rng,
                 P['basalt2'] if rng.random() < 0.6 else P['rust'], h=rng.uniform(0.06, 0.12) * s, r=rng.uniform(0.02, 0.03) * s)
        p.count('Felsspitze')

    p.meta.update(tagline="Die Vulkaninsel",
                  features=["Großzügige, ruhige Basaltfläche mit heller Aschekante",
                            "Vulkan mit Lavasee auf der hinteren rechten Seite",
                            "Sparsame Lavaspalten, rostrote Klippen an Terrasse und Küste",
                            "Basaltsäulen und scharfe Felsspitzen weit außerhalb des Bauplatzes"])
    p.finalize()
    return p


# ================================================================ 7 PRISMARA
def prismara():
    p = Planet(7, "Prismara", "Prismara", 707)
    P = p.P
    P.add('water', '#4253C4', rough=0.05, alpha=0.6, spec=0.8, label='Blauviolettes Meer')
    P.add('sea_sand', '#BEB0EA', show=False)
    P.add('sea_mid', '#5656BE', show=False)
    P.add('sea_deep', '#24287A', label='Tiefsee')
    P.add('violet', '#6E4DAA', label='Violette Küste')
    P.add('violet2', '#8A66C8', show=False)
    P.add('blue', '#4259BC', label='Blaue Küste')
    P.add('blue2', '#5C7AD8', show=False)
    P.add('shore', '#CBBCEE', show=False)
    P.add('crystal', '#3FE6D6', rough=0.04, emit=0.9, emit_hex='#22CDBF', spec=0.9, label='Türkiskristall')
    P.add('crystal2', '#A8F8EF', rough=0.04, emit=1.3, spec=0.9, label='Kristallspitze')
    P.add('crystal3', '#1FB2BC', rough=0.05, emit=0.5, spec=0.9, show=False)
    P.add('build', '#EAE5F5', label='Mineralfläche (Baufläche)')
    P.add('build2', '#E2DCF0', show=False)
    P.add('edge', '#BFB3DD', label='Mineralkante')
    P.add('terr', '#A08BD3', show=False)

    p.plat = Plateau(zp=1.035, rho0=0.5, var=0.05, seed=7.7, poly=6, polyamt=0.3, phase=0.2)

    def ttop(i, k, c):
        return P['terr'] if fbm(c, 5, 2, 2) > -0.05 else P['violet2']

    def tcliff(i, k, c=None):
        return P['violet'] if onz(TAU * i / 160, 2.2, 3) > -0.1 else P['blue']
    std_terraces(p, [dict(r=1.096, width=5.4, wvar=1.5, top=ttop, rim=P['edge'], cliffs=[tcliff, tcliff], drop=0.088)])
    isl = [(dirs(a, f), r * DEG, h) for a, f, r, h in ((60, 128, 7, 0.05), (62, 52, 7, 0.05), (70, -6, 6, 0.04), (70, 188, 6, 0.04),
                                                       (96, -118, 7, 0.035), (110, 40, 9, 0.04), (138, 170, 11, 0.05),
                                                       (78, -48, 5, 0.035), (84, -146, 6, 0.04), (100, -80, 5, 0.03))]

    def hfun(d):
        a, phi = ang(d)
        x = a - p.outer_alpha(phi)
        h = coast_profile(x, 0.064, (8 + 2.5 * onz(phi, 1.8, 3)) * DEG, 7 * DEG, 11 * DEG)
        h += 0.01 * fbm(d, 7, 2, 6) * smooth(0, 0.04, h)
        h = max(h, seabed(d, -0.14, 0.035, 7))
        for k, (c, r, hh) in enumerate(isl):
            h = max(h, mound(d, c, r, hh, 90 + k, wobble=0.35))
        return h

    def paint(dc, h, slope, c):
        if h > 0.004:
            if h < 0.012 and slope < 0.2:
                return P['shore']
            n = fbm(dc, 4.5, 3, 5)
            if slope > 0.24:
                return P['violet'] if n > 0 else P['blue']
            return P['violet2'] if n > 0.05 else P['blue2']
        if h > -0.034:
            return P['sea_sand']
        if h > -0.08:
            return P['sea_mid']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['violet'], P['blue'], P['blue']])
    p.build_bvh()
    rng = p.rng
    cm = (P['crystal'], P['crystal2'])

    # small crystals framing the build area
    for k, pr in enumerate(ring_around(p, 30, 1.3, 3.4)):
        s = p.frontal(pr['d'], 0.6)
        up = (pr['d'] + outward(pr['d']) * rng.uniform(0.15, 0.45)).normalized()
        if k % 3 == 0:
            pf_crystal_cluster(p.d('CrystalsSmall'), frame(pr['loc'] - pr['d'] * 0.004, up, rng.uniform(0, TAU)), rng,
                               P['crystal3'], P['crystal2'], h=rng.uniform(0.035, 0.05) * s, count=3)
        else:
            pf_crystal(p.d('CrystalsSmall'), frame(pr['loc'] - pr['d'] * 0.004, up, rng.uniform(0, TAU)), rng, *cm,
                       h=rng.uniform(0.024, 0.045) * s)
        p.claim(pr['d'], 0.7 * DEG)
        p.count('Kleiner Kristall')
    # big clusters back and sides
    for (a, f, h, n) in ((47, 126, 0.29, 7), (49, 56, 0.25, 6), (61, 188, 0.22, 6), (64, -7, 0.2, 6), (74, 152, 0.15, 5)):
        pr = p.probe(dirs(a, f))
        pf_crystal_cluster(p.d('CrystalsLarge'), frame(pr['loc'] - pr['d'] * 0.01, place_up(p, pr, 0.2), rng.uniform(0, TAU)),
                           rng, *cm, h=h, count=n, spread=0.55)
        p.claim(pr['d'], 6 * DEG)
        p.count('Großer Kristall')
    # medium clusters along coasts and on islets
    for pr in p.scatter(10, lambda pr: pr['h'] > -0.025 and off_build(pr, 11), 3.2 * DEG, a=(36, 150)):
        s = p.frontal(pr['d'], 0.45)
        pf_crystal_cluster(p.d('CrystalsMedium'), frame(pr['loc'] - pr['d'] * 0.006, place_up(p, pr, 0.3), rng.uniform(0, TAU)),
                           rng, *cm, h=rng.uniform(0.09, 0.14) * s, count=rng.randint(3, 5))
        p.count('Mittlerer Kristall')
    # submerged crystals glowing through the lagoon
    for pr in p.scatter(10, lambda pr: -0.032 < pr['h'] < -0.008 and off_build(pr, 8), 2 * DEG, a=(30, 120)):
        pf_crystal_cluster(p.d('CrystalsLagoon'), frame(pr['loc'], pr['d'], rng.uniform(0, TAU)), rng, P['crystal3'], P['crystal'],
                           h=rng.uniform(0.04, 0.06), count=3)
        p.count('Lagunenkristall')

    p.meta.update(tagline="Der Kristallozean",
                  features=["Helle, flache Mineralfläche mit leicht facettiertem Umriss",
                            "Rahmen aus 30 kleinen Türkiskristallen rund um den Bauplatz",
                            "Fünf große Kristallgruppen hinten und seitlich",
                            "Zweifarbige Küsten in Violett und Blau, leuchtende Kristalle in der Lagune"])
    p.finalize()
    return p


# ================================================================ 8 SPOREHAVEN
def sporehaven():
    p = Planet(8, "Sporehaven", "Sporehaven", 808)
    P = p.P
    P.add('water', '#167884', rough=0.05, alpha=0.66, spec=0.8, label='Petrolmeer')
    P.add('sea_shallow', '#3A9A96', show=False)
    P.add('sea_deep', '#0E3D48', label='Tiefsee')
    P.add('moss', '#246A6F', label='Petrolboden')
    P.add('moss2', '#2A7376', show=False)
    P.add('moss3', '#1F5D62', show=False)
    P.add('moss_light', '#34827F', show=False)
    P.add('build', '#80B6A9', label='Moos-Lichtung (Baufläche)')
    P.add('build2', '#79AFA2', show=False)
    P.add('edge', '#ABD5C8', label='Heller Moosrand')
    P.add('root', '#604B46', label='Wurzeln')
    P.add('root2', '#4B3A37', show=False)
    P.add('stem', '#EBE0CC', label='Pilzstiel')
    P.add('cap_v', '#9065CD', label='Kappe Violett')
    P.add('cap_r', '#E3728F', label='Kappe Rosé')
    P.add('cap_a', '#E8A45A', label='Kappe Bernstein')
    P.add('gill', '#F4BDCC', show=False)
    P.add('gill2', '#DBC8F1', show=False)
    P.add('spot', '#F7ECDD', show=False)
    P.add('glow', '#58F5D3', emit=5.0, label='Leuchtpunkte')
    P.add('glow2', '#7FE3FF', emit=4.0, show=False)
    P.add('cliff', '#1C4F55', show=False)

    p.plat = Plateau(zp=1.035, rho0=0.5, var=0.07, seed=8.8)

    def mtop(i, k, c):
        return P['moss2'] if fbm(c, 5, 2, 2) > -0.1 else P['moss']
    std_terraces(p, [dict(r=1.096, width=6.2, wvar=1.6, top=mtop, rim=P['moss_light'], cliffs=[P['root'], P['cliff']], drop=0.086)])
    seas = [(dirs(92, -150), 14 * DEG), (dirs(86, -38), 11 * DEG), (dirs(70, 165), 8 * DEG), (dirs(112, 30), 22 * DEG),
            (dirs(140, -150), 20 * DEG), (dirs(104, -95), 8 * DEG)]

    def hfun(d):
        a, phi = ang(d)
        x = a - p.outer_alpha(phi)
        h = 0.03 + 0.02 * fbm(d, 3.5, 3, 4) + 0.035 * max(0.0, 1 - adist(d, dirs(55, 92)) / (22 * DEG)) ** 1.4
        for c, r in seas:
            dn = adist(d, c) / r * (1 + 0.25 * fbm(d, 3, 2, 3))
            if dn < 1.4:
                sea = -0.004 - 0.12 * smooth(1.0, 0.4, dn)
                h = lerp(sea, h, smooth(1.0, 1.35, dn))
        return h

    def paint(dc, h, slope, c):
        if h > 0.004:
            if slope > 0.28:
                return P['moss3']
            n = fbm(dc, 3.5, 3, 1)
            if n > 0.3:
                return P['moss_light']
            return P['moss2'] if n > 0.02 else P['moss'] if n > -0.3 else P['moss3']
        if h > -0.034:
            return P['sea_shallow']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['root'], P['cliff'], P['cliff']])
    p.build_bvh()
    rng = p.rng
    caps = [(P['cap_v'], P['gill2']), (P['cap_r'], P['gill']), (P['cap_a'], P['gill'])]

    def shroom(cat, pr, h, R=None, style=None, glowing=True):
        cap, gill = caps[rng.randrange(3)]
        st = style or ['dome', 'flat', 'bell'][rng.randrange(3)]
        up = (pr['d'] + outward(pr['d']) * rng.uniform(0.0, 0.25)).normalized()
        pf_mushroom(p.d(cat), frame(pr['loc'] - pr['d'] * 0.004, up, rng.uniform(0, TAU)), rng, cap, gill, P['stem'],
                    glow=P['glow'] if glowing else None, spot=P['spot'], h=h, R=R, bend=rng.uniform(0.1, 0.3), style=st)

    # roots arching around the clearing (never on it)
    for i in range(14):
        phi0 = TAU * (i + rng.uniform(-0.2, 0.2)) / 14
        a0 = p.plat.alpha(phi0) + 0.8 * DEG
        phi1 = phi0 + rng.uniform(0.25, 0.4) * (1 if i % 2 else -1)
        a1 = p.plat.alpha(phi1) + rng.uniform(3.0, 5.0) * DEG
        pts = []
        m = 9
        for k in range(m + 1):
            t = k / m
            d = sph(lerp(a0, a1, t), lerp(phi0, phi1, t))
            pr = p.probe(d)
            lift = 0.022 * math.sin(math.pi * min(1.0, t * 1.15)) * (1 if t < 0.87 else 0.2)
            pts.append(pr['loc'] + pr['d'] * (lift - 0.004 * (1 - math.sin(math.pi * t))))
        rad = [lerp(0.0085, 0.0028, k / m) for k in range(m + 1)]
        v, f = tube(pts, rad, 5, cap0=True, cap1=True, jit=0.1, rng=rng)
        p.d('Roots').add(v, f, P['root'] if i % 3 else P['root2'])
        p.count('Wurzel')
    # big mushrooms at the back, mid-size at the sides
    for (a, f, h, R) in ((41, 92, 0.24, 0.15), (46, 132, 0.21, 0.13), (45, 52, 0.22, 0.13), (56, 165, 0.18, 0.11), (55, 16, 0.18, 0.11),
                         (66, -150, 0.12, 0.08), (67, -32, 0.12, 0.08)):
        pr = p.probe(dirs(a, f))
        shroom('MushroomsLarge', pr, h, R)
        # roots spreading from the foot
        for k in range(3):
            th = TAU * k / 3 + rng.uniform(-0.3, 0.3)
            ds = [around(pr['d'], 0.004 + 0.012 * i, th) for i in range(5)]
            pts = [p.probe(dd)['loc'] + dd * (0.012 * math.sin(math.pi * i / 4) - 0.002) for i, dd in enumerate(ds)]
            v, f_ = tube(pts, [0.012, 0.009, 0.006, 0.004, 0.002], 5, jit=0.1, rng=rng)
            p.d('Roots').add(v, f_, P['root'])
        for k in range(5):
            th = TAU * k / 5 + rng.uniform(-0.4, 0.4)
            dd = around(pr['d'], rng.uniform(3.2, 5.5) * DEG, th)
            if p.plat.margin(dd) < 2.0 * DEG:
                continue
            q = p.probe(dd)
            if q and q['h'] > 0.006:
                shroom('MushroomsMedium', q, rng.uniform(0.07, 0.12) * (h / 0.24), R=None)
                p.count('Mittlerer Pilz')
        p.claim(pr['d'], 6.5 * DEG)
        p.count('Großer Pilz')
    for pr in p.scatter(22, lambda pr: land(pr, 0.008) and off_build(pr, 7) and (pr['front'] < 0.25 or pr['a'] > 52 * DEG), 2.6 * DEG, a=(36, 140)):
        shroom('MushroomsMedium', pr, rng.uniform(0.07, 0.11) * p.frontal(pr['d'], 0.75))
        p.count('Mittlerer Pilz')
    for pr in p.scatter(40, lambda pr: land(pr, 0.006) and off_build(pr, 1.6), 1.3 * DEG, a=(27, 150)):
        shroom('MushroomsSmall', pr, rng.uniform(0.045, 0.075) * p.frontal(pr['d'], 0.8), glowing=rng.random() < 0.5)
        p.count('Kleiner Pilz')
    # blue-green glow dots on the ground
    for pr in p.scatter(48, lambda pr: land(pr, 0.004) and off_build(pr, 1.2), 0.9 * DEG, a=(27, 160), claim=False):
        vv, ff = ico(1)
        s = rng.uniform(0.0035, 0.0065)
        p.d('GlowDots').add(vv, ff, P['glow'] if rng.random() < 0.7 else P['glow2'], frame(pr['loc'] + pr['d'] * s * 0.4, pr['d'], 0, s))
    p.count('Leuchtpunkt', 48)

    p.meta.update(tagline="Die leuchtende Pilzwelt",
                  features=["Offene, helle Moos-Lichtung als Baufläche",
                            "Wurzelbögen ausschließlich rund um die Lichtung",
                            "Pilze in drei Formen mit sichtbaren Lamellen, groß hinten, klein vorne",
                            "Blaugrüne Leuchtpunkte auf Kappen und Boden, kleine Petrolmeere"])
    p.finalize()
    return p


# ================================================================ 9 RINGHAVEN
def ringhaven():
    p = Planet(9, "Ringhaven", "Ringhaven", 909)
    P = p.P
    P.add('water', '#2D6DA3', rough=0.05, alpha=0.7, spec=0.8, label='Kleines Meer')
    P.add('sea_shallow', '#5884A4', show=False)
    P.add('sea_deep', '#1B3854', label='Tiefes Wasser')
    P.add('rock', '#72869B', label='Graublauer Fels')
    P.add('rock2', '#66798E', show=False)
    P.add('rock3', '#8A9DB0', show=False)
    P.add('rock4', '#4F5F72', show=False)
    P.add('build', '#B1BECB', label='Felsplateau (Baufläche)')
    P.add('build2', '#A9B6C3', show=False)
    P.add('edge', '#C8D0D8', metal=0.85, rough=0.32, label='Metallkante')
    P.add('metal', '#B9C3CC', metal=0.9, rough=0.3, label='Dock-Metall')
    P.add('metal_dark', '#5E6873', metal=0.75, rough=0.45, show=False)
    P.add('deck', '#4D5966', show=False)
    P.add('light', '#FFD47E', emit=6.0, label='Signallicht')
    P.add('ring1', '#E2C99C', label='Ring Sand')
    P.add('ring2', '#B88E62', label='Ring Bronze')
    P.add('ring3', '#F1E6CF', show=False)
    P.add('ring4', '#9A7A58', show=False)

    p.plat = Plateau(zp=1.04, rho0=0.5, var=0.06, seed=9.9)
    std_terraces(p, [dict(r=1.1, width=5.0, wvar=1.5, top=P['rock3'], rim=P['rock'], cliffs=[P['rock2'], P['rock4']], drop=0.09)])
    seas = [(dirs(60, -50), 13 * DEG), (dirs(62, 150), 11 * DEG), (dirs(108, -120), 18 * DEG), (dirs(125, 40), 20 * DEG),
            (dirs(84, 96), 9 * DEG), (dirs(160, 0), 12 * DEG)]

    def hfun(d):
        a, phi = ang(d)
        h = 0.035 + 0.03 * fbm(d, 3.2, 3, 4) + 0.018 * abs(fbm(d, 7, 2, 1))
        h += 0.05 * max(0.0, 1 - adist(d, dirs(56, 100)) / (20 * DEG)) ** 1.5
        for c, r in seas:
            dn = adist(d, c) / r * (1 + 0.22 * fbm(d, 3, 2, 5))
            if dn < 1.4:
                sea = -0.004 - 0.12 * smooth(1.0, 0.45, dn)
                h = lerp(sea, h, smooth(1.0, 1.28, dn))
        return h

    def paint(dc, h, slope, c):
        if h > 0.004:
            if slope > 0.3:
                return P['rock4']
            if slope > 0.18:
                return P['rock2']
            if h < 0.014:
                return P['rock3']
            return P['rock'] if fbm(dc, 3, 3, 2) > -0.2 else P['rock2']
        if h > -0.034:
            return P['sea_shallow']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['rock'], P['rock2'], P['rock4']])
    p.build_bvh()
    rng = p.rng

    # tilted planetary ring: front dips down, back rises, so it never crosses the build area
    tilt = Matrix.Rotation(0.27, 4, 'X') @ Matrix.Rotation(0.3, 4, 'Y')
    pf_ring(p.d('Ring'), [(1.22, 1.28, 0.014, P['ring3']), (1.29, 1.38, 0.018, P['ring1']), (1.39, 1.44, 0.014, P['ring2']),
                          (1.452, 1.482, 0.01, P['ring4'])], tilt=tilt, rng=rng)
    p.count('Planetenring')
    # docks in the two upper seas
    for (fdeg, L) in ((-50, 0.21), (150, 0.16)):
        phi = fdeg * DEG
        res = p.coast(phi, p.outer_alpha(phi) + 0.01)
        if not res:
            continue
        a_c, loc, _ = res
        d0 = sph(a_c - 0.012, phi)
        M = basis(d0 * (RW + 0.012), d0, outward(d0))
        pf_dock(p.d('Docks'), M, rng, P['deck'], P['metal'], P['metal_dark'], P['light'], length=L * 1.15, width=0.06)
        p.claim(sph(a_c + 0.05, phi), 6 * DEG)
        p.count('Dock')
        if fdeg == -50:
            q = p.probe(sph(a_c - 0.05, phi + 0.09))
            pf_crane(p.d('Docks'), frame(q['loc'] - q['d'] * 0.003, q['d'], phi + math.pi * 0.6), P['metal'], P['metal_dark'], P['ring2'], h=0.15)
            p.claim(q['d'], 3 * DEG)
            p.count('Dockkran')
    # signal beacons on the hills
    for (a, f) in ((50, 100), (58, 170), (60, 15)):
        pr = p.probe(dirs(a, f))
        pf_beacon(p.d('Beacons'), frame(pr['loc'], pr['d'], 0.0), P['metal'], P['light'], h=0.075)
        p.claim(pr['d'], 2.5 * DEG)
        p.count('Signalmast')
    # rock spires at the back, angular boulders around
    for pr in p.scatter(7, lambda pr: land(pr, 0.02) and off_build(pr, 9), 3.5 * DEG, a=(40, 75), phis=[(40, 170)]):
        pf_spike(p.d('RockSpires'), frame(pr['loc'], pr['d'], rng.uniform(0, TAU)), rng, P['rock2'] if rng.random() < 0.5 else P['rock4'],
                 h=rng.uniform(0.1, 0.16), r=rng.uniform(0.025, 0.035), n=5, lean=0.15)
        p.count('Felsnadel')
    for pr in p.scatter(14, lambda pr: land(pr, 0.004) and off_build(pr, 7), 2.2 * DEG, a=(30, 160)):
        s = rng.uniform(0.02, 0.04) * p.frontal(pr['d'], 0.6)
        pf_rock(p.d('Rocks'), frame(pr['loc'], place_up(p, pr, 0.5), rng.uniform(0, TAU), (s, s * 0.9, s)), rng,
                [P['rock'], P['rock2'], P['rock3']][rng.randrange(3)], sub=1, jit=0.32, squash=0.75)
        p.count('Felsbrocken')

    p.meta.update(tagline="Der kosmische Handelshafen",
                  features=["Großes, helles Felsplateau mit dezenter Metallkante",
                            "Schräger Planetenring in Sand- und Bronzetönen, vorne abgesenkt",
                            "Zwei Metalldocks mit Signallichtern und einem kleinen Kran",
                            "Kleine Meere, Felsnadeln und Signalmasten auf den Hügeln"])
    p.finalize()
    return p


# ================================================================ 10 ABYSSAL CROWN
def abyssal_crown():
    p = Planet(10, "AbyssalCrown", "Abyssal Crown", 1010)
    P = p.P
    P.add('water', '#0E1430', rough=0.04, alpha=0.74, spec=0.9, label='Fast schwarzes Wasser')
    P.add('sea_shallow', '#3B2C6E', show=False)
    P.add('sea_mid', '#1E1840', show=False)
    P.add('sea_deep', '#07080F', show=False)
    P.add('rock', '#57407F', label='Violetter Fels')
    P.add('rock2', '#6A4E9E', show=False)
    P.add('rock3', '#3B2B5A', show=False)
    P.add('shore', '#7A66A6', show=False)
    P.add('tent', '#6D4C99', label='Tentakelbogen')
    P.add('tent_under', '#9479C2', show=False)
    P.add('build', '#3E3858', label='Dunkler Boden (Baufläche)')
    P.add('build2', '#3A3453', show=False)
    P.add('pearl', '#EFE9F6', rough=0.15, spec=0.9, coat=1.0, label='Perlmuttkante')
    P.add('pearl2', '#DAD1EF', rough=0.2, spec=0.9, coat=1.0, show=False)
    P.add('glow', '#4CF2E2', emit=4.5, label='Biolumineszenz Cyan')
    P.add('glow2', '#C77BFF', emit=3.5, label='Biolumineszenz Violett')

    p.plat = Plateau(zp=1.035, rho0=0.5, var=0.06, seed=10.1)
    std_terraces(p, [dict(r=1.096, width=5.2, wvar=1.6, top=P['rock3'], rim=P['pearl2'], cliffs=[P['rock'], P['rock3']], drop=0.088)])
    isl = [(dirs(a, f), r * DEG, h) for a, f, r, h in ((66, 120, 7, 0.05), (64, 40, 6, 0.045), (78, -150, 7, 0.045), (104, 10, 9, 0.05),
                                                       (130, -90, 12, 0.05), (122, 150, 9, 0.045), (82, -40, 7, 0.045),
                                                       (98, -105, 6, 0.04), (72, 196, 6, 0.04))]

    def hfun(d):
        a, phi = ang(d)
        x = a - p.outer_alpha(phi)
        h = coast_profile(x, 0.064, (13 + 4 * onz(phi, 1.7, 8)) * DEG, 9 * DEG, 12 * DEG, hs=-0.03, hd=-0.16)
        h += 0.012 * fbm(d, 6, 2, 3) * smooth(0, 0.04, h)
        h = max(h, seabed(d, -0.16, 0.04, 8))
        for k, (c, r, hh) in enumerate(isl):
            h = max(h, mound(d, c, r, hh, 110 + k, wobble=0.4))
        return h

    def paint(dc, h, slope, c):
        if h > 0.004:
            if slope > 0.26:
                return P['rock3']
            if h < 0.012:
                return P['shore']
            return P['rock2'] if fbm(dc, 5, 3, 2) > 0.05 else P['rock']
        if h > -0.034:
            return P['sea_shallow']
        if h > -0.08:
            return P['sea_mid']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['pearl'], [P['rock'], P['rock3'], P['rock3']])
    p.build_bvh()
    rng = p.rng

    # tentacle-like arches around the back half: root on land, curling tip in the dark water
    for (fdeg, span, hh) in ((-158, 0.27, 0.16), (-122, 0.24, 0.14), (-62, 0.24, 0.14), (-24, 0.27, 0.16), (95, 0.3, 0.2)):
        phi = fdeg * DEG
        res = p.coast(phi, p.outer_alpha(phi) + 0.01)
        a_c = res[0] if res else p.outer_alpha(phi) + 10 * DEG
        d = sph(a_c + 0.02, phi)
        M = basis(d * (RW - 0.004), d, outward(d))
        M = M @ Rz(rng.uniform(-0.6, 0.6))
        pf_tentacle(p.d('TentacleArches'), M, rng, P['tent'], under=P['tent_under'], dots=P['glow'], span=span,
                    r0=0.05, r1=0.009, a=1.15, b=3.6, height=hh)
        p.claim(d, 6 * DEG)
        p.count('Tentakelbogen')
    # giant clams with pearls on the beach
    for (fdeg, s) in ((-150, 0.075), (205, 0.0)):
        if s <= 0:
            continue
        phi = fdeg * DEG
        pr = p.probe(sph(p.outer_alpha(phi) + 3.5 * DEG, phi))
        M = frame(pr['loc'] - pr['d'] * 0.004, place_up(p, pr, 0.4), rng.uniform(0, TAU))
        pf_shell(p.d('Clams'), M @ Ry(-0.25), rng, P['rock2'], P['tent_under'], s=s)
        vv, ff = ico(2)
        p.d('Clams').add(vv, ff, P['pearl'], M @ T(s * 0.35, 0, s * 0.42) @ S(s * 0.16))
        p.claim(pr['d'], 3 * DEG)
        p.count('Riesenmuschel mit Perle')
    # pearl beads along the terrace just outside the build rim
    for i in range(36):
        phi = TAU * i / 36
        pr = p.probe(sph(p.plat.alpha(phi) + 0.9 * DEG, phi))
        vv, ff = ico(1)
        p.d('PearlBeads').add(vv, ff, P['pearl'], frame(pr['loc'] + pr['d'] * 0.002, pr['d'], 0, 0.0055))
    p.count('Perle', 36)
    # slim spires with glowing tips
    for pr in p.scatter(7, lambda pr: land(pr, 0.012) and off_build(pr, 8), 3.5 * DEG, a=(36, 110), phis=[(-20, 200)]):
        h = rng.uniform(0.1, 0.17) * p.frontal(pr['d'], 0.45)
        M = frame(pr['loc'], pr['d'], rng.uniform(0, TAU))
        pf_spike(p.d('Spires'), M, rng, P['rock2'], h=h, r=0.022, n=5, lean=0.3)
        p.count('Felsnadel')
    # rocks + sparse bioluminescence
    for pr in p.scatter(12, lambda pr: land(pr, 0.004) and off_build(pr, 6), 2.2 * DEG, a=(30, 160)):
        s = rng.uniform(0.02, 0.04) * p.frontal(pr['d'], 0.6)
        pf_rock(p.d('Rocks'), frame(pr['loc'], place_up(p, pr, 0.5), rng.uniform(0, TAU), (s, s * 0.9, s)), rng,
                [P['rock'], P['rock2'], P['rock3']][rng.randrange(3)], jit=0.28, squash=0.8)
        p.count('Fels')
    n = 0
    for pr in p.scatter(34, lambda pr: pr['h'] > -0.004 and off_build(pr, 2.5), 1.1 * DEG, a=(28, 165), claim=False):
        vv, ff = ico(1)
        s = rng.uniform(0.0035, 0.007)
        p.d('Bioluminescence').add(vv, ff, P['glow'] if rng.random() < 0.72 else P['glow2'], frame(pr['loc'] + pr['d'] * s * 0.3, pr['d'], 0, s))
        n += 1
    # drifting plankton lights on the dark water
    for pr in p.scatter(22, lambda pr: pr['h'] < -0.01 and off_build(pr, 10), 2.5 * DEG, a=(40, 150), claim=False):
        vv, ff = ico(1)
        s = rng.uniform(0.003, 0.0055)
        p.d('Bioluminescence').add(vv, ff, P['glow'] if rng.random() < 0.6 else P['glow2'], frame(pr['d'] * (RW + 0.002), pr['d'], 0, s))
        n += 1
    p.count('Leuchtpunkt', n)

    p.meta.update(tagline="Die geheimnisvolle Tiefseewelt",
                  features=["Dunkle, gut lesbare Baufläche mit hellen Perlmuttkanten",
                            "Fünf geschwungene Felsbögen mit Tentakel-Anmutung",
                            "Fast schwarzes Wasser, violette Felsküsten",
                            "Zurückhaltende Biolumineszenz in Cyan und Violett, Perlen am Terrassenrand"])
    p.finalize()
    return p
