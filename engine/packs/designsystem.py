"""Generated token sections for the design-system pack.

Each renderer takes the shared Tokens model and returns an HTML fragment.
Ordering/registration lives in SECTIONS at the bottom; slugs are FROZEN
(prose cites them by `{{section:<slug>}}`).

TWO RULES BIND EVERY RENDERER HERE:

  1. Every colour, size, duration and count is READ FROM `tok`, through the
     shared `engine.svg` helpers. A hand-typed hex or px is drift the gate
     cannot see -- test_designsystem_no_hand_typed_hex in test_packs.py fails
     the suite on any hex the token model does not know. Structural layout
     numbers that are NOT tokens (SVG row heights, viewBox math, gallery
     column widths) are fine and expected.
  2. Deterministic output. Token-driven content follows tokens.yaml order
     (dicts are insertion-ordered).

Page CSS belongs to the site shell -- this module cannot emit <style> tags
(a fragment lands inside <body>). Where a class hook does not exist, use
inline style="..." with values read from `tok`.
"""
from __future__ import annotations

import html as h

from .. import svg

SAMPLE = "Aa The quick brown fox 0123"

# The @keyframes these name live in the site's shared page CSS, which this
# module may not redefine (no <style> block in a fragment).
MOTION_KEYFRAMES = {"quick": "ds-slide", "standard": "ds-slide", "enter": "ds-fade"}
MOTION_FALLBACK = "ds-fade"


# ==========================================================================
# helpers
# ==========================================================================

def _on(tok, hex_value):
    """Readable type over an arbitrary palette member: paper or ink, chosen by
    luma so a stop label never disappears into its own swatch."""
    r, g, b = (int(hex_value[i:i + 2], 16) for i in (1, 3, 5))
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return svg.role(tok, "text.primary") if luma > 140 else svg.role(tok, "text.reversed")


def _fmt(value):
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _hairline(tok):
    orn = tok.section("ornament")
    thickness = svg.need(orn, "hairline.thickness", "ornament")
    alpha = round(svg.need(orn, "hairline.alpha", "ornament") / 100, 2)
    return f"{thickness}px solid {svg.rgba(svg.role(tok, 'text.primary'), alpha)}"


def _meta(tok, text):
    """A caption line. `.meta` in the page CSS is scoped to `.specimen`, so
    captions elsewhere carry the same two tokens inline."""
    return (f'<div style="font-size:{svg.micro(tok)}px;color:{svg.role(tok, "text.secondary")}">'
            f"{h.escape(text)}</div>")


def _swatch_cell(name, hexval, note=""):
    return (
        f'<div class="swatch"><span class="chip" style="background:{hexval}"></span>'
        f"<b>{h.escape(name)}</b><code>{hexval}</code>"
        f"<span class=note>{h.escape(note)}</span></div>"
    )


def _spec_chip(label, value):
    return (f'<div class="spec"><b>{h.escape(label)}</b>'
            f"<code>{h.escape(_fmt(value))}</code></div>")


def _table(headers, rows):
    out = ["<table><thead><tr>"]
    out += [f"<th>{cell}</th>" for cell in headers]
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _svg_text(x, y, text, fill, size, family, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}"'
            f' font-family="{family}" text-anchor="{anchor}">'
            f"{h.escape(text)}</text>")


# ==========================================================================
# palette
# ==========================================================================

def render_inks(tok):
    # role hints: which roles bind each ink (derived, not hand-typed)
    bound = {}
    for r in tok.roles.values():
        bound.setdefault(r.source, []).append(r.name)
    cells = [
        _swatch_cell(name, value, ", ".join(bound.get(name, [])))
        for name, value in tok.inks.items()
    ]
    return '<div class="swatch-grid">' + "".join(cells) + "</div>"


def render_ramps(tok):
    """Hard steps, no blending: one flex row per ramp, 0-based indices labelled."""
    parts = []
    for name, stops in tok.ramps.items():
        cells = []
        for i, value in enumerate(stops):
            cells.append(
                f'<div class="ramp-stop" style="background:{value};'
                f'color:{_on(tok, value)}">{i}<br>{value}</div>')
        anchored = ""
        if name in tok.inks:
            # Asserted by the generator: an ink-named ramp contains its ink verbatim.
            anchored = (f' — contains <code>ink.{h.escape(name)}</code> '
                        f"{tok.inks[name]} verbatim")
        parts.append(f"<h4>{h.escape(name)}</h4>"
                     f'<div class="ramp-row">{"".join(cells)}</div>'
                     f'<p class="gen-note">{len(stops)} stops{anchored}</p>')
    counts = ", ".join(f"{name} {len(stops)}" for name, stops in tok.ramps.items())
    return ('<p class="gen-note">Stop counts are not uniform: '
            f"{h.escape(counts)}.</p>" + "".join(parts))


