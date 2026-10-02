#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DRAGONES vs NOMBRE — animaciones SVG para el README de GitHub.

Guion de cada ciclo (16 s):
  1. INSERT COIN parpadea, entra un crédito (CREDIT 0 → 1) y aparece READY!
  2. Se monta el nombre.
  3. Cuatro dragones lo queman y lo hacen pedazos.
  4. GAME OVER, pasada triunfal de los dragones y vuelta a empezar.

Estilos (todos pensados para fondo blanco):
  pixel       1 · Pixel art 8-bit, transparente
  gameboy     4 · Game Boy, 4 tonos verdes dentro de la consola
  comic      15 · Cómic pop-art

Todo es SVG + CSS, sin JavaScript, así que funciona dentro de un <img> en GitHub.

Uso:
    python3 generate.py                     # los 5 estilos en ./out
    python3 generate.py --theme comic       # sólo uno
    python3 generate.py --name octocat      # otro nombre
    python3 generate.py --seed 42           # otra coreografía de escombros

Los estilos pixel y gameboy sólo usan la librería estándar de Python.
El estilo vectorial (comic) convierten tipografías en
trazados y necesitan fontTools:  pip install fonttools
"""
import argparse
import math
import os
import random
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(HERE, "fonts")

# ══════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN GENERAL
# ══════════════════════════════════════════════════════════════════════
NAME = "nikeyes"
WIDTH, HEIGHT = 800, 300
CYCLE = 16.0          # duración del bucle completo (s)
SEED = 1987           # cambia la forma en que saltan los escombros

# Guion de la partida (segundos dentro del ciclo)
T_COIN_BLINK = (0.15, 1.4)  # INSERT COIN parpadea; al final "entra" el crédito
T_READY = (1.6, 2.5)        # READY!
T_START = 2.3               # empieza a montarse el nombre
T_GAMEOVER = 9.0            # GAME OVER, como pronto (si los dragones aún no se han ido, espera)
GAMEOVER_Y = 140            # altura del centro del cartel GAME OVER
T_FADE = 14.8               # todo se desvanece
T_RESET = 15.3              # escombros fuera
PASS_TIME = 1.6             # lo que tarda cada pasada final en cruzar la pantalla (s): cuanto menos, más rápida
EXIT_TIME = 1.1             # lo que tarda cada dragón en salir de la pantalla tras destruir el nombre
SETTLE = 1.3                # esperan a que los últimos trozos caigan al suelo antes de irse (s)
EXTRA_FIRE = 1.5            # si al acabar su barrido queda nombre en pie, siguen disparando hasta este tiempo extra (s)
FIRE_STYLE = "llama"         # forma del fuego en TODOS los estilos: "llama" | "bola" | "chispa"
HITS_TO_BREAK = 2           # fogonazos que aguanta cada trozo del nombre antes de reventar

FIRE_TRAVEL = 0.28    # segundos que tarda una llama en llegar al objetivo
FIRE_PERIOD = 0.30    # cada cuánto se reemite cada llama
FIRE_REACH = 150      # distancia horizontal boca → objetivo (px)
MOUTH_MARGIN = 70     # la boca nunca se acerca más que esto a los bordes al barrer (px)

# ══════════════════════════════════════════════════════════════════════
#  LOS DRAGONES
#   sprite/px  dibujo y tamaño en los estilos pixel ("small", "medium", "large")
#   scale      tamaño en el cómic
#   flap       segundos por aleteo · bob  balanceo (px)
#   fire       tamaño de las llamas · particles  llamas a la vez · puffs  fuego a "hipos"
#   facing     +1 mira a la derecha y barre el nombre de izquierda a derecha; -1 al revés
#   start/end  cuándo empieza y termina su barrido de fuego sobre TODO el nombre (s).
#              Dispara mientras quede algo en pie delante; si el nombre cae antes, se queda
#              mirando hasta que los trozos tocan el suelo (SETTLE) y se marcha.
#   mouth_y    altura de la boca mientras barre
#   lane       altura de sus pasadas finales: los que miran a la derecha pasan por
#              encima del GAME OVER y los que miran a la izquierda por debajo
#   pass_at    cuántos segundos después de aparecer GAME OVER hace su pasada final
#              (cruza la pantalla en PASS_TIME s)
#
#   Todos atacan el nombre entero. Cada llama apunta a un trozo que siga en pie: la primera
#   que le llega lo chamusca y la HITS_TO_BREAK-ésima lo revienta. Lo que destruye el nombre
#   es el propio fuego, así que nada cae sin que le haya llegado una llama.
#
#   Regla: cada tramo de vuelo (barrido + salida, cada pasada) debe empezar cuando
#   termina el anterior. Si no, el dragón parpadearía saltando de sitio, así que
#   el generador se niega a generar y te dice qué dragón falla.
# ══════════════════════════════════════════════════════════════════════
DRAGONS = [
    dict(sprite="large", px=5, scale=1.3, flap=0.45, bob=4, fire=1.3, particles=18, puffs=False,
         facing=+1, start=4.6, end=7.4, mouth_y=54, lane=62, pass_at=0.6),
    dict(sprite="small", px=4, scale=0.85, flap=0.18, bob=6, fire=1.1, particles=16, puffs=False,
         facing=-1, start=4.9, end=7.6, mouth_y=62, lane=236, pass_at=1.0),
    dict(sprite="medium", px=5, scale=1.1, flap=0.32, bob=4, fire=1.2, particles=18, puffs=False,
         facing=+1, start=5.5, end=8.1, mouth_y=46, lane=58, pass_at=1.4),
    dict(sprite="medium", px=4, scale=1.0, flap=0.26, bob=5, fire=1.15, particles=16, puffs=False,
         facing=-1, start=5.8, end=8.4, mouth_y=70, lane=226, pass_at=1.8),
]

# ══════════════════════════════════════════════════════════════════════
#  TEMAS  (los colores de "dragons" siguen el orden de la lista DRAGONS)
# ══════════════════════════════════════════════════════════════════════
INK = "#1d1424"
GB = ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"]   # paleta Game Boy

THEMES = {
    # ── 1 · Pixel art 8-bit ─────────────────────────────────────────
    "pixel": dict(
        kind="pixel", panel=None, inset=0,
        name_rows=["#ffc21a", "#ffaa00", "#ff8a00", "#f56a00", "#e04a12", "#c4321a", "#9c2222"],
        pixel_gap=1, pixel_rx=0, pixel_stroke=INK, outline=INK,
        flash="#ffe14d", fire="#ff6a00", burnt="#3a2420", ember="#d24a1c", ember_cold="#a39890",
        fire_colors=["#ffd31a", "#ff7a00", "#d7261e"], fire_core=("#ffe14d", "#fff8d0"), particle_size=20,
        floor=(266, 288),
        dragons=[
            dict(B="#d6334a", L="#ff9b73", W="#7a1f3d", D="#4a1028", E="#ffe066", H="#fff1d0"),
            dict(B="#c86bf0", L="#ffc9f2", W="#8a3fd0", D="#5a2a8a", E="#ffffff", H="#fff1d0"),
            dict(B="#3b7dd8", L="#73eff7", W="#29366f", D="#1a2048", E="#ffcd75", H="#fff1d0"),
            dict(B="#38b764", L="#a7f070", W="#257179", D="#1a4a3a", E="#ffcd75", H="#fff1d0"),
        ],
        title_fill="#ff004d", title_shadow=INK, text_fill=INK, accent="#e03e1a",
        start_text="INSERT COIN", credit=True, hud=True,
        hp=dict(frame=INK, back="#ffffff", colors=("#e8331c", "#ffc21a", "#38b764")),
    ),
    # ── 4 · Game Boy ────────────────────────────────────────────────
    "gameboy": dict(
        kind="pixel", panel="gameboy", inset=18,
        name_rows=[GB[0]] * 4 + [GB[1]] * 3,
        pixel_gap=1, pixel_rx=0, pixel_stroke=None, outline=GB[0],
        flash=GB[2], fire=GB[1], burnt=GB[0], ember=GB[1], ember_cold=GB[2],
        fire_colors=[GB[1], GB[0], GB[0]], fire_core=(GB[2], GB[3]), particle_size=20,
        floor=(252, 270),
        dragons=[dict(B=GB[1], L=GB[2], W=GB[0], D=GB[0], E=GB[3], H=GB[2])] * 4,
        title_fill=GB[0], title_shadow=GB[2], text_fill=GB[0], accent=GB[1],
        start_text="PRESS START", credit=False, hud=True, hud_ps=2.5,
        hp=dict(frame=GB[0], back=GB[2], colors=(GB[0], GB[0], GB[0])),
    ),
    # ── 15 · Cómic pop-art ──────────────────────────────────────────
    "comic": dict(
        kind="vector", style="comic", panel="comic", font="Bangers-Regular.ttf", axes={}, case="upper",
        spacing=4, name_size=134, tile=22,
        fire_colors=["#ff9f1c", "#ff5a1f", "#e8331c"], fire_core=("#ffd60a", "#fff8d0"), fire_outline="#111", particle_size=14,
        floor=(262, 284),
        dragons=[dict(B="#ff4d6d"), dict(B="#8338ec"), dict(B="#3a86ff"), dict(B="#2ec4b6")],
        start_text="INSERT COIN", credit=True, hud=True,
        bursts=["BOOM!", "RAWR!", "POW!", "ZAS!"],
        hp=dict(frame="#111", back="#ffffff", colors=("#ff3b30", "#ffd60a", "#2ec4b6"), sw=3, rx=4),
    ),
}

# ══════════════════════════════════════════════════════════════════════
#  FUENTE BITMAP 5x7 (estilos pixel)
# ══════════════════════════════════════════════════════════════════════
_F = """
A 01110 10001 10001 11111 10001 10001 10001
B 11110 10001 10001 11110 10001 10001 11110
C 01110 10001 10000 10000 10000 10001 01110
D 11110 10001 10001 10001 10001 10001 11110
E 11111 10000 10000 11110 10000 10000 11111
F 11111 10000 10000 11110 10000 10000 10000
G 01110 10001 10000 10111 10001 10001 01111
H 10001 10001 10001 11111 10001 10001 10001
I 11111 00100 00100 00100 00100 00100 11111
J 00111 00010 00010 00010 00010 10010 01100
K 10001 10010 10100 11000 10100 10010 10001
L 10000 10000 10000 10000 10000 10000 11111
M 10001 11011 10101 10101 10001 10001 10001
N 10001 11001 11001 10101 10011 10011 10001
O 01110 10001 10001 10001 10001 10001 01110
P 11110 10001 10001 11110 10000 10000 10000
Q 01110 10001 10001 10001 10101 10010 01101
R 11110 10001 10001 11110 10100 10010 10001
S 01111 10000 10000 01110 00001 00001 11110
T 11111 00100 00100 00100 00100 00100 00100
U 10001 10001 10001 10001 10001 10001 01110
V 10001 10001 10001 10001 10001 01010 00100
W 10001 10001 10001 10101 10101 10101 01010
X 10001 10001 01010 00100 01010 10001 10001
Y 10001 10001 01010 00100 00100 00100 00100
Z 11111 00001 00010 00100 01000 10000 11111
0 01110 10001 10011 10101 11001 10001 01110
1 00100 01100 00100 00100 00100 00100 01110
2 01110 10001 00001 00010 00100 01000 11111
3 11111 00010 00100 00010 00001 10001 01110
4 00010 00110 01010 10010 11111 00010 00010
5 11111 10000 11110 00001 00001 10001 01110
6 00110 01000 10000 11110 10001 10001 01110
7 11111 00001 00010 00100 01000 01000 01000
8 01110 10001 10001 01110 10001 10001 01110
9 01110 10001 10001 01111 00001 00010 01100
. 00000 00000 00000 00000 00000 01100 01100
- 00000 00000 00000 11111 00000 00000 00000
! 00100 00100 00100 00100 00100 00000 00100
? 01110 10001 00001 00010 00100 00000 00100
"""
FONT = {}
for _line in _F.strip().splitlines():
    _ch, *_rows = _line.split()
    FONT[_ch] = _rows
FONT[" "] = ["00000"] * 7



def text_cells(text):
    """[(col, fila, índice_de_letra)] de los píxeles encendidos."""
    cells = []
    for i, ch in enumerate(text.upper()):
        for r, row in enumerate(FONT.get(ch, FONT["?"])):
            for c, bit in enumerate(row):
                if bit == "1":
                    cells.append((i * 6 + c, r, i))
    return cells


def pixel_text_path(text, ps, cx, cy, gap=0):
    """Texto en la fuente bitmap centrado en (cx, cy)."""
    x0 = cx - (6 * len(text) - 1) * ps / 2
    y0 = cy - 3.5 * ps
    s = ps - gap
    return "".join(f"M{n(x0 + c * ps)} {n(y0 + r * ps)}h{n(s)}v{n(s)}h-{n(s)}z" for c, r, _ in text_cells(text))


# ══════════════════════════════════════════════════════════════════════
#  TIPOGRAFÍAS VECTORIALES → TRAZADOS (estilos vectoriales)
# ══════════════════════════════════════════════════════════════════════
_fonts = {}


def load_font(name, axes):
    key = (name, tuple(sorted(axes.items())))
    if key not in _fonts:
        from fontTools.ttLib import TTFont
        f = TTFont(os.path.join(FONTS_DIR, name))
        if axes and "fvar" in f:
            from fontTools.varLib import instancer
            have = {a.axisTag for a in f["fvar"].axes}
            f = instancer.instantiateVariableFont(f, {k: v for k, v in axes.items() if k in have})
        _fonts[key] = f
    return _fonts[key]


def glyph_paths(font, text, size, cx, base, spacing=0.0):
    """Devuelve [(d, (xmin, ymin, xmax, ymax))] por letra, centrado en cx."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.boundsPen import BoundsPen
    gs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm
    s = size / upm
    names = [cmap.get(ord(c)) or cmap.get(ord(c.upper())) or cmap.get(ord("?")) for c in text]
    widths = [font["hmtx"][g][0] * s + spacing for g in names]
    x = cx - (sum(widths) - spacing) / 2
    out = []
    for g, w in zip(names, widths):
        pen, bp = SVGPathPen(gs, ntos=n), BoundsPen(gs)
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, base)))
        gs[g].draw(TransformPen(bp, (s, 0, 0, -s, x, base)))
        out.append((pen.getCommands(), bp.bounds or (x, base, x + w, base)))
        x += w
    return out


def vector_text(th, text, size, cx, cy):
    """Trazado de un texto en la tipografía del tema, centrado en (cx, cy)."""
    f = load_font(th["font"], th["axes"])
    gl = glyph_paths(f, text, size, cx, 0, th.get("spacing", 0) * size / th["name_size"])
    ymin = min(b[1] for _, b in gl if b)
    ymax = max(b[3] for _, b in gl if b)
    dy = cy - (ymin + ymax) / 2
    return "".join(d for d, _ in gl), dy


# ══════════════════════════════════════════════════════════════════════
#  SPRITES PIXEL  (B cuerpo · L vientre · W ala · D sombra · E ojo · H cuernos)
# ══════════════════════════════════════════════════════════════════════
SPRITES = {
    "small": dict(mouth=(13, 5.5), up="""
....W........
...WW....H.H.
..WWW...BBBB.
..WWW..BBBBBB
...WW..BEBBBB
......BBBBBBD
...BBBBBBLL..
.BBBBBBLLLL..
B..BBBBLLL...
....D...D....
""", down="""
.............
.........H.H.
........BBBB.
.......BBBBBB
.......BEBBBB
......BBBBBBD
...BBBBBBLL..
.BWWWBBLLLL..
BWWWWBBLLL...
.WWWD...D....
.W...........
"""),
    "medium": dict(mouth=(18, 5.0), up="""
.......W..........
......WW......HH..
.....WWW.....HBBB.
....WWWW....BBEBBB
...WWWWW....BBBBBB
..WWWWWWW..BBB.DDD
......BBBBBBBB....
....BBBBBBBBLL....
...BBBBBBBLLL.....
BB.BBBBBBBBL......
.BBB.BB..BB.......
......D...D.......
""", down="""
..................
..............HH..
.............HBBB.
............BBEBBB
............BBBBBB
...........BBB.DDD
......BBBBBBBB....
....BBBBBBBBLL....
...BWWWWWBBLL.....
BB.WWWWWWBBL......
.BWWWWWW.BB.......
.WWWWW.D..D.......
.WWW..............
W.................
"""),
    "large": dict(mouth=(22, 5.5), up="""
........W.............
.......WW......H......
......WWW.......HBBB..
.....WWWW......BBBEBBB
....WWWWW......BBBBBBB
...WWWWWW.....BBB.....
..WWWWWWWW...BBB..DDDD
.WWWWWWWWWD.BBB.......
......DBDBBBBB........
....BBBBBBBBBLL.......
..BBBBBBBBBBLLL.......
BBB.BBBBBBBLLL........
B....BB...BB..........
.....DD...DD..........
""", down="""
......................
...............H......
................HBBB..
...............BBBEBBB
...............BBBBBBB
..............BBB.....
.............BBB..DDDD
............BBB.......
......DBDBBBBB........
....BWWWWWWBBLL.......
..BBWWWWWWWBLLL.......
BBBWWWWWWWBLLL........
B.WWWWWW..BB..........
.WWWWWD...DD..........
.WWW..................
"""),
}


