"""Shared drawing helpers for section packs. Import this; never re-implement it.

THE TWO LAWS every renderer obeys:
  1. Every colour and size is READ FROM `tok` — a role where a role exists, otherwise
     an ink. A hand-typed hex is drift the gate cannot see; the hex-leak test fails
     the suite on one. Structural geometry (box widths, arc heights) is not a token.
  2. Deterministic output. Iterate lists in file order; never a set; fixed-precision
     floats.

Also: a fragment lands inside <body>, so no <style> blocks (page CSS is the site's);
arrowheads are explicit <polygon>s, never SVG <marker>s (a marker needs an id, and
ids on a page belong to the TOC)."""
from __future__ import annotations
import html as _html


def need(block, key, where):
    if key not in block:
        raise ValueError(f"{where}: tokens.yaml is missing {key!r}")
    return block[key]


def role(tok, name):
    if name not in tok.roles:
        raise ValueError(f"role {name!r} is missing from tokens.yaml but a renderer draws with it")
    return tok.roles[name].hex


def ink(tok, name):
    if name not in tok.inks:
        raise ValueError(f"ink {name!r} is missing from tokens.yaml but a renderer draws with it")
    return tok.inks[name]


def rgba(hex_value, alpha):
    r, g, b = (int(hex_value[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def space(tok):
    steps = tok.section("spacing")
    if not steps:
        raise ValueError("tokens.yaml has no `spacing` steps")
    return list(steps)


def micro(tok):
    return need(need(tok.section("type"), "micro", "type"), "size", "type.micro")


def chrome(tok):
    """The palette a diagram draws with, resolved once through roles."""
    return {
        "paper": role(tok, "surface.card"),
        "band": role(tok, "surface.band"),
        "ink": role(tok, "text.primary"),
        "text": role(tok, "text.primary"),
        "quiet": role(tok, "text.secondary"),
        "line": role(tok, "contour.line"),
        "rule": role(tok, "ornament.rule"),
        "yes": role(tok, "action.commit"),
        "no": role(tok, "action.danger"),
        "locked": role(tok, "state.locked"),
        "deep": role(tok, "ground.deep"),
        "reversed": role(tok, "text.reversed"),
    }


def esc(text):
    return _html.escape(str(text), quote=True)


def text(x, y, label, fill, size=12, anchor="start", weight="normal", family=None):
    fam = f" font-family=\"{esc(family)}\"" if family else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}"'
            f' text-anchor="{anchor}" font-weight="{weight}"{fam}>{esc(label)}</text>')


def rect(x, y, w, h, fill, stroke=None, r=0, sw=1):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}"{s}/>'


def line(x1, y1, x2, y2, stroke, sw=1.5, dashed=False):
    d = ' stroke-dasharray="4 3"' if dashed else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def arrowhead(x1, y1, x2, y2, fill, size=7):
    """A triangle at (x2,y2) pointing along (x1,y1)->(x2,y2)."""
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    left = (x2 - size * math.cos(ang - 0.5), y2 - size * math.sin(ang - 0.5))
    right = (x2 - size * math.cos(ang + 0.5), y2 - size * math.sin(ang + 0.5))
    pts = f"{x2:.1f},{y2:.1f} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}"
    return f'<polygon points="{pts}" fill="{fill}"/>'


def arrow(x1, y1, x2, y2, stroke, sw=1.5, dashed=False):
    return line(x1, y1, x2, y2, stroke, sw, dashed) + arrowhead(x1, y1, x2, y2, stroke)


def frame(width, height, body, tok, title=None):
    """A complete <svg> with the paper ground and an accessible title."""
    t = f"<title>{esc(title)}</title>" if title else ""
    return (f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">'
            f'{t}<rect x="0" y="0" width="{width}" height="{height}" fill="{role(tok, "surface.card")}"/>'
            f"{body}</svg>")


def note(tok, html_text):
    """A caption paragraph in the site's quiet style; html_text is already-escaped HTML."""
    return f'<p class="gen-note">{html_text}</p>'


def table(headers, rows):
    """A plain HTML table; every cell is escaped here."""
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def wrap(label, width_chars):
    """Greedy word wrap -> list of lines, deterministic."""
    words, lines, cur = str(label).split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width_chars:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines
