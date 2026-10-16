"""Maniquíes articulados de madera con ropa (se ejecuta dentro de build.py).

Coordenadas locales de la figura: frente hacia -Y, arriba +Z.
Sentado: origen en el centro del asiento. De pie: origen en el suelo.
Materiales de cada figura: 0 madera, 1 prenda superior, 2 prenda inferior, 3 calzado, 4+ extras.
"""
from mathutils import Matrix, Vector, Euler

M["wood_fig"] = material("Madera maniquí", (0.98, 0.8, 0.6), 0.38, tex="beech_col.jpg", nrm="wood_nrm.jpg", nrm_s=0.15)


def loft(bm, pts, rx, ry, mi=0, segs=12, cap=True, side_ref=Vector((1, 0, 0))):
    """Tubo de sección elíptica a lo largo de una polilínea."""
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        side = side_ref - t * side_ref.dot(t)
        if side.length < 1e-4:
            side = Vector((0, 1, 0)) - t * t.y
        side.normalize()
        nrm = t.cross(side).normalized()
        ring = [bm.verts.new(p + side * math.cos(a) * rx[i] + nrm * math.sin(a) * ry[i])
                for a in (j / segs * 2 * math.pi for j in range(segs))]
        rings.append(ring)
    for i in range(n - 1):
        for j in range(segs):
            f = bm.faces.new((rings[i][j], rings[i][(j + 1) % segs], rings[i + 1][(j + 1) % segs], rings[i + 1][j]))
            f.material_index = mi
    if cap:
        for k, ring in enumerate((rings[0], rings[-1])):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            for j in range(segs):
                vs = (ring[j], ring[(j + 1) % segs], c) if k else (ring[(j + 1) % segs], ring[j], c)
                f = bm.faces.new(vs); f.material_index = mi


def lerp(a, b, t):
    return a + (b - a) * t


def head_geo(bm, rot, center, hs=1.0, lod=False, bun=False, glasses=False, chin=False):
    """Cabeza de maniquí: huevo con nariz, arco ciliar y orejas. rot: Matrix 3x3."""
    r = 0.098 * hs
    us, vs = (14, 10) if lod else (22, 16)
    res = bmesh.ops.create_uvsphere(bm, u_segments=us, v_segments=vs, radius=r)
    for v in res["verts"]:
        x, y, z = v.co
        k = 1.0 - 0.22 * max(0.0, -z / r)          # mentón más estrecho
        v.co = rot @ Vector((x * 0.9 * k, y * 1.0 * k, z * 1.2)) + center
    set_mat(faces_of(res["verts"]), 0)
    def part(c, rr, sc, mi=0, u=10, w=7):
        res2 = bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=w, radius=rr)
        for v in res2["verts"]:
            v.co = rot @ (Vector((v.co.x * sc[0], v.co.y * sc[1], v.co.z * sc[2])) + Vector(c)) + center
        set_mat(faces_of(res2["verts"]), mi)
    part((0, -0.088 * hs, -0.005 * hs), 0.022 * hs, (0.7, 1.0, 1.4))       # nariz
    if not lod:
        part((0, -0.075 * hs, 0.035 * hs), 0.05 * hs, (1.4, 0.35, 0.3))     # arco ciliar
        for sx in (-1, 1):
            part((sx * 0.088 * hs, 0.005, 0.0), 0.026 * hs, (0.35, 0.8, 1.2))  # orejas
    if bun:
        part((0, 0.085 * hs, 0.06 * hs), 0.05 * hs, (1, 1, 0.9), 0)
    if chin:
        part((0, -0.045 * hs, -0.105 * hs), 0.07 * hs, (1.25, 0.95, 0.6))
    if glasses:
        for sx in (-1, 1):
            c = rot @ Vector((sx * 0.034 * hs, -0.1 * hs, 0.018 * hs)) + center
            add_torus(bm, c, 0.021 * hs, 0.0035, 4, axis="Y", seg=16, rseg=6)


