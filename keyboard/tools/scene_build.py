"""Build the Blender showcase scenes for both keyboards, and optionally render them.

Run from keyboard/, after tools/scene_export.py has written the meshes:

    blender -b --python tools/scene_build.py -- [--render] [--size 1080p|2k|4k] [--only kb1|retro] [--preview]
                                                [--colours NAME=BODY,ACCENT] [--camera TEXT]

It writes cad/scenes/kb1.blend and cad/scenes/retro.blend. Each file has two scenes,
"assembled" (both halves on a desk) and "exploded" (the left half taken apart along its
assembly axis), each with five cameras and its own lighting. The cameras are bound to
timeline markers: frames 1 to 5 step through them. --render writes a still for each camera to
cad/scenes/renders/<size>/ (1080p by default; 2k is 2560 x 1440, 4k is 3840 x 2160). --preview
makes small quick ones in cad/scenes/build/ instead, for trying a change. --colours tries a
pair of filament colours (hex codes) on the retro case: only that case is built, and its file
and stills (cad/scenes/build/colours/NAME-...) go to the build folder too, so the kept ones are
left alone. --camera renders only the cameras whose name has the text, as "hero".

Nothing is placed by hand: every position comes from the layout, the case files and the
manifest, so a regenerated case is shown by running this again. Units: Blender metres; the
sources are millimetres.

The keycaps are the KLP Lame models by braindefender (CC BY-SA 4.0), so the scenes and the
pictures made from them are CC BY-SA 4.0 too and must credit the author (docs/scenes.md).
"""

import csv
import json
import math
import os
import sys

import bmesh
import bpy
import yaml
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

BUILD, OUT = "cad/scenes/build", "cad/scenes"
MM = 0.001
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = "--preview" in ARGS
SIZES = {"1080p": (1920, 1080), "2k": (2560, 1440), "4k": (3840, 2160)}
SIZE = ARGS[ARGS.index("--size") + 1] if "--size" in ARGS else "1080p"
assert SIZE in SIZES, "--size is one of %s" % ", ".join(SIZES)
TRIAL = ARGS[ARGS.index("--colours") + 1] if "--colours" in ARGS else None
CAMERA = ARGS[ARGS.index("--camera") + 1] if "--camera" in ARGS else ""
with open(BUILD + "/manifest.json") as f:
    MAN = json.load(f)

with open("layout/layout.yaml") as f:
    CAPS = yaml.safe_load(f)["keycaps"]   # which keycap goes where, as [model, turn in degrees]

# How far each group lifts in the exploded view, mm along the case's z.
LIFT = {"plinth": -52, "stripe": -34, "screws": -30, "tray": 0, "cell": 26, "board": 44, "controller": 56,
        "plate": 80, "lid": 92, "switches": 106, "caps": 138}
SPLAY, HALF_X = 8.0, 128.0   # assembled: each half turned outwards by this, its origin this far from the middle

LOOKS = {
    "kb1": {
        "case": ((0.014, 0.014, 0.016), 0.42), "plate": ((0.014, 0.014, 0.016), 0.42), "accent": ((0.014, 0.014, 0.016), 0.42),
        "caps": ((0.011, 0.011, 0.012), 0.48),
        "floor": ((0.016, 0.017, 0.019), 0.42), "world": ((0.004, 0.004, 0.005), 1.0),
        "lights": [   # name, offset from the subject in m, size in m, watts, kelvin
            ("key", (-0.55, -0.45, 0.95), (1.1, 1.1), 11, 6200),
            ("top", (0.10, 0.10, 1.10), (1.6, 0.9), 8, 6500),
            ("rim left", (-0.95, 0.75, 0.40), (1.5, 0.18), 22, 7000),
            ("rim right", (0.90, 0.80, 0.45), (1.5, 0.18), 26, 7000),
            ("fill", (0.85, -0.90, 0.55), (1.8, 1.8), 2.5, 5600),
        ],
    },
    "retro": {
        "case": ((0.80, 0.76, 0.64), 0.48), "plate": ((0.62, 0.20, 0.015), 0.45), "accent": ((0.62, 0.20, 0.015), 0.45),
        "caps": ((0.86, 0.85, 0.80), 0.36),
        "floor": ((0.115, 0.050, 0.022), 0.55), "world": ((0.060, 0.028, 0.012), 1.0),
        "lights": [
            ("key", (-0.60, -0.55, 0.90), (1.0, 1.0), 9.0, 4300),
            ("top", (0.05, 0.15, 1.10), (1.4, 0.9), 4.0, 4800),
            ("rim left", (-0.90, 0.80, 0.45), (1.4, 0.2), 8.0, 3600),
            ("rim right", (0.95, 0.70, 0.40), (1.4, 0.2), 9.0, 5200),
            ("fill", (0.90, -0.80, 0.50), (1.8, 1.8), 2.0, 4000),
        ],
    },
}