def sprite_rects(art, mouth, palette, facing, s, outline=None):
    """Rects del sprite con la boca en (0,0); une píxeles contiguos y añade contorno opcional."""
    rows = art.strip("\n").splitlines()
    h, w = len(rows), max(len(r) for r in rows)
    cell = {(c, r): palette[ch] for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "."}
    if outline:
        ring = {}
        for (c, r) in cell:
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (c + dc, r + dr) not in cell:
                    ring[(c + dc, r + dr)] = outline
        cell.update(ring)
    out = []
    for r in range(-1, h + 1):
        c = -1
        while c <= w:
            col = cell.get((c, r))
            if col is None:
                c += 1
                continue
            run = 1
            while cell.get((c + run, r)) == col:
                run += 1
            x = (c - mouth[0]) * s if facing > 0 else (mouth[0] - c - run) * s
            out.append(f'<rect x="{n(x)}" y="{n((r - mouth[1]) * s)}" width="{run * s}" height="{s}" fill="{col}"/>')
            c += run
    return "".join(out)


# ══════════════════════════════════════════════════════════════════════
#  DRAGÓN VECTORIAL  (coordenadas locales, boca en (54, -21))
# ══════════════════════════════════════════════════════════════════════
V_BODY = ("M-62 -8 L-55 -15 L-52 -4 Q-40 4 -22 -2 Q-2 -10 14 -8 Q22 -12 26 -24 Q28 -32 36 -32 "
          "L50 -28 L54 -24 L44 -21 L52 -18 L38 -14 Q32 -12 30 -4 Q28 10 16 14 Q-4 20 -20 10 Q-36 6 -50 -2 Z")
V_HORN = "M33 -31 L25 -44 L38 -32 Z"
V_WING = "M4 -8 Q-10 -30 -42 -48 Q-32 -38 -28 -31 Q-20 -40 -13 -33 Q-6 -42 1 -35 Q8 -44 17 -40 Q15 -24 14 -9 Z"
V_RIBS = "M5 -9 L-40 -46 M8 -9 L-13 -33 M10 -9 L1 -35 M12 -9 L16 -39"
V_LEGS = "M6 13 L8 25 L14 25 L11 12 Z M-14 13 L-15 24 L-9 24 L-8 12 Z"
V_MOUTH = (54, -21)
WING_DOWN = 'transform="translate(0 -8) scale(1 -0.62) translate(0 8)"'
NS = 'vector-effect="non-scaling-stroke"'


def vector_dragon(th, pal, facing, s, anim):
    """Dragón vectorial con la boca en (0,0) y las alas batiendo."""
    style = th["style"]
    inner = f'transform="scale({s * facing} {s}) translate({-V_MOUTH[0]} {-V_MOUTH[1]})"'

    def shapes(body, wing, horn, eye, ribs=None, pupil=None):
        wings = ""
        for cls, tr in (("wa", ""), ("wb", WING_DOWN)):
            rb = f'<path d="{V_RIBS}" {ribs}/>' if ribs else ""
            wings += f'<g class="{cls}" style="{anim}"><g {tr}><path d="{V_WING}" {wing}/>{rb}</g></g>'
        p = f'<circle cx="41" cy="-27" r="1.2" {pupil}/>' if pupil else ""
        return (f'<path d="{V_LEGS}" {body}/><path d="{V_BODY}" {body}/><path d="{V_HORN}" {horn}/>'
                f'{wings}<circle cx="40" cy="-27" r="2.3" {eye}/>{p}')

    if style == "comic":
        st = f'stroke="#111" stroke-width="3.5" stroke-linejoin="round" {NS}'
        return f'<g {inner}>' + shapes(f'fill="{pal["B"]}" {st}', f'fill="#fff" {st}', f'fill="#fff" {st}',
                                        'fill="#111"', ribs=f'fill="none" {st}') + "</g>"
    raise ValueError(style)


# ══════════════════════════════════════════════════════════════════════
#  FORMAS DEL FUEGO  (la misma en todos los estilos: con píxeles o lisa)
#  Todas apuntan hacia +x con la "cabeza" en (0,0): al girarlas en la
#  dirección del chorro, la cola queda hacia la boca del dragón.
#  O = parte exterior (cambia de color con la animación) · I = interior · C = núcleo
# ══════════════════════════════════════════════════════════════════════
PIXEL_FIRE = {
    "llama": (7, 2, [".....OOO.", "...OOIIIO", "OOOIICCIO", "...OOIIIO", ".....OOO."]),
    "bola": (2, 2, [".OOO.", "OIIIO", "OICIO", "OIIIO", ".OOO."]),
    "chispa": (1, 1, ["OOO", "OCO", "OOO"]),
}


def fire_shape(th, size, style=None):
    """Contenido SVG de una partícula de fuego de tamaño ~size (sin el color exterior, que se anima)."""
    style = style or FIRE_STYLE
    inner, core = th["fire_core"]
    if th["kind"] == "pixel":
        ox, oy, rows = PIXEL_FIRE[style]
        u = size / len(rows)
        out = {"O": [], "I": [], "C": []}
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != ".":
                    out[ch].append(f"M{n((c - ox - .5) * u)} {n((r - oy - .5) * u)}h{n(u)}v{n(u)}h{n(-u)}z")
        return (f'<path d="{"".join(out["O"])}"/><path d="{"".join(out["I"])}" fill="{inner}"/>'
                f'<path d="{"".join(out["C"])}" fill="{core}"/>')
    r = size / 2
    st = f' stroke="{th["fire_outline"]}" stroke-width="1.6" stroke-linejoin="round" {NS}' if th.get("fire_outline") else ""
    if style == "llama":
        def drop(k, dx=0):
            q = r * k
            return (f"M{n(q + dx)} 0 C{n(q + dx)} {n(q * .95)} {n(-q * .3 + dx)} {n(q * 1.1)} {n(-q + dx)} {n(q * .7)} "
                    f"C{n(-q * 1.9 + dx)} {n(q * .35)} {n(-q * 2.6 + dx)} {n(q * .2)} {n(-q * 3.4 + dx)} 0 "
                    f"C{n(-q * 2.6 + dx)} {n(-q * .2)} {n(-q * 1.9 + dx)} {n(-q * .35)} {n(-q + dx)} {n(-q * .7)} "
                    f"C{n(-q * .3 + dx)} {n(-q * 1.1)} {n(q + dx)} {n(-q * .95)} {n(q + dx)} 0Z")
        return (f'<path d="{drop(1)}"{st}/><path d="{drop(.62, r * .2)}" fill="{inner}"/>'
                f'<circle cx="{n(r * .25)}" r="{n(r * .32)}" fill="{core}"/>')
    if style == "bola":
        return (f'<circle r="{n(r)}"{st}/><circle cx="{n(r * .15)}" r="{n(r * .62)}" fill="{inner}"/>'
                f'<circle cx="{n(r * .25)}" r="{n(r * .3)}" fill="{core}"/>')
    return (f'<rect x="{n(-r * .8)}" y="{n(-r * .8)}" width="{n(r * 1.6)}" height="{n(r * 1.6)}" rx="{n(r * .2)}"{st}/>'
            f'<rect x="{n(-r * .35)}" y="{n(-r * .35)}" width="{n(r * .7)}" height="{n(r * .7)}" fill="{core}"/>')


# ══════════════════════════════════════════════════════════════════════
#  UTILIDADES DE ANIMACIÓN
# ══════════════════════════════════════════════════════════════════════
def n(v):
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def tf(x, y, a=0.0, sc=1.0):
    return f"translate({n(x)}px,{n(y)}px) rotate({n(a)}deg) scale({sc:.2f})"


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def lerp(a, b, u):
    return a + (b - a) * u


