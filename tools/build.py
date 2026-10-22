"""Genera los SVG animados de profile/assets (portada de la org Forgia-AI-Agents en GitHub).

GitHub muestra los SVG como <img>: sin JavaScript ni recursos externos. Por eso cada SVG
lleva sus fuentes (Space Mono y Plus Jakarta Sans, OFL) recortadas a los caracteres que usa
e incrustadas en base64, y todo el movimiento es CSS o SMIL. Con «reducir movimiento» del
sistema, cada SVG queda quieto en su estado final.

Uso:  python tools/build.py      (requiere fonttools y brotli)
"""
from __future__ import annotations

import base64
import io
import pathlib
import random
from html import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "profile" / "assets"

# Marca Forgia
NERO, NERO_SOFT, NERO_DEEP = "#0E0E0E", "#151515", "#071318"
GOLD, GOLD_LIGHT, GOLD_DARK = "#C9A96E", "#E8D5A8", "#A68D5B"
CREAM, TEAL, TEAL_LIGHT = "#F7F3ED", "#2A6B7C", "#6FC8D8"
TAUPE, TAUPE_LIGHT, GREEN = "#7A7068", "#B0A89A", "#25D366"

FACES = {
    "mono": ("Space Mono", 400, "SpaceMono-Regular.woff2"),
    "monob": ("Space Mono", 700, "SpaceMono-Bold.woff2"),
    "sans": ("Plus Jakarta Sans", 400, "PlusJakartaSans-Regular.woff2"),
    "sansb": ("Plus Jakarta Sans", 600, "PlusJakartaSans-SemiBold.woff2"),
}
_fonts: dict[str, TTFont] = {}


def font(key: str) -> TTFont:
    if key not in _fonts:
        _fonts[key] = TTFont(FONTS / FACES[key][2])
    return _fonts[key]


def measure(key: str, text: str, size: float, spacing: float = 0) -> float:
    """Ancho en px de `text` con esa fuente (para dimensionar burbujas y centrar)."""
    f = font(key)
    cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    w = 0
    for ch in text:
        g = cmap.get(ord(ch))
        w += (hmtx[g][0] if g else upm * 0.6) * size / upm + spacing
    return w - spacing if text else 0


