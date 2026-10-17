"""The ten Harbor Market planets."""
import math
from mathutils import Vector, Matrix
from core import (TAU, DEG, RW, MB, Planet, Plateau, clamp, smooth, lerp, sph, ang, adist, dirs, nz, fbm, onz,
                  frame, basis, outward, ico, lathe, tube, ribbon, rock)
from prefabs import *  # noqa


# ---------------------------------------------------------------- shared helpers
def coast_profile(x, hu, wb, ws, wd, hs=-0.028, hd=-0.14):
    """Elevation beyond an island edge: beach -> shallow shelf -> deep sea."""
    if x <= 0:
        return hu
    if x < wb:
        return hu * (1 - smooth(0, 1, x / wb))
    x -= wb
    if x < ws:
        return hs * smooth(0, 1, x / ws)
    x -= ws
    return hs + (hd - hs) * smooth(0, 1, x / wd)


def mound(d, c, rad, h, seed, shelf=-0.03, deep=-0.14, wobble=0.3):
    """Island bump around direction c: dome above water, shallow shelf, then deep."""
    dl = adist(d, c) / rad
    dl *= 1 + wobble * fbm(d, 3.0, 3, seed)
    if dl < 1:
        return h * (1 - dl * dl) ** 0.8
    return shelf * smooth(1, 1.45, dl) + (deep - shelf) * smooth(1.45, 2.6, dl)


def seabed(d, base=-0.14, amp=0.035, seed=0.0):
    return base + amp * fbm(d, 2.2, 3, seed)


def std_terraces(p, specs, n=160):
    """specs: list of dict(r, width(deg), wvar, top, rim, cliffs, drop, bev, mid)."""
    mb = MB()
    prev_out = p.plat.alpha
    for k, s in enumerate(specs):
        w, wv, seed = s['width'] * DEG, s.get('wvar', 1.6) * DEG, s.get('seed', 3.0 + k)
        prev = prev_out

        def a_in(phi, prev=prev, k=k):
            return prev(phi) - (0.026 if k == 0 else 0.03)

        def a_out(phi, prev=prev, w=w, wv=wv, seed=seed):
            return prev(phi) + w + wv * (0.7 * onz(phi, 1.4, seed) + 0.3 * onz(phi, 3.1, seed + 2))

        p.make_terrace(mb, s['r'], a_in, a_out, s['top'], s['rim'], s['cliffs'], bev=s.get('bev', 0.012),
                       drop=s.get('drop', 0.085), n=n, mid=s.get('mid', 2), jit=s.get('jit', 0.006))
        prev_out = a_out
    p.finish_terraces(mb)


def place_up(p, pr, tilt=0.0):
    up = (pr['d'] * (1 - tilt) + pr['n'] * tilt).normalized()
    return up


def near_plateau_ring(p, lo, hi):
    """Predicate: angular margin from plateau edge within [lo, hi] degrees."""
    return lambda pr: lo * DEG <= pr['pm'] <= hi * DEG


def on_terrace_top(p, idx, inset=0.6):
    r_top, a_out, _ = p.terr[idx]
    def pred(pr):
        a, phi = pr['a'], pr['phi']
        a_in = p.plat.alpha(phi) if idx == 0 else p.terr[idx - 1][1](phi)
        return (a_in + inset * DEG < a < a_out(phi) - inset * DEG) and abs(pr['loc'].length - r_top) < 0.006
    return pred


def land(pr, lo=0.006):
    return pr['h'] > lo


def off_build(pr, m=1.0):
    return pr['pm'] > m * DEG