class KF:
    """Acumula fotogramas clave (en segundos) y los convierte a @keyframes CSS."""

    def __init__(self, name):
        self.name, self.frames = name, {}

    def add(self, t, **props):
        key = round(clamp(t, 0.0, CYCLE) / CYCLE * 100, 3)
        self.frames.setdefault(key, {}).update(props)
        return self

    def css(self):
        parts = []
        for k in sorted(self.frames):
            body = ";".join(f"{p.replace('_', '-')}:{v}" for p, v in self.frames[k].items())
            parts.append(f"{f'{k:.3f}'.rstrip('0').rstrip('.')}%{{{body}}}")
        return f"@keyframes {self.name}{{{''.join(parts)}}}"


def steps_kf(name, changes, prop="opacity"):
    kf = KF(name)
    for t, v in changes:
        kf.add(t, **{prop: v})
    return kf.add(CYCLE, **{prop: changes[-1][1]})


def blink(t0, t1, period=0.45, duty=0.5):
    """Parpadeo entre t0 y t1: encendido `duty` del periodo."""
    ch, t, on = [(0, 0)], t0, True
    while t < t1:
        ch.append((t, 1 if on else 0))
        t += period * (duty if on else 1 - duty)
        on = not on
    ch.append((t1, 0))
    return ch


def spline(pts, step=0.08):
    """Interpolación Hermite con tiempo de [(t, x, y)]."""
    m = []
    for i in range(len(pts)):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dt = b[0] - a[0]
        m.append(((b[1] - a[1]) / dt, (b[2] - a[2]) / dt))
    out = []
    for i in range(len(pts) - 1):
        (t0, x0, y0), (t1, x1, y1) = pts[i], pts[i + 1]
        h = t1 - t0
        k = max(1, int(math.ceil(h / step)))
        for j in range(k):
            s = j / k
            h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
            out.append((t0 + h * s, h00 * x0 + h10 * h * m[i][0] + h01 * x1 + h11 * h * m[i + 1][0],
                        h00 * y0 + h10 * h * m[i][1] + h01 * y1 + h11 * h * m[i + 1][1]))
    out.append(pts[-1])
    return out