def render_roles(tok):
    """Surfaces reference roles, never inks — so this table is the contract."""
    rows = []
    for r in tok.roles.values():
        rows.append([
            f"<code>{h.escape(r.name)}</code>",
            f"<code>{h.escape(r.source)}</code>",
            f'<span class="tk"><span class="sw" style="background:{r.hex}">'
            f"</span><code>{r.hex}</code></span>",
            h.escape(r.scope),
            "◆ indicator" if r.indicator else "",
        ])
    return (f'<p class="gen-note">{len(tok.roles)} roles, in tokens.yaml order. '
            "A role names one ink or one ramp stop; there is no arithmetic.</p>"
            + _table(["role", "source", "resolved", "scope", "flag"], rows))


def render_binding_map(tok):
    """The role table as a diagram, from the SAME parsed roles so the two cannot
    disagree. Layout is pure arithmetic on the role/source counts."""
    ink = tok.inks
    type_block = tok.section("type")
    orn = tok.section("ornament")
    family = svg.need(type_block, "face.body", "type")
    size = svg.micro(tok)
    stroke_w = svg.need(orn, "hairline.thickness", "ornament")
    hairline = svg.rgba(svg.role(tok, 'text.primary'),
                        round(svg.need(orn, "hairline.alpha", "ornament") / 100, 2))
    label_ink = svg.role(tok, "action.danger")

    # Structural (not tokens): the diagram's own geometry.
    width, row_h, pad_top, pad_bottom = 700, 22, 30, 12
    role_text_x, chip_x, chip_w = 232, 238, 10
    edge_x1, edge_x2, src_x = 252, 424, 430

    roles = list(tok.roles.values())
    # A source resolves to exactly one colour, so first-seen order is stable and
    # the chip colour is unambiguous.
    sources = {}
    for r in roles:
        sources.setdefault(r.source, r.hex)
    inner = max(len(roles), len(sources)) * row_h
    height = pad_top + inner + pad_bottom

    def y_of(index, count):
        return pad_top + (index + 0.5) * inner / count

    src_y = {name: y_of(i, len(sources)) for i, name in enumerate(sources)}
    out = [f'<svg viewBox="0 0 {width} {height}" width="{width}" '
           f'role="img" aria-label="role to ink binding map">']
    out.append(_svg_text(role_text_x, pad_top - 12, "role", label_ink,
                         size, family, anchor="end"))
    out.append(_svg_text(src_x, pad_top - 12, "ink / ramp stop", label_ink,
                         size, family))
    for i, r in enumerate(roles):
        y1 = y_of(i, len(roles))
        y2 = src_y[r.source]
        mid = (edge_x1 + edge_x2) / 2
        curve = (f'M {edge_x1} {y1:.1f} C {mid} {y1:.1f}, {mid} {y2:.1f},'
                 f" {edge_x2} {y2:.1f}")
        # Backing stroke: roles resolving to paper or band would otherwise be an
        # invisible edge on this ground, and an edge you cannot follow is not a
        # diagram. The backing is the same hairline the page rules with.
        out.append(f'<path d="{curve}" fill="none" stroke="{hairline}"'
                   f' stroke-width="{stroke_w * 3}"/>')
        out.append(f'<path d="{curve}" fill="none" stroke="{r.hex}"'
                   f' stroke-width="{stroke_w}"/>')
        out.append(_svg_text(role_text_x, y1 + 4, r.name, ink["ink"], size,
                             family, anchor="end"))
        out.append(f'<rect x="{chip_x}" y="{y1 - 5:.1f}" width="{chip_w}" '
                   f'height="{chip_w}" fill="{r.hex}" stroke="{hairline}" '
                   f'stroke-width="{stroke_w}"/>')
    for name, y in src_y.items():
        out.append(f'<rect x="{src_x - chip_w - 4}" y="{y - 5:.1f}" '
                   f'width="{chip_w}" height="{chip_w}" '
                   f'fill="{sources[name]}" stroke="{hairline}" '
                   f'stroke-width="{stroke_w}"/>')
        out.append(_svg_text(src_x, y + 4, name, ink["ink"], size, family))
    out.append("</svg>")
    return ('<p class="gen-note">Each edge is stroked in the colour the role '
            "resolves to — this diagram and the table above are drawn from the "
            "same parsed roles, so they cannot disagree.</p>" + "".join(out))


# ==========================================================================
# state, type, space
# ==========================================================================