def linear(code):
    """A hex colour code as the linear RGB that Blender's materials take."""
    return tuple(((c / 255 + 0.055) / 1.055) ** 2.4 if c > 10 else c / 255 / 12.92 for c in bytes.fromhex(code.lstrip("#")))


if TRIAL:   # for judging colour: white lamps, a grey floor and no colour grading. The finishes stay as they are
    TRIAL, pair = TRIAL.split("=")
    body, accent = (linear(code) for code in pair.split(","))
    LOOKS["retro"].update(case=(body, 0.48), plate=(accent, 0.45), accent=(accent, 0.45),
                          floor=((0.18, 0.18, 0.18), 0.55), world=((0.05, 0.05, 0.05), 1.0),
                          lights=[(name, off, size, watts, 6500) for name, off, size, watts, _ in LOOKS["retro"]["lights"]])

# Cameras: name, direction the camera stands in (azimuth from the user's side, clockwise seen
# from above; elevation), lens in mm, f-stop, what to frame, margin.
CAMERAS = {
    "assembled": [
        ("1 hero", -32, 26, 70, 8.0, "all", 0.05),
        ("2 above", 0, 89, 85, 11.0, "all", 0.05),
        ("3 low front", 8, 9, 85, 8.0, "all", 0.05),
        ("4 detail", -48, 22, 100, 9.0, "detail", 0.03),
        ("5 rear", 152, 20, 70, 8.0, "all", 0.05),
    ],
    "exploded": [
        ("1 hero", -34, 16, 70, 11.0, "all", 0.05),
        ("2 side", -90, 4, 85, 11.0, "all", 0.05),
        ("3 front", 0, 8, 85, 11.0, "all", 0.05),
        ("4 above", -25, 52, 70, 11.0, "all", 0.05),
        ("5 detail", -40, 12, 100, 9.0, "detail", 0.03),
    ],
}

CREDITS = """Keycap models: KLP Lame by braindefender, https://github.com/braindefender/KLP-Lame-Keycaps,
CC BY-SA 4.0. This scene and pictures rendered from it are therefore CC BY-SA 4.0 as well.
Switch model: kiswitch, https://github.com/kiswitch/kiswitch (MIT / CC BY-SA 4.0).
The board, controller, battery and screws are plain stand-ins of the right size, not models
of the parts. Built by tools/scene_build.py; do not edit by hand, run it again.
"""


def material(name, rgb, rough, metallic=0.0, bump=0.0, **inputs):
    m = bpy.data.materials.new(name)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    for k, v in inputs.items():
        b.inputs[k].default_value = v
    if bump:   # a fine grain, so printed faces are not mirror-flat
        noise = m.node_tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 2500.0
        noise.inputs["Detail"].default_value = 3.0
        node = m.node_tree.nodes.new("ShaderNodeBump")
        node.inputs["Strength"].default_value = bump
        node.inputs["Distance"].default_value = 0.0002
        m.node_tree.links.new(noise.outputs["Fac"], node.inputs["Height"])
        m.node_tree.links.new(node.outputs["Normal"], b.inputs["Normal"])
    return m


def load(name, mat, smooth=None):
    """A mesh from the build folder, scaled to metres. smooth: the angle above which an edge stays sharp."""
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.abspath("%s/%s.stl" % (BUILD, name)))
    ob = (set(bpy.data.objects) - before).pop()
    me = ob.data
    bpy.data.objects.remove(ob)
    me.transform(Matrix.Scale(MM, 4))   # the importer's own scale goes on the object, which is not kept
    me.name = name
    if smooth:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(smooth))
    me.materials.append(mat)
    return me


