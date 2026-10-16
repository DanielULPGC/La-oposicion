"""Incrusta el bundle de la escena en la página y genera las variantes de publicación.

python3 assemble.py artifact  -> /home/claude/el-tribunal.html (página para el artefacto)
python3 assemble.py zip DIR   -> DIR/index.html (documento completo para el zip)
"""
import sys, re
HERE = "/home/claude/tribunal3d/web/"
src = open(HERE + "page.src.html", encoding="utf-8").read()
bundle = open(HERE + "dist/escena.min.js", encoding="utf-8").read().replace("</script", "<\\/script")
tag = "<script>\n/* Escena 3D: Three.js r170 (MIT) y código propio, empaquetados con esbuild */\n" + bundle + "\n</script>"
mode = sys.argv[1] if len(sys.argv) > 1 else "artifact"
if mode == "zip":
    tag += '\n<!-- Copias incrustadas para abrir el archivo con doble clic (file://) -->\n<script src="sala.glb.js"></script>\n<script src="sala_env.hdr.js"></script>'
page = src.replace("<!--ESCENA-->", tag)
if mode == "artifact":
    open("/home/claude/el-tribunal.html", "w", encoding="utf-8").write(page)
else:
    out = sys.argv[2]
    lines = page.split("\n")
    idx = [i for i, l in enumerate(lines) if l.strip() == "</style>"][0]
    head, body = "\n".join(lines[:idx + 1]), "\n".join(lines[idx + 1:])
    reset = ("<style>\n:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}\n"
             "body{margin:0}\nimg{max-width:100%}\n[hidden]{display:none!important}\n</style>")
    doc = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
           f"{reset}\n{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n")
    open(out + "/index.html", "w", encoding="utf-8").write(doc)
print("ok", mode, len(page))
