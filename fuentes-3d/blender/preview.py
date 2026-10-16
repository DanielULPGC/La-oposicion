"""Render de comprobación (Cycles CPU) de sala.blend desde varias vistas."""
import bpy, math, sys
from mathutils import Vector

ROOT = "/home/claude/tribunal3d"
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/prev"
views = sys.argv[sys.argv.index("--") + 2].split(",") if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 2 else ["sala"]
show = sys.argv[sys.argv.index("--") + 3] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 3 else ""
bpy.ops.wm.open_mainfile(filepath=ROOT + "/out/sala.blend")
sc = bpy.context.scene


def P(x, y, z):
    return Vector((x, -z, y))


for st in ("ST2", "ST3", "ST4", "ST5"):
    ob = bpy.data.objects[st]
    vis = st == show
    for c in [ob] + list(ob.children_recursive):
        c.hide_render = not vis
bpy.data.objects["AudienceTemplate"].hide_render = True

w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
env = w.node_tree.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(ROOT + "/tex/hall.hdr")
w.node_tree.links.new(env.outputs["Color"], w.node_tree.nodes["Background"].inputs["Color"])
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
sun = bpy.data.lights.new("Sol", "SUN"); sun.energy = 4.5; sun.angle = 0.02; sun.color = (1, 0.88, 0.7)
so = bpy.data.objects.new("Sol", sun); sc.collection.objects.link(so)
d = (P(0, -1, 0) - P(0, 0, 0)) * 0.55 + (P(0, 0, 1) - P(0, 0, 0)) * 0.6 + (P(1, 0, 0) - P(0, 0, 0)) * 0.25
so.rotation_euler = (-d).to_track_quat("Z", "Y").to_euler()
for (x, y, z) in [(-4, 4.9, -1.5), (4, 4.9, -1.5), (0, 4.9, 2.5), (0, 4.9, -6)]:
    l = bpy.data.lights.new("L", "POINT"); l.energy = 120; l.color = (1, 0.85, 0.6); l.shadow_soft_size = 0.3
    o = bpy.data.objects.new("L", l); o.location = P(x, y - 0.4, z); sc.collection.objects.link(o)

V = {
    "sala": dict(look=(0, 1.0, -3.5), r=10.0, yaw=0.39, pitch=0.39),
    "opositor": dict(look=(0, 1.4, -1.2), r=4.6, yaw=0.62, pitch=0.22),
    "tribunal": dict(look=(0, 1.2, -5.0), r=5.6, yaw=-0.08, pitch=0.18),
    "st": dict(look=(0, 1.0, -2.8), r=6.5, yaw=0.0, pitch=0.28),
}
cam = bpy.data.cameras.new("C"); cam.lens = 28
co = bpy.data.objects.new("C", cam); sc.collection.objects.link(co); sc.camera = co
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x = 960; sc.render.resolution_y = 540
sc.view_settings.view_transform = "AgX"
for name in views:
    v = V[name]
    lk = Vector(v["look"])
    cp = math.cos(v["pitch"])
    pos3 = lk + Vector((math.sin(v["yaw"]) * cp, math.sin(v["pitch"]), math.cos(v["yaw"]) * cp)) * v["r"]
    co.location = P(*pos3)
    co.rotation_euler = (P(*lk) - P(*pos3)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}_{name}.png"
    bpy.ops.render.render(write_still=True)
    print("render", name)