class Svg:
    """Acumula cuerpo, CSS y el texto usado por cada fuente (para recortarlas)."""

    def __init__(self, w: int, h: int, title: str, desc: str):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.css: list[str] = []
        self.defs: list[str] = []
        self.body: list[str] = []
        self.used: dict[str, set[str]] = {k: set() for k in FACES}

    def text(self, x, y, s, key="sans", size=16, fill=CREAM, anchor="start", spacing=0, cls="", style="", extra=""):
        self.used[key].update(s)
        fam, wt, _ = FACES[key]
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-weight="{wt}" font-size="{size}" '
                f'fill="{fill}" text-anchor="{anchor}"{ls}{c}{st}{extra}>{escape(s)}</text>')

    def render(self) -> str:
        faces = []
        for key, chars in self.used.items():
            if not chars:
                continue
            fam, wt, file = FACES[key]
            opts = subset.Options()
            opts.flavor = "woff2"
            opts.layout_features = ["kern", "liga"]
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(sorted(chars)) + " ")
            f = TTFont(FONTS / file)
            sub.subset(f)
            buf = io.BytesIO()
            f.flavor = "woff2"
            f.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            faces.append(f"@font-face{{font-family:'{fam}';font-weight:{wt};"
                         f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
        css = "\n".join(faces + self.css + [
            "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">\n'
                f'<title id="t">{escape(self.title)}</title>\n<desc id="d">{escape(self.desc)}</desc>\n'
                f'<style>\n{css}\n</style>\n<defs>\n' + "\n".join(self.defs) + "\n</defs>\n"
                + "\n".join(self.body) + "\n</svg>\n")


def brackets(x, y, w, h, size=22, color=GOLD, width=2, cls=""):
    c = f' class="{cls}"' if cls else ""
    d = (f"M{x},{y + size} V{y} H{x + size} M{x + w - size},{y} H{x + w} V{y + size} "
         f"M{x + w},{y + h - size} V{y + h} H{x + w - size} M{x + size},{y + h} H{x} V{y + h - size}")
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{c}/>'


def frame(s: Svg, glow=True):
    """Fondo común: nero, rejilla dorada que se desvanece hacia los bordes y halo."""
    w, h = s.w, s.h
    s.defs += [
        f'<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        f'<path d="M40 0H0V40" fill="none" stroke="{GOLD}" stroke-opacity=".09" stroke-width="1"/></pattern>',
        '<radialGradient id="fade" cx="50%" cy="45%" r="65%"><stop offset="0" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>',
        f'<mask id="gridmask"><rect width="{w}" height="{h}" fill="url(#fade)"/></mask>',
        f'<radialGradient id="halo" cx="50%" cy="38%" r="55%"><stop offset="0" stop-color="{GOLD}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="halo2" cx="92%" cy="100%" r="45%"><stop offset="0" stop-color="{TEAL}" stop-opacity=".22"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>',
        f'<clipPath id="round"><rect width="{w}" height="{h}" rx="18"/></clipPath>',
    ]
    s.body.append('<g clip-path="url(#round)">')
    s.body.append(f'<rect width="{w}" height="{h}" fill="{NERO}"/>')
    if glow:
        s.body.append(f'<rect width="{w}" height="{h}" fill="url(#halo)"/>')
        s.body.append(f'<rect width="{w}" height="{h}" fill="url(#halo2)"/>')
    s.body.append(f'<rect width="{w}" height="{h}" fill="url(#grid)" mask="url(#gridmask)"/>')


def close_frame(s: Svg):
    s.body.append("</g>")
    s.body.append(f'<rect x=".5" y=".5" width="{s.w - 1}" height="{s.h - 1}" rx="18" fill="none" '
                  f'stroke="{GOLD}" stroke-opacity=".22"/>')


# ─────────────────────────────────────────────────────────────────────────────
def hero() -> str:
    s = Svg(1200, 460, "Forgia · Agentes de IA para WhatsApp",
            "Portada animada: el logotipo FORGIA se enciende letra a letra sobre una rejilla dorada; "
            "debajo, «Agentes de IA para WhatsApp que cualifican tus leads».")
    frame(s)
    W = s.w
    s.css += [
        "@keyframes ignite{0%{opacity:0;transform:translateY(26px)}60%{opacity:1}100%{opacity:1;transform:none}}",
        ".l{animation:ignite .9s cubic-bezier(.2,.8,.2,1) both}",
        "@keyframes dot{0%,100%{opacity:1}50%{opacity:.35}}",
        ".dot{animation:dot 2.4s ease-in-out 1.6s infinite}",
        "@keyframes fadeup{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}",
        ".tag{animation:fadeup .9s ease-out 1.1s both}",
        "@keyframes rule{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        ".rule{transform-box:fill-box;transform-origin:center;animation:rule 1.1s cubic-bezier(.2,.8,.2,1) .8s both}",
        "@keyframes draw{from{stroke-dashoffset:120}to{stroke-dashoffset:0}}",
        ".br{stroke-dasharray:120;animation:draw 1.2s ease-out .2s both}",
        "@keyframes scan{0%{transform:translateY(-10px);opacity:0}10%{opacity:.5}90%{opacity:.5}100%{transform:translateY(470px);opacity:0}}",
        ".scan{animation:scan 7s linear 2s infinite both}",
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}",
        ".caret{animation:blink 1s steps(1) infinite}",
        "@keyframes live{0%{r:4;opacity:.9}100%{r:13;opacity:0}}",
        ".ping{animation:live 1.8s ease-out infinite}",
        "@keyframes float{0%{transform:translateY(0);opacity:0}15%{opacity:.7}100%{transform:translateY(-140px);opacity:0}}",
        ".p{animation:float linear infinite both}",
        ".hud{animation:fadeup .8s ease-out 1.5s both}",
    ]
    # Partículas (chispas de forja)
    rnd = random.Random(7)
    for _ in range(22):
        x, y = rnd.uniform(60, W - 60), rnd.uniform(240, 460)
        d, dl, r = rnd.uniform(6, 11), rnd.uniform(0, 9), rnd.uniform(1, 2.2)
        s.body.append(f'<circle class="p" cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{GOLD_LIGHT}" '
                      f'style="animation-duration:{d:.1f}s;animation-delay:-{dl:.1f}s"/>')
    # Línea de barrido
    s.defs.append(f'<linearGradient id="scang" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{GOLD_LIGHT}" stop-opacity=".55"/>'
                  f'<stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>')
    s.body.append(f'<rect class="scan" x="0" y="0" width="{W}" height="1.5" fill="url(#scang)"/>')
    # Esquinas HUD
    s.body.append(brackets(28, 28, W - 56, s.h - 56, size=30, cls="br"))
    # HUD: esquinas con texto
    hud = []
    hud.append(s.text(64, 70, "AGENTES DE IA · WHATSAPP", "mono", 13, TAUPE_LIGHT, spacing=2.6))
    hud.append(f'<circle class="ping" cx="{W - 236}" cy="65" r="4" fill="none" stroke="{GREEN}" stroke-width="2"/>')
    hud.append(f'<circle cx="{W - 236}" cy="65" r="4" fill="{GREEN}"/>')
    hud.append(s.text(W - 222, 70, "EN PRODUCCIÓN", "mono", 13, TAUPE_LIGHT, spacing=2.6))
    hud.append(s.text(64, s.h - 56, "ESPAÑA · ECUADOR", "mono", 13, TAUPE_LIGHT, spacing=2.6))
    hud.append(s.text(W - 64, s.h - 56, "FORGIA.ES", "mono", 13, GOLD, anchor="end", spacing=2.6))
    s.body.append('<g class="hud">' + "".join(hud) + "</g>")
    # Logotipo letra a letra
    size, track = 118, 0.16 * 118
    adv = measure("monob", "F", size)
    letters = "FORGIA"
    total = len(letters) * (adv + track) + adv * 0.75
    x0, base = W / 2 - total / 2, 222
    s.defs.append(f'<linearGradient id="shine" x1="-700" y1="0" x2="-100" y2="0" gradientUnits="userSpaceOnUse">'
                  f'<stop offset="0" stop-color="{CREAM}"/><stop offset=".45" stop-color="{CREAM}"/>'
                  f'<stop offset=".5" stop-color="{GOLD_LIGHT}"/><stop offset=".55" stop-color="{CREAM}"/>'
                  f'<stop offset="1" stop-color="{CREAM}"/>'
                  f'<animate attributeName="x1" values="-700;1300" dur="5s" begin="2.2s" repeatCount="indefinite"/>'
                  f'<animate attributeName="x2" values="-100;1900" dur="5s" begin="2.2s" repeatCount="indefinite"/>'
                  f'</linearGradient>')
    s.defs.append('<filter id="glow" x="-20%" y="-40%" width="140%" height="180%">'
                  '<feGaussianBlur stdDeviation="9" result="b"/><feMerge><feMergeNode in="b"/>'
                  '<feMergeNode in="SourceGraphic"/></feMerge></filter>')
    g = []
    for i, ch in enumerate(letters):
        g.append(s.text(x0 + i * (adv + track), base, ch, "monob", size, "url(#shine)", cls="l",
                        style=f"animation-delay:{0.15 + i * 0.12:.2f}s"))
    dot_x = x0 + len(letters) * (adv + track) - track * 0.4
    s.body.append(f'<g filter="url(#glow)">{"".join(g)}</g>')
    s.body.append(s.text(dot_x, base, ".", "monob", size, GOLD, cls="l dot",
                         style=f"animation-delay:{0.15 + 6 * 0.12:.2f}s"))
    # Regla dorada y lema
    s.body.append(f'<rect class="rule" x="{W / 2 - 150}" y="250" width="300" height="2" fill="{GOLD}"/>')
    s.body.append(f'<rect class="rule" x="{W / 2 - 5}" y="246" width="10" height="10" fill="{GOLD}" '
                  f'transform="rotate(45 {W / 2} 251)"/>')
    s.body.append(s.text(W / 2, 306, "Agentes de IA para WhatsApp que cualifican tus leads.", "sansb", 31, CREAM,
                         anchor="middle", cls="tag"))
    # Máquina de escribir: 3 frases en bucle
    lines = ["responde al momento, también a las 3 de la mañana",
             "precualifica, agenda la cita y manda el recordatorio",
             "te avisa solo cuando hay alguien listo para cerrar"]
    fs = 22
    cw = measure("mono", "a", fs)
    cycle, n = 13.5, len(lines)
    win = 100 / n
    for i, line in enumerate(lines):
        txt = "> " + line
        tw = len(txt) * cw
        x = W / 2 - tw / 2
        a, b = i * win, (i + 1) * win
        t_end = a + win * 0.48
        vis = (f"@keyframes v{i}{{0%{{opacity:{1 if i == 0 else 0}}}"
               + (f"{a:.2f}%{{opacity:0}}{a + 0.01:.2f}%{{opacity:1}}" if i else "")
               + f"{b - 1.5:.2f}%{{opacity:1}}{b:.2f}%,100%{{opacity:0}}}}")
        typ = (f"@keyframes k{i}{{0%{{transform:scaleX(0)}}{a:.2f}%{{transform:scaleX(0);"
               f"animation-timing-function:steps({len(txt)},end)}}{t_end:.2f}%,100%{{transform:scaleX(1)}}}}")
        car = (f"@keyframes c{i}{{0%{{transform:translateX(0)}}{a:.2f}%{{transform:translateX(0);"
               f"animation-timing-function:steps({len(txt)},end)}}{t_end:.2f}%,100%{{transform:translateX({tw:.1f}px)}}}}")
        s.css += [vis, typ, car,
                  f".v{i}{{opacity:{1 if i == 0 else 0};animation:v{i} {cycle}s linear 1.8s infinite both}}",
                  f".k{i}{{transform-box:fill-box;transform-origin:left;animation:k{i} {cycle}s linear 1.8s infinite both}}",
                  f".c{i}{{animation:c{i} {cycle}s linear 1.8s infinite both}}"]
        s.defs.append(f'<clipPath id="tc{i}"><rect class="k{i}" x="{x:.1f}" y="330" width="{tw:.1f}" height="34"/></clipPath>')
        s.body.append(
            f'<g class="v{i}">'
            + f'<g clip-path="url(#tc{i})">' + s.text(x, 356, txt, "mono", fs, GOLD) + "</g>"
            + f'<g class="c{i}"><rect class="caret" x="{x + 2:.1f}" y="337" width="11" height="24" fill="{GOLD_LIGHT}"/></g>'
            + "</g>")
    close_frame(s)
    return s.render()


# ─────────────────────────────────────────────────────────────────────────────
def chat() -> str:
    s = Svg(1200, 680, "Demo: una conversación real de principio a fin",
            "A la izquierda, un chat de WhatsApp: un cliente pide cita, el agente ofrece dos horarios, el cliente "
            "responde con una nota de voz y el agente confirma la reserva con código. A la derecha, los avisos que "
            "ve el equipo en su panel y el lead avanzando de «nuevo» a «cita».")
    frame(s, glow=False)
    s.body.append(f'<rect width="{s.w}" height="{s.h}" fill="url(#halo2)"/>')
    LOOP, END = 17.0, 15.6           # segundos: bucle y comienzo del fundido final
    pct = lambda t: t / LOOP * 100   # noqa: E731
    uid = iter(range(1000))

    def appear(t: float, hide: float | None = None, base_visible=True) -> str:
        """Clase con su keyframe: aparece en `t`, se va en `hide` (o al final del bucle)."""
        k = f"a{next(uid)}"
        a, b = pct(t), pct(t + 0.35)
        if hide is None:
            h0, h1 = pct(END), pct(END + 0.6)
        else:
            h0, h1 = pct(hide), pct(hide + 0.2)
        s.css.append(f"@keyframes {k}{{0%,{a:.2f}%{{opacity:0;transform:translateY(10px)}}"
                     f"{b:.2f}%,{h0:.2f}%{{opacity:1;transform:none}}{h1:.2f}%,100%{{opacity:0;transform:none}}}}")
        s.css.append(f".{k}{{opacity:{1 if base_visible else 0};animation:{k} {LOOP}s linear infinite both}}")
        return k

    # ── Teléfono ──
    px, py, pw, ph = 64, 36, 410, 608
    s.defs.append(f'<clipPath id="phone"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="34"/></clipPath>')
    s.defs.append('<pattern id="wa" width="26" height="26" patternUnits="userSpaceOnUse">'
                  '<circle cx="4" cy="4" r="1" fill="#fff" fill-opacity=".035"/>'
                  '<circle cx="17" cy="15" r="1.4" fill="#fff" fill-opacity=".03"/></pattern>')
    s.body.append(f'<rect x="{px - 6}" y="{py - 6}" width="{pw + 12}" height="{ph + 12}" rx="40" fill="#050505" '
                  f'stroke="{GOLD}" stroke-opacity=".35"/>')
    s.body.append(f'<g clip-path="url(#phone)"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="#0B141A"/>'
                  f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="url(#wa)"/>')
    s.body.append(f'<rect x="{px}" y="{py}" width="{pw}" height="74" fill="#1F2C34"/>')
    s.body.append(f'<circle cx="{px + 42}" cy="{py + 38}" r="20" fill="{NERO}" stroke="{GOLD}" stroke-width="1.5"/>')
    s.body.append(s.text(px + 42, py + 45, "F", "monob", 19, GOLD, anchor="middle"))
    s.body.append(s.text(px + 74, py + 33, "Asistente de IA", "sansb", 17, "#E9EDEF"))
    s.css.append("@keyframes typingtxt{0%,100%{opacity:1}50%{opacity:.55}}")
    s.body.append(s.text(px + 74, py + 54, "en línea · responde por tu negocio", "sans", 13, "#8696A0"))
    # input
    s.body.append(f'<rect x="{px + 12}" y="{py + ph - 58}" width="{pw - 76}" height="44" rx="22" fill="#1F2C34"/>')
    s.body.append(s.text(px + 34, py + ph - 30, "Mensaje", "sans", 15, "#8696A0"))
    s.body.append(f'<circle cx="{px + pw - 36}" cy="{py + ph - 36}" r="22" fill="#00A884"/>')
    s.body.append(f'<path d="M{px + pw - 41},{py + ph - 45} v12 a5,5 0 0 0 10,0 v-12 a5,5 0 0 0 -10,0 z '
                  f'M{px + pw - 45},{py + ph - 34} a9,9 0 0 0 18,0 M{px + pw - 36},{py + ph - 25} v5" '
                  f'fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')

    FS, LH, PADX, PADY = 16, 22, 13, 10
    y = py + 96

    def ticks(x, yy, t_read):
        k = f"tk{next(uid)}"
        s.css.append(f"@keyframes {k}{{0%,{pct(t_read):.2f}%{{stroke:#8696A0}}{pct(t_read + .1):.2f}%,100%{{stroke:#53BDEB}}}}")
        s.css.append(f".{k}{{stroke:#53BDEB;animation:{k} {LOOP}s linear infinite both}}")
        return (f'<path class="{k}" d="M{x - 4},{yy} l3.5,3.5 l7,-8 M{x + 2},{yy + 3.5} l7,-8" '
                f'fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')

    def bubble(lines, side, t, time="10:41", mono_last=False, read=None):
        nonlocal y
        widths = [measure("sans", ln, FS) for ln in lines]
        if mono_last:
            widths[-1] = measure("monob", lines[-1], FS)
        bw = max(max(widths) + PADX * 2, 120)
        bh = len(lines) * LH + PADY * 2 + 12
        bx = px + 16 if side == "in" else px + pw - 16 - bw
        fill = "#1F2C34" if side == "in" else "#005C4B"
        k = appear(t)
        parts = [f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{bh}" rx="10" fill="{fill}"/>']
        for i, ln in enumerate(lines):
            last = mono_last and i == len(lines) - 1
            parts.append(s.text(bx + PADX, y + PADY + 16 + i * LH, ln, "monob" if last else "sans", FS,
                                GOLD_LIGHT if last else "#E9EDEF"))
        tx = bx + bw - (34 if side == "out" else 12)
        parts.append(s.text(tx, y + bh - 8, time, "sans", 11, "#8696A0" if side == "in" else "#9FD6C8", anchor="end"))
        if side == "out":
            parts.append(ticks(bx + bw - 28, y + bh - 15, read if read else t + 1))
        s.body.append(f'<g class="{k}">' + "".join(parts) + "</g>")
        top = y
        y += bh + 12
        return top

    def typing(t0, t1, at_y):
        k = appear(t0, hide=t1, base_visible=False)
        x = px + pw - 16 - 70
        dots = "".join(
            f'<circle cx="{x + 22 + i * 13}" cy="{at_y + 20}" r="4" fill="#9FD6C8" '
            f'style="animation:bounce 1s ease-in-out {i * .15:.2f}s infinite"/>' for i in range(3))
        s.body.append(f'<g class="{k}"><rect x="{x}" y="{at_y}" width="70" height="40" rx="10" fill="#005C4B"/>{dots}</g>')

    s.css.append("@keyframes bounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-5px)}}")

    bubble(["Hola, ¿tienen hueco esta semana", "para una limpieza dental?"], "in", 0.6)
    typing(1.4, 3.0, y)
    bubble(["¡Hola! Sí: mañana a las 10:00", "o el viernes a las 17:30.", "¿Cuál le viene mejor?"], "out", 3.0, read=4.2)
    # Nota de voz
    t_voice = 5.0
    k = appear(t_voice)
    bw, bh, bx = 300, 96, px + 16
    vp = [f'<rect x="{bx}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="#1F2C34"/>',
          f'<circle cx="{bx + 30}" cy="{y + 30}" r="15" fill="{TEAL_LIGHT}"/>',
          f'<path d="M{bx + 26},{y + 23} l11,7 l-11,7 z" fill="#0B141A"/>']
    rnd = random.Random(3)
    bars = []
    for i in range(30):
        hgt = rnd.choice([6, 9, 12, 16, 20, 14, 8, 18, 11])
        bars.append(f'<rect x="{bx + 56 + i * 6.6:.1f}" y="{y + 30 - hgt / 2:.1f}" width="3" height="{hgt}" rx="1.5"/>')
    vp.append(f'<g fill="#8696A0">{"".join(bars)}</g>')
    s.css.append(f"@keyframes play{{0%,{pct(t_voice + .5):.2f}%{{transform:scaleX(0)}}{pct(t_voice + 1.6):.2f}%,100%{{transform:scaleX(1)}}}}")
    s.css.append(f".play{{transform-box:fill-box;transform-origin:left;animation:play {LOOP}s linear infinite both}}")
    s.defs.append(f'<clipPath id="played"><rect class="play" x="{bx + 54}" y="{y + 8}" width="202" height="44"/></clipPath>')
    vp.append(f'<g fill="{TEAL_LIGHT}" clip-path="url(#played)">{"".join(bars)}</g>')
    vp.append(s.text(bx + 56, y + 58, "0:06", "sans", 11, "#8696A0"))
    vp.append(s.text(bx + bw - 12, y + 58, "10:42", "sans", 11, "#8696A0", anchor="end"))
    kt = appear(t_voice + 0.9)
    vp.append(f'<g class="{kt}"><path d="M{bx + 12},{y + 68} H{bx + bw - 12}" stroke="#ffffff" stroke-opacity=".08"/>'
              + s.text(bx + 14, y + 86, "transcrita: «El viernes, porfa. Soy Daniela.»", "sans", 13, TAUPE_LIGHT,
                       style="font-style:italic") + "</g>")
    s.body.append(f'<g class="{k}">' + "".join(vp) + "</g>")
    y += bh + 12
    typing(6.5, 8.0, y)
    bubble(["Perfecto, Daniela. Reserva", "confirmada: viernes a las 17:30.", "Le escribo el día antes.",
            "Código FRG-4821"], "out", 8.0, time="10:42", mono_last=True, read=9.0)
    s.body.append("</g>")

    # ── Panel derecho: lo que ve el equipo (resultado, no cómo se hace) ──
    rx0, rw = 530, 610
    s.body.append(s.text(rx0, 74, "LO QUE VE TU EQUIPO", "mono", 13, GOLD, spacing=2.6))
    s.body.append(s.text(rx0, 104, "Mientras el cliente escribe, el panel se pone al día solo.", "sans", 17, CREAM))
    stages = [("NUEVO", 0.6), ("CONTACTADO", 3.0), ("CALIENTE", 5.2), ("CUALIFICADO", 7.4), ("CITA", 8.2)]
    sy, gap = 134, 8
    cw = (rw - gap * (len(stages) - 1)) / len(stages)
    for i, (name, t) in enumerate(stages):
        x = rx0 + i * (cw + gap)
        k = f"st{i}"
        on_fill, on_stroke = ("#1d1a14", GOLD) if i < 4 else ("#10261c", GREEN)
        s.css.append(f"@keyframes {k}{{0%,{pct(t):.2f}%{{fill:{NERO_SOFT};stroke:{GOLD};stroke-opacity:.25}}"
                     f"{pct(t + .3):.2f}%,{pct(END):.2f}%{{fill:{on_fill};stroke:{on_stroke};stroke-opacity:1}}"
                     f"{pct(END + .6):.2f}%,100%{{fill:{NERO_SOFT};stroke:{GOLD};stroke-opacity:.25}}}}")
        s.css.append(f".{k}{{fill:{on_fill};stroke:{on_stroke};animation:{k} {LOOP}s linear infinite both}}")
        kt = f"sl{i}"
        col = GOLD_LIGHT if i < 4 else GREEN
        s.css.append(f"@keyframes {kt}{{0%,{pct(t):.2f}%{{fill:{TAUPE}}}{pct(t + .3):.2f}%,{pct(END):.2f}%{{fill:{col}}}"
                     f"{pct(END + .6):.2f}%,100%{{fill:{TAUPE}}}}}")
        s.css.append(f".{kt}{{fill:{col};animation:{kt} {LOOP}s linear infinite both}}")
        s.body.append(f'<rect class="{k}" x="{x:.1f}" y="{sy}" width="{cw:.1f}" height="38" rx="4" stroke-width="1.4"/>')
        s.body.append(s.text(x + cw / 2, sy + 24, name, "monob", 12, TAUPE, anchor="middle", spacing=1.2, cls=kt))
    # Avisos del panel
    cards = [
        (0.6, TEAL_LIGHT, "Nuevo contacto por WhatsApp", "Pregunta por una limpieza dental", "10:41"),
        (3.0, GREEN, "Respondido al momento", "Le ofrece los dos horarios libres", "10:41"),
        (5.6, TEAL_LIGHT, "Nota de voz entendida", "«El viernes, porfa. Soy Daniela.»", "10:42"),
        (8.0, GOLD, "Cita agendada · Daniela", "Viernes 17:30 · código FRG-4821", "10:42"),
        (8.8, GOLD_LIGHT, "Recordatorio programado", "Le escribe el día antes de la cita", "10:42"),
        (9.6, GREEN, "Aviso en el móvil del vendedor", "Todo listo para atenderla el viernes", "10:42"),
    ]
    ch, cg, y0 = 64, 12, 196
    for i, (t, col, title, sub, clock) in enumerate(cards):
        yy = y0 + i * (ch + cg)
        k = appear(t)
        s.body.append(
            f'<g class="{k}"><rect x="{rx0}" y="{yy}" width="{rw}" height="{ch}" rx="10" fill="{NERO_SOFT}" '
            f'stroke="{col}" stroke-opacity=".35"/>'
            f'<rect x="{rx0}" y="{yy + 12}" width="3" height="{ch - 24}" rx="1.5" fill="{col}"/>'
            f'<circle cx="{rx0 + 34}" cy="{yy + ch / 2}" r="15" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".6"/>'
            f'<circle cx="{rx0 + 34}" cy="{yy + ch / 2}" r="4.5" fill="{col}"/>'
            + s.text(rx0 + 62, yy + 27, title, "sansb", 17, CREAM)
            + s.text(rx0 + 62, yy + 48, sub, "sans", 14, TAUPE_LIGHT)
            + s.text(rx0 + rw - 18, yy + 27, clock, "mono", 12, TAUPE, anchor="end") + "</g>")
    close_frame(s)
    return s.render()


# ─────────────────────────────────────────────────────────────────────────────
def stats() -> str:
    # Cifras públicas con fuente (las mismas de forgia.es), no datos internos de Forgia.
    items = [("", "42", " h", "tarda de media una empresa", "en responder a un lead.", "Harvard Business Review, 2011"),
             ("", "23", " %", "de las empresas nunca", "llega a responder.", "Harvard Business Review, 2011"),
             ("×", "21", "", "más probable cualificar si respondes", "en 5 minutos en vez de en 30.", "Oldroyd / InsideSales.com, 2007")]
    s = Svg(1200, 250, "Por qué importa responder rápido",
            "Una empresa tarda de media 42 horas en responder a un lead (HBR, 2011); el 23 % nunca responde (HBR, "
            "2011); responder en 5 minutos en vez de 30 multiplica por 21 la probabilidad de cualificarlo "
            "(Oldroyd / InsideSales.com, 2007).")
    frame(s, glow=False)
    s.css += [
        "@keyframes roll{from{transform:translateY(0)}}",
        ".r{animation:roll 1.9s cubic-bezier(.16,.84,.24,1) both}",
        "@keyframes bar{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        ".bar{transform-box:fill-box;transform-origin:left;animation:bar 1.6s cubic-bezier(.2,.8,.2,1) both}",
        "@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}",
        ".lab{animation:in .8s ease-out both}",
    ]
    n, gap, mx = len(items), 22, 34
    cw = (s.w - mx * 2 - gap * (n - 1)) / n
    fs, rowh = 66, 78
    dw = measure("monob", "0", fs)
    for i, (pre, num, suf, l1, l2, src) in enumerate(items):
        x = mx + i * (cw + gap)
        s.body.append(f'<rect x="{x:.1f}" y="28" width="{cw:.1f}" height="194" rx="8" fill="{NERO_SOFT}" '
                      f'stroke="{GOLD}" stroke-opacity=".22"/>')
        s.body.append(brackets(x, 28, cw, 194, size=14, color=GOLD, width=1.6))
        top, cx = 48, x + 24
        if pre:
            s.body.append(s.text(cx, top + 62, pre, "monob", fs, GOLD))
            cx += measure("monob", pre, fs)
        for j, ch in enumerate(num):
            dx = cx + j * dw
            cid = f"o{i}{j}"
            s.defs.append(f'<clipPath id="{cid}"><rect x="{dx - 2:.1f}" y="{top}" width="{dw + 4:.1f}" height="{rowh}"/></clipPath>')
            final = -(10 + int(ch)) * rowh
            digits = "".join(s.text(dx, top + 62 + r * rowh, str(r % 10), "monob", fs, GOLD) for r in range(20))
            s.body.append(f'<g clip-path="url(#{cid})"><g class="r" style="transform:translateY({final}px);'
                          f'animation-delay:{0.2 + i * 0.15 + j * 0.12:.2f}s">{digits}</g></g>')
        if suf:
            s.body.append(s.text(cx + len(num) * dw + 6, top + 62, suf.strip(), "monob", 34, GOLD_LIGHT))
        s.body.append(f'<rect class="bar" x="{x + 24:.1f}" y="134" width="{cw - 48:.1f}" height="2" fill="{GOLD}" '
                      f'style="animation-delay:{0.4 + i * 0.15:.2f}s"/>')
        s.body.append(f'<g class="lab" style="animation-delay:{0.8 + i * 0.15:.2f}s">'
                      + s.text(x + 24, 162, l1, "sansb", 16, CREAM)
                      + s.text(x + 24, 183, l2, "sansb", 16, CREAM)
                      + s.text(x + 24, 206, src, "sans", 12, TAUPE) + "</g>")
    close_frame(s)
    return s.render()


# ─────────────────────────────────────────────────────────────────────────────
def divider() -> str:
    s = Svg(1200, 34, "", "")
    s.title, s.desc = "Separador", "Línea dorada"
    s.defs.append(f'<linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{GOLD}" stop-opacity=".55"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>')
    s.defs.append(f'<linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="{GOLD_LIGHT}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{GOLD_LIGHT}"/><stop offset="1" stop-color="{GOLD_LIGHT}" stop-opacity="0"/></linearGradient>')
    s.css += ["@keyframes glint{0%{transform:translateX(-200px)}100%{transform:translateX(1400px)}}",
              ".g{animation:glint 4.5s cubic-bezier(.5,0,.5,1) infinite}"]
    s.body += [f'<rect x="0" y="16.5" width="1200" height="1" fill="url(#ln)"/>',
               f'<rect class="g" x="0" y="16" width="160" height="2" fill="url(#gl)"/>',
               f'<rect x="594" y="11" width="12" height="12" fill="{NERO}" stroke="{GOLD}" transform="rotate(45 600 17)"/>']
    return s.render()


def footer() -> str:
    s = Svg(1200, 220, "Forgia", "El logotipo FORGIA sobre un ecualizador dorado que se mueve como una nota de voz.")
    frame(s)
    s.css += ["@keyframes eq{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}",
              ".eq{transform-box:fill-box;transform-origin:center;animation:eq ease-in-out infinite}"]
    rnd = random.Random(11)
    n = 64
    for i in range(n):
        x = 60 + i * (1080 / n)
        h = 90 * (0.35 + 0.65 * abs(((i / (n - 1)) - 0.5) * 2 - 1))
        d, dl = rnd.uniform(0.9, 1.8), rnd.uniform(0, 1.5)
        col = GOLD if i % 3 else TEAL_LIGHT
        s.body.append(f'<rect class="eq" x="{x:.1f}" y="{110 - h / 2:.1f}" width="6" height="{h:.1f}" rx="3" fill="{col}" '
                      f'fill-opacity=".22" style="animation-duration:{d:.2f}s;animation-delay:-{dl:.2f}s"/>')
    s.body.append(f'<rect x="420" y="70" width="360" height="80" fill="{NERO}" fill-opacity=".72" rx="6"/>')
    s.body.append(brackets(420, 70, 360, 80, size=16))
    adv = measure("monob", "F", 46)
    word = s.text(600 - 14, 126, "FORGIA", "monob", 46, CREAM, anchor="middle", spacing=7.4)
    s.body.append(word)
    s.body.append(s.text(600 - 14 + (6 * adv + 5 * 7.4) / 2 + 2, 126, ".", "monob", 46, GOLD))
    s.body.append(s.text(600, 186, "Tus leads, atendidos al momento. Las 24 horas.", "sans", 16, TAUPE_LIGHT,
                         anchor="middle"))
    close_frame(s)
    return s.render()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("hero", hero), ("demo", chat), ("datos", stats),
                     ("divider", divider), ("footer", footer)]:
        svg = fn()
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        print(f"{name}.svg  {len(svg) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
