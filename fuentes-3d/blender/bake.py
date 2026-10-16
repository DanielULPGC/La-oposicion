"""Hornea la iluminación de la sala y exporta la escena con lightmaps.

Uso: python3 bake.py [resolución_A] [resolución_B] [muestras]
- Lightmap = (luz total difusa) − (luz solar directa). El sol directo se recalcula
  en tiempo real en Three.js para conservar sombras nítidas de las lamas.
- Los lightmaps se guardan codificados en sRGB con un factor de escala por atlas
  y viajan dentro del GLB en el material «LM_A»/«LM_B» de un objeto portador.
- Además renderiza un panorama equirectangular de la propia sala (entorno de reflejos).
"""
import bpy, math, sys, os, json, time
import numpy as np
from mathutils import Vector

ROOT = "/home/claude/tribunal3d"
OUT = ROOT + "/out/"
args = [a for a in sys.argv[1:] if not a.startswith("-")]
RES_A = int(args[0]) if len(args) > 0 else 2048
RES_B = int(args[1]) if len(args) > 1 else 1024
SPP = int(args[2]) if len(args) > 2 else 64
bpy.ops.wm.open_mainfile(filepath=OUT + "sala.blend")
sc = bpy.context.scene
t0 = time.time()


def P(x, y, z):
    return Vector((x, -z, y))


GROUP_A = ["Suelo", "Gradas", "MuroCurvo", "Zocalo", "Muros", "Boiserie", "Techo", "Casetones", "Puertas", "Estrado", "Ventanas"]
GROUP_B = ["Mesa", "Sillas", "Atril", "RelojCaja"]
OB = bpy.data.objects

# Ocultar lo que no está siempre presente
for st in ("ST2", "ST3", "ST4", "ST5"):
    for c in [OB[st]] + list(OB[st].children_recursive):
        c.hide_render = True
for c in [OB["AudienceTemplates"]] + list(OB["AudienceTemplates"].children_recursive):
    c.hide_render = True

# Mundo negro: la sala está cerrada y la luz diurna entra por las ventanas
w = bpy.data.worlds.new("Negro"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0

# Sol (misma dirección que en Three.js: desde (7,18,-28) hacia (0,0,-1))
SUN_STRENGTH = 4.0
sun = bpy.data.lights.new("Sol", "SUN"); sun.energy = SUN_STRENGTH; sun.angle = math.radians(0.6); sun.color = (1.0, 0.89, 0.72)
so = bpy.data.objects.new("Sol", sun); sc.collection.objects.link(so)
d3 = Vector((0, 0, -1)) - Vector((7, 18, -28))
so.rotation_euler = P(*d3).normalized().to_track_quat("-Z", "Y").to_euler()

# Lámparas: luces puntuales bajo cada globo
lamps = json.loads(OB["LampPositions"]["lamps"])
lamp_objs = []
for (x, y, z) in lamps:
    l = bpy.data.lights.new("Lamp", "POINT"); l.energy = 140; l.color = (1.0, 0.82, 0.58); l.shadow_soft_size = 0.18
    o = bpy.data.objects.new("Lamp", l); o.location = P(x, y - 0.32, z); sc.collection.objects.link(o)
    lamp_objs.append(o)
# Luz de cielo: luces de área en cada ventana (mucho menos ruido que los paneles emisivos)
sky = bpy.data.materials["Cielo"].node_tree.nodes["Principled BSDF"]
sky.inputs["Emission Strength"].default_value = 0.0
SKY_POWER = 320.0
for x in (-8.6, -4.6, 4.6, 8.6):
    a = bpy.data.lights.new("Ventana", "AREA"); a.shape = "RECTANGLE"; a.size = 1.6; a.size_y = 3.3
    a.energy = SKY_POWER; a.color = (0.86, 0.92, 1.0)
    o = bpy.data.objects.new("Ventana", a); o.location = P(x, 4.6, -7.5)
    o.rotation_euler = P(0, 0, 1).normalized().to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(o); lamp_objs.append(o)

sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SPP
sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 4; sc.cycles.glossy_bounces = 1; sc.cycles.transparent_max_bounces = 4
sc.cycles.sample_clamp_direct = 0.0; sc.cycles.sample_clamp_indirect = 1.5
sc.render.bake.margin = 8
sc.render.bake.use_clear = True


# UV de lightmap compartido por grupo
def lightmap_uv(names):
    bpy.ops.object.select_all(action="DESELECT")
    for n in names:
        me = OB[n].data
        if "Lightmap" not in me.uv_layers:
            me.uv_layers.new(name="Lightmap")
        me.uv_layers.active = me.uv_layers["Lightmap"]
        for uvl in me.uv_layers:
            uvl.active_render = (uvl.name != "Lightmap")
        OB[n].select_set(True)
    bpy.context.view_layer.objects.active = OB[names[0]]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake(names, img, pass_filter, spp=None):
    sc.cycles.samples = spp or SPP
    mats = {m for n in names for m in OB[n].data.materials if m}
    nodes = []
    for m in mats:
        nt = m.node_tree
        nd = nt.nodes.new("ShaderNodeTexImage"); nd.image = img
        nt.nodes.active = nd; nodes.append((nt, nd))
    bpy.ops.object.select_all(action="DESELECT")
    for n in names:
        OB[n].select_set(True)
    bpy.context.view_layer.objects.active = OB[names[0]]
    bpy.ops.object.bake(type="DIFFUSE", pass_filter=pass_filter, margin=8, use_clear=True)
    for nt, nd in nodes:
        nt.nodes.remove(nd)


def to_np(img):
    a = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)[..., :3]
    return a


