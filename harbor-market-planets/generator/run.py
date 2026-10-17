"""Build, render and export the Harbor Market planets.

usage: python run.py --out DIR [--only 1,2] [--res 1200] [--samples 96] [--overview] [--save] [--glb]
"""
import argparse, json, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import core
import planets as PL
import p2, p3

BUILDERS = [PL.pelagia, p2.coralune, p2.verdantide, p2.dunewake, p2.frostharbor,
            p3.ember_shoal, p3.prismara, p3.sporehaven, p3.ringhaven, p3.abyssal_crown]

ELEV = 50.0 * core.DEG
VIEW = Vector((0.0, math.cos(ELEV), -math.sin(ELEV)))      # camera looks along this
CAM_UP = Vector((0.0, math.sin(ELEV), math.cos(ELEV)))
CAM_RIGHT = Vector((1.0, 0.0, 0.0))
ORTHO = 3.05
TARGET_V = 0.1
VIEW_LOOK = 'AgX - Punchy'


def setup_render(res, samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 12
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = VIEW_LOOK
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.threads_mode = 'AUTO'


def make_rig():
    sc = bpy.context.scene
    rig = bpy.data.collections.new("00_Preview_Rig")
    sc.collection.children.link(rig)
    w = bpy.data.worlds.new("Harbor_World")
    sc.world = w
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.30, 0.34, 0.42, 1.0)
    bg.inputs["Strength"].default_value = 0.85

    def sun(name, towards_light, energy, color, angle):
        ld = bpy.data.lights.new(name, 'SUN')
        ld.energy = energy
        ld.color = color
        ld.angle = angle * core.DEG
        ob = bpy.data.objects.new(name, ld)
        ob.rotation_mode = 'QUATERNION'
        ob.rotation_quaternion = (-towards_light.normalized()).to_track_quat('-Z', 'Y')
        ob.location = towards_light.normalized() * 8
        rig.objects.link(ob)
        return ob
    sun("Key_Sun", Vector((-0.55, -0.5, 0.75)), 4.0, (1.0, 0.95, 0.88), 5.0)
    sun("Rim_Sun", Vector((0.7, 0.75, 0.25)), 2.6, (0.72, 0.84, 1.0), 6.0)
    sun("Fill_Sun", Vector((0.6, -0.7, -0.2)), 0.45, (0.85, 0.9, 1.0), 10.0)
    cd = bpy.data.cameras.new("Preview_Cam")
    cd.type = 'ORTHO'
    cd.ortho_scale = ORTHO
    cd.clip_start = 0.1
    cd.clip_end = 200
    cam = bpy.data.objects.new("Preview_Cam", cd)
    rig.objects.link(cam)
    sc.camera = cam
    return rig, cam


def aim(cam, centre, ortho=ORTHO):
    target = centre + CAM_UP * TARGET_V
    cam.location = target - VIEW * 30.0
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = VIEW.to_track_quat('-Z', 'Y')
    cam.data.ortho_scale = ortho


def tri_count(objs):
    t = 0
    for o in objs:
        if o.type == 'MESH':
            for p in o.data.polygons:
                t += len(p.vertices) - 2
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', default='')
    ap.add_argument('--res', type=int, default=1200)
    ap.add_argument('--samples', type=int, default=96)
    ap.add_argument('--overview', action='store_true')
    ap.add_argument('--save', action='store_true')
    ap.add_argument('--glb', action='store_true')
    ap.add_argument('--noprev', action='store_true')
    ap.add_argument('--look', default='')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    global VIEW_LOOK
    if a.look:
        VIEW_LOOK = a.look
    os.makedirs(a.out, exist_ok=True)
    for sub in ('previews', 'glb'):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    core.reset_scene()
    setup_render(a.res, a.samples)
    rig, cam = make_rig()
    only = [int(x) for x in a.only.split(',') if x]
    built = []
    for i, b in enumerate(BUILDERS):
        if only and (i + 1) not in only:
            continue
        t0 = time.time()
        p = b()
        p.meta["tris"] = tri_count(p.objects)
        p.meta["objects"] = [o.name for o in p.objects]
        print(f"built {p.idx:02d} {p.key}: {p.meta['tris']} tris in {time.time() - t0:.1f}s", flush=True)
        built.append(p)
    sc = bpy.context.scene
    meta = []
    for p in built:
        for q in built:
            q.col.hide_render = (q is not p)
        if not a.noprev:
            aim(cam, p.root.location)
            sc.render.filepath = os.path.join(a.out, 'previews', f"{p.idx:02d}_{p.key}.png")
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            print(f"rendered {p.key} in {time.time() - t0:.1f}s", flush=True)
        if a.glb:
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            p.root.select_set(True)
            for o in p.objects:
                o.select_set(True)
            bpy.context.view_layer.objects.active = p.root
            fp = os.path.join(a.out, 'glb', f"{p.idx:02d}_{p.key}.glb")
            bpy.ops.export_scene.gltf(filepath=fp, export_format='GLB', use_selection=True, export_apply=True,
                                      export_extras=True, export_yup=True, export_cameras=False, export_lights=False)
            p.meta["glb_bytes"] = os.path.getsize(fp)
        meta.append({"idx": p.idx, "key": p.key, "title": p.title, "palette": p.P.info, "counts": p.counts, **p.meta})
    for q in built:
        q.col.hide_render = False
    # grid layout for the overview and the saved file (5 x 2, in the camera plane)
    cols, sx, sy = 5, 3.75, 3.35
    for i, p in enumerate(built):
        r, c = divmod(i, cols)
        p.root.location = CAM_RIGHT * ((c - (cols - 1) / 2) * sx) - CAM_UP * ((r - 0.5) * sy if len(built) > cols else 0)
        # per-planet camera, parented so it travels with the planet
        cd = bpy.data.cameras.new(f"{p.key}_Cam")
        cd.type = 'ORTHO'
        cd.ortho_scale = ORTHO
        pc = bpy.data.objects.new(f"{p.key}_Cam", cd)
        rig.objects.link(pc)
        aim(pc, Vector((0, 0, 0)))
        pc.parent = p.root
    bpy.context.view_layer.update()
    if a.overview and len(built) > 1:
        rows = (len(built) + cols - 1) // cols
        aim(cam, Vector((0, 0, 0)) - CAM_UP * 0.0, ortho=cols * sx + 0.4)
        cam.location = cam.location - CAM_UP * TARGET_V + CAM_UP * 0.12
        sc.render.resolution_x = 2600
        sc.render.resolution_y = int(2600 * (rows * sy + 0.25) / (cols * sx + 0.4))
        sc.render.filepath = os.path.join(a.out, 'previews', "00_Overview.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"rendered overview in {time.time() - t0:.1f}s", flush=True)
    aim(cam, Vector((0, 0, 0)), ortho=cols * sx + 0.4)
    if a.save:
        sc.render.resolution_x = a.res
        sc.render.resolution_y = a.res
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(a.out, "HarborMarket_Planets.blend"), compress=True)
    with open(os.path.join(a.out, 'meta.json'), 'w') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)


main()