def hand_geo(bm, elbow, wrist, s=1.0, lod=False, up=Vector((0, 0, 1))):
    d = (wrist - elbow).normalized()
    side = up.cross(d)
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    nrm = d.cross(side).normalized()
    rot = Matrix((side, nrm, d)).transposed()
    palm = wrist + d * 0.045 * s
    res = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=1.0)
    for v in res["verts"]:
        v.co = rot @ Vector((v.co.x * 0.042 * s, v.co.y * 0.018 * s, v.co.z * 0.05 * s)) + palm
    set_mat(faces_of(res["verts"]), 0)
    tip = palm + d * 0.045 * s
    if lod:
        loft(bm, [tip - d * 0.01 * s, tip + d * 0.04 * s], [0.034 * s, 0.026 * s], [0.014 * s, 0.012 * s], 0, 8, True, side)
    else:
        for k in range(4):
            off = side * ((k - 1.5) * 0.019 * s)
            base = tip + off - d * 0.005 * s
            mid = base + d * 0.035 * s - nrm * 0.006 * s
            end = mid + d * 0.03 * s - nrm * 0.014 * s
            L = 0.85 + 0.15 * (1 - abs(k - 1.5) / 1.5)
            loft(bm, [base, lerp(base, mid, L), lerp(mid, end, L)], [0.0085 * s] * 3, [0.0075 * s] * 3, 0, 6, True, side)
    tb = palm - side * 0.035 * s - d * 0.01 * s
    loft(bm, [tb, tb - side * 0.02 * s + d * 0.03 * s, tb - side * 0.022 * s + d * 0.055 * s - nrm * 0.008 * s],
         [0.01 * s] * 3, [0.009 * s] * 3, 0, 6, True, d)


def shoe_geo(bm, ankle, s=1.0, heel=False):
    c = ankle + Vector((0, -0.075, -0.055)) * s
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=1.0)
    for v in tmp.verts:
        x, y, z = v.co
        w = 0.1 if y > 0 else 0.085
        h = 0.085 if y > 0 else 0.06
        v.co = Vector((x * w, y * 0.26, z * h + (0.01 if y < 0 else 0))) * s + c
    bmesh.ops.bevel(tmp, geom=list(tmp.edges) + list(tmp.verts), offset=0.02 * s, segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
    for f in tmp.faces:
        f.material_index = 3
    me = bpy.data.meshes.new("_tmp"); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)


def seated_skeleton(lean=0.0, roll=0.0, twist=0.0, w=1.0, arms=None):
    """Puntos del esqueleto sentado (antes de escalar). arms: dict con elbows/wrists absolutos."""
    piv = Vector((0, 0.02, 0.1))
    R = (Matrix.Rotation(twist, 3, "Z") @ Matrix.Rotation(roll, 3, "Y") @ Matrix.Rotation(lean, 3, "X"))
    T = lambda p: R @ (Vector(p) - piv) + piv
    sk = {
        "spine": [Vector((0, 0.02, 0.03)), Vector((0, 0.02, 0.12)), T((0, 0.03, 0.27))],
        "chest": [T((0, 0.03, 0.235)), T((0, 0.035, 0.42)), T((0, 0.04, 0.51)), T((0, 0.04, 0.565))],
        "neck": [T((0, 0.04, 0.55)), T((0, 0.035, 0.655))],
        "headc": T((0, 0.03, 0.745)),
        "R": R, "T": T,
        "shoulders": [T((sx * 0.185 * w, 0.04, 0.515)) for sx in (-1, 1)],
        "hips": [Vector((sx * 0.095, 0.0, 0.1)) for sx in (-1, 1)],
        "knees": [Vector((sx * 0.11, -0.43, 0.11)) for sx in (-1, 1)],
        "ankles": [Vector((sx * 0.11, -0.47, -0.39)) for sx in (-1, 1)],
    }
    a = arms or {}
    sk["elbows"] = [Vector(e) for e in a.get("elbows", [(-0.24, -0.1, 0.28), (0.24, -0.1, 0.28)])]
    sk["wrists"] = [Vector(e) for e in a.get("wrists", [(-0.15, -0.37, 0.3), (0.15, -0.37, 0.3)])]
    return sk


def standing_skeleton(w=1.0):
    sk = {
        "spine": [Vector((0, 0, 0.9)), Vector((0, 0, 0.98)), Vector((0, 0.01, 1.14))],
        "chest": [Vector((0, 0.01, 1.105)), Vector((0, 0.015, 1.3)), Vector((0, 0.02, 1.39)), Vector((0, 0.02, 1.445))],
        "neck": [Vector((0, 0.02, 1.43)), Vector((0, 0.015, 1.535))],
        "headc": Vector((0, 0.01, 1.625)),
        "R": Matrix.Identity(3), "T": lambda p: Vector(p),
        "shoulders": [Vector((sx * 0.185 * w, 0.02, 1.395)) for sx in (-1, 1)],
        "hips": [Vector((sx * 0.095, 0, 0.94)) for sx in (-1, 1)],
        "knees": [Vector((sx * 0.1, -0.02, 0.52)) for sx in (-1, 1)],
        "ankles": [Vector((sx * 0.1, 0.02, 0.09)) for sx in (-1, 1)],
        "elbows": [Vector((-0.3, -0.12, 1.42)), Vector((0.24, -0.04, 1.14))],
        "wrists": [Vector((-0.27, -0.24, 1.70)), Vector((0.2, -0.3, 1.08))],
    }
    return sk