def solid(name, mat, build, bevel=0.0):
    """A mesh made here; build(bm) fills it, in millimetres."""
    bm = bmesh.new()
    build(bm)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=3, affect="EDGES")
    bmesh.ops.scale(bm, vec=(MM, MM, MM), verts=bm.verts[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    me.materials.append(mat)
    return me


def add_box(bm, b):
    made = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=(b[1] - b[0], b[3] - b[2], b[5] - b[4]), verts=made)
    bmesh.ops.translate(bm, vec=((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2), verts=made)


def add_cyl(bm, r, z0, z1):
    made = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=r, radius2=r, depth=z1 - z0)["verts"]
    bmesh.ops.translate(bm, vec=(0, 0, (z0 + z1) / 2), verts=made)


def place(coll, name, data, parent=None, at=(0, 0, 0), turn=0.0):
    ob = bpy.data.objects.new(name, data)
    coll.objects.link(ob)
    ob.parent = parent
    ob.location = (at[0] * MM, at[1] * MM, at[2] * MM)
    ob.rotation_euler = (0, 0, math.radians(turn))
    return ob


def keys(side):
    with open("layout/generated/%s-hand.csv" % side) as f:
        return [(r["id"], r["row"], float(r["x_mm"]), float(r["y_mm"]), float(r["rotation_deg"])) for r in csv.DictReader(f)]


def half(kb, side, coll, mats, explode):
    """One half in the case's own coordinates, under an empty. explode: 0 assembled, 1 taken apart."""
    root = place(coll, "%s %s" % (kb, side), None)
    made = {}

    def put(group, name, data, at=(0, 0, 0), turn=0.0):
        ob = place(coll, "%s %s" % (side, name), data, root, (at[0], at[1], at[2] + explode * LIFT[group]), turn)
        made.setdefault(group, []).append(ob)
        return ob

    parts = ("tray", "plate", "lid") + (("plinth", "stripe") if kb == "retro" else ())
    for n in parts:
        mat = mats["plate"] if n == "plate" else mats["accent"] if n == "stripe" else mats["case"]
        put(n, n, load("%s-%s-%s" % (kb, side, n), mat, smooth=None if n in ("tray", "plinth") else 25))
    put("board", "board", load("%s-board" % side, mats["board"]))

    c = MAN[side]["cell"]
    put("cell", "cell", solid("%s cell" % side, mats["cell"], lambda bm: add_box(bm, c), bevel=1.2))

    u = MAN[side]["controller"]   # 18.2 x 35 x 6.5: the case generator's block for the nice!nano on its sockets
    cx = (u[0] + u[1]) / 2
    put("controller", "controller sockets", solid("%s sockets" % side, mats["plastic"], lambda bm: [
        add_box(bm, (cx + s * 7.62 - 1.25, cx + s * 7.62 + 1.25, u[2] + 1.0, u[3] - 2.0, 0.0, 2.9)) for s in (-1, 1)]))
    put("controller", "controller board", solid("%s controller" % side, mats["controller"], lambda bm: add_box(
        bm, (cx - 8.9, cx + 8.9, u[2] + 0.5, u[3] - 1.5, 2.9, 4.5))))
    put("controller", "controller usb", solid("%s usb" % side, mats["steel"], lambda bm: add_box(
        bm, (cx - 4.45, cx + 4.45, u[3] - 8.0, u[3], 2.1, 5.3)), bevel=0.6))
    if side == "left":   # the right half's controller is fitted face down (docs/pcb.md)
        put("controller", "controller can", solid("%s can" % side, mats["steel"], lambda bm: add_box(
            bm, (cx - 5.0, cx + 5.0, u[2] + 8.0, u[2] + 20.0, 4.5, 6.2)), bevel=0.3))

    for s in MAN[kb]["screws"]:
        x = s["at"][0] * (1 if side == "left" else -1)
        name = "screw M3x%d" % s["length"]
        if name not in bpy.data.meshes:
            L = s["length"]
            solid(name, mats["screw"], lambda bm: (add_cyl(bm, 2.8, -1.9, 0.0), add_cyl(bm, 1.45, 0.0, L)), bevel=0.25)
        put("screws", name, bpy.data.meshes[name], (x, s["at"][1], s["seat"]))

    stem_top = MAN["switch"]["stem_top"]
    for kid, row, x, y, rot in keys(side):
        for piece in ("bottom", "top", "stem", "metal"):
            put("switches", "switch %s %s" % (kid, piece), load("switch-" + piece, mats["switch " + piece], smooth=30), (x, y, 0), rot)
        kind, turn = CAPS["keys"].get(kid) or CAPS["rows"][row]
        # the cap sits where its stem hole's end meets the top of the switch's stem
        put("caps", "cap %s" % kid, load("cap-" + kind, mats["caps"], smooth=30), (x, y, stem_top - MAN["caps"][kind]["ceiling"]), rot + turn)
    return root, made


def stand(kb, side, coll, root):
    """Put a half on the desk: keyboard 1 on its floor, the retro one on its raked plinth."""
    base = place(coll, "%s %s on the desk" % (kb, side), None)
    root.parent = base
    if kb == "retro":
        t = math.radians(MAN["retro"]["rake"])
        dz = MAN["retro"]["t_min"] - (MAN[side]["retro_ymin"] * math.sin(t) + MAN["z_bot"] * math.cos(t))
        base.rotation_euler = (t, 0, 0)
        base.location = (0, 0, dz * MM)
    else:
        base.location = (0, 0, -MAN["z_bot"] * MM)
    return base


def world(ob):
    """An object's world matrix from its own and its parents' placing: a new object's matrix_world is not set yet."""
    return (world(ob.parent) @ ob.matrix_basis) if ob.parent else ob.matrix_basis.copy()


BOXES = {}


def corners(objects):
    """The corners of the objects' bounding boxes, in the world."""
    pts = []
    for ob in objects:
        if ob.type != "MESH":
            continue
        if ob.data.name not in BOXES:
            vs = [v.co for v in ob.data.vertices]
            lo, hi = [min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]
            BOXES[ob.data.name] = [Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        m = world(ob)
        pts += [m @ c for c in BOXES[ob.data.name]]
    return pts


def aim(scene, cam, pts, az, el, margin):
    """Stand the camera in the given direction from the points' middle, as near as keeps them all in frame."""
    lo, hi = Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])
    target = (lo + hi) / 2
    a, e = math.radians(az), math.radians(el)
    out = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    quat = (-out).to_track_quat("-Z", "Y")
    near, far = 0.05, 30.0
    for _ in range(40):
        d = (near + far) / 2
        cam.matrix_world = Matrix.LocRotScale(target + out * d, quat, None)
        views = [world_to_camera_view(scene, cam, p) for p in pts]
        if all(margin <= v.x <= 1 - margin and margin <= v.y <= 1 - margin and v.z > 0 for v in views):
            far = d
        else:
            near = d
    cam.location, cam.rotation_euler = target + out * far, quat.to_euler()
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = far
    return target