def sample_at(samples, t):
    for (t0, x0, y0), (t1, x1, y1) in zip(samples, samples[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return lerp(x0, x1, u), lerp(y0, y1, u)
    return samples[-1][1], samples[-1][2]


def star_path(r_out, r_in, k=8):
    return "M" + " L".join(
        f"{n((r_out if i % 2 == 0 else r_in) * math.cos(i / (2 * k) * math.tau))} "
        f"{n((r_out if i % 2 == 0 else r_in) * math.sin(i / (2 * k) * math.tau))}" for i in range(2 * k)) + "Z"


# ══════════════════════════════════════════════════════════════════════
#  FONDOS, FILTROS Y DECORADOS
# ══════════════════════════════════════════════════════════════════════
def panel(th, W, H):
    """(defs, fondo, clip-id) del panel de cada estilo."""
    kind, ins = th["panel"], th.get("inset", 0)
    if kind == "gameboy":
        x, y, w, h = ins, ins, W - 2 * ins, H - 2 * ins
        back = (f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="20" fill="#c9c5bd" stroke="#9e9a92" stroke-width="2"/>'
                f'<rect x="{x - 5}" y="{y - 5}" width="{w + 10}" height="{h + 10}" rx="10" fill="#5f5d6b"/>'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{GB[3]}"/>'
                )
        defs = f'<clipPath id="pc"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/></clipPath>'
        return defs, back, "pc"
    if kind == "comic":
        defs = ('<pattern id="dots" width="10" height="10" patternUnits="userSpaceOnUse"><circle cx="5" cy="5" r="2.2" fill="#e63946" opacity=".3"/></pattern>'
                f'<clipPath id="pc"><rect width="{W}" height="{H}" rx="10"/></clipPath>')
        rays = "".join(
            f'<path d="M400 160 L{n(400 + 900 * math.cos(k / 24 * math.tau))} {n(160 + 900 * math.sin(k / 24 * math.tau))} '
            f'L{n(400 + 900 * math.cos((k + .5) / 24 * math.tau))} {n(160 + 900 * math.sin((k + .5) / 24 * math.tau))}Z"/>'
            for k in range(24))
        back = (f'<rect width="{W}" height="{H}" rx="10" fill="#ffe14d"/>'
                f'<g clip-path="url(#pc)"><g class="rays" fill="#fff3a0">{rays}</g>'
                f'<rect width="{W}" height="{H}" fill="url(#dots)"/></g>')
        return defs, back, "pc"
    return "", "", None


def style_defs(th):
    """Filtros y patrones que usa cada estilo vectorial."""
    st = th.get("style")
    if st == "comic":
        return ('<pattern id="dots2" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.4" fill="#111" opacity=".3"/></pattern>')
    return ""


def glyph_layers(th):
    """Capas con las que se dibuja cada letra: [(atributos de la capa, función d,i → contenido)]."""
    st = th.get("style")
    if st == "comic":
        def art(d, i):
            ext = (f'<path id="gx{i}" d="{d}" fill="#111" transform="translate(1 1)"/>'
                   + "".join(f'<use href="#gx{i}" transform="translate({k} {k})"/>' for k in range(1, 8)))
            return (ext + f'<path d="{d}" fill="#ff3b30" stroke="#111" stroke-width="5" paint-order="stroke" stroke-linejoin="round"/>'
                    f'<path d="{d}" fill="url(#dots2)"/>')
        return [("", art)]
    raise ValueError(st)


# ══════════════════════════════════════════════════════════════════════
#  TEXTOS (GAME OVER, INSERT COIN, READY!, SCORE)
# ══════════════════════════════════════════════════════════════════════
def text_svg(th, text, role, cx, cy, cls="", style=""):
    """Texto en el estilo del tema. role: title | start | small."""
    attrs = f'class="{cls}" style="{style}"' if cls else ""
    if th["kind"] == "pixel":
        ps = {"title": 10, "start": 6, "small": th.get("hud_ps", 3)}[role]
        fill = {"title": th["title_fill"], "start": th["text_fill"], "small": th["text_fill"]}[role]
        d = pixel_text_path(text, ps, cx, cy, 1 if role == "title" else 0)
        sh = ""
        if role == "title" and th.get("title_shadow"):
            sh = f'<path d="{pixel_text_path(text, ps, cx + 4, cy + 4)}" fill="{th["title_shadow"]}"/>'
        return f'<g {attrs}>{sh}<path d="{d}" fill="{fill}"/></g>'
    size = {"title": 96, "start": 52, "small": 22}[role]
    d, dy = vector_text(th, text, size, cx, cy)
    st = th["style"]
    if st == "comic":
        if role == "small":
            body = f'<path d="{d}" fill="#111"/>'
        else:
            col = "#ff3b30" if role == "title" else "#fff"
            tid = f"tx{zlib.crc32((text + role).encode()) % 99999}"
            ext = (f'<path id="{tid}" d="{d}" fill="#111" transform="translate(1 1)"/>'
                   + "".join(f'<use href="#{tid}" transform="translate({k} {k})"/>' for k in range(1, 5)))
            body = ext + f'<path d="{d}" fill="{col}" stroke="#111" stroke-width="4" paint-order="stroke"/>'
    return f'<g {attrs}><g transform="translate(0 {n(dy)})">{body}</g></g>'


def choreography(seed):
    """Papel de cada dragón en la partida. Con la semilla por defecto, tal cual DRAGONS; con
    cualquier otra se reparten de nuevo (dentro de márgenes seguros): quién barre hacia cada lado,
    cuándo entra, a qué altura ataca, por qué carril pasa al final y en qué orden."""
    ds = [dict(d) for d in DRAGONS]
    if seed == SEED:
        return ds
    r = random.Random(seed * 7919 + 13)
    facings = [+1, -1] * (len(ds) // 2) + [+1] * (len(ds) % 2)
    r.shuffle(facings)
    starts = [4.4 + j * r.uniform(0.3, 0.55) for j in range(len(ds))]
    r.shuffle(starts)
    pass_order = [0.6 + 0.4 * j for j in range(len(ds))]
    r.shuffle(pass_order)
    for d, f, st, pa in zip(ds, facings, starts, pass_order):
        d.update(facing=f, start=round(st, 2), end=round(st + r.uniform(2.5, 3.0), 2),
                 mouth_y=r.randint(48, 72), pass_at=pa,
                 lane=r.randint(56, 66) if f > 0 else r.randint(222, 238))
    return ds


# ══════════════════════════════════════════════════════════════════════
#  RENDER
# ══════════════════════════════════════════════════════════════════════
def render(theme_key, name=NAME, seed=SEED):
    th = THEMES[theme_key]
    rnd = random.Random(seed)
    W, H = WIDTH, HEIGHT
    ins = th.get("inset", 0)
    css, defs = [], []
    L = {k: [] for k in ("back", "name", "dragons", "fire", "front", "hud")}

    # ── 1. Elementos del nombre (píxeles o trozos de letra) ───────────
    # Cada elemento: dict(x, y, letter, base_fill?, html) — x,y es su centro.
    elements = []
    if th["kind"] == "pixel":
        text = name.upper()
        cols = 6 * len(text) - 1
        p = min(14, (W - 120) // cols)
        nx0, ny0 = (W - cols * p) / 2, 118 + (98 - 7 * p) / 2
        g = th["pixel_gap"]
        stroke = f' stroke="{th["pixel_stroke"]}" stroke-width="1.5"' if th["pixel_stroke"] else ""
        for col, row, li in text_cells(text):
            x, y = nx0 + col * p, ny0 + row * p
            elements.append(dict(x=x + p / 2, y=y + p / 2, letter=li, row=row, base=th["name_rows"][row],
                                 html=f'x="{n(x)}" y="{n(y)}" width="{p - g}" height="{p - g}" rx="{th["pixel_rx"]}"'
                                      f' fill="{th["name_rows"][row]}"{stroke}', tag="rect"))
        name_x0, name_x1, name_y0, name_y1 = nx0, nx0 + cols * p, ny0, ny0 + 7 * p
        unit = p
    else:
        text = name.upper() if th["case"] == "upper" else name.lower()
        f = load_font(th["font"], th["axes"])
        size = th["name_size"]
        gl = glyph_paths(f, text, size, W / 2, 0, th["spacing"])
        while gl[-1][1][2] - gl[0][1][0] > 560:
            size *= 0.95
            gl = glyph_paths(f, text, size, W / 2, 0, th["spacing"] * size / th["name_size"])
        ymin, ymax = min(b[1] for _, b in gl), max(b[3] for _, b in gl)
        dy = 166 - (ymin + ymax) / 2
        gl = [(d, (b[0], b[1] + dy, b[2], b[3] + dy)) for d, b in gl]
        layers = glyph_layers(th)
        for li, (d, b) in enumerate(gl):
            for k, (_, art) in enumerate(layers):
                defs.append(f'<g id="g{li}_{k}" transform="translate(0 {n(dy)})">{art(d, li)}</g>')
        ts = th["tile"]
        for li, (d, (x0, y0, x1, y1)) in enumerate(gl):
            x0, y0, x1, y1 = x0 - 3, y0 - 3, x1 + 10, y1 + 10
            nxc, nyc = max(1, round((x1 - x0) / ts)), max(1, round((y1 - y0) / ts))
            cw, chh = (x1 - x0) / nxc, (y1 - y0) / nyc
            for a in range(nxc):
                for c in range(nyc):
                    cx0, cy0 = x0 + a * cw, y0 + c * chh
                    cid = f"c{len(elements)}"
                    defs.append(f'<clipPath id="{cid}"><rect x="{n(cx0)}" y="{n(cy0)}" width="{n(cw + .6)}" height="{n(chh + .6)}"/></clipPath>')
                    elements.append(dict(x=cx0 + cw / 2, y=cy0 + chh / 2, letter=li, row=c * 7 / nyc, clip=cid, tag="use"))
        name_x0, name_x1 = gl[0][1][0], gl[-1][1][2]
        name_y0, name_y1 = ymin + dy, ymax + dy
        unit = (name_y1 - name_y0) / 7

    # ── 2. Ataques: cada dragón barre el nombre entero ────────────────
    attacks = []
    for i, d in enumerate(choreography(seed)):
        lo, hi = name_x0 + unit / 2, name_x1 - unit / 2
        xs, xe = (lo, hi) if d["facing"] > 0 else (hi, lo)
        attacks.append(dict(d, idx=i, xs=xs, xe=xe, dur=d["end"] - d["start"]))

    def target_x(a, t):
        return lerp(a["xs"], a["xe"], clamp((t - a["start"] - FIRE_TRAVEL) / a["dur"]))

    # ── 3. Vuelo del barrido (posición de la boca en cada instante) ─────
    # boca del dragón mientras barre: siempre dentro de la pantalla (en los bordes dispara más en picado),
    # para que también pueda quemar desde el principio las columnas de los extremos
    mxf = lambda a, t: clamp(target_x(a, t + FIRE_TRAVEL) - a["facing"] * FIRE_REACH, MOUTH_MARGIN, W - MOUTH_MARGIN)

    def attack_points(a, t_stop):
        """Entrada y barrido hasta t_stop (muestreado fino para que la curva no se desvíe)."""
        fa, ym, ts = a["facing"], a["mouth_y"], a["start"]
        off_in = -160 if fa > 0 else W + 160
        pts = [(ts - 1.4, off_in, ym - 70), (ts - 0.7, mxf(a, ts) - fa * 90, ym + 25)]
        t = ts
        while t < t_stop - 1e-6:
            pts.append((t, mxf(a, t), ym))
            t += 0.12
        pts.append((t_stop, mxf(a, t_stop), ym))
        return pts

    for a in attacks:
        a["phase"] = rnd.uniform(0, math.tau)
        hold = a["end"] + EXTRA_FIRE + 1.0
        a["pieces"] = [spline(attack_points(a, a["end"]) + [(hold, mxf(a, a["end"]), a["mouth_y"])])]

    def bob(a, t):
        return a["bob"] * math.sin(math.tau * t / (a["flap"] * 2) + a["phase"])

    def mouth_pos(a, t):
        for piece in a["pieces"]:
            if piece[0][0] <= t <= piece[-1][0]:
                x, y = sample_at(piece, t)
                return x, y + bob(a, t)
        return None

    def on_screen(m):          # nunca fuego sin dragón a la vista
        return m and 10 < m[0] < W - 10 and 5 < m[1] < H - 5

    # ── 4. El fuego destruye el nombre: simulación llama a llama, en orden de tiempo ──
    emissions = []
    for a in attacks:
        for k in range(a["particles"]):
            te = a["start"] + k * FIRE_PERIOD / a["particles"]
            while te <= a["end"] + EXTRA_FIRE:
                emissions.append((te, a["idx"], k))
                te += FIRE_PERIOD
    emissions.sort()
    for e in elements:
        e["hits"], e["hit"] = [], None
    a_flames = {}                                    # (dragón, partícula) -> [(t, boca, objetivo)]
    for te, ai, k in emissions:
        a = attacks[ai]
        m = mouth_pos(a, te)
        if not on_screen(m) or (a["puffs"] and ((te - a["start"]) % 0.5) > 0.3):
            continue
        t_arr = te + FIRE_TRAVEL
        reach = 320 if te <= a["end"] else 480
        alive = [e for e in elements if e["hit"] is None and (e["x"] - m[0]) * a["facing"] > 15
                 and abs(e["x"] - m[0]) <= reach]
        if not alive:
            continue                                  # delante ya no queda nada: no dispara
        guess = target_x(a, t_arr)
        alive.sort(key=lambda e: abs(e["x"] - guess))
        e = rnd.choice(alive[:6])
        e["hits"].append((t_arr, a))
        if len(e["hits"]) >= HITS_TO_BREAK:
            e["hit"], e["owner"] = t_arr, a
        tgt = (e["x"] + rnd.uniform(-.4, .4) * unit, e["y"] + rnd.uniform(-.4, .4) * unit)
        a_flames.setdefault((ai, k), []).append((te, m, tgt))
    left = [e for e in elements if e["hit"] is None]
    if left:   # (no debería pasar) lo que nadie alcanzó revienta con su último impacto
        print(f"  ⚠ {len(left)} trozos sin alcanzar: revientan con su último fogonazo")
        t_last = max(t for e in elements for t, _ in e["hits"])
        for e in left:
            e["hit"], e["owner"] = (e["hits"][-1] if e["hits"] else (t_last, attacks[0]))
    for e in elements:
        first = e["hits"][0][0] if e["hits"] else e["hit"]
        e["scorch"] = first if e["hit"] - first > 0.25 else None
    t_done = max(e["hit"] for e in elements)          # cae el último trozo del nombre

    # ── 5. Vuelo definitivo: barrido, espera a que caigan los trozos, salida y pasada final ──
    t_leave = t_done + SETTLE
    # mientras caen los trozos se separan un poco (sin cambiar su orden) para no amontonarse
    by_x = sorted(attacks, key=lambda a: mxf(a, min(a["end"], t_done)))
    for j, a in enumerate(by_x):
        a["wait_x"] = lerp(170, 630, j / max(1, len(by_x) - 1))
    for a in attacks:
        fa, ym = a["facing"], a["mouth_y"]
        t_stop = min(a["end"], t_done)
        wx = a["wait_x"]
        tl = t_leave + a["idx"] * 0.15
        pts = attack_points(a, t_stop) + [(tl, wx, ym + 8), (tl + EXIT_TIME * .45, wx + fa * 130, ym - 45),
                                          (tl + EXIT_TIME, wx + fa * 300, -150)]
        a["pieces"] = [spline(pts)]
    # GAME OVER cuando ya han salido por arriba, y lo bastante tarde para que ninguna pasada
    # empiece antes de que su dragón haya terminado de salir
    t_gameover = max([T_GAMEOVER, t_leave + 0.9] +
                     [a["pieces"][0][-1][0] - a["pass_at"] + 0.1 for a in attacks])
    for a in attacks:   # una pasada rápida de lado a lado por su carril
        fa = a["facing"]
        off_in, off_out = (-160, W + 160) if fa > 0 else (W + 160, -160)
        t0 = t_gameover + a["pass_at"]
        a["pass"] = t0
        arc = -10 if a["lane"] < GAMEOVER_Y else 8
        a["pieces"].append(spline([(t0, off_in, a["lane"]), (t0 + PASS_TIME / 2, W / 2, a["lane"] + arc),
                                   (t0 + PASS_TIME, off_out, a["lane"])]))

    check_choreography(attacks)

    first_hit = min(e["hit"] for e in elements)
    last_hit = max(e["hit"] for e in elements)

    # ── 5. Panel / fondo ──────────────────────────────────────────────
    pdefs, pback, clip_id = panel(th, W, H)
    defs.append(pdefs + style_defs(th))

    # ── 6. Pantalla de inicio: INSERT COIN → CREDIT 1 → READY! ────────
    cy_start = 140
    t_coin = T_COIN_BLINK[1]
    if th["credit"]:
        seq = blink(T_COIN_BLINK[0], t_coin, period=0.5, duty=0.7)
    else:   # Game Boy: PRESS START parpadea despacio y, al "pulsar", muy rápido
        seq = blink(T_COIN_BLINK[0], t_coin - 0.35, period=0.6, duty=0.65)[:-1] + blink(t_coin - 0.35, t_coin, 0.08)[1:]
    css.append(steps_kf("ins", seq).css())
    L["front"].append(text_svg(th, th["start_text"], "start", W / 2, cy_start, "sp", "animation-name:ins"))
    css.append(steps_kf("rdy", [(0, 0), (T_READY[0], 1), (T_READY[1], 0)]).css())
    L["front"].append(text_svg(th, "READY!", "start", W / 2, cy_start, "sp", "animation-name:rdy"))
    if th["credit"]:
        cy_cr = cy_start + 62
        css.append(steps_kf("cr0", [(0, 1), (t_coin, 0), (T_RESET, 1)]).css())
        css.append(steps_kf("cr1", [(0, 0)] + blink(t_coin, t_coin + 0.4, 0.1)[1:-1] + [(t_coin + 0.4, 1), (T_READY[1], 0)]).css())
        L["front"].append(text_svg(th, "CREDIT 0", "small", W / 2, cy_cr, "sp", "animation-name:cr0"))
        L["front"].append(text_svg(th, "CREDIT 1", "small", W / 2, cy_cr, "sp", "animation-name:cr1"))

    # ── 7. Nombre: montaje, impacto y escombros ───────────────────────
    fl_lo, fl_hi = th["floor"]
    letter_land = {}
    name_html = []
    for i, e in enumerate(elements):
        x, y, a, t_hit = e["x"], e["y"], e["owner"], e["hit"]
        pixel = th["kind"] == "pixel"
        base = e.get("base")
        kf = KF(f"n{i}")
        y_off = -(y + 60)

        def S(**kw):   # estado: en pixel anima el color, en vectorial el brillo
            if pixel:
                return kw
            kw.pop("fill", None)
            if "glow" in kw:
                kw["filter"] = f'brightness({kw.pop("glow")})'
            return kw

        if pixel:
            t_land = T_START + 0.1 + (x - name_x0) / (name_x1 - name_x0) * 0.9 + (6 - e["row"]) * 0.05 + rnd.uniform(0, .05)
        else:
            if e["letter"] not in letter_land:
                letter_land[e["letter"]] = T_START + 0.15 + e["letter"] * 0.17
            t_land = letter_land[e["letter"]]
        kf.add(0, **S(transform=tf(0, y_off), opacity=0, fill=base, glow=1))
        kf.add(t_land - 0.45, **S(transform=tf(0, y_off), opacity=1, fill=base, glow=1),
               animation_timing_function="cubic-bezier(.5,0,1,1)")
        kf.add(t_land, transform=tf(0, 0))
        kf.add(t_land + 0.07, transform=tf(0, -unit * 0.35))
        kf.add(t_land + 0.14, transform=tf(0, 0))
        pre_fill, pre_glow = base, 1
        if e.get("scorch"):   # primer fogonazo: se chamusca pero aguanta
            ts_ = e["scorch"]
            kf.add(ts_ - 0.01, **S(transform=tf(0, 0), fill=base, glow=1))
            if pixel:
                pre_fill = th["ember"]
                kf.add(ts_, fill=th["flash"])
                kf.add(ts_ + 0.12, fill=pre_fill)
            else:
                pre_glow = .8
                kf.add(ts_, filter="brightness(1.7)")
                kf.add(ts_ + 0.15, filter=f"brightness({pre_glow})")
        kf.add(t_hit - 0.01, **S(transform=tf(0, 0), opacity=1, fill=pre_fill, glow=pre_glow))
        if pixel:
            kf.add(t_hit, fill=th["flash"])
            kf.add(t_hit + 0.1, fill=th["fire"])
            kf.add(t_hit + 0.25, transform=tf(0, 0), fill=th["fire"])
        else:
            kf.add(t_hit, filter="brightness(1.9)")
            kf.add(t_hit + 0.25, transform=tf(0, 0), filter="brightness(.55)")
        dx = rnd.uniform(-55, 55) + a["facing"] * 25
        rot = rnd.uniform(-360, 360) if pixel else rnd.uniform(-160, 160)
        if rnd.random() < 0.45:   # sale volando y se consume
            kf.add(t_hit + 1.2, **S(transform=tf(dx, -rnd.uniform(60, 140), rot, 0.3), opacity=0,
                                    fill=th.get("burnt"), glow=.3))
        else:                     # cae al suelo
            floor = rnd.uniform(fl_lo, fl_hi) - y
            sc = 0.7 if pixel else 0.85
            kf.add(t_hit + 0.42, transform=tf(dx * 0.3, -rnd.uniform(12, 34), rot * 0.3, 0.9),
                   animation_timing_function="cubic-bezier(.5,0,1,1)")
            kf.add(t_hit + 0.9, **S(transform=tf(dx, floor, rot, sc), fill=th.get("ember"), glow=.7))
            kf.add(t_hit + 1.0, transform=tf(dx * 1.04, floor - 5, rot, sc))
            kf.add(t_hit + 1.1, transform=tf(dx * 1.08, floor, rot, sc), opacity=1)
            kf.add(T_FADE - 1.0, **S(fill=th.get("ember_cold"), glow=.75))
            kf.add(T_FADE, opacity=1)
            kf.add(T_RESET, transform=tf(dx * 1.08, floor, rot, sc), opacity=0)
        kf.add(CYCLE, **S(transform=tf(0, y_off), opacity=0, fill=base, glow=1))
        css.append(kf.css())
        if pixel:
            name_html.append(f'<rect class="px" style="animation-name:n{i}" {e["html"]}/>')
        else:
            org = f"transform-origin:{n(x)}px {n(y)}px"
            for k in range(len(glyph_layers(th))):
                e.setdefault("uses", []).append(
                    f'<use href="#g{e["letter"]}_{k}" clip-path="url(#{e["clip"]})" class="tl" style="animation-name:n{i};{org}"/>')
    if th["kind"] == "pixel":
        L["name"].append('<g class="shake">' + "".join(name_html) + "</g>")
    else:
        for k, (attrs, _) in enumerate(glyph_layers(th)):
            L["name"].append(f'<g class="shake"><g {attrs}>' + "".join(e["uses"][k] for e in elements) + "</g></g>")

    shake = KF("shake").add(0, transform="translate(0,0)").add(first_hit - 0.05, transform="translate(0,0)")
    t = first_hit
    while t < last_hit:
        shake.add(t, transform=f"translate({rnd.uniform(-2.5, 2.5):.1f}px,{rnd.uniform(-2, 2):.1f}px)")
        t += 0.06
    css.append(shake.add(last_hit + 0.05, transform="translate(0,0)").add(CYCLE, transform="translate(0,0)").css())

    # ── 8. Dragones ───────────────────────────────────────────────────
    for a in attacks:
        i, fa = a["idx"], a["facing"]
        pal = th["dragons"][i % len(th["dragons"])]
        kf = KF(f"d{i}").add(0, opacity=0, transform="translate(-200px,-120px) rotate(0deg)")
        for piece in a["pieces"]:
            kf.add(piece[0][0] - 0.01, opacity=0)
            for j, (t, x, y) in enumerate(piece):
                nx_, ny_ = piece[min(j + 1, len(piece) - 1)][1:]
                px_, py_ = piece[max(j - 1, 0)][1:]
                ang = clamp(math.degrees(math.atan2(ny_ - py_, abs(nx_ - px_) + 25)) * fa * 0.6, -25, 25)
                kf.add(t, transform=f"translate({n(x)}px,{n(y + bob(a, t))}px) rotate({n(ang)}deg)", opacity=1)
            kf.add(piece[-1][0] + 0.01, opacity=0)
        last = a["pieces"][-1][-1]
        kf.add(CYCLE, opacity=0, transform=f"translate({n(last[1])}px,{n(last[2])}px) rotate(0deg)")
        css.append(kf.css())
        anim = f'animation-duration:{a["flap"]:.2f}s;animation-delay:-{rnd.uniform(0, a["flap"]):.2f}s'
        if th["kind"] == "pixel":
            spr = SPRITES[a["sprite"]]
            body = (f'<g class="wa" style="{anim}">{sprite_rects(spr["up"], spr["mouth"], pal, fa, a["px"], th["outline"])}</g>'
                    f'<g class="wb" style="{anim}">{sprite_rects(spr["down"], spr["mouth"], pal, fa, a["px"], th["outline"])}</g>')
        else:
            body = vector_dragon(th, pal, fa, a["scale"], anim)
        L["dragons"].append(f'<g class="dr" style="animation-name:d{i}">{body}</g>')

    # ── 9. Fuego ──────────────────────────────────────────────────────
    # Cada llama nace en la boca del dragón, vuela en línea recta girada en la dirección del chorro
    # y muere al llegar. Las del ataque son las de la simulación (cada una golpea un trozo en pie);
    # en la pasada final, un chorro largo hacia delante, más rápido que el propio dragón.
    c0, c1, c2 = th["fire_colors"]
    snap = 45 if th["kind"] == "pixel" else 1      # en pixel, giros de 45° para no romper la rejilla
    for a in attacks:
        for k in range(a["particles"]):
            te = a["pass"] + PASS_TIME * .2 + k * FIRE_PERIOD / a["particles"]
            while te <= a["pass"] + PASS_TIME * .8:
                m = mouth_pos(a, te)
                if on_screen(m):
                    dy = rnd.uniform(4, 26) if m[1] < GAMEOVER_Y else rnd.uniform(-12, 10)
                    a_flames.setdefault((a["idx"], k), []).append((te, m, (m[0] + a["facing"] * rnd.uniform(250, 320), m[1] + dy)))
                te += FIRE_PERIOD
        ps_ = th["particle_size"] * a["fire"]
        for k in range(a["particles"]):
            kf = KF(f"f{a['idx']}_{k}").add(0, opacity=0, transform=tf(-50, -50, 0, 0.4), fill=c0)
            for te, m, (tx, ty) in sorted(a_flames.get((a["idx"], k), []), key=lambda q: q[0]):
                mx_, my_ = lerp(m[0], tx, 0.5), lerp(m[1], ty, 0.5)
                ang = round(math.degrees(math.atan2(ty - m[1], tx - m[0])) / snap) * snap
                kf.add(te - 0.01, opacity=0, transform=tf(m[0], m[1], ang, 0.45), fill=c0)
                kf.add(te, opacity=1)
                kf.add(te + FIRE_TRAVEL * 0.5, transform=tf(mx_, my_, ang, 1.0), fill=c1)
                kf.add(te + FIRE_TRAVEL * 0.85, opacity=0.9, fill=c2)
                kf.add(te + FIRE_TRAVEL, opacity=0, transform=tf(tx, ty, ang, 1.35))
            css.append(kf.add(CYCLE, opacity=0, transform=tf(-50, -50, 0, 0.4), fill=c0).css())
            L["fire"].append(f'<g class="fl" style="animation-name:f{a["idx"]}_{k}" fill="{c0}">{fire_shape(th, ps_)}</g>')

    # chispas fijas donde revienta cada trozo (no se desplazan con el chorro)
    sparks = []
    for j, e in enumerate(sorted(elements, key=lambda e: e["hit"])):
        if j % 3:
            continue
        for q in range(3):
            ang = rnd.uniform(-160, -20)      # hacia arriba y a los lados
            sparks.append((e["hit"], e["x"], e["y"], ang, rnd.uniform(18, 34)))
    slots = []
    for sp in sparks:
        for sl in slots:
            if sl[-1][0] + 0.34 < sp[0] - 0.02:
                sl.append(sp)
                break
        else:
            slots.append([sp])
    for k, group in enumerate(slots):
        kf = KF(f"sk{k}").add(0, opacity=0, fill=c0)
        for (t, x, y, ang, dd) in group:
            ra, angs = math.radians(ang), round(ang / snap) * snap
            kf.add(t - 0.01, opacity=0, transform=tf(x, y, angs, .4), fill=c0)
            kf.add(t, opacity=1)
            kf.add(t + 0.16, transform=tf(x + dd * .7 * math.cos(ra), y + dd * .7 * math.sin(ra), angs, .8), fill=c1)
            kf.add(t + 0.32, opacity=0, transform=tf(x + dd * math.cos(ra), y + dd * math.sin(ra), angs, .5), fill=c2)
        css.append(kf.add(CYCLE, opacity=0).css())
        L["fire"].append(f'<g class="fl" style="animation-name:sk{k}" fill="{c0}">{fire_shape(th, th["particle_size"] * .55)}</g>')

    # onomatopeyas del cómic
    if th.get("bursts"):
        for a, word in zip(attacks, th["bursts"]):
            t0 = a["start"] + FIRE_TRAVEL + 0.2 * a["dur"]
            bx = target_x(a, t0)
            by = name_y0 - 22 if a["idx"] % 2 == 0 else name_y1 + 22
            kf = KF(f"bu{a['idx']}").add(0, opacity=0, transform="scale(0)")
            kf.add(t0, opacity=0, transform="scale(0)")
            kf.add(t0 + 0.12, opacity=1, transform="scale(1.25)")
            kf.add(t0 + 0.22, transform="scale(1) rotate(-6deg)")
            kf.add(t0 + 0.9, opacity=1, transform="scale(1) rotate(-6deg)")
            kf.add(t0 + 1.1, opacity=0, transform="scale(.6)")
            css.append(kf.add(CYCLE, opacity=0, transform="scale(0)").css())
            d, dy = vector_text(th, word, 30, bx, by)
            star = star_path(52, 30, 10)
            L["front"].append(
                f'<g class="bu" style="animation-name:bu{a["idx"]};transform-origin:{n(bx)}px {n(by)}px">'
                f'<path d="{star}" transform="translate({n(bx)} {n(by)}) scale(1 .8)" fill="#fff" stroke="#111" stroke-width="4"/>'
                f'<path d="{d}" transform="translate(0 {n(dy)})" fill="#ff3b30" stroke="#111" stroke-width="2" paint-order="stroke"/></g>')
        css.append(f".bu{{animation:{CYCLE}s linear infinite;opacity:0}}")

    # ── 10. GAME OVER ─────────────────────────────────────────────────
    L["front"].append(text_svg(th, "GAME OVER", "title", W / 2, GAMEOVER_Y, "go", ""))
    kf = KF("go").add(0, opacity=0, transform="scale(2.5)").add(t_gameover, opacity=0, transform="scale(2.5)")
    kf.add(t_gameover + 0.25, opacity=1, transform="scale(.92)").add(t_gameover + 0.35, transform="scale(1.05)")
    kf.add(t_gameover + 0.45, transform="scale(1)").add(T_FADE, opacity=1, transform="scale(1)")
    kf.add(T_FADE + 0.3, opacity=0, transform="scale(1)").add(CYCLE, opacity=0, transform="scale(2.5)")
    css.append(kf.css())

    # ── 11. Marcador ──────────────────────────────────────────────────
    if th["hud"]:
        hx, hy = 16 + ins, hud_y(ins)
        if th["kind"] == "pixel":
            hps = th.get("hud_ps", 3)
            L["hud"].append(text_svg(th, "SCORE", "small", hx + 14.5 * hps, hy))
            vx = hx + 36 * hps + 17.5 * hps
        else:
            gl = glyph_paths(load_font(th["font"], th["axes"]), "SCORE", 22, 0, 0)
            sw = gl[-1][1][2] - gl[0][1][0]
            L["hud"].append(text_svg(th, "SCORE", "small", hx + sw / 2, hy))
            vx = hx + sw + 8 + 40
        done = sorted(max(e["hit"] for e in elements if e["letter"] == li) + 0.35
                      for li in {e["letter"] for e in elements})
        times = [0.0] + done
        for k, t0 in enumerate(times):
            t1 = times[k + 1] if k + 1 < len(times) else T_RESET
            ch = [(0, 1 if k == 0 else 0)] + ([(t0, 1)] if k else []) + [(t1, 0)] + ([(T_RESET, 1)] if k == 0 else [])
            css.append(steps_kf(f"sc{k}", ch).css())
            val = f"{k * 12500:06d}"
            if th["kind"] == "pixel":
                L["hud"].append(f'<path class="sp" style="animation-name:sc{k}" fill="{th["accent"]}" d="{pixel_text_path(val, hps, vx, hy)}"/>')
            else:
                L["hud"].append(text_svg(th, val, "small", vx + 20, hy, "sp", f"animation-name:sc{k}"))


        # barra de energía del nombre: un bloque por letra, se vacía de derecha a izquierda
        hb = th["hp"]
        nb = len(done)
        hps = th.get("hud_ps", 3)
        bw, bh, gap = 16 * hps / 3, 10 * hps / 3, 3
        bx0 = W - ins - 18 - nb * (bw + gap)
        if th["kind"] == "pixel":
            L["hud"].append(f'<path fill="{th["text_fill"]}" d="{pixel_text_path("HP", hps, bx0 - 26 * hps / 3, hy)}"/>')
        else:
            L["hud"].append(text_svg(th, "HP", "small", bx0 - 22, hy))
        L["hud"].append(f'<rect x="{bx0 - 3}" y="{n(hy - bh / 2 - 3)}" width="{nb * (bw + gap) + 3}" height="{bh + 6}" '
                        f'rx="{hb.get("rx", 0)}" fill="{hb["back"]}" stroke="{hb["frame"]}" stroke-width="{hb.get("sw", 1.5)}"/>')
        low, mid, high = hb["colors"]
        for j in range(nb):
            t_lost = done[nb - 1 - j]
            ch = [(0, 1)] + [(t_lost + k * 0.08, 1 - k % 2) for k in range(5)] + [(t_lost + 0.4, 0), (T_RESET, 1)]
            css.append(steps_kf(f"hp{j}", ch).css())
            col = low if j < nb * 0.3 else (mid if j < nb * 0.6 else high)
            L["hud"].append(f'<rect class="sp" style="animation-name:hp{j}" x="{bx0 + j * (bw + gap)}" '
                            f'y="{n(hy - bh / 2)}" width="{bw}" height="{bh}" rx="{hb.get("rx", 0) / 2}" fill="{col}"/>')

    # ── 12. CSS y montaje final ───────────────────────────────────────
    common = (
        f".px,.fp{{animation:{CYCLE}s linear infinite;transform-box:fill-box;transform-origin:center}}"
        f".tl{{animation:{CYCLE}s linear infinite;transform-box:view-box}}"
        ".fp{opacity:0}"
        f".fl{{animation:{CYCLE}s linear infinite;transform-box:view-box;transform-origin:0 0;opacity:0}}"
        f".dr{{animation:{CYCLE}s linear infinite;transform-box:view-box;transform-origin:0 0;opacity:0}}"
        ".wa{animation:wa .36s steps(1,end) infinite}.wb{animation:wb .36s steps(1,end) infinite}"
        "@keyframes wa{0%{opacity:1}50%{opacity:0}}@keyframes wb{0%{opacity:0}50%{opacity:1}}"
        f".shake{{animation:shake {CYCLE}s linear infinite}}"
        f".go{{animation:go {CYCLE}s ease-out infinite;transform-box:fill-box;transform-origin:center;opacity:0}}"
        f".sp{{animation:{CYCLE}s steps(1,end) infinite;opacity:0}}"
        ".tw{animation:tw 1.6s steps(1,end) infinite}@keyframes tw{0%{opacity:1}60%{opacity:.35}}"
        ".led{animation:led 2.4s steps(1,end) infinite}@keyframes led{0%{opacity:1}90%{opacity:.3}}"
        ".rays{animation:rays 30s linear infinite;transform-origin:400px 160px}@keyframes rays{to{transform:rotate(360deg)}}"
    )
    scene = "".join(L["back"] + L["name"] + L["dragons"] + L["fire"] + L["front"] + L["hud"])
    if clip_id:
        scene = f'<g clip-path="url(#{clip_id})">{scene}</g>'
    if th["panel"] == "comic":
        scene += f'<rect x="2.5" y="2.5" width="{W - 5}" height="{H - 5}" rx="9" fill="none" stroke="#111" stroke-width="5"/>'
    crisp = ' shape-rendering="crispEdges"' if th["kind"] == "pixel" else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"{crisp}>'
            f"<title>{name} vs. 4 dragones</title><style>{common}{''.join(css)}</style>"
            f'<defs>{"".join(defs)}</defs>{pback}{scene}</svg>\n')


# ══════════════════════════════════════════════════════════════════════
#  COMPROBACIÓN DE LA COREOGRAFÍA
# ══════════════════════════════════════════════════════════════════════
def hud_y(ins):
    """Altura del centro del marcador (más pegado arriba si hay marco de consola)."""
    return 22 + ins // 2 - (3 if ins else 0)


def check_choreography(attacks):
    """Un dragón es UN solo elemento animado: si dos tramos de su vuelo se solapan en el
    tiempo, el navegador mezcla sus fotogramas clave y el dragón parpadea saltando de sitio."""
    for a in attacks:
        pieces = a["pieces"]
        for k, (p, q) in enumerate(zip(pieces, pieces[1:])):
            if q[0][0] < p[-1][0] + 0.05:
                raise SystemExit(
                    f"✘ Dragón {a['idx'] + 1}: su pasada final empieza en {q[0][0]:.2f} s pero su salida "
                    f"no termina hasta {p[-1][0]:.2f} s. Sube su pass_at.")
    for a in attacks:
        if a["pieces"][-1][-1][0] > T_FADE:
            print(f"  ⚠ el dragón {a['idx'] + 1} sigue volando después del fundido ({T_FADE} s)")

def main():
    ap = argparse.ArgumentParser(description="Genera la animación SVG de dragones vs nombre")
    ap.add_argument("--name", default=NAME)
    ap.add_argument("--theme", choices=list(THEMES) + ["all"], default="all")
    ap.add_argument("--seed", type=int, default=SEED, help="otra partida (la de por defecto es la de siempre)")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--fire", choices=list(PIXEL_FIRE), help="forma del fuego (por defecto FIRE_STYLE)")
    args = ap.parse_args()
    if args.fire:
        global FIRE_STYLE
        FIRE_STYLE = args.fire
    os.makedirs(args.out, exist_ok=True)
    for key in (THEMES if args.theme == "all" else [args.theme]):
        path = os.path.join(args.out, f"dragons-{key}.svg")
        svg = render(key, args.name, args.seed)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"✔ {path}  ({len(svg) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