AUD_POSES = [
    dict(name="atento", lean=0.06),
    dict(name="escribe", lean=0.3, hp=0.35, arms=dict(elbows=[(-0.2, -0.16, 0.27), (0.24, -0.12, 0.27)], wrists=[(-0.07, -0.42, 0.3), (0.17, -0.38, 0.3)])),
    dict(name="brazos cruzados", lean=-0.08, arms=dict(elbows=[(-0.21, -0.1, 0.3), (0.21, -0.1, 0.3)], wrists=[(0.1, -0.2, 0.37), (-0.1, -0.2, 0.35)])),
    dict(name="menton en la mano", lean=0.22, hp=0.12, arms=dict(elbows=[(-0.12, -0.36, 0.3), (0.24, -0.12, 0.28)], wrists=[(-0.06, -0.28, 0.54), (0.16, -0.38, 0.3)])),
    dict(name="recostado", lean=-0.16, arms=dict(elbows=[(-0.22, -0.02, 0.24), (0.22, -0.02, 0.24)], wrists=[(-0.12, -0.3, 0.14), (0.12, -0.3, 0.14)])),
    dict(name="mira izquierda", lean=0.04, twist=0.18, hy=0.65),
    dict(name="mira derecha", lean=0.04, twist=-0.18, hy=-0.65),
    dict(name="mano alzada", lean=0.0, arms=dict(elbows=[(-0.27, -0.06, 0.74), (0.24, -0.12, 0.28)], wrists=[(-0.25, -0.12, 0.99), (0.15, -0.37, 0.3)])),
    dict(name="susurra", lean=0.1, roll=0.12, twist=0.25, hy=0.8),
    dict(name="manos juntas", lean=0.12, arms=dict(elbows=[(-0.26, -0.16, 0.28), (0.26, -0.16, 0.28)], wrists=[(-0.04, -0.38, 0.32), (0.04, -0.38, 0.32)])),
]