def stage(scene, coll, look, centre):
    floor = bpy.data.meshes.new("floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30.0)
    bm.to_mesh(floor)
    bm.free()
    floor.materials.append(material("floor", *look["floor"]))
    place(coll, "floor", floor)
    for name, off, size, watts, kelvin in look["lights"]:
        light = bpy.data.lights.new(name, "AREA")
        light.shape, light.size, light.size_y, light.energy = "RECTANGLE", size[0], size[1], watts
        light.use_temperature, light.temperature = True, kelvin
        ob = bpy.data.objects.new(name, light)
        coll.objects.link(ob)
        ob.location = centre + Vector(off)
        ob.rotation_euler = (-Vector(off)).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new(scene.name)
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*look["world"][0], 1.0)
    bg.inputs["Strength"].default_value = look["world"][1]
    scene.world = world


def settings(scene):
    scene.render.engine = "CYCLES"
    scene.render.resolution_x, scene.render.resolution_y = (960, 540) if PREVIEW else SIZES[SIZE]
    scene.cycles.samples = 32 if PREVIEW else 160
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.03 if PREVIEW else 0.015
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    scene.unit_settings.scale_length = 1.0
    if TRIAL:
        scene.view_settings.view_transform = "Standard"   # Blender's default one shifts strong colours
    # Every graphics card this Blender can reach, together (owner, 2026-11-24). Otherwise the CPU.
    prefs = bpy.context.preferences.addons["cycles"].preferences
    scene.cycles.device = "CPU"
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.refresh_devices()
        except TypeError:
            continue
        cards = [d for d in prefs.devices if d.type == kind]
        if cards:
            for d in prefs.devices:
                d.use = d in cards
            scene.cycles.device = "GPU"
            print("SCENE renders on %s (%s)" % (" and ".join(d.name for d in cards), kind), flush=True)
            break