def render_states(tok):
    """Only what the tokens define: `state` values, plus `locked` which resolves
    through a role. Rationale is prose."""
    state = tok.section("state")
    if not state:
        raise ValueError("tokens.yaml has no `state` block")
    s = svg.space(tok)
    shape = tok.section("shape")
    chip_r = svg.need(shape, "corner.chip", "shape")
    translate = svg.need(state, "pressed.translate", "state")
    darken = svg.need(state, "pressed.darken", "state")
    offset = svg.need(state, "selected.offset", "state")

    base = (f"border-radius:{chip_r}px;padding:{s[1]}px {s[3]}px")
    demos = [
        ("enabled", f"background:{svg.role(tok, 'action.commit')};"
                    f"color:{svg.role(tok, 'text.reversed')};{base}"),
        ("disabled", f"background:{svg.need(state, 'disabled.fill', 'state')};"
                     f"color:{svg.need(state, 'disabled.text', 'state')};{base}"),
        ("pressed", f"background:{svg.role(tok, 'action.commit')};"
                    f"color:{svg.role(tok, 'text.reversed')};{base};"
                    f"transform:translate({translate}px,{translate}px);"
                    f"filter:brightness({1 + darken / 100:.2f})"),
        ("selected", f"background:{svg.role(tok, 'action.commit')};"
                     f"color:{svg.role(tok, 'text.reversed')};{base};"
                     f"box-shadow:{offset}px {offset}px 0 0 "
                     f"{svg.role(tok, 'text.primary')}"),
        ("locked", f"background:{svg.role(tok, 'state.locked')};"
                   f"color:{svg.role(tok, 'text.reversed')};{base}"),
    ]
    chips = "".join(f'<div class="chip-demo" style="{style}">{label}</div>'
                    for label, style in demos)

    swatches = "".join(_swatch_cell(key, value) for key, value in state.items()
                       if isinstance(value, str) and value.startswith("#"))
    chips_num = "".join(_spec_chip(key, value) for key, value in state.items()
                        if not (isinstance(value, str) and value.startswith("#")))
    hover = any(key.startswith("hover") for key in state)
    hover_note = ("" if hover else
                  " The block names no hover value — hover is not one of the "
                  "states here.")
    return (f'<p class="gen-note">`locked` resolves through the role '
            f"<code>state.locked</code> ({svg.role(tok, 'state.locked')}), which is "
            f"why it is distinct from `disabled` rather than a repaint of it."
            f"{hover_note}</p>"
            f'<div class="demo">{chips}</div>'
            f'<div class="swatch-grid">{swatches}</div>'
            f'<div class="spec-grid" style="margin-top:{s[2]}px">{chips_num}</div>')


def render_type(tok):
    """Each step set at its true size in its true face."""
    type_block = tok.section("type")
    parts = []
    for step, body in type_block.items():
        if not isinstance(body, dict):
            continue
        size = svg.need(body, "size", f"type.{step}")
        face = svg.need(body, "face", f"type.{step}")
        family = svg.need(type_block, f"face.{face}", "type")
        sample = SAMPLE.upper() if face == "display" else SAMPLE
        parts.append(
            f'<div class="specimen">'
            f'<div style="font-family:\'{family}\';font-size:{size}px">'
            f"{h.escape(sample)}</div>"
            f'<div class="meta">{h.escape(step)} — {size}px {h.escape(family)}'
            f"</div></div>")
    return ('<p class="gen-note">Reference pixels against a 1920×1080 canvas. '
            "Nothing ships below <code>micro</code>.</p>" + "".join(parts))


def render_spacing(tok):
    """Bars drawn at exactly their step width — the grid measured, not described."""
    steps = svg.space(tok)
    rows = []
    for n in steps:
        rows.append(
            f'<div style="display:flex;align-items:center;gap:{steps[1]}px;'
            f'margin-bottom:{steps[0]}px">'
            f'<code style="min-width:3ch;text-align:right">{n}</code>'
            f'<div class="bar" style="width:{n}px"></div></div>')
    return (f'<p class="gen-note">{len(steps)} steps. Every gap, pad and inset '
            "on this page picks one of them.</p>" + "".join(rows))


# ==========================================================================
# shape, ornament, motion
# ==========================================================================

