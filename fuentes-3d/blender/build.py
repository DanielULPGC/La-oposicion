"""Construye la escena de «El tribunal» en Blender y la exporta a GLB.

Convención: las coordenadas se escriben en el sistema de Three.js (Y arriba,
metros) y se convierten a Blender (Z arriba) con P(). El tribunal está en
C = (0, -4.4); el público se dispone en gradas semicirculares centradas en C.
"""
import bpy, bmesh, math, json, os, sys
from mathutils import Vector, Matrix, Euler
from PIL import Image, ImageDraw, ImageFont

ROOT = "/home/claude/tribunal3d"
TEX = ROOT + "/tex/"
OUT = ROOT + "/out/"
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene
COL = SC.collection
CX, CZ = 0.0, -4.4
TIERS = 5
A0 = 5.0          # radio interior de la primera fila
BAND = 1.2        # fondo de cada fila
RISE = 0.42       # altura de cada grada
SPAN = 1.15       # semiapertura angular de las gradas (rad)
AISLES = (-0.42, 0.42)
WALL_R = 11.9
WALK_H = RISE * TIERS
ROOM_H = 7.0
BACK_Z = -7.8


def P(x, y, z):
    return Vector((x, -z, y))


# ---------------------------------------------------------------- materiales
def image(name, noncolor=False):
    im = bpy.data.images.load(TEX + name, check_existing=True)
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    return im


def material(name, color=(0.8, 0.8, 0.8), rough=0.6, metal=0.0, tex=None, nrm=None, nrm_s=1.0,
             emit=None, emit_s=1.0, alpha=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if tex:
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = image(tex)
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1.0
        a_in = [s for s in mix.inputs if s.name == "A" and s.type == "RGBA"][0]
        b_in = [s for s in mix.inputs if s.name == "B" and s.type == "RGBA"][0]
        out = [s for s in mix.outputs if s.type == "RGBA"][0]
        nt.links.new(t.outputs["Color"], a_in)
        b_in.default_value = (*color, 1)
        nt.links.new(out, b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*color, 1)
    if nrm:
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = image(nrm, True)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = nrm_s
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_s
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
    return m


M = {}
M["oak"] = material("Roble", (1.0, 0.93, 0.85), 0.55, tex="wood_col.jpg", nrm="wood_nrm.jpg", nrm_s=0.6)
M["walnut"] = material("Nogal", (0.55, 0.42, 0.34), 0.5, tex="wood_col.jpg", nrm="wood_nrm.jpg", nrm_s=0.6)
M["parquet"] = material("Parqué", (0.95, 0.9, 0.85), 0.45, tex="parquet_col.jpg", nrm="parquet_nrm.jpg", nrm_s=0.5)
M["plaster"] = material("Yeso", (1, 0.98, 0.95), 0.9, tex="plaster_col.jpg", nrm="plaster_nrm.jpg", nrm_s=0.4)
M["baize"] = material("Paño", (1, 1, 1), 0.95, tex="baize_col.jpg", nrm="baize_nrm.jpg", nrm_s=0.5)
M["marble"] = material("Mármol", (1, 1, 1), 0.3, tex="marble_col.jpg")
M["stone"] = material("Arenisca", (1, 1, 1), 0.85, tex="stone_col.jpg", nrm="stone_nrm.jpg", nrm_s=1.0)
M["bronze"] = material("Bronce", (1, 1, 1), 0.45, 0.85, tex="bronze_col.jpg", nrm="bronze_nrm.jpg", nrm_s=0.8)
M["leather_red"] = material("Cuero rojo", (0.45, 0.12, 0.08), 0.55, tex="leather_col.jpg", nrm="leather_nrm.jpg")
M["leather_brown"] = material("Cuero marrón", (0.35, 0.2, 0.1), 0.55, tex="leather_col.jpg", nrm="leather_nrm.jpg")
M["leather_green"] = material("Cuero verde", (0.12, 0.22, 0.14), 0.55, tex="leather_col.jpg", nrm="leather_nrm.jpg")
M["leather_dark"] = material("Cuero oscuro", (0.12, 0.08, 0.06), 0.5, tex="leather_col.jpg", nrm="leather_nrm.jpg")
M["parchment"] = material("Pergamino", (1, 1, 1), 0.8, tex="parchment_col.jpg")
M["paper"] = material("Papel", (0.93, 0.92, 0.88), 0.85)
M["steel"] = material("Acero", (0.78, 0.79, 0.8), 0.22, 1.0)
M["iron"] = material("Hierro", (0.2, 0.19, 0.18), 0.6, 0.9)
M["gold"] = material("Dorado", (0.83, 0.64, 0.3), 0.3, 1.0)
M["black"] = material("Laca negra", (0.015, 0.015, 0.02), 0.15)
M["glass"] = material("Vidrio", (0.85, 0.92, 0.95), 0.05, alpha=0.18)
M["paint_white"] = material("Pintura blanca", (0.86, 0.85, 0.82), 0.6)
M["window"] = material("Cielo", (1, 0.97, 0.9), 1.0, emit=(1.0, 0.95, 0.85), emit_s=2.5)
M["lamp"] = material("Globo", (1, 0.95, 0.85), 0.3, emit=(1.0, 0.86, 0.62), emit_s=3.0)
M["skin"] = material("Maniquí", (0.80, 0.74, 0.65), 0.45)
M["shoe"] = material("Calzado", (0.06, 0.05, 0.05), 0.35)
M["sea"] = material("Mar", (1, 1, 1), 0.08, tex="sea_col.jpg", nrm="sea_nrm.jpg", nrm_s=0.6)
M["sail"] = material("Lona", (0.9, 0.85, 0.72), 0.85, tex="fabric_col.jpg")
M["flame"] = material("Llama", (1.0, 0.45, 0.1), 0.9, emit=(1.0, 0.42, 0.08), emit_s=6.0)
M["board"] = material("Pizarra", (1, 1, 1), 0.8, tex="blackboard_col.jpg")
M["metal_grey"] = material("Metal gris", (0.35, 0.36, 0.38), 0.4, 0.8)


def cloth(name, color):
    return material(name, color, 0.85, tex="fabric_col.jpg", nrm="fabric_nrm.jpg", nrm_s=0.5)


# Esfera de reloj
def clock_face():
    n = 512
    img = Image.new("RGB", (n, n), (236, 230, 214))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, n - 8, n - 8), outline=(40, 34, 28), width=10)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 44)
    except OSError:
        f = ImageFont.load_default()
    nums = ["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    for i, t in enumerate(nums):
        a = i / 12 * 2 * math.pi
        x = n / 2 + math.sin(a) * n * 0.37; y = n / 2 - math.cos(a) * n * 0.37
        w = d.textlength(t, font=f)
        d.text((x - w / 2, y - 26), t, font=f, fill=(30, 26, 22))
    for i in range(60):
        a = i / 60 * 2 * math.pi
        r1 = n * 0.46; r2 = n * (0.43 if i % 5 == 0 else 0.445)
        d.line((n / 2 + math.sin(a) * r1, n / 2 - math.cos(a) * r1, n / 2 + math.sin(a) * r2, n / 2 - math.cos(a) * r2), fill=(30, 26, 22), width=3)
    img.save(TEX + "clock_col.jpg", quality=88)


clock_face()
M["clock"] = material("Esfera", (1, 1, 1), 0.4, tex="clock_col.jpg")


# ---------------------------------------------------------------- utilidades
def new_object(name, bm, mats, smooth=None, parent=None, loc=None):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth is not None:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(smooth))
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    if loc is not None:
        ob.location = loc
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    COL.objects.link(e)
    if parent is not None:
        e.parent = parent
    return e


def faces_of(verts):
    return list({f for v in verts for f in v.link_faces})