def build(kb):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    look = LOOKS[kb]
    mats = {
        "case": material("case", *look["case"], bump=0.08), "plate": material("plate", *look["plate"], bump=0.08),
        "accent": material("accent", *look["accent"], bump=0.08), "caps": material("keycaps", *look["caps"], bump=0.03),
        "board": material("board", (0.015, 0.11, 0.04), 0.7, **{"Specular IOR Level": 0.25}),
        "controller": material("controller", (0.02, 0.02, 0.025), 0.35),
        "plastic": material("black plastic", (0.02, 0.02, 0.02), 0.5),
        "steel": material("steel", (0.60, 0.60, 0.62), 0.32, 1.0),
        "cell": material("cell", (0.62, 0.63, 0.66), 0.38, 1.0),
        "screw": material("screw", (0.05, 0.05, 0.055), 0.38, 1.0),
        "switch bottom": material("switch bottom", (0.82, 0.82, 0.80), 0.4),
        "switch top": material("switch top", (0.9, 0.9, 0.9), 0.12, **{"Transmission Weight": 0.85, "IOR": 1.55}),
        "switch stem": material("switch stem", (0.45, 0.27, 0.10), 0.4),
        "switch metal": material("switch metal", (0.80, 0.62, 0.30), 0.3, 1.0),
    }
    text = bpy.data.texts.new("CREDITS")
    text.write(CREDITS)
    text.use_fake_user = True

    scenes = {}
    for name in ("assembled", "exploded"):
        scene = bpy.context.scene if name == "assembled" else bpy.data.scenes.new(name)
        scene.name = name
        scenes[name] = scene
        coll = scene.collection
        groups = {}
        if name == "assembled":
            for side, sx in (("left", -1), ("right", 1)):
                root, made = half(kb, side, coll, mats, 0)
                base = stand(kb, side, coll, root)
                spot = place(coll, "%s %s place" % (kb, side), None, at=(sx * HALF_X, 0, 0), turn=sx * SPLAY)
                base.parent = spot
                for g, obs in made.items():
                    groups.setdefault(g, []).extend(obs)
                if side == "left":
                    detail = made["lid"] + [o for o in made["caps"] if o.name.split()[-1][0] == "T"]
        else:
            root, made = half(kb, "left", coll, mats, 1)
            stand(kb, "left", coll, root).location.z += -LIFT["plinth" if kb == "retro" else "screws"] * MM + 0.012
            groups = made
            detail = made["caps"][:8] + made["switches"][:32]
        everything = [o for obs in groups.values() for o in obs]
        pts = corners(everything)
        centre = (Vector([min(p[i] for p in pts) for i in range(3)]) + Vector([max(p[i] for p in pts) for i in range(3)])) / 2
        print("SCENE %s %s: %d objects, the subject is %s m, centred on %s" % (
            kb, name, len(everything), " x ".join("%.3f" % (max(p[i] for p in pts) - min(p[i] for p in pts)) for i in range(3)),
            ", ".join("%.3f" % c for c in centre)), flush=True)
        stage(scene, coll, look, centre)
        settings(scene)
        for i, (cname, az, el, lens, fstop, what, margin) in enumerate(CAMERAS[name]):
            data = bpy.data.cameras.new(cname)
            data.lens, data.dof.aperture_fstop = lens, fstop
            cam = bpy.data.objects.new("%s %s" % (name, cname), data)
            coll.objects.link(cam)
            aim(scene, cam, corners(detail) if what == "detail" else pts, az, el, margin)
            print("SCENE %s %s: camera %s at %.2f m" % (kb, name, cname, cam.data.dof.focus_distance), flush=True)
            scene.timeline_markers.new(cname, frame=i + 1).camera = cam
        scene.frame_start, scene.frame_end = 1, len(CAMERAS[name])
        scene.frame_set(1)

    os.makedirs(OUT, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0   # no .blend1 beside the file
    path = os.path.abspath("%s/%s.blend" % (BUILD if PREVIEW or TRIAL else OUT, kb))
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("SCENE %s: %s, %d objects, %d meshes, device %s" % (kb, path, len(bpy.data.objects), len(bpy.data.meshes),
                                                             scenes["assembled"].cycles.device), flush=True)
    if "--render" in ARGS:
        folder = os.path.abspath(BUILD + "/colours" if TRIAL else BUILD + "/preview" if PREVIEW else "%s/renders/%s" % (OUT, SIZE))
        os.makedirs(folder, exist_ok=True)
        for name, scene in scenes.items():
            if bpy.context.window:
                bpy.context.window.scene = scene   # markers only switch the camera in the window's scene
            for marker in sorted(scene.timeline_markers, key=lambda m: m.frame):
                if CAMERA not in marker.name:
                    continue
                scene.frame_set(marker.frame)   # the marker at this frame puts its camera in charge
                scene.camera = marker.camera
                scene.render.filepath = "%s/%s-%s-%s.png" % (folder, TRIAL or kb, name, marker.name.replace(" ", "-"))
                bpy.ops.render.render(write_still=True, scene=scene.name)
                print("SCENE rendered", scene.render.filepath, flush=True)


for kb in ("kb1", "retro"):
    if kb == "retro" if TRIAL else "--only" not in ARGS or ARGS[ARGS.index("--only") + 1] == kb:
        build(kb)