def render_shape(tok):
    """Actual CSS/SVG shapes at true pixel values — a radius you can measure."""
    shape = tok.section("shape")
    orn = tok.section("ornament")
    s = svg.space(tok)
    box_w, box_h = s[6] + s[5], s[6]          # structural demo box, grid-sized
    ground = svg.role(tok, "surface.card")
    band = svg.role(tok, "surface.band")
    rule = svg.role(tok, "ornament.rule")

    corners = []
    for key in [k for k in shape if k.startswith("corner.")]:
        radius = shape[key]
        corners.append(
            f'<div><div style="width:{box_w}px;height:{box_h}px;'
            f"background:{ground};border:{_hairline(tok)};"
            f'border-radius:{radius}px"></div>'
            + _meta(tok, f"{key} {radius}px") + "</div>")

    overlaps = []
    for key in [k for k in shape if k.startswith("overlap.")]:
        offset = shape[key]
        overlaps.append(
            f'<div><div style="width:{box_w}px;height:{box_h}px;background:{band};'
            f'border:{_hairline(tok)}"></div>'
            f'<div style="width:{box_w}px;height:{box_h}px;background:{ground};'
            f'border:{_hairline(tok)};margin-top:{offset}px"></div>'
            + _meta(tok, f"{key} {offset}px") + "</div>")

    arm = svg.need(orn, "bracket.arm", "ornament")
    thick = svg.need(orn, "bracket.thickness", "ornament")
    span = arm + thick
    bracket = (f'<svg viewBox="0 0 {span} {span}" width="{span * 3}" '
               f'role="img" aria-label="corner bracket">'
               f'<path d="M {thick / 2} {span} L {thick / 2} {thick / 2} '
               f'L {span} {thick / 2}" fill="none" stroke="{rule}" '
               f'stroke-width="{thick}"/></svg>')
    hair_alpha = svg.need(orn, "hairline.alpha", "ornament")
    hair_th = svg.need(orn, "hairline.thickness", "ornament")
    rule_th = svg.need(orn, "rule.thickness", "ornament")
    ornaments = (
        f'<div style="flex:1 1 100%">'
        f'<div style="height:{rule_th}px;background:{rule}"></div>'
        + _meta(tok, f"rule.thickness {rule_th}px, inset "
                     f"{svg.need(orn, 'rule.inset', 'ornament')}px")
        + "</div>"
        f'<div style="flex:1 1 100%">'
        f'<div style="height:{hair_th}px;background:'
        f'{svg.rgba(svg.role(tok, "text.primary"), round(hair_alpha / 100, 2))}"></div>'
        + _meta(tok, f"hairline {hair_th}px at {hair_alpha}% alpha")
        + "</div>"
        f"<div>{bracket}"
        + _meta(tok, f"bracket.arm {arm}px, thickness {thick}px")
        + "</div>")

    budget = "".join(_spec_chip(key, orn[key])
                     for key in orn if key.startswith("budget."))
    return (f'<div class="demo">{"".join(corners)}</div>'
            f'<h4>overlap</h4><div class="demo">{"".join(overlaps)}</div>'
            f'<h4>ornament</h4><div class="demo">{ornaments}</div>'
            f'<div class="spec-grid">{budget}</div>')


def render_motion(tok):
    """Chips running at the true token durations. The @keyframes and the
    prefers-reduced-motion freeze both live in the site's shared page CSS:
    reduced motion gets static chips."""
    motion = tok.section("motion")
    if not motion:
        raise ValueError("tokens.yaml has no `motion` block")
    chips = []
    for name, ms in motion.items():
        keyframes = MOTION_KEYFRAMES.get(name, MOTION_FALLBACK)
        chips.append(
            f'<div class="chip-demo" style="animation:{keyframes} {ms}ms '
            f'ease-in-out infinite alternate">{h.escape(name)} {ms}ms</div>')
    return ('<p class="gen-note">Durations in milliseconds, running live. '
            "Under <code>prefers-reduced-motion: reduce</code> these chips hold "
            "still.</p>"
            f'<div class="demo">{"".join(chips)}</div>')


# ==========================================================================
# registration
# ==========================================================================

SECTIONS = [
    ("ds-inks", "Inks", "The closed palette, one swatch per ink", render_inks),
    ("ds-ramps", "Ramps", "Hand-picked stops, one strip per ramp", render_ramps),
    ("ds-roles", "Roles", "Every job a colour does, by name", render_roles),
    ("ds-binding-map", "Binding Map", "Which ink each role resolves to, drawn", render_binding_map),
    ("ds-states", "States", "Enabled, disabled, pressed, selected, locked, demonstrated", render_states),
    ("ds-type", "Type Scale", "Six steps, two faces, shown at size", render_type),
    ("ds-spacing", "Spacing", "The seven-step grid, drawn to scale", render_spacing),
    ("ds-shape", "Shape and Ornament", "Corners, overlaps, rules and brackets at size", render_shape),
    ("ds-motion", "Motion", "Three durations, running live at true speed", render_motion),
]