def set_mat(faces, idx):
    for f in faces:
        f.material_index = idx


def box_uv(bm, scale=1.0, faces=None):
    uv = bm.loops.layers.uv.verify()
    for f in (faces if faces is not None else bm.faces):
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            c = l.vert.co
            if ax == 0:
                u, v = c.y, c.z
            elif ax == 1:
                u, v = c.x, c.z
            else:
                u, v = c.x, c.y
            l[uv].uv = (u / scale, v / scale)


def add_box(bm, center, size, mi=0, bevel=0.008, rot=None, segs=2):
    """center/size en coordenadas de Blender. rot: Matrix 3x3 opcional."""
    tmp = bmesh.new()
    r = bmesh.ops.create_cube(tmp, size=1.0)
    for v in tmp.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if bevel > 0 and min(size) > bevel * 2.5:
        bmesh.ops.bevel(tmp, geom=list(tmp.edges) + list(tmp.verts), offset=bevel, segments=segs,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    for v in tmp.verts:
        co = v.co.copy()
        if rot is not None:
            co = rot @ co
        v.co = co + Vector(center)
    for f in tmp.faces:
        f.material_index = mi
    me = bpy.data.meshes.new("_tmp"); tmp.to_mesh(me); tmp.free()
    bm.from_mesh(me); bpy.data.meshes.remove(me)


def add_cone(bm, p1, p2, r1, r2, mi=0, segs=16, flat=1.0, cap=True):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1; L = d.length
    q = d.normalized().to_track_quat("Z", "Y")
    mat = Matrix.Translation((p1 + p2) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((1, flat, 1, 1))
    r = bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=L, matrix=mat)
    set_mat(faces_of(r["verts"]), mi)
    return r["verts"]


def add_sphere(bm, c, r, mi=0, us=16, vs=10, scale=(1, 1, 1), rot=None):
    m = Matrix.Translation(Vector(c))
    if rot is not None:
        m = m @ rot.to_4x4()
    m = m @ Matrix.Diagonal((*scale, 1))
    res = bmesh.ops.create_uvsphere(bm, u_segments=us, v_segments=vs, radius=r, matrix=m)
    set_mat(faces_of(res["verts"]), mi)
    return res["verts"]


def add_torus(bm, c, R, r, mi=0, axis="Z", seg=24, rseg=8):
    verts = []
    ring = []
    for i in range(seg):
        a = i / seg * 2 * math.pi
        row = []
        for j in range(rseg):
            b = j / rseg * 2 * math.pi
            x = (R + r * math.cos(b)) * math.cos(a); y = (R + r * math.cos(b)) * math.sin(a); z = r * math.sin(b)
            p = Vector((x, y, z))
            if axis == "X":
                p = Vector((z, x, y))
            elif axis == "Y":
                p = Vector((x, z, y))
            row.append(bm.verts.new(Vector(c) + p))
        ring.append(row)
    for i in range(seg):
        for j in range(rseg):
            f = bm.faces.new((ring[i][j], ring[(i + 1) % seg][j], ring[(i + 1) % seg][(j + 1) % rseg], ring[i][(j + 1) % rseg]))
            f.material_index = mi


def tube(bm, pts, radii, mi=0, segs=10, cap=True):
    """Barre un círculo a lo largo de una polilínea (coordenadas Blender)."""
    rings = []
    n = len(pts)
    up = Vector((0, 0, 1))
    prev_side = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        side = t.cross(up)
        if side.length < 1e-4:
            side = prev_side or Vector((1, 0, 0))
        side.normalize(); prev_side = side
        nrm = side.cross(t).normalized()
        ring = []
        for j in range(segs):
            a = j / segs * 2 * math.pi
            ring.append(bm.verts.new(p + (side * math.cos(a) + nrm * math.sin(a)) * radii[i]))
        rings.append(ring)
    for i in range(n - 1):
        for j in range(segs):
            f = bm.faces.new((rings[i][j], rings[i][(j + 1) % segs], rings[i + 1][(j + 1) % segs], rings[i + 1][j]))
            f.material_index = mi
    if cap:
        for ring in (rings[0], rings[-1]):
            f = bm.faces.new(ring if ring is rings[-1] else list(reversed(ring)))
            f.material_index = mi


def sector(bm, r0, r1, a0, a1, y0, y1, mi_top=0, mi_side=None, segs=None, cx=CX, cz=CZ):
    """Prisma de corona circular (en coordenadas Three: y vertical). UV por longitud de arco."""
    if mi_side is None:
        mi_side = mi_top
    if segs is None:
        segs = max(4, int(abs(a1 - a0) * r1 / 0.25))
    uv = bm.loops.layers.uv.verify()
    rings = []
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        s, c = math.sin(a), math.cos(a)
        ring = []
        for (r, y) in ((r0, y0), (r1, y0), (r1, y1), (r0, y1)):
            ring.append(bm.verts.new(P(cx + r * s, y, cz + r * c)))
        rings.append((a, ring))
    rmid = (r0 + r1) / 2

    def face(vs, uvs, mi):
        f = bm.faces.new(vs); f.material_index = mi
        for l, u in zip(f.loops, uvs):
            l[uv].uv = u
        return f

    for i in range(segs):
        (aa, A), (ab, B) = rings[i], rings[i + 1]
        ua, ub = aa * rmid, ab * rmid
        # superior, inferior, interior, exterior
        face([A[3], A[2], B[2], B[3]], [(ua, r0), (ua, r1), (ub, r1), (ub, r0)], mi_top)
        face([A[0], B[0], B[1], A[1]], [(ua, r0), (ub, r0), (ub, r1), (ua, r1)], mi_side)
        face([A[0], A[3], B[3], B[0]], [(aa * r0, y0), (aa * r0, y1), (ab * r0, y1), (ab * r0, y0)], mi_side)
        face([A[1], B[1], B[2], A[2]], [(aa * r1, y0), (ab * r1, y0), (ab * r1, y1), (aa * r1, y1)], mi_side)
    for k, (a, R) in enumerate((rings[0], rings[-1])):
        vs = [R[0], R[1], R[2], R[3]] if k == 0 else [R[3], R[2], R[1], R[0]]
        uvs = [(r0, y0), (r1, y0), (r1, y1), (r0, y1)] if k == 0 else [(r0, y1), (r1, y1), (r1, y0), (r0, y0)]
        face(vs, uvs, mi_side)


def yaw(theta):
    """Rotación Three alrededor de Y == rotación Blender alrededor de Z."""
    return Matrix.Rotation(theta, 3, "Z")


# ---------------------------------------------------------------- sala
def build_room():
    # Suelo
    bm = bmesh.new()
    add_box(bm, P(0, -0.05, -0.1), (24.6, 15.9, 0.1), 0, bevel=0)
    box_uv(bm, 1.6)
    new_object("Suelo", bm, [M["parquet"]])

    # Gradas, pupitres y bancos
    bm = bmesh.new()
    seats = []
    for r in range(TIERS):
        a = A0 + BAND * r
        h = RISE * r
        w = 0.55 / a
        blocks = [(-SPAN, AISLES[0] - w), (AISLES[0] + w, AISLES[1] - w), (AISLES[1] + w, SPAN)]
        aisles = [(AISLES[0] - w, AISLES[0] + w), (AISLES[1] - w, AISLES[1] + w)]
        if r > 0:
            for (b0, b1) in blocks:
                sector(bm, a, a + BAND, b0, b1, 0, h, 2, 1)
            for (b0, b1) in aisles:
                sector(bm, a, a + BAND / 2, b0, b1, 0, h - RISE / 2, 2, 1)
                sector(bm, a + BAND / 2, a + BAND, b0, b1, 0, h, 2, 1)
        for (b0, b1) in blocks:
            sector(bm, a + 0.12, a + 0.16, b0, b1, h, h + 0.72, 1, 1)          # frente del pupitre
            sector(bm, a + 0.04, a + 0.5, b0, b1, h + 0.72, h + 0.76, 0, 0)    # tablero
            sector(bm, a + 0.68, a + 1.08, b0, b1, h + 0.42, h + 0.46, 0, 0)   # asiento
            sector(bm, a + 0.94, a + 0.98, b0, b1, h, h + 0.42, 1, 1)          # apoyo del asiento
            sector(bm, a + 1.1, a + 1.14, b0, b1, h + 0.5, h + 0.95, 0, 0)     # respaldo
            # posiciones de asiento
            arc = (b1 - b0) * (a + 0.9)
            k = int(arc / 0.62)
            for i in range(k):
                ang = b0 + (b1 - b0) * (i + 0.5) / k
                rr = a + 0.92
                seats.append([round(CX + rr * math.sin(ang), 3), round(h + 0.46, 3), round(CZ + rr * math.cos(ang), 3), round(ang + math.pi, 4), r])
    # Pasillo superior
    sector(bm, A0 + BAND * TIERS, WALL_R - 0.05, -math.pi / 2, math.pi / 2, 0, WALK_H, 2, 1)
    new_object("Gradas", bm, [M["oak"], M["walnut"], M["parquet"]], smooth=30)
    s = empty("Seats")
    s["seats"] = json.dumps(seats)
    print("asientos:", len(seats))

    # Muro curvo, zócalo y cornisa
    bm = bmesh.new()
    sector(bm, WALL_R, WALL_R + 0.25, -math.pi / 2, math.pi / 2, 0, ROOM_H, 0, 0, segs=96)
    new_object("MuroCurvo", bm, [M["plaster"]], smooth=40)
    bm = bmesh.new()
    sector(bm, WALL_R - 0.04, WALL_R, -math.pi / 2, math.pi / 2, WALK_H, WALK_H + 1.15, 0, 0, segs=96)
    sector(bm, WALL_R - 0.09, WALL_R, -math.pi / 2, math.pi / 2, WALK_H + 1.12, WALK_H + 1.22, 0, 0, segs=96)
    sector(bm, WALL_R - 0.18, WALL_R, -math.pi / 2, math.pi / 2, ROOM_H - 0.3, ROOM_H - 0.12, 1, 1, segs=96)
    new_object("Zocalo", bm, [M["walnut"], M["paint_white"]], smooth=40)

    # Muros laterales rectos y muro del fondo con ventanas
    bm = bmesh.new()
    for sx in (-1, 1):
        x = sx * (WALL_R + 0.12)
        add_box(bm, P(x, ROOM_H / 2, (CZ + BACK_Z) / 2), (0.25, CZ - BACK_Z + 0.3, ROOM_H), 0, bevel=0)
    wins = [-8.6, -4.6, 4.6, 8.6]
    sill, top, ww = 2.9, 6.3, 1.7
    W = 2 * WALL_R + 0.5
    add_box(bm, P(0, sill / 2, BACK_Z), (W, 0.3, sill), 0, bevel=0)
    add_box(bm, P(0, (top + ROOM_H) / 2, BACK_Z), (W, 0.3, ROOM_H - top), 0, bevel=0)
    edges = [-W / 2] + [e for x in wins for e in (x - ww / 2, x + ww / 2)] + [W / 2]
    for i in range(0, len(edges), 2):
        x0, x1 = edges[i], edges[i + 1]
        add_box(bm, P((x0 + x1) / 2, (sill + top) / 2, BACK_Z), (x1 - x0, 0.3, top - sill), 0, bevel=0)
    box_uv(bm, 2.0)
    new_object("Muros", bm, [M["plaster"]])

    # Zócalo de paneles en el muro del fondo
    bm = bmesh.new()
    zf = BACK_Z + 0.16
    add_box(bm, P(0, 1.3, zf), (W - 0.6, 0.04, 2.6), 0, bevel=0.004)
    n = 18
    pw = (W - 1.2) / n
    for i in range(n):
        x = -W / 2 + 0.6 + pw * (i + 0.5)
        add_box(bm, P(x, 1.05, zf + 0.03), (pw - 0.14, 0.03, 1.5), 0, bevel=0.012)
        add_box(bm, P(x, 2.25, zf + 0.03), (pw - 0.14, 0.03, 0.45), 0, bevel=0.012)
    add_box(bm, P(0, 2.64, zf + 0.04), (W - 0.6, 0.08, 0.1), 0, bevel=0.01)
    add_box(bm, P(0, 0.07, zf + 0.04), (W - 0.6, 0.06, 0.14), 0, bevel=0.01)
    box_uv(bm, 1.0)
    new_object("Boiserie", bm, [M["walnut"]], smooth=30)

    # Ventanas: marco, cielo, lamas semientornadas
    bm = bmesh.new()
    for x in wins:
        zc = BACK_Z
        for (dx, dy, sx, sy) in ((-(ww / 2 + 0.05), (sill + top) / 2, 0.1, top - sill + 0.2), ((ww / 2 + 0.05), (sill + top) / 2, 0.1, top - sill + 0.2),
                                 (0, top + 0.05, ww + 0.2, 0.1), (0, sill - 0.05, ww + 0.3, 0.1), (0, (sill + top) / 2, 0.06, top - sill)):
            add_box(bm, P(x + dx, dy, zc + 0.12), (sx, 0.12, sy), 0, bevel=0.01)
        add_box(bm, P(x, (sill + top) / 2 + 0.6, zc + 0.12), (ww, 0.12, 0.06), 0, bevel=0.01)
    box_uv(bm, 1.0)
    new_object("Ventanas", bm, [M["paint_white"]], smooth=30)
    bm = bmesh.new()
    for x in wins:
        add_box(bm, P(x, (sill + top) / 2, BACK_Z - 0.4), (ww + 0.4, 0.02, top - sill + 0.4), 0, bevel=0)
    new_object("Cielo", bm, [M["window"]])
    bm = bmesh.new()
    tilt = Matrix.Rotation(math.radians(-38), 3, "X")
    for x in wins:
        for k in range(30):
            y = sill + 0.08 + k * (top - sill - 0.16) / 29
            add_box(bm, P(x, y, BACK_Z + 0.05), (ww - 0.04, 0.07, 0.006), 0, bevel=0, rot=tilt)
    new_object("Lamas", bm, [M["paint_white"]])

    # Techo con casetones
    bm = bmesh.new()
    add_box(bm, P(0, ROOM_H + 0.1, -0.1), (2 * WALL_R + 0.6, 15.9, 0.2), 0, bevel=0)
    box_uv(bm, 2.0)
    new_object("Techo", bm, [M["plaster"]])
    bm = bmesh.new()
    for i in range(-5, 6):
        add_box(bm, P(i * 2.4, ROOM_H - 0.18, -0.2), (0.22, 15.6, 0.36), 0, bevel=0.02)
    for j in range(-3, 4):
        add_box(bm, P(0, ROOM_H - 0.18, -1.2 + j * 2.4), (2 * WALL_R, 0.22, 0.36), 0, bevel=0.02)
    box_uv(bm, 1.0)
    new_object("Casetones", bm, [M["paint_white"]], smooth=30)

    # Lámparas colgantes
    bm = bmesh.new()
    lamps = [(-4.5, -2.0), (4.5, -2.0), (-6.5, 3.0), (6.5, 3.0), (-3.0, -6.2), (3.0, -6.2)]
    for (x, z) in lamps:
        add_sphere(bm, P(x, 5.5, z), 0.22, 0, 20, 12)
        add_cone(bm, P(x, 5.7, z), P(x, ROOM_H - 0.3, z), 0.012, 0.012, 1, 8)
        add_cone(bm, P(x, 5.68, z), P(x, 5.78, z), 0.08, 0.045, 2, 16)
    new_object("Lamparas", bm, [M["lamp"], M["black"], M["gold"]], smooth=40)
    e = empty("LampPositions")
    e["lamps"] = json.dumps([[x, 5.5, z] for (x, z) in lamps])

    # Puertas superiores
    bm = bmesh.new()
    for ang in (-0.95, 0.95):
        r = WALL_R - 0.03
        cx_, cz_ = CX + r * math.sin(ang), CZ + r * math.cos(ang)
        rot = yaw(ang + math.pi)
        c = P(cx_, WALK_H + 1.15, cz_)
        add_box(bm, c, (1.5, 0.06, 2.3), 0, bevel=0.01, rot=rot)
        for dx in (-0.36, 0.36):
            add_box(bm, c + rot @ Vector((dx, -0.03, 0.4)), (0.6, 0.04, 0.95), 1, bevel=0.015, rot=rot)
            add_box(bm, c + rot @ Vector((dx, -0.03, -0.6)), (0.6, 0.04, 0.8), 1, bevel=0.015, rot=rot)
        add_box(bm, c + rot @ Vector((0, -0.05, 1.22)), (1.7, 0.1, 0.16), 1, bevel=0.015, rot=rot)
        add_sphere(bm, c + rot @ Vector((0.1, -0.08, 0)), 0.035, 2)
        add_sphere(bm, c + rot @ Vector((-0.1, -0.08, 0)), 0.035, 2)
    box_uv(bm, 1.0)
    new_object("Puertas", bm, [M["walnut"], M["oak"], M["gold"]], smooth=30)

    # Reloj
    bm = bmesh.new()
    rot = Matrix.Rotation(math.radians(90), 3, "X")
    cz_ = BACK_Z + 0.2
    c = P(0, 4.6, cz_)
    add_cone(bm, c, c + Vector((0, -0.08, 0)), 0.62, 0.62, 0, 48)
    add_torus(bm, c + Vector((0, -0.08, 0)), 0.62, 0.05, 1, axis="Y", seg=48)
    box_uv(bm, 0.8)
    new_object("RelojCaja", bm, [M["walnut"], M["gold"]], smooth=40)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    ring = []
    for i in range(48):
        a = i / 48 * 2 * math.pi
        ring.append(bm.verts.new(c + Vector((math.sin(a) * 0.56, -0.085, math.cos(a) * 0.56))))
    f = bm.faces.new(list(reversed(ring)))
    for l in f.loops:
        co = l.vert.co - c
        l[uv].uv = (0.5 + co.x / 1.12, 0.5 + co.z / 1.12)
    new_object("RelojEsfera", bm, [M["clock"]])
    bm = bmesh.new()
    add_box(bm, c + Vector((0.12, -0.1, 0.1)), (0.3, 0.01, 0.025), 0, bevel=0, rot=Matrix.Rotation(math.radians(-50), 3, "Y"))
    add_box(bm, c + Vector((0, -0.1, 0.2)), (0.018, 0.01, 0.42), 0, bevel=0)
    new_object("RelojAgujas", bm, [M["black"]])
    return seats


# ---------------------------------------------------------------- maniquíes
exec(open(ROOT + "/src/figures.py", encoding="utf-8").read())


def mannequin(name, pose="sit", girth=1.0, scale=1.0, clothes=None, segs=14, sph=(14, 9), head=1.0,
              raise_right=False, loc=(0, 0, 0), theta=0.0, parent=None, extra=None):
    """Maniquí articulado. Origen: centro del asiento (sentado) o suelo (de pie). Frente: -Y local."""
    bm = bmesh.new()
    S = lambda x, y, z: Vector((x, y, z)) * scale
    gt = girth
    if pose == "sit":
        pelvis = S(0, 0.02, 0.12); waist = S(0, 0.03, 0.30); chest = S(0, 0.04, 0.52)
        neck0 = S(0, 0.04, 0.58); headc = S(0, 0.03, 0.74)
        hips = [S(sx * 0.1, 0, 0.1) for sx in (-1, 1)]
        knees = [S(sx * 0.11, -0.44, 0.12) for sx in (-1, 1)]
        ankles = [S(sx * 0.11, -0.47, -0.36) for sx in (-1, 1)]
        shoulders = [S(sx * 0.19 * (0.9 + 0.1 * gt), 0.04, 0.50) for sx in (-1, 1)]
        elbows = [S(sx * 0.23 * (0.9 + 0.1 * gt), -0.06, 0.28) for sx in (-1, 1)]
        wrists = [S(sx * 0.15, -0.36, 0.30) for sx in (-1, 1)]
    else:
        pelvis = S(0, 0, 0.98); waist = S(0, 0.01, 1.14); chest = S(0, 0.01, 1.38)
        neck0 = S(0, 0.01, 1.45); headc = S(0, 0.0, 1.62)
        hips = [S(sx * 0.1, 0, 0.94) for sx in (-1, 1)]
        knees = [S(sx * 0.1, -0.02, 0.52) for sx in (-1, 1)]
        ankles = [S(sx * 0.1, 0.02, 0.09) for sx in (-1, 1)]
        shoulders = [S(sx * 0.19 * (0.9 + 0.1 * gt), 0.01, 1.40) for sx in (-1, 1)]
        elbows = [S(-0.24, -0.02, 1.13), S(0.24, -0.02, 1.13)]
        wrists = [S(-0.25, -0.06, 0.87), S(0.20, -0.30, 1.08)]
        if raise_right:
            elbows[0] = S(-0.30, -0.12, 1.42)
            wrists[0] = S(-0.27, -0.24, 1.70)
    C, K, Sh = 1, 0, 2  # índices: piel, ropa, calzado
    # tronco
    add_cone(bm, pelvis, waist, 0.15 * gt * scale, 0.135 * gt * scale, C, segs, flat=0.7)
    add_cone(bm, waist, chest, 0.135 * gt * scale, 0.17 * (0.85 + 0.15 * gt) * scale, C, segs, flat=0.68)
    add_sphere(bm, pelvis, 0.15 * gt * scale, C, segs, sph[1], scale=(1, 0.7, 0.75))
    add_sphere(bm, chest, 0.17 * (0.85 + 0.15 * gt) * scale, C, segs, sph[1], scale=(1, 0.68, 0.55))
    add_cone(bm, neck0, neck0 + S(0, -0.005, 0.1), 0.055 * scale, 0.05 * scale, K, 10)
    hc = headc
    add_sphere(bm, hc, 0.1 * head * scale, K, sph[0] + 4, sph[1] + 4, scale=(0.92, 1.0, 1.22))
    if gt > 1.2:
        add_sphere(bm, hc + S(0, -0.05, -0.1), 0.065 * scale, K, 12, 8, scale=(1.2, 0.9, 0.7))  # papada
    # brazos
    for i in range(2):
        add_sphere(bm, shoulders[i], 0.06 * (0.9 + 0.1 * gt) * scale, C, 12, 8)
        add_cone(bm, shoulders[i], elbows[i], 0.058 * (0.9 + 0.1 * gt) * scale, 0.045 * scale, C, segs)
        add_sphere(bm, elbows[i], 0.045 * scale, C, 10, 7)
        add_cone(bm, elbows[i], wrists[i], 0.045 * scale, 0.036 * scale, C, segs)
        d = (wrists[i] - elbows[i]).normalized()
        q = d.to_track_quat("Z", "Y").to_matrix()
        add_sphere(bm, wrists[i] + d * 0.06 * scale, 0.05 * scale, K, 12, 8, scale=(0.75, 0.42, 1.35), rot=q)
    # piernas
    for i in range(2):
        add_sphere(bm, hips[i], 0.085 * gt * scale, C, 12, 8)
        add_cone(bm, hips[i], knees[i], 0.085 * gt * scale, 0.058 * scale, C, segs)
        add_sphere(bm, knees[i], 0.058 * scale, C, 10, 7)
        add_cone(bm, knees[i], ankles[i], 0.056 * scale, 0.04 * scale, C, segs)
        foot = ankles[i] + S(0, -0.08, -0.05)
        tmpm = bmesh.new()
        add_box(bm, foot, (0.1 * scale, 0.26 * scale, 0.08 * scale), Sh, bevel=0.02 * scale, segs=2)
    if extra:
        extra(bm, S, headc)
    box_uv(bm, 0.35)
    mats = [M["skin"], clothes or M["skin"], M["shoe"]]
    if extra and hasattr(extra, "mats"):
        mats += extra.mats
    ob = new_object(name, bm, mats, smooth=50, parent=parent)
    ob.matrix_world = Matrix.Translation(Vector(loc)) @ yaw(theta).to_4x4()
    return ob


def world_point(ob, p):
    return ob.matrix_world @ p


# ---------------------------------------------------------------- tribunal
def build_tribunal():
    T = empty("Tribunal")
    bm = bmesh.new()
    add_box(bm, P(0, 0.15, -5.05), (7.6, 2.9, 0.3), 1, bevel=0.015)        # estrado
    add_box(bm, P(0, 0.075, -3.42), (5.2, 0.4, 0.15), 1, bevel=0.012)      # peldaño
    add_box(bm, P(0, 0.305, -5.05), (7.66, 2.96, 0.02), 0, bevel=0.005)   # canto de mármol
    box_uv(bm, 1.2)
    new_object("Estrado", bm, [M["marble"], M["walnut"]], smooth=30, parent=T)

    # Mesa con tapete verde
    bm = bmesh.new()
    top_y = 0.3 + 0.76
    add_box(bm, P(0, top_y - 0.02, -4.7), (4.6, 1.1, 0.04), 0, bevel=0.01)
    add_box(bm, P(0, top_y + 0.012, -4.7), (4.68, 1.16, 0.024), 1, bevel=0.008)
    add_box(bm, P(0, 0.3 + 0.38, -4.7 + 0.585), (4.68, 0.02, 0.72), 1, bevel=0.004)   # faldón frontal
    for sx in (-1, 1):
        add_box(bm, P(sx * 2.335, 0.3 + 0.38, -4.7), (0.02, 1.16, 0.72), 1, bevel=0.004)
    for sx in (-2.1, 2.1):
        add_box(bm, P(sx, 0.3 + 0.36, -5.15), (0.08, 0.08, 0.72), 0, bevel=0.01)
    box_uv(bm, 1.0)
    new_object("Mesa", bm, [M["walnut"], M["baize"]], smooth=30, parent=T)

    # Sillas de respaldo alto
    bm = bmesh.new()
    for x in (-1.4, 0, 1.4):
        z = -5.5
        for dx in (-0.24, 0.24):
            for dz in (-0.22, 0.2):
                add_box(bm, P(x + dx, 0.3 + 0.23, z + dz), (0.05, 0.05, 0.46), 0, bevel=0.008)
        add_box(bm, P(x, 0.3 + 0.47, z), (0.56, 0.5, 0.05), 0, bevel=0.012)
        add_box(bm, P(x, 0.3 + 0.52, z), (0.5, 0.44, 0.06), 1, bevel=0.025)
        for dx in (-0.25, 0.25):
            add_box(bm, P(x + dx, 0.3 + 0.95, z - 0.24), (0.06, 0.06, 0.95), 0, bevel=0.01)
        add_box(bm, P(x, 0.3 + 1.4, z - 0.24), (0.62, 0.08, 0.1), 0, bevel=0.02)
        add_box(bm, P(x, 0.3 + 1.0, z - 0.25), (0.44, 0.05, 0.62), 1, bevel=0.02)
    box_uv(bm, 0.8)
    new_object("Sillas", bm, [M["walnut"], M["leather_dark"]], smooth=30, parent=T)

    # Objetos sobre la mesa
    bm = bmesh.new()
    for x in (-1.4, 0, 1.4):
        add_box(bm, P(x + 0.05, top_y + 0.03, -4.55), (0.3, 0.42, 0.01), 0, bevel=0)
        add_box(bm, P(x - 0.2, top_y + 0.04, -4.48), (0.21, 0.3, 0.02), 0, bevel=0)
        add_box(bm, P(x, top_y + 0.07, -4.22), (0.34, 0.012, 0.09), 1, bevel=0.002)  # placa
    new_object("Papeles", bm, [M["paper"], M["gold"]], parent=T)
    bm = bmesh.new()
    cpos = P(0.55, top_y + 0.025, -4.75)
    add_cone(bm, cpos, cpos + Vector((0, 0, 0.18)), 0.06, 0.055, 0, 24)
    add_cone(bm, cpos + Vector((0, 0, 0.18)), cpos + Vector((0, 0, 0.26)), 0.055, 0.025, 0, 24)
    add_cone(bm, cpos + Vector((0, 0, 0.26)), cpos + Vector((0, 0, 0.3)), 0.025, 0.03, 0, 24)
    for x in (-1.15, 0.3, 1.65):
        g = P(x, top_y + 0.025, -4.62)
        add_cone(bm, g, g + Vector((0, 0, 0.11)), 0.03, 0.036, 0, 20)
    new_object("Vidrios", bm, [M["glass"]], smooth=40, parent=T)

    # Maniquíes del tribunal: presidente, vocal (mujer) y vocal joven
    seat_y = 0.3 + 0.55

    beads_mats = [material(f"Cuenta{i}", c, 0.3) for i, c in enumerate([(0.75, 0.2, 0.15), (0.2, 0.55, 0.75), (0.9, 0.62, 0.15), (0.3, 0.6, 0.3), (0.55, 0.3, 0.65)])]
    suit = cloth("Traje gris marengo", (0.13, 0.14, 0.16))
    tie = material("Corbata granate", (0.36, 0.06, 0.07), 0.5)

    def pres_extra(body, hb, arms, S, sk):
        T = sk["T"]
        loft(body, [S(T((0, -0.07, 0.535))), S(T((0, -0.14, 0.44))), S(T((0, -0.152, 0.33)))],
             [0.016 * 1, 0.026, 0.03], [0.007] * 3, 5, 6, True)
    seated("Presidente", dict(lean=0.06, hp=0.05, arms=dict(elbows=[(-0.27, -0.13, 0.28), (0.27, -0.13, 0.28)], wrists=[(-0.045, -0.41, 0.29), (0.045, -0.41, 0.29)])),
           [suit, suit, M["shoe"]], girth=1.5, w=1.05, head_scale=1.08, glasses=True,
           loc=P(0, seat_y, -5.45), theta=0.0, parent=T, split_head=True, extra_mats=[M["black"], tie], extra=pres_extra)

    def vocal_extra(body, hb, arms, S, sk):
        T = sk["T"]
        for k in range(15):
            a = -1.35 + 2.7 * k / 14
            add_sphere(body, S(T((math.sin(a) * 0.088, 0.04 - math.cos(a) * 0.072, 0.54 - 0.04 * math.cos(a)))), 0.0135, 5 + k % 5, 8, 6)
        pen_in_hand(body, S, sk, 0, 4)
    dress = cloth("Vestido azul pizarra", (0.2, 0.26, 0.36))
    seated("Vocal", dict(lean=0.24, hp=0.38, hy=0.06, arms=dict(elbows=[(-0.2, -0.17, 0.27), (0.25, -0.13, 0.27)], wrists=[(-0.07, -0.43, 0.275), (0.17, -0.39, 0.275)])),
           [dress, dress, M["shoe"]], girth=0.9, w=0.94, head_scale=0.96, skirt=True, bun=True,
           loc=P(-1.4, seat_y, -5.45), theta=0.0, parent=T, split_head=True, extra_mats=[M["black"]] + beads_mats, extra=vocal_extra)
    seated("VocalJoven", dict(lean=-0.07, hy=-0.12, arms=dict(elbows=[(-0.21, -0.1, 0.3), (0.21, -0.1, 0.3)], wrists=[(0.1, -0.21, 0.37), (-0.1, -0.2, 0.345)])),
           [cloth("Traje ocre", (0.58, 0.42, 0.2)), cloth("Pantalón pardo", (0.2, 0.17, 0.14)), M["shoe"]], girth=0.95,
           loc=P(1.4, seat_y, -5.45), theta=0.0, parent=T, split_head=True)


# ---------------------------------------------------------------- atril y opositor
def build_speaker():
    G = empty("Ponente")
    bm = bmesh.new()
    zc = -1.2
    add_box(bm, P(0, 0.04, zc), (0.62, 0.48, 0.08), 0, bevel=0.012)
    add_box(bm, P(0, 0.55, zc), (0.46, 0.32, 0.95), 0, bevel=0.015)
    for dx in (-0.14, 0.14):
        add_box(bm, P(dx, 0.55, zc + 0.165), (0.12, 0.02, 0.7), 1, bevel=0.01)
    tilt = Matrix.Rotation(math.radians(16), 3, "X")
    add_box(bm, P(0, 1.08, zc + 0.02), (0.66, 0.5, 0.05), 0, bevel=0.012, rot=tilt)
    add_box(bm, P(0, 1.06, zc + 0.27), (0.62, 0.03, 0.05), 0, bevel=0.01)
    box_uv(bm, 0.8)
    new_object("Atril", bm, [M["walnut"], M["oak"]], smooth=30, parent=G)
    bm = bmesh.new()
    add_box(bm, P(0.03, 1.12, zc + 0.04), (0.21, 0.3, 0.004), 0, bevel=0, rot=tilt)
    new_object("Notas", bm, [M["paper"]], parent=G)
    bm = bmesh.new()
    base = P(-0.22, 1.1, zc - 0.08)
    pts = [base + Vector((0, 0.03 * k * k / 10, 0.05 * k)) for k in range(8)]
    tube(bm, pts, [0.006] * 8, 0, 8)
    add_cone(bm, pts[-1], pts[-1] + Vector((0, -0.05, 0.02)), 0.012, 0.016, 0, 12)
    new_object("Microfono", bm, [M["black"]], smooth=40, parent=G)

    sk = standing_skeleton()
    opp, piv = figure("Opositor", sk, [cloth("Chaqueta gris", (0.3, 0.31, 0.34)), cloth("Pantalón gris oscuro", (0.12, 0.12, 0.13)), M["shoe"]],
                      loc=P(0, 0, -0.62), theta=math.pi, parent=G, split_head=True, split_arm=0)
    # Pluma en la mano derecha alzada (hija del pivote del brazo)
    bm = bmesh.new()
    add_cone(bm, (0, 0, -0.06), (0, 0, 0.06), 0.006, 0.006, 0, 12)
    add_cone(bm, (0, 0, 0.06), (0, 0, 0.075), 0.0065, 0.0065, 1, 12)
    add_cone(bm, (0, 0, -0.06), (0, 0, -0.08), 0.006, 0.0015, 1, 12)
    add_box(bm, (0.0075, 0, 0.035), (0.002, 0.003, 0.035), 1, bevel=0)
    pen = new_object("Pen", bm, [M["black"], M["gold"]], smooth=40)
    wr, el = sk["wrists"][0], sk["elbows"][0]
    hand = opp.matrix_world @ (wr + (wr - el).normalized() * 0.075)
    want = Matrix.Translation(hand) @ Euler((math.radians(25), math.radians(-15), 0)).to_matrix().to_4x4()
    arm = piv["Brazo"]
    pen.parent = arm
    pen.matrix_parent_inverse = Matrix.Identity(4)
    pen.matrix_basis = arm.matrix_world.inverted() @ want


# ---------------------------------------------------------------- estaciones
def book(bm, c, size, mi_cover, mi_page, rot=None):
    sx, sy, sz = size
    add_box(bm, c, (sx, sy, sz), mi_cover, bevel=0.004, rot=rot)
    off = Vector((0.006, 0, 0))
    add_box(bm, c + (rot @ off if rot else off), (sx - 0.006, sy - 0.012, sz - 0.008), mi_page, bevel=0, rot=rot)


def build_st2():
    G = empty("ST2")
    top_y = 0.3 + 0.76 + 0.025
    bm = bmesh.new()
    y = top_y
    sizes = [(0.32, 0.24, 0.07), (0.3, 0.22, 0.06), (0.28, 0.21, 0.08), (0.26, 0.2, 0.05), (0.22, 0.17, 0.05)]
    for i, (a, b, h) in enumerate(sizes):
        rot = Matrix.Rotation(math.radians([-6, 8, -3, 12, -10][i]), 3, "Z")
        book(bm, P(-1.95, y + h / 2, -4.55), (a, b, h), i % 3, 3, rot)
        y += h
    box_uv(bm, 0.3)
    new_object("Codices", bm, [M["leather_red"], M["leather_brown"], M["leather_green"], M["parchment"]], smooth=30, parent=G)
    bm = bmesh.new()
    for k in range(3):
        c = P(1.95, top_y + 0.045 + (0.07 if k == 2 else 0), -4.5 + (k % 2) * 0.1 - (0.05 if k == 2 else 0))
        ax = Vector((1, 0.15 * (k - 1), 0)).normalized()
        add_cone(bm, c - ax * 0.17, c + ax * 0.17, 0.045, 0.045, 0, 20)
        for sgn in (-1, 1):
            add_cone(bm, c + ax * 0.17 * sgn, c + ax * 0.22 * sgn, 0.012, 0.012, 1, 10)
            add_sphere(bm, c + ax * 0.225 * sgn, 0.018, 1, 10, 6)
    box_uv(bm, 0.3)
    new_object("Rollos", bm, [M["parchment"], M["walnut"]], smooth=40, parent=G)

    # Columna de las Serpientes
    cx, cz = 4.0, -2.6
    bm = bmesh.new()
    add_box(bm, P(cx, 0.15, cz), (0.8, 0.8, 0.3), 0, bevel=0.02)
    add_box(bm, P(cx, 0.34, cz), (0.62, 0.62, 0.08), 0, bevel=0.015)
    box_uv(bm, 0.6)
    new_object("ColumnaBase", bm, [M["marble"]], smooth=30, parent=G)
    bm = bmesh.new()
    H = 1.9
    for k in range(3):
        pts, rad = [], []
        n = 160
        for i in range(n + 1):
            t = i / n
            a = t * math.pi * 2 * 4.5 + k * 2 * math.pi / 3
            rr = 0.085 + 0.02 * t
            pts.append(P(cx + math.cos(a) * rr, 0.38 + t * H, cz + math.sin(a) * rr))
            rad.append(0.066 - 0.016 * t)
        # cuello y cabeza que se abren hacia fuera
        a_end = math.pi * 2 * 4.5 + k * 2 * math.pi / 3
        for j in range(1, 9):
            t = j / 8
            pts.append(P(cx + math.cos(a_end) * (0.13 + 0.28 * t), 0.38 + H + 0.12 * math.sin(t * math.pi * 0.8), cz + math.sin(a_end) * (0.13 + 0.28 * t)))
            rad.append(0.065 - 0.012 * t)
        tube(bm, pts, rad, 0, 12)
        hp = pts[-1]
        dirv = (pts[-1] - pts[-2]).normalized()
        add_sphere(bm, hp + dirv * 0.06, 0.07, 0, 14, 10, scale=(1.0, 0.75, 1.6), rot=dirv.to_track_quat("Z", "Y").to_matrix())
    box_uv(bm, 0.4)
    new_object("ColumnaSerpientes", bm, [M["bronze"]], smooth=60, parent=G)


def build_st3():
    G = empty("ST3")
    cx, cz = -4.0, -2.6
    bm = bmesh.new()
    add_box(bm, P(cx, 0.05, cz), (0.78, 0.78, 0.1), 1, bevel=0.015)
    add_box(bm, P(cx, 0.55, cz), (0.62, 0.62, 0.9), 0, bevel=0.012)
    add_box(bm, P(cx, 1.02, cz), (0.7, 0.7, 0.05), 1, bevel=0.012)
    add_box(bm, P(cx, 0.75, cz + 0.312), (0.26, 0.004, 0.08), 2, bevel=0)
    box_uv(bm, 0.8)
    new_object("Pedestal", bm, [M["marble"], M["walnut"], M["gold"]], smooth=30, parent=G)
    bm = bmesh.new()
    add_box(bm, P(cx, 1.62, cz), (0.6, 0.6, 1.14), 0, bevel=0)
    new_object("Vitrina", bm, [M["glass"]], parent=G)
    bm = bmesh.new()
    for dx in (-0.3, 0.3):
        for dz in (-0.3, 0.3):
            add_box(bm, P(cx + dx, 1.62, cz + dz), (0.018, 0.018, 1.15), 0, bevel=0.003)
    for dy in (1.05, 2.19):
        for (dx, dz, sx, sz) in ((0, -0.3, 0.62, 0.018), (0, 0.3, 0.62, 0.018), (-0.3, 0, 0.018, 0.62), (0.3, 0, 0.018, 0.62)):
            add_box(bm, P(cx + dx, dy, cz + dz), (sx, sz, 0.018), 0, bevel=0.003)
    new_object("VitrinaMarco", bm, [M["gold"]], parent=G)
    # La Tizona (origen en su centro para girarla)
    bm = bmesh.new()
    L = 0.88
    add_cone(bm, (0, 0, -L / 2 + 0.04), (0, 0, L / 2 - 0.12), 0.024, 0.028, 0, 4, flat=0.16)
    add_cone(bm, (0, 0, -L / 2 - 0.02), (0, 0, -L / 2 + 0.04), 0.002, 0.024, 0, 4, flat=0.16)
    add_box(bm, (0, 0, L / 2 - 0.1), (0.24, 0.03, 0.03), 1, bevel=0.008)
    add_sphere(bm, (0.125, 0, L / 2 - 0.1), 0.02, 1, 10, 6)
    add_sphere(bm, (-0.125, 0, L / 2 - 0.1), 0.02, 1, 10, 6)
    add_cone(bm, (0, 0, L / 2 - 0.085), (0, 0, L / 2 + 0.02), 0.016, 0.015, 2, 12)
    add_sphere(bm, (0, 0, L / 2 + 0.05), 0.032, 1, 14, 10, scale=(1, 0.55, 1))
    box_uv(bm, 0.3)
    sw = new_object("Sword", bm, [M["steel"], M["gold"], M["leather_dark"]], smooth=40, parent=G)
    sw.location = P(cx, 1.62, cz)
    # Piedra de Scone sobre plinto
    sx, sz = 3.7, -2.5
    bm = bmesh.new()
    add_box(bm, P(sx, 0.12, sz), (0.9, 0.62, 0.24), 0, bevel=0.012)
    box_uv(bm, 0.8)
    new_object("PlintoScone", bm, [M["walnut"]], smooth=30, parent=G)
    bm = bmesh.new()
    add_box(bm, P(sx, 0.24 + 0.135, sz), (0.66, 0.42, 0.27), 0, bevel=0.035, segs=3)
    add_box(bm, P(sx, 0.24 + 0.272, sz), (0.12, 0.02, 0.006), 0, bevel=0)
    add_box(bm, P(sx, 0.24 + 0.272, sz), (0.02, 0.12, 0.006), 0, bevel=0)
    box_uv(bm, 0.5)
    new_object("PiedraScone", bm, [M["stone"]], smooth=35, parent=G)
    bm = bmesh.new()
    for d in (-1, 1):
        add_torus(bm, P(sx + d * 0.36, 0.24 + 0.17, sz), 0.07, 0.012, 0, axis="X", seg=20, rseg=8)
    new_object("Anillas", bm, [M["iron"]], smooth=40, parent=G)


def ship(bm, c, length=0.46, mi_hull=0, mi_sail=1, mi_dark=2, sails=True):
    """Carraca esquemática: casco por secciones, castillos, palos y velas."""
    n = 14
    rings = []
    for i in range(n + 1):
        t = i / n
        x = (t - 0.5) * length
        w = 0.085 * math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.7
        hdeck = 0.075 + 0.04 * (abs(t - 0.5) * 2) ** 2
        ring = []
        for j in range(9):
            a = math.pi * j / 8
            y = -math.cos(a) * w
            z = -math.sin(a) * 0.075 * (0.6 + 0.4 * math.sin(math.pi * t))
            ring.append(bm.verts.new(c + Vector((x, y, z + 0.02))))
        ring.insert(0, bm.verts.new(c + Vector((x, -w, hdeck))))
        ring.append(bm.verts.new(c + Vector((x, w, hdeck))))
        rings.append(ring)
    for i in range(n):
        for j in range(len(rings[0]) - 1):
            f = bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][j + 1], rings[i][j + 1])); f.material_index = mi_hull
    for ring in (rings[0], rings[-1]):
        f = bm.faces.new(ring if ring is rings[-1] else list(reversed(ring))); f.material_index = mi_hull
    add_box(bm, c + Vector((-length * 0.36, 0, 0.11)), (0.11, 0.15, 0.06), mi_hull, bevel=0.004)
    add_box(bm, c + Vector((length * 0.38, 0, 0.1)), (0.08, 0.13, 0.05), mi_hull, bevel=0.004)
    add_cone(bm, c + Vector((length * 0.5, 0, 0.09)), c + Vector((length * 0.72, 0, 0.17)), 0.006, 0.003, mi_dark, 6)
    masts = [(-0.12, 0.34), (0.02, 0.42), (0.15, 0.3)]
    for (mx, mh) in masts:
        add_cone(bm, c + Vector((mx * length / 0.46, 0, 0.05)), c + Vector((mx * length / 0.46, 0, 0.05 + mh)), 0.006, 0.004, mi_dark, 8)
        if sails:
            for (sy0, sh, sw) in ((0.14, 0.11, 0.17), (0.27, 0.08, 0.12)):
                if sy0 + sh > mh:
                    continue
                cols = []
                for i in range(5):
                    u = i / 4
                    col = []
                    for k in range(4):
                        v = k / 3
                        col.append(bm.verts.new(c + Vector((mx * length / 0.46 + 0.02 * math.sin(v * math.pi), (u - 0.5) * sw, 0.05 + sy0 + sh * (1 - v)))))
                    cols.append(col)
                for i in range(4):
                    for k in range(3):
                        f = bm.faces.new((cols[i][k], cols[i + 1][k], cols[i + 1][k + 1], cols[i][k + 1])); f.material_index = mi_sail
                add_cone(bm, c + Vector((mx * length / 0.46, -sw / 2 - 0.01, 0.05 + sy0 + sh)), c + Vector((mx * length / 0.46, sw / 2 + 0.01, 0.05 + sy0 + sh)), 0.003, 0.003, mi_dark, 6)