# ================================================================ 1 PELAGIA
def pelagia():
    p = Planet(1, "Pelagia", "Pelagia", 101)
    P = p.P
    P.add('water', '#3CC6CB', rough=0.08, alpha=0.66, spec=0.7, label='Lagunenwasser')
    P.add('sea_sand', '#F0E2BE', label='Flachwasser-Sand', show=False)
    P.add('sea_mid', '#4DB7BE', label='Riffkante', show=False)
    P.add('sea_deep', '#147894', label='Tiefsee')
    P.add('sand', '#F4E4C1', label='Cremesand')
    P.add('sand2', '#EBD6AE', label='Sand, schattiert', show=False)
    P.add('build', '#EBC596', label='Sandstein (Baufläche)')
    P.add('build2', '#E5BD8C', show=False)
    P.add('edge', '#C99868', label='Sandsteinkante')
    P.add('terr', '#EAD3A6', label='Terrassenstein', show=False)
    P.add('cliff', '#CDA97E', show=False)
    P.add('cliff2', '#BF9A70', show=False)
    P.add('rock', '#A9A097', label='Sanfter Fels')
    P.add('rock2', '#928980', show=False)
    P.add('trunk', '#9B6B45', label='Palmstamm', show=False)
    P.add('leaf', '#4FB060', label='Palmblatt')
    P.add('leaf2', '#3E9A55', show=False)
    P.add('wood', '#93613E', label='Holzsteg')
    P.add('wood_dark', '#6C4630', show=False)
    P.add('lh_white', '#F5F1E8', label='Leuchtturm', show=False)
    P.add('lh_red', '#D8574F', label='Leuchtturm-Rot')
    P.add('lamp', '#FFE6A3', emit=5.0, label='Leuchtfeuer')
    P.add('grass', '#9CC56A', show=False)

    p.plat = Plateau(zp=1.035, rho0=0.5, var=0.075, seed=1.3)
    std_terraces(p, [dict(r=1.098, width=5.6, wvar=1.8, top=P['terr'], rim=P['edge'], cliffs=[P['cliff'], P['cliff2']], drop=0.09)])

    islets = [  # (alpha, phi, radius deg, height, rocky)
        (44, 58, 6.0, 0.062, True),
        (60, 142, 8.0, 0.036, False),
        (66, -18, 7.0, 0.032, False),
        (64, 92, 6.0, 0.03, False),
        (74, -152, 5.0, 0.022, False),
        (88, -96, 5.5, 0.02, False),
        (104, 18, 8.0, 0.03, False),
        (122, -168, 9.0, 0.035, False),
        (146, 80, 10.0, 0.04, True),
        (92, 168, 6.0, 0.024, False),
        (76, -40, 5.5, 0.03, False),
        (98, -132, 7.0, 0.034, False),
        (82, -70, 3.5, 0.016, False),
    ]
    isl = [(dirs(a, f), r * DEG, h, rk) for a, f, r, h, rk in islets]

    def hfun(d):
        a, phi = ang(d)
        x = a - p.outer_alpha(phi)
        h = coast_profile(x, 0.068, (9.5 + 2.5 * onz(phi, 2.0, 7)) * DEG, 7 * DEG, 12 * DEG)
        h += 0.006 * fbm(d, 9, 2, 3) * smooth(0, 0.05, x)
        h = max(h, seabed(d, -0.15, 0.04, 1))
        for k, (c, r, hh, _) in enumerate(isl):
            h = max(h, mound(d, c, r, hh, 10 + k))
        return h

    def rocky(c):
        return any(rk and adist(c, cc) < r * 0.9 for cc, r, _, rk in isl)

    def paint(dc, h, slope, c):
        if h > 0.004:
            if slope > 0.22 or (rocky(dc) and h > 0.014):
                return P['rock'] if fbm(dc, 7, 2, 4) > -0.1 else P['rock2']
            return P['sand'] if fbm(dc, 6, 2, 5) > -0.15 else P['sand2']
        if h > -0.034:
            return P['sea_sand']
        if h > -0.075:
            return P['sea_mid']
        return P['sea_deep']

    p.make_body(hfun, paint)
    p.make_water(P['water'])
    p.make_plateau((P['build'], P['build2']), P['edge'], [P['cliff'], P['cliff2'], P['cliff2']])
    p.build_bvh()
    rng = p.rng

    # lighthouse on its rocky islet (right edge of the silhouette)
    pr = p.probe(dirs(45, 58))
    pf_lighthouse(p.d('Lighthouse'), frame(pr['loc'] - pr['d'] * 0.006, pr['d'], 0.3, 1.0), P, h=0.25)
    p.claim(pr['d'], 6 * DEG)
    p.count('Leuchtturm')

    # wooden piers on the central island, front-left / front-right and back-left
    for phi_deg, L in ((-125, 0.2), (-58, 0.17), (160, 0.16)):
        phi = phi_deg * DEG
        res = p.coast(phi, p.outer_alpha(phi) + 0.01)
        if not res:
            continue
        a_c, loc, _ = res
        a0 = a_c - 0.018
        d0 = sph(a0, phi)
        start = d0 * (RW + 0.012)
        M = basis(start, d0, outward(d0))
        reach = pf_pier(p.d('Piers'), M, rng, P['wood'], P['wood_dark'], length=L)
        p.claim(sph(a0 + 0.06, phi), 5 * DEG)
        p.count('Holzsteg')
        if phi_deg == -58:
            tip = M @ Vector((reach + 0.03, 0.05, -0.006))
            dd = tip.normalized()
            pf_boat(p.d('Boats'), basis(dd * (RW + 0.003), dd, outward(dd)) @ Matrix.Rotation(0.5, 4, 'Z'),
                    P['wood'], P['lh_white'], s=0.075)
            p.count('Ruderboot')

    # palms: few, mostly back & sides
    def palm_ok(pr):
        return land(pr, 0.008) and off_build(pr, 7.5) and pr['slope'] < 0.25 and pr['front'] < 0.45
    for pr in p.scatter(9, palm_ok, 3.0 * DEG, a=(30, 150)):
        s = p.frontal(pr['d'], 0.6)
        pf_palm(p.d('Palms'), frame(pr['loc'] - pr['d'] * 0.004, pr['d'], rng.uniform(0, TAU)), rng,
                P['trunk'], [P['leaf'], P['leaf2']], nut=P['wood_dark'], h=rng.uniform(0.15, 0.21) * s, lean=0.35)
        p.count('Palme')

    # soft rocks along the beaches and islets
    def rock_ok(pr):
        return pr['h'] > 0.004 and off_build(pr, 7.0)
    for pr in p.scatter(16, rock_ok, 2.2 * DEG, a=(30, 165)):
        s = rng.uniform(0.022, 0.045) * p.frontal(pr['d'], 0.6)
        pf_rock(p.d('Rocks'), frame(pr['loc'], place_up(p, pr, 0.6), rng.uniform(0, TAU), (s, s * 0.9, s)), rng,
                P['rock'] if rng.random() < 0.6 else P['rock2'], sub=2, jit=0.16, squash=0.62)
        p.count('Felsen')

    # beach grass tufts
    for pr in p.scatter(14, lambda pr: land(pr, 0.012) and off_build(pr, 6.5) and pr['slope'] < 0.2, 1.2 * DEG, a=(30, 120)):
        pf_grass(p.d('Grass'), frame(pr['loc'], pr['d'], rng.uniform(0, TAU)), rng, P['grass'], h=0.03)
        p.count('Strandgras')

    p.meta.update(tagline="Der freundliche Ozeanplanet",
                  features=["Zentrale Handelsinsel aus Sandstein über einer Sandsteinterrasse",
                            "Zwölf kleine Sand- und Felsinseln, flache Lagunen mit sichtbarem Sandgrund",
                            "Drei Holzstege mit Ruderboot, Leuchtturm auf der rechten Felsinsel",
                            "Neun stilisierte Palmen, weiche Felsen, Strandgras"])
    p.finalize()
    return p