def blur(a, it=2):
    from scipy.ndimage import median_filter, gaussian_filter
    a = np.stack([median_filter(a[..., c], size=3) for c in range(3)], -1)
    return np.stack([gaussian_filter(a[..., c], sigma=1.0) for c in range(3)], -1)


scales = {}
for tag, names, res in (("A", GROUP_A, RES_A), ("B", GROUP_B, RES_B)):
    lightmap_uv(names)
    full = bpy.data.images.new(f"LM_{tag}_full", res, res, float_buffer=True)
    bake(names, full, {"DIRECT", "INDIRECT"})
    print(f"[{time.time()-t0:.0f}s] horneado completo {tag}", flush=True)
    # Solo sol directo: apagar lámparas y cielo
    for o in lamp_objs:
        o.hide_render = True
    sunimg = bpy.data.images.new(f"LM_{tag}_sun", res, res, float_buffer=True)
    bake(names, sunimg, {"DIRECT"}, spp=max(4, SPP // 6))
    for o in lamp_objs:
        o.hide_render = False
    print(f"[{time.time()-t0:.0f}s] horneado solar {tag}", flush=True)
    L = np.clip(to_np(full) - to_np(sunimg), 0, None)
    L = blur(L, 2)
    k = float(np.percentile(L, 99.7)) or 1.0
    enc = np.clip(L / k, 0, 1) ** (1 / 2.2)
    from PIL import Image
    Image.fromarray((enc[::-1] * 255 + 0.5).astype(np.uint8)).save(OUT + f"lm_{tag}.jpg", quality=90)
    np.save(OUT + f"lm_{tag}_raw.npy", L.astype(np.float16))
    scales[tag] = k
    print(f"lightmap {tag}: escala {k:.4f}", flush=True)

# Portador de lightmaps dentro del GLB
import bmesh
for tag in ("A", "B"):
    m = bpy.data.materials.new(f"LM_{tag}"); m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(OUT + f"lm_{tag}.jpg")
    m.node_tree.links.new(t.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
bm = bmesh.new()
for i in range(2):
    vs = [bm.verts.new((i * 0.02 + x, y, -50)) for (x, y) in ((0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01))]
    f = bm.faces.new(vs); f.material_index = i
uv = bm.loops.layers.uv.verify()
for f in bm.faces:
    for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[uv].uv = c
me = bpy.data.meshes.new("LM_Carrier"); bm.to_mesh(me); bm.free()
me.materials.append(bpy.data.materials["LM_A"]); me.materials.append(bpy.data.materials["LM_B"])
car = bpy.data.objects.new("LM_Carrier", me); sc.collection.objects.link(car)
car["lmScale"] = json.dumps({**scales, "groupA": GROUP_A, "groupB": GROUP_B, "sun": SUN_STRENGTH})

# Panorama equirectangular de la sala para reflejos
sky.inputs["Emission Strength"].default_value = 6.0
for o in OB:
    pass
cam = bpy.data.cameras.new("Pano"); cam.type = "PANO"
try:
    cam.panorama_type = "EQUIRECTANGULAR"
except AttributeError:
    cam.cycles.panorama_type = "EQUIRECTANGULAR"
co = bpy.data.objects.new("Pano", cam); sc.collection.objects.link(co); sc.camera = co
co.location = P(0, 1.7, -2.2)
co.rotation_euler = Vector((1, 0, 0)).to_track_quat("-Z", "Y").to_euler()
sc.render.resolution_x = 1024; sc.render.resolution_y = 512
sc.cycles.samples = 64; sc.cycles.use_denoising = True
sc.render.image_settings.file_format = "HDR"
sc.view_settings.view_transform = "Standard"
sc.render.filepath = OUT + "sala_env.hdr"
bpy.ops.render.render(write_still=True)
print(f"[{time.time()-t0:.0f}s] panorama", flush=True)
co.hide_render = True
sc.camera = None
bpy.data.objects.remove(co)

# Limpiar luces de horneado y exportar
for o in [so] + lamp_objs:
    bpy.data.objects.remove(o)
sky.inputs["Emission Strength"].default_value = 2.5
for st in ("ST2", "ST3", "ST4", "ST5"):
    for c in [OB[st]] + list(OB[st].children_recursive):
        c.hide_render = False
for c in [OB["AudienceTemplates"]] + list(OB["AudienceTemplates"].children_recursive):
    c.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=OUT + "sala_baked.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "sala_baked.glb", export_format="GLB", export_apply=True, export_extras=True,
                          export_yup=True, export_image_format="AUTO", export_cameras=False, export_lights=False,
                          export_texcoords=True)
print(f"[{time.time()-t0:.0f}s] exportado", os.path.getsize(OUT + "sala_baked.glb"), scales, flush=True)