def build_st4():
    G = empty("ST4")
    cx, cz = -3.35, -2.6
    bm = bmesh.new()
    for dx in (-0.63, 0.63):
        for dz in (-0.3, 0.3):
            add_box(bm, P(cx + dx, 0.42, cz + dz), (0.07, 0.07, 0.84), 0, bevel=0.01)
    add_box(bm, P(cx, 0.86, cz), (1.44, 0.72, 0.06), 0, bevel=0.012)
    for (dx, dz, sx, sz) in ((0, -0.34, 1.44, 0.04), (0, 0.34, 1.44, 0.04), (-0.7, 0, 0.04, 0.72), (0.7, 0, 0.04, 0.72)):
        add_box(bm, P(cx + dx, 0.92, cz + dz), (sx, sz, 0.08), 0, bevel=0.008)
    box_uv(bm, 0.8)
    new_object("MesaMaqueta", bm, [M["oak"]], smooth=30, parent=G)
    bm = bmesh.new()
    add_box(bm, P(cx, 0.905, cz), (1.36, 0.64, 0.03), 0, bevel=0)
    box_uv(bm, 0.8)
    new_object("MarMaqueta", bm, [M["sea"]], parent=G)
    hull_m = material("Casco", (0.5, 0.36, 0.24), 0.6, tex="wood_col.jpg")
    for k, (dx, dz, ry, fire, tiltx) in enumerate(((-0.42, 0.1, 0.3, False, 18), (0.0, -0.08, -0.2, True, 0), (0.42, 0.12, 0.15, False, -24))):
        bm = bmesh.new()
        ship(bm, Vector((0, 0, 0)), sails=not (not fire and False))
        box_uv(bm, 0.3)
        ob = new_object(f"Ship{k}", bm, [hull_m, M["sail"], M["black"]], smooth=40, parent=G)
        sink = 0.0 if fire else -0.035
        ob.matrix_world = Matrix.Translation(P(cx + dx, 0.92 + sink, cz + dz)) @ yaw(ry).to_4x4() @ Matrix.Rotation(math.radians(tiltx), 4, "X")
        if fire:
            for j in range(6):
                bmf = bmesh.new()
                add_cone(bmf, (0, 0, 0), (0, 0, 0.16 + 0.05 * (j % 2)), 0.035, 0.0, 0, 8)
                fl = new_object(f"Flame{j}", bmf, [M["flame"]], smooth=60, parent=ob)
                fl.location = (-0.18 + 0.07 * j, 0.02 * ((j % 3) - 1), 0.07)