def figure(name, sk, mats, scale=1.0, girth=1.0, lod=False, skirt=False, bun=False, glasses=False, chin=False,
           head_scale=1.0, hp=0.0, hy=0.0, loc=Vector(), theta=0.0, parent=None, split_head=False, split_arm=None,
           extra_mats=(), extra=None):
    """Construye un maniquí. Devuelve (objeto cuerpo, pivotes{nombre: empty})."""
    g, s = girth, scale
    seg = 8 if lod else 12
    S = lambda p: Vector(p) * s
    world = Matrix.Translation(Vector(loc)) @ yaw(theta).to_4x4()
    pivots = {}

    def new_bm():
        return bmesh.new()

    body = new_bm()
    # Pelvis y piernas (prenda inferior)
    sp = [S(p) for p in sk["spine"]]
    loft(body, sp, [0.15 * g * s, 0.165 * g * s, 0.14 * g * s], [0.1 * g * s, 0.11 * g * s, 0.1 * g * s], 2, seg)
    if skirt:
        waist = S(sk["spine"][2]) ; kn = [S(k) for k in sk["knees"]]
        hem = (kn[0] + kn[1]) / 2 + Vector((0, 0.03, 0.0)) * s
        hip = lerp(waist, hem, 0.35) + Vector((0, 0, -0.03)) * s
        loft(body, [waist, hip, lerp(hip, hem, 0.6), hem], [0.155 * g * s, 0.2 * s, 0.205 * s, 0.215 * s],
             [0.115 * g * s, 0.12 * s, 0.105 * s, 0.1 * s], 2, 18)
    for i in range(2):
        h, k, a = S(sk["hips"][i]), S(sk["knees"][i]), S(sk["ankles"][i])
        legm = 0 if skirt else 2
        loft(body, [h, lerp(h, k, 0.4), k], [0.085 * g * s, 0.08 * g * s, 0.058 * s], [0.085 * g * s, 0.075 * g * s, 0.056 * s], legm, seg)
        add_sphere(body, k, 0.058 * s, legm, seg, 7)
        loft(body, [k, lerp(k, a, 0.35), a], [0.055 * s, 0.054 * s, 0.038 * s], [0.055 * s, 0.056 * s, 0.038 * s], legm, seg)
        add_sphere(body, a, 0.037 * s, 0, 8, 6)
        shoe_geo(body, a, s)
    # Tronco (prenda superior)
    ch = [S(p) for p in sk["chest"]]
    loft(body, ch, [0.152 * g * s, 0.165 * (0.9 + 0.1 * g) * s, 0.175 * (0.92 + 0.08 * g) * s, 0.09 * s],
         [0.108 * g * s, 0.115 * g * s, 0.1 * (0.9 + 0.1 * g) * s, 0.07 * s], 1, seg + 2)
    for i in range(2):
        add_sphere(body, S(sk["shoulders"][i]), 0.062 * (0.92 + 0.08 * g) * s, 1, seg, 8)
    # Brazos
    arm_bms = {}
    for i in range(2):
        tgt = body
        if split_arm is not None and i == split_arm:
            tgt = arm_bms.setdefault(i, new_bm())
        sh, el, wr = S(sk["shoulders"][i]), S(sk["elbows"][i]), S(sk["wrists"][i])
        loft(tgt, [sh, lerp(sh, el, 0.45), el], [0.056 * (0.9 + 0.1 * g) * s, 0.054 * s, 0.044 * s], [0.056 * s, 0.05 * s, 0.043 * s], 1, seg)
        add_sphere(tgt, el, 0.044 * s, 1, seg, 7)
        cuff = lerp(el, wr, 0.93)
        loft(tgt, [el, lerp(el, wr, 0.5), cuff], [0.045 * s, 0.043 * s, 0.037 * s], [0.044 * s, 0.04 * s, 0.035 * s], 1, seg)
        add_sphere(tgt, wr, 0.026 * s, 0, 8, 6)
        hand_geo(tgt, el, wr, 0.9 * s, lod)
    # Cuello y cabeza (madera)
    nk = [S(p) for p in sk["neck"]]
    hb = new_bm() if split_head else body
    gn = 0.8 + 0.2 * g
    loft(hb, nk, [0.048 * gn * s, 0.043 * gn * s], [0.05 * gn * s, 0.045 * gn * s], 0, seg)
    Rrel = sk["R"] @ Matrix.Rotation(hy, 3, "Z") @ Matrix.Rotation(hp, 3, "X") @ sk["R"].inverted()
    hrot = Rrel @ sk["R"]
    hc = nk[1] + Rrel @ (S(sk["headc"]) - nk[1])
    head_geo(hb, hrot, hc, hs=head_scale * s, lod=lod, bun=bun, glasses=glasses, chin=chin)
    if extra:
        extra(body, hb, arm_bms, S, sk)
    for b in (body, hb, *arm_bms.values()):
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
        box_uv(b, 0.14 * s)
    allm = [M["wood_fig"]] + list(mats) + list(extra_mats)
    ob = new_object(name, body, allm, smooth=55, parent=parent)
    ob.matrix_world = world

    def pivot_obj(label, bm_, piv_local):
        for v in bm_.verts:
            v.co -= piv_local
        e = bpy.data.objects.new(f"{name}_{label}", None)
        COL.objects.link(e)
        if parent is not None:
            e.parent = parent
        e.matrix_world = world @ Matrix.Translation(piv_local)
        me_ob = new_object(f"{name}_{label}Mesh", bm_, allm, smooth=55)
        me_ob.parent = e
        me_ob.matrix_parent_inverse = Matrix.Identity(4)
        me_ob.matrix_basis = Matrix.Identity(4)
        pivots[label] = e
        return e

    if split_head:
        pivot_obj("Cabeza", hb, nk[0].copy())
    for i, bm_ in arm_bms.items():
        pivot_obj("Brazo", bm_, S(sk["shoulders"][i]).copy())
    return ob, pivots


def seated(name, pose, mats, w=1.0, **kw):
    sk = seated_skeleton(pose.get("lean", 0.0), pose.get("roll", 0.0), pose.get("twist", 0.0), w, pose.get("arms"))
    return figure(name, sk, mats, hp=pose.get("hp", 0.0), hy=pose.get("hy", 0.0), **kw)


def pen_in_hand(bm, S, sk, i, mi_black, mi_gold=None, tilt=Vector((0.5, 0.25, 0.8))):
    wr, el = S(sk["wrists"][i]), S(sk["elbows"][i])
    d = (wr - el).normalized()
    p = wr + d * 0.075 * (S(Vector((1, 0, 0))).length) + Vector((0, 0, 0.012))
    ax = (d * 0.3 + tilt).normalized()
    add_cone(bm, p - ax * 0.07, p + ax * 0.065, 0.0055, 0.0055, mi_black, 10)
    add_cone(bm, p - ax * 0.07, p - ax * 0.088, 0.0055, 0.0012, mi_gold if mi_gold is not None else mi_black, 10)
