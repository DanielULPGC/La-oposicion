"""Texturas PBR tileables generadas por síntesis espectral (numpy).

Todas las texturas son periódicas: el ruido se genera filtrando ruido blanco
en el dominio de Fourier, lo que garantiza continuidad en los bordes.
Salida: JPEG de color (sRGB) y mapas normales (espacio tangente, OpenGL).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "tex"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1983)


def noise(n, scale, aniso=(1.0, 1.0), seed=None, power=2.0):
    """Ruido periódico n×n. scale ~ número de rasgos por lado. aniso estira ejes (x, y)."""
    r = np.random.default_rng(seed) if seed is not None else rng
    w = r.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None] * n
    fx = np.fft.fftfreq(n)[None, :] * n
    f = np.sqrt((fx * aniso[0]) ** 2 + (fy * aniso[1]) ** 2)
    f[0, 0] = 1
    filt = 1.0 / (1.0 + (f / scale) ** power)
    filt[0, 0] = 0
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * filt))
    out -= out.mean()
    return out / (out.std() + 1e-9)


def fbm(n, base, octaves=4, aniso=(1, 1), seed=0, gain=0.5):
    acc = np.zeros((n, n)); amp = 1.0; tot = 0
    for o in range(octaves):
        acc += amp * noise(n, base * 2 ** o, aniso, seed + o, power=4)
        tot += amp; amp *= gain
    return acc / tot


def ramp(t, stops):
    """t en [0,1] -> color por interpolación entre paradas [(pos, (r,g,b)), ...]."""
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    pos = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], float)
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return out


def norm01(a):
    a = a - a.min(); return a / (a.max() + 1e-9)


def save_rgb(arr, name, q=86):
    img = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "RGB")
    img.save(os.path.join(OUT, name), quality=q, optimize=True, progressive=True)


def save_normal(height, name, strength=2.0, q=90):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    nx = -gx * strength; ny = gy * strength; nz = np.ones_like(height)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    rgb = np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5
    save_rgb(rgb, name, q)


def wood(n=1024):
    # Veta a lo largo del eje X (U). Anillos periódicos deformados por ruido.
    warp = fbm(n, 2, 2, aniso=(5, 1.0), seed=11)
    y = np.linspace(0, 1, n, endpoint=False)[:, None]
    rings = np.sin(2 * np.pi * (9 * y + 0.22 * warp))
    rings = norm01(rings) ** 1.6
    grain = fbm(n, 40, 3, aniso=(14, 1.0), seed=21)
    pores = noise(n, 160, aniso=(10, 1.0), seed=31)
    blotch = fbm(n, 2, 3, seed=41)
    t = 0.32 * rings + 0.4 * norm01(grain) + 0.2 * norm01(blotch)
    t = norm01(t)
    col = ramp(t, [(0, (0.80, 0.61, 0.41)), (0.5, (0.71, 0.51, 0.32)), (1, (0.55, 0.37, 0.22))])
    col *= (1 - 0.08 * norm01(pores))[..., None]
    save_rgb(col, "wood_col.jpg")
    h = 0.5 * rings + 0.25 * norm01(grain) - 0.35 * (norm01(pores) > 0.78)
    save_normal(h, "wood_nrm.jpg", strength=3.0)


def parquet(n=1024):
    # Lamas de 1/8 del ancho de la textura, juntas escalonadas.
    rows = 8; plank_len = n // 2
    base = np.zeros((n, n, 3)); height = np.ones((n, n)) * 0.5
    y_idx = np.arange(n)
    rings_src = []
    for k in range(4):
        warp = fbm(n, 2, 2, aniso=(5, 1), seed=100 + k)
        y = np.linspace(0, 1, n, endpoint=False)[:, None]
        r = norm01(np.sin(2 * np.pi * (24 * y + 0.3 * warp))) ** 1.5
        g = norm01(fbm(n, 60, 2, aniso=(14, 1), seed=200 + k))
        rings_src.append(0.6 * r + 0.4 * g)
    rh = n // rows
    for row in range(rows):
        off = (row * plank_len * 3 // 5) % n
        for p in range(n // plank_len):
            x0 = (off + p * plank_len) % n
            idx = (row * 7 + p * 3) % 4
            tint = 0.85 + 0.25 * ((row * 13 + p * 7) % 5) / 4
            ys = slice(row * rh, (row + 1) * rh)
            xs = (np.arange(plank_len) + x0) % n
            src = rings_src[idx][ys][:, (np.arange(plank_len) + row * 97) % n]
            c = ramp(src, [(0, (0.80, 0.58, 0.36)), (0.6, (0.62, 0.40, 0.22)), (1, (0.44, 0.27, 0.14))]) * tint
            base[ys.start:ys.stop][:, xs] = np.clip(c, 0, 1)
            height[ys.start:ys.stop][:, xs] = 0.5 + 0.2 * src
            # junta de testa
            base[ys.start:ys.stop][:, x0:x0 + 2] *= 0.45
            height[ys.start:ys.stop][:, x0:x0 + 2] = 0.0
        base[row * rh: row * rh + 2] *= 0.4
        height[row * rh: row * rh + 2] = 0.0
    wear = norm01(fbm(n, 3, 3, seed=7))
    base *= (0.92 + 0.12 * wear)[..., None]
    save_rgb(np.clip(base, 0, 1), "parquet_col.jpg")
    save_normal(height, "parquet_nrm.jpg", strength=4.0)


def plaster(n=512):
    h = fbm(n, 6, 5, seed=300)
    col = ramp(norm01(h), [(0, (0.80, 0.77, 0.71)), (1, (0.90, 0.88, 0.83))])
    save_rgb(col, "plaster_col.jpg")
    save_normal(h * 0.4 + 0.2 * noise(n, 120, seed=301), "plaster_nrm.jpg", strength=1.2)


def baize(n=512):
    fib = noise(n, 200, seed=400) + 0.5 * noise(n, 90, seed=401)
    blot = fbm(n, 4, 3, seed=402)
    t = norm01(0.6 * fib + 0.4 * blot)
    col = ramp(t, [(0, (0.06, 0.20, 0.13)), (1, (0.13, 0.33, 0.22))])
    save_rgb(col, "baize_col.jpg")
    save_normal(fib, "baize_nrm.jpg", strength=1.5)


def stone(n=512):
    layers_y = np.linspace(0, 1, n, endpoint=False)[:, None]
    warp = fbm(n, 2, 4, seed=500)
    strata = norm01(np.sin(2 * np.pi * (5 * layers_y + 0.6 * warp)))
    grit = noise(n, 180, seed=501)
    t = norm01(0.15 * strata + 0.45 * norm01(fbm(n, 5, 4, seed=502)) + 0.4 * norm01(grit))
    col = ramp(t, [(0, (0.48, 0.30, 0.22)), (0.5, (0.62, 0.42, 0.30)), (1, (0.74, 0.56, 0.42))])
    save_rgb(col, "stone_col.jpg")
    save_normal(0.6 * t + 0.4 * norm01(grit), "stone_nrm.jpg", strength=2.5)


def marble(n=512):
    warp = fbm(n, 2, 5, seed=550)
    x = np.linspace(0, 1, n, endpoint=False)[None, :]
    v = np.abs(np.sin(2 * np.pi * (3 * x + 2.2 * warp)))
    t = norm01(v ** 0.25)
    col = ramp(t, [(0, (0.55, 0.53, 0.50)), (0.25, (0.80, 0.78, 0.74)), (1, (0.90, 0.89, 0.86))])
    save_rgb(col, "marble_col.jpg")


def bronze(n=512):
    patch = norm01(fbm(n, 4, 5, seed=600))
    grime = norm01(noise(n, 80, seed=601))
    verd = np.clip((patch - 0.62) * 2.5, 0, 0.7)
    metal = ramp(grime, [(0, (0.22, 0.15, 0.08)), (1, (0.42, 0.29, 0.15))])
    green = ramp(grime, [(0, (0.18, 0.28, 0.22)), (1, (0.30, 0.42, 0.34))])
    col = metal * (1 - verd[..., None]) + green * verd[..., None]
    save_rgb(col, "bronze_col.jpg")
    save_normal(patch * 0.5 + grime * 0.3, "bronze_nrm.jpg", strength=1.5)


def leather(n=512):
    cells = noise(n, 70, seed=700, power=6)
    creases = np.abs(noise(n, 40, seed=701))
    t = norm01(0.7 * norm01(cells) - 0.3 * norm01(creases))
    g = 0.55 + 0.45 * t
    col = np.stack([g, g * 0.97, g * 0.94], -1)  # neutro: se tiñe con baseColorFactor
    save_rgb(col, "leather_col.jpg")
    save_normal(t, "leather_nrm.jpg", strength=2.0)


def fabric(n=512):
    x = np.arange(n)[None, :]; y = np.arange(n)[:, None]
    weave = np.sin(2 * np.pi * (x + y) / 8) * np.sin(2 * np.pi * (x - y) / 16)
    fuzz = noise(n, 180, seed=800)
    t = norm01(0.6 * weave + 0.4 * fuzz)
    g = 0.75 + 0.25 * t
    save_rgb(np.stack([g, g, g], -1), "fabric_col.jpg")
    save_normal(weave * 0.7 + fuzz * 0.3, "fabric_nrm.jpg", strength=1.2)


def parchment(n=256):
    st = norm01(fbm(n, 3, 4, seed=900))
    col = ramp(st, [(0, (0.72, 0.62, 0.45)), (1, (0.92, 0.86, 0.72))])
    save_rgb(col, "parchment_col.jpg")


def blackboard(w=1024, h=512):
    base = fbm(h, 6, 4, seed=1000)
    base = np.tile(base, (1, w // h))
    col = ramp(norm01(base), [(0, (0.10, 0.16, 0.13)), (1, (0.17, 0.24, 0.20))])
    img = Image.fromarray((col * 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)
    try:
        f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", 58)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", 40)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    chalk = (226, 226, 214)
    d.text((70, 90), "¿Qué Historia enseñamos?", font=f1, fill=chalk)
    d.text((70, 210), "pasado  ≠  relato", font=f2, fill=chalk)
    d.text((70, 280), "fuentes → preguntas → pruebas", font=f2, fill=chalk)
    d.line((70, 175, 760, 175), fill=chalk, width=3)
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    smear = (norm01(fbm(h, 8, 3, seed=1001)) * 30).astype(np.int16)
    arr = np.array(img).astype(np.int16) + np.tile(smear, (1, w // h))[..., None] // 3
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "blackboard_col.jpg"), quality=88)


def sea(n=512):
    h = fbm(n, 5, 4, seed=1100)
    col = ramp(norm01(h), [(0, (0.04, 0.16, 0.20)), (1, (0.10, 0.30, 0.34))])
    save_rgb(col, "sea_col.jpg")
    save_normal(h, "sea_nrm.jpg", strength=3)


for fn in (wood, parquet, plaster, baize, stone, marble, bronze, leather, fabric, parchment, blackboard, sea):
    fn(); print("ok", fn.__name__)