def build_st5():
    G = empty("ST5")
    origin = P(-3.1, 0, -2.75)
    rot = yaw(0.7)
    base = Matrix.Translation(origin) @ rot.to_4x4()
    bm = bmesh.new()
    desks = []
    for row in range(2):
        for col in range(3):
            x = (col - 1) * 0.78
            z = 0.25 + row * 0.85
            desks.append((x, z))
            loc = lambda dx, dy, dz: base @ P(x + dx, dy, z + dz)
            for ddx in (-0.27, 0.27):
                add_box(bm, loc(ddx, 0.25, 0), (0.025, 0.36, 0.5), 1, bevel=0.005, rot=rot)
            add_box(bm, loc(0, 0.51, 0), (0.62, 0.42, 0.03), 0, bevel=0.006, rot=rot)
            add_box(bm, loc(0, 0.3, 0.42), (0.36, 0.34, 0.025), 0, bevel=0.006, rot=rot)
            add_box(bm, loc(0, 0.56, 0.58), (0.36, 0.025, 0.24), 0, bevel=0.006, rot=rot)
            for ddx in (-0.16, 0.16):
                add_box(bm, loc(ddx, 0.15, 0.42), (0.02, 0.3, 0.3), 1, bevel=0.004, rot=rot)
                add_box(bm, loc(ddx, 0.43, 0.58), (0.02, 0.025, 0.26), 1, bevel=0.004, rot=rot)
    box_uv(bm, 0.6)
    new_object("Pupitres", bm, [M["oak"], M["metal_grey"]], smooth=30, parent=G)
    bm = bmesh.new()
    bpos = lambda dx, dy, dz: base @ P(dx, dy, dz)
    for ddx in (-0.65, 0.65):
        add_box(bm, bpos(ddx, 0.75, -0.75), (0.05, 0.05, 1.5), 1, bevel=0.008, rot=rot @ Matrix.Rotation(math.radians(-8), 3, "X"))
    add_box(bm, bpos(0, 1.15, -0.78), (1.4, 0.05, 0.75), 1, bevel=0.01, rot=rot @ Matrix.Rotation(math.radians(-8), 3, "X"))
    box_uv(bm, 0.8)
    new_object("Caballete", bm, [M["oak"], M["walnut"]], smooth=30, parent=G)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    R = rot @ Matrix.Rotation(math.radians(-8), 3, "X")
    c = bpos(0, 1.15, -0.75)
    corners = [(-0.66, -0.33), (0.66, -0.33), (0.66, 0.33), (-0.66, 0.33)]
    vs = [bm.verts.new(c + R @ Vector((x, -0.03, y))) for (x, y) in corners]
    f = bm.faces.new(vs)
    for l, (x, y) in zip(f.loops, corners):
        l[uv].uv = (x / 1.32 + 0.5, y / 0.66 + 0.5)
    new_object("Pizarra", bm, [M["board"]], parent=G)
    kid_cols = [(0.75, 0.25, 0.22), (0.25, 0.45, 0.72), (0.45, 0.62, 0.3), (0.55, 0.38, 0.65), (0.85, 0.6, 0.25), (0.3, 0.6, 0.65)]
    kid_poses = [AUD_POSES[1], AUD_POSES[7], AUD_POSES[0], AUD_POSES[3], AUD_POSES[9], AUD_POSES[5]]
    shorts = cloth("PantalonNino", (0.16, 0.2, 0.32))
    for i, (x, z) in enumerate(desks):
        p = base @ P(x, 0.3125, z + 0.42)
        seated(f"Nino{i}", kid_poses[i], [cloth(f"RopaNino{i}", kid_cols[i]), shorts, M["shoe"]], girth=0.95, scale=0.72,
               head_scale=1.14, lod=True, skirt=(i in (1, 4)), bun=(i in (1, 4)), loc=p, theta=0.7 + math.pi, parent=G)


# ---------------------------------------------------------------- público (plantilla)
def build_audience_template():
    G = empty("AudienceTemplates")
    top = cloth("RopaPublico", (0.8, 0.8, 0.8))
    bot = cloth("PantalonPublico", (0.78, 0.78, 0.77))  # distinto de RopaPublico para que no se fusionen al optimizar
    for i, pz in enumerate(AUD_POSES):
        sk_ = i in (2, 5, 9)
        seated(f"Aud{i}", pz, [top, bot, M["shoe"]], lod=True, skirt=sk_, bun=sk_,
               girth=0.9 if sk_ else (1.0, 1.12, 1.05, 1.22)[i % 4], w=0.94 if sk_ else 1.0, parent=G)


seats = build_room()
build_tribunal()
build_speaker()
build_st2(); build_st3(); build_st4(); build_st5()
build_audience_template()

bpy.ops.wm.save_as_mainfile(filepath=OUT + "sala.blend")
bpy.ops.export_scene.gltf(filepath=OUT + "sala.glb", export_format="GLB", export_apply=True, export_extras=True,
                          export_yup=True, export_image_format="AUTO", export_cameras=False, export_lights=False)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
print("triángulos:", tris, "objetos:", len(bpy.data.objects))
print("glb:", os.path.getsize(OUT + "sala.glb"))
