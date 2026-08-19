"""The Example domain: one renderer per generic diagram idiom, drawn from placeholder
data with engine.svg. It exists to be copied -- take the idiom you need into your own
pack, then delete this module, prose/2-example and tests/test_example_pack.py.

Slugs are frozen and prefixed `ex-`; prose places each exactly once.
"""
from __future__ import annotations

import math

from engine import config, markdown, svg

# ==========================================================================
# placeholder data -- neutral labels only, never a project noun
# ==========================================================================

PIPELINE_STAGES = ("Stage A", "Stage B", "Stage C", "Stage D", "Stage E")

CHAIN_STAGES = ("Input 1", "Input 2", "Input 3", "Input 4")
CHAIN_BAY = "Read-back bay"

CYCLE_STATES = ("State 1", "State 2", "State 3", "State 4")

FAN_HUB = "Hub"
FAN_SPOKES = ("Spoke 1", "Spoke 2", "Spoke 3", "Spoke 4", "Spoke 5", "Spoke 6")

BOUNDARY_LEFT = ("Item A1", "Item A2", "Item A3")
BOUNDARY_RIGHT = ("Item B1", "Item B2", "Item B3")

CONVERGE_INPUTS = ("Input 1", "Input 2", "Input 3")
CONVERGE_OUTCOME = "Outcome"

MATRIX_ROWS = ("Row 1", "Row 2", "Row 3", "Row 4")
MATRIX_COLS = ("Column 1", "Column 2", "Column 3")
MATRIX_VERDICTS = ("yes", "no", "quiet")

MULTIPLES_PANELS = ("Panel 1", "Panel 2", "Panel 3", "Panel 4")
MULTIPLES_PASS = (True, False, True, False)

BEFORE_AFTER_SCENE = "Scene"
BEFORE_AFTER_ELEMENT = "Condition X"

LADDER_STEPS = ("Step 1", "Step 2", "Step 3", "Step 4", "Step 5")

PINS_SCENE = "Scene"
PINS = (
    (1, 90, 90, "Marker 1: Input 1"),
    (2, 260, 150, "Marker 2: Input 2"),
    (3, 400, 70, "Marker 3: Input 3"),
    (4, 330, 210, "Marker 4: Outcome"),
)

RULE_BOX_RULES = (
    ("RULE 1", "Condition X", "Stage A"),
    ("RULE 2", "Condition Y", "Stage B"),
    ("RULE 3", "Condition Z", "Stage C"),
    ("RULE 4", "Condition W", "Stage D"),
)

TABLE_CONDITIONS = ("Condition X", "Condition Y", "Condition Z")
TABLE_OUTCOMES = ("Outcome 1", "Outcome 2")

IMAGERY_CAPTION = "A committed placeholder image"


# ==========================================================================
# shared drawing helpers -- built ONLY from engine.svg primitives
# ==========================================================================

def _label(cx, cy, label, fill, size, width_chars=14):
    """Centred, possibly-wrapped text -- built from svg.wrap + svg.text."""
    lines = svg.wrap(label, width_chars)
    n = len(lines)
    line_h = size + 3
    start_y = cy - (n - 1) * line_h / 2 + size / 3
    return "".join(
        svg.text(cx, start_y + i * line_h, line, fill, size=size, anchor="middle")
        for i, line in enumerate(lines)
    )


def _box(x, y, w, h, label, fill, stroke, text_fill, size):
    return (svg.rect(x, y, w, h, fill, stroke=stroke, r=6)
            + _label(x + w / 2, y + h / 2, label, text_fill, size))


def _shrink(x1, y1, x2, y2, pad1, pad2=None):
    """Move both endpoints of a segment inward by pad1 (start) / pad2 (end),
    so an arrow between two box centres stops at their edges instead of
    overlapping the boxes."""
    pad2 = pad1 if pad2 is None else pad2
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy) or 1.0
    ux, uy = dx / dist, dy / dist
    return x1 + ux * pad1, y1 + uy * pad1, x2 - ux * pad2, y2 - uy * pad2


def _arc(x1, y1, cx, cy, x2, y2, stroke, dashed=True):
    """A quadratic-bezier edge with an explicit arrowhead -- svg.py has no
    curve helper, so the path element is raw SVG (the same idiom the
    binding-map diagram in the design-system pack uses); the arrowhead comes
    from svg.arrowhead, oriented along the curve's own tangent at the end."""
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    path = (f'<path d="M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}" '
            f'fill="none" stroke="{stroke}" stroke-width="1.5"{dash}/>')
    return path + svg.arrowhead(cx, cy, x2, y2, stroke)


def _pin(cx, cy, r, number, fill, text_fill, size):
    """A numbered marker -- svg.py has no circle helper, so the circle is raw
    SVG; the number is svg.text."""
    circle = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"/>'
    return circle + svg.text(cx, cy + size / 3, str(number), text_fill,
                              size=size, anchor="middle", weight="bold")


# ==========================================================================
# flow
# ==========================================================================

def render_pipeline(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    box_w, box_h, gap, margin = 120, 56, 36, 30
    n = len(PIPELINE_STAGES)
    width = margin * 2 + n * box_w + (n - 1) * (gap)
    y = 50
    height = 220
    xs = [margin + i * (box_w + gap) for i in range(n)]

    body = []
    for i, (x, label) in enumerate(zip(xs, PIPELINE_STAGES)):
        body.append(_box(x, y, box_w, box_h, label, c["band"], c["line"], c["text"], size))
        if i > 0:
            x1, y1, x2, y2 = xs[i - 1] + box_w, y + box_h / 2, x, y + box_h / 2
            body.append(svg.arrow(x1, y1, x2, y2, c["line"]))

    x1, y1 = xs[-1] + box_w / 2, y + box_h
    x2, y2 = xs[0] + box_w / 2, y + box_h
    body.append(_arc(x1, y1, (x1 + x2) / 2, height - 24, x2, y2, c["quiet"]))

    frag = svg.frame(width, height, "".join(body), tok, title="Pipeline with feedback")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect, svg.arrow and svg.wrap; the return "
             "edge is a quadratic path closed by svg.arrowhead.")


def render_stage_chain(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    box_w, box_h, gap, margin = 120, 56, 40, 30
    n = len(CHAIN_STAGES)
    width = margin * 2 + n * box_w + (n - 1) * gap
    y = 40
    bay_w, bay_h = 200, 50
    bay_y = y + box_h + 70
    height = bay_y + bay_h + 30
    xs = [margin + i * (box_w + gap) for i in range(n)]
    bay_x = (xs[1] + box_w + xs[2]) / 2 - bay_w / 2

    body = []
    for i, (x, label) in enumerate(zip(xs, CHAIN_STAGES)):
        body.append(_box(x, y, box_w, box_h, label, c["band"], c["line"], c["text"], size))
        if i > 0:
            body.append(svg.arrow(xs[i - 1] + box_w, y + box_h / 2, x, y + box_h / 2, c["line"]))
    body.append(_box(bay_x, bay_y, bay_w, bay_h, CHAIN_BAY, c["paper"], c["quiet"], c["text"], size))

    down_x = bay_x + bay_w * 0.3
    up_x = bay_x + bay_w * 0.7
    body.append(svg.arrow(down_x, y + box_h, down_x, bay_y, c["quiet"], dashed=True))
    body.append(svg.arrow(up_x, bay_y, up_x, y + box_h, c["quiet"], dashed=True))

    frag = svg.frame(width, height, "".join(body), tok, title="Stage chain with a bay")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect and svg.arrow -- the bay's two "
             "dashed arrows are svg.arrow with dashed=True.")


def render_state_cycle(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    width, height = 440, 340
    cx, cy, radius = 220, 170, 110
    box_w, box_h = 110, 50
    n = len(CYCLE_STATES)
    pts = []
    for i in range(n):
        angle = math.radians(-90 + i * (360 / n))
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

    body = []
    for i in range(n):
        j = (i + 1) % n
        x1, y1, x2, y2 = _shrink(pts[i][0], pts[i][1], pts[j][0], pts[j][1], box_w / 2)
        body.append(svg.arrow(x1, y1, x2, y2, c["line"]))
    for i, j in ((0, 2), (1, 3)):
        mx, my = (pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2
        dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
        dist = math.hypot(dx, dy) or 1.0
        perp = (-dy / dist * 46, dx / dist * 46)
        x1, y1, x2, y2 = _shrink(pts[i][0], pts[i][1], pts[j][0], pts[j][1], box_w / 2)
        body.append(_arc(x1, y1, mx + perp[0], my + perp[1], x2, y2, c["quiet"]))
    for (px, py), label in zip(pts, CYCLE_STATES):
        body.append(_box(px - box_w / 2, py - box_h / 2, box_w, box_h, label,
                          c["band"], c["line"], c["text"], size))

    frag = svg.frame(width, height, "".join(body), tok, title="State cycle")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect and svg.arrow for neighbour "
             "transitions; the two skip transitions are arced paths closed "
             "by svg.arrowhead.")


# ==========================================================================
# structure
# ==========================================================================

def render_fan(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    width, height = 480, 380
    cx, cy, radius = 240, 190, 140
    hub_w, hub_h = 90, 50
    leaf_w, leaf_h = 104, 46
    n = len(FAN_SPOKES)
    pts = []
    for i in range(n):
        angle = math.radians(-90 + i * (360 / n))
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

    body = []
    for px, py in pts:
        x1, y1, x2, y2 = _shrink(cx, cy, px, py, hub_w / 2, leaf_h / 2)
        body.append(svg.line(x1, y1, x2, y2, c["line"]))
    body.append(_box(cx - hub_w / 2, cy - hub_h / 2, hub_w, hub_h, FAN_HUB,
                      c["yes"], c["line"], c["reversed"], size))
    for (px, py), label in zip(pts, FAN_SPOKES):
        body.append(_box(px - leaf_w / 2, py - leaf_h / 2, leaf_w, leaf_h, label,
                          c["band"], c["line"], c["text"], size))

    frag = svg.frame(width, height, "".join(body), tok, title="Hub and spoke")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect and svg.line -- every spoke is a "
             "plain line, not an arrow.")


def render_decision_boundary(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    item_w, item_h = 150, 44
    left_x, right_x = 50, 380
    gap_y = 66
    top = 40
    width = right_x + item_w + 50
    height = top + len(BOUNDARY_LEFT) * gap_y + 40
    mid_x = (left_x + item_w + right_x) / 2

    body = [svg.line(mid_x, 16, mid_x, height - 16, c["quiet"], dashed=True)]
    left_pts, right_pts = [], []
    for i, label in enumerate(BOUNDARY_LEFT):
        y = top + i * gap_y
        body.append(_box(left_x, y, item_w, item_h, label, c["band"], c["line"], c["text"], size))
        left_pts.append((left_x + item_w, y + item_h / 2))
    for i, label in enumerate(BOUNDARY_RIGHT):
        y = top + i * gap_y
        body.append(_box(right_x, y, item_w, item_h, label, c["band"], c["line"], c["text"], size))
        right_pts.append((right_x, y + item_h / 2))

    x1, y1, x2, y2 = _shrink(left_pts[0][0], left_pts[0][1], right_pts[2][0], right_pts[2][1], 6)
    body.append(svg.arrow(x1, y1, x2, y2, c["yes"]))
    x1, y1, x2, y2 = _shrink(right_pts[0][0], right_pts[0][1], left_pts[2][0], left_pts[2][1], 6)
    body.append(svg.arrow(x1, y1, x2, y2, c["no"]))

    frag = svg.frame(width, height, "".join(body), tok, title="Decision boundary")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect, svg.line (dashed) and svg.arrow "
             "for the two crossing edges.")


def render_converge(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    box_w, box_h = 150, 50
    left_x = 40
    gap_y = 70
    top = 30
    right_x = 340
    width = right_x + box_w + 40
    height = top + len(CONVERGE_INPUTS) * gap_y + 30
    right_y = top + (len(CONVERGE_INPUTS) - 1) * gap_y / 2

    body = []
    for i, label in enumerate(CONVERGE_INPUTS):
        y = top + i * gap_y
        body.append(_box(left_x, y, box_w, box_h, label, c["band"], c["line"], c["text"], size))
        x1, y1, x2, y2 = _shrink(left_x + box_w, y + box_h / 2, right_x, right_y + box_h / 2, 0, box_w / 2)
        body.append(svg.arrow(x1, y1, x2, y2, c["line"]))
    body.append(_box(right_x, right_y, box_w, box_h, CONVERGE_OUTCOME,
                      c["yes"], c["line"], c["reversed"], size))

    frag = svg.frame(width, height, "".join(body), tok, title="Converging axes")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect and svg.arrow -- three inputs, "
             "one shared target point.")


# ==========================================================================
# comparison
# ==========================================================================

def render_matrix(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    cell_w, cell_h = 116, 44
    origin_x, origin_y = 150, 60
    width = origin_x + len(MATRIX_COLS) * cell_w + 30
    height = origin_y + len(MATRIX_ROWS) * cell_h + 80
    fills = {"yes": c["yes"], "no": c["no"], "quiet": c["quiet"]}

    body = []
    for j, col in enumerate(MATRIX_COLS):
        body.append(svg.text(origin_x + j * cell_w + cell_w / 2, origin_y - 14, col,
                              c["quiet"], size=size, anchor="middle"))
    for i, row in enumerate(MATRIX_ROWS):
        body.append(svg.text(origin_x - 12, origin_y + i * cell_h + cell_h / 2 + size / 3,
                              row, c["quiet"], size=size, anchor="end"))
        for j, _col in enumerate(MATRIX_COLS):
            verdict = MATRIX_VERDICTS[(i + j) % len(MATRIX_VERDICTS)]
            x, y = origin_x + j * cell_w, origin_y + i * cell_h
            body.append(_box(x, y, cell_w - 4, cell_h - 4, verdict, fills[verdict],
                              c["paper"], c["reversed"], size))

    legend_y = origin_y + len(MATRIX_ROWS) * cell_h + 30
    lx = origin_x
    for verdict in MATRIX_VERDICTS:
        body.append(svg.rect(lx, legend_y, 16, 16, fills[verdict]))
        body.append(svg.text(lx + 22, legend_y + 13, verdict, c["text"], size=size))
        lx += 90

    frag = svg.frame(width, height, "".join(body), tok, title="Verdict matrix")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect and svg.text -- cell fill is "
             "svg.chrome's yes/no/quiet roles, cycled by row plus column.")


def render_small_multiples(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    panel_w, panel_h, gap, margin = 170, 130, 30, 30
    cols = 2
    width = margin * 2 + cols * panel_w + (cols - 1) * gap
    rows = math.ceil(len(MULTIPLES_PANELS) / cols)
    height = margin * 2 + rows * panel_h + (rows - 1) * gap + 20

    body = []
    for i, (label, passed) in enumerate(zip(MULTIPLES_PANELS, MULTIPLES_PASS)):
        col, row = i % cols, i // cols
        x = margin + col * (panel_w + gap)
        y = margin + row * (panel_h + gap)
        body.append(svg.rect(x, y, panel_w, panel_h, c["paper"], stroke=c["line"], r=6))
        body.append(svg.text(x + panel_w / 2, y + 20, label, c["text"], size=size, anchor="middle"))
        gx, gy = x + panel_w / 2, y + panel_h / 2 + 12
        if passed:
            body.append(svg.line(gx - 22, gy, gx - 4, gy + 18, c["yes"], sw=4))
            body.append(svg.line(gx - 4, gy + 18, gx + 26, gy - 22, c["yes"], sw=4))
        else:
            body.append(svg.line(gx - 20, gy - 20, gx + 20, gy + 20, c["no"], sw=4))
            body.append(svg.line(gx - 20, gy + 20, gx + 20, gy - 20, c["no"], sw=4))

    frag = svg.frame(width, height, "".join(body), tok, title="Small multiples")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect, svg.text and svg.line -- the "
             "check and cross glyphs are both built from two svg.line calls.")


def render_before_after(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    panel_w, panel_h, gap, margin = 240, 180, 40, 30
    width = margin * 2 + 2 * panel_w + gap
    height = margin * 2 + panel_h + 20

    def panel(x, changed):
        out = [svg.rect(x, margin, panel_w, panel_h, c["paper"], stroke=c["line"], r=6),
               svg.text(x + panel_w / 2, margin + 22, BEFORE_AFTER_SCENE, c["quiet"],
                         size=size, anchor="middle")]
        elem_w, elem_h = 120, 60
        ex, ey = x + (panel_w - elem_w) / 2, margin + (panel_h - elem_h) / 2 + 10
        fill = c["yes"] if changed else c["band"]
        stroke = c["paper"] if changed else c["line"]
        out.append(_box(ex, ey, elem_w, elem_h, BEFORE_AFTER_ELEMENT, fill, stroke,
                         c["reversed"] if changed else c["text"], size))
        return "".join(out)

    body = panel(margin, False) + panel(margin + panel_w + gap, True)
    body += svg.text(margin + panel_w / 2, height - 8, "before", c["quiet"], size=size, anchor="middle")
    body += svg.text(margin + panel_w + gap + panel_w / 2, height - 8, "after", c["quiet"],
                      size=size, anchor="middle")

    frag = svg.frame(width, height, body, tok, title="Before and after")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect and svg.text -- the same element "
             "restyled from a plain fill to the yes role.")


def render_ladder(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    rung_w, rung_h = 110, 50
    step_x, step_y, margin = 108, 34, 30
    n = len(LADDER_STEPS)
    width = margin * 2 + (n - 1) * step_x + rung_w
    height = margin + (n - 1) * step_y + rung_h + 30

    body = []
    xs, ys = [], []
    for i in range(n):
        x = margin + i * step_x
        y = height - 30 - rung_h - i * step_y
        xs.append(x)
        ys.append(y)
    for i, label in enumerate(LADDER_STEPS):
        body.append(_box(xs[i], ys[i], rung_w, rung_h, label, c["band"], c["line"], c["text"], size))
        if i > 0:
            x1, y1, x2, y2 = _shrink(xs[i - 1] + rung_w / 2, ys[i - 1], xs[i] + rung_w / 2, ys[i] + rung_h,
                                      rung_h / 2)
            body.append(svg.arrow(x1, y1, x2, y2, c["line"]))
    body.append(svg.line(margin - 10, height - 20, xs[-1] + rung_w + 10, height - 20, c["quiet"], dashed=True))

    frag = svg.frame(width, height, "".join(body), tok, title="Ladder")
    return frag + svg.note(
        tok, "Drawn with svg.frame, svg.rect, svg.arrow and a dashed svg.line "
             "baseline.")


# ==========================================================================
# annotation
# ==========================================================================

def render_pins(tok):
    c = svg.chrome(tok)
    size = svg.micro(tok)
    width, height = 500, 260
    pin_r = 15

    body = [svg.rect(0, 0, width, height, c["band"]),
            svg.text(14, 22, PINS_SCENE, c["quiet"], size=size)]
    for number, x, y, _label in PINS:
        body.append(_pin(x, y, pin_r, number, c["no"], c["reversed"], size))

    frag = svg.frame(width, height, "".join(body), tok, title="Numbered pins")
    legend = svg.table(["pin", "label"], [[str(n), lbl] for n, _x, _y, lbl in PINS])
    return frag + legend + svg.note(
        tok, "The scene is svg.frame and svg.rect, each pin a numbered marker "
             "with svg.text; the legend is svg.table.")


def render_rule_box(tok):
    svg.chrome(tok)  # no colour is drawn, but every renderer still proves role coverage
    width = max(len(f"{num}  IF {cond}") for num, cond, _out in RULE_BOX_RULES) + \
        max(len(f"    THEN {out}") for _num, _cond, out in RULE_BOX_RULES)
    width = max(width, 30) + 2
    rule = "+" + "-" * width + "+"
    lines = [rule]
    for num, cond, outcome in RULE_BOX_RULES:
        lines.append(f"| {num}  IF {cond}".ljust(width + 1) + "|")
        lines.append(f"|      THEN {outcome}".ljust(width + 1) + "|")
        lines.append(rule)
    ascii_box = "\n".join(lines)
    return (f"<pre><code>{svg.esc(ascii_box)}</code></pre>"
            + svg.note(tok, "An ASCII box built from plain string formatting -- no "
                            "svg helper draws a rule that is read top to bottom, "
                            "not sighted."))


def render_decision_table(tok):
    svg.chrome(tok)  # no colour is drawn, but every renderer still proves role coverage
    headers = ["condition", *TABLE_OUTCOMES]
    rows = []
    for i, condition in enumerate(TABLE_CONDITIONS):
        row = [condition]
        for j, _outcome in enumerate(TABLE_OUTCOMES):
            row.append("yes" if (i + j) % 2 == 0 else "no")
        rows.append(row)
    return svg.table(headers, rows) + svg.note(tok, "Drawn with svg.table alone.")


# ==========================================================================
# imagery
# ==========================================================================

def render_imagery(tok):
    prefix = markdown.image_prefix(config.current().images_dir)
    figure = (f'<figure><img src="{prefix}/placeholder.png" alt="{svg.esc(IMAGERY_CAPTION)}">'
              f'<figcaption>{svg.esc(IMAGERY_CAPTION)}</figcaption></figure>')
    return (f'<div class="spec-grid">{figure}</div>'
            + svg.note(tok, "A committed file cited by bare filename, wrapped in "
                            "a plain spec-grid div -- no svg helper draws a "
                            "photograph."))


# ==========================================================================
# registration
# ==========================================================================

SECTIONS = [
    ("ex-pipeline", "Pipeline with feedback",
     "Five stages in a row, one return edge", render_pipeline),
    ("ex-stage-chain", "Stage chain with a bay",
     "A chain, plus a side bay for read-backs", render_stage_chain),
    ("ex-state-cycle", "State cycle",
     "Four states, straight and arced transitions", render_state_cycle),
    ("ex-fan", "Hub and spoke",
     "One hub, six spokes, fanning outward", render_fan),
    ("ex-decision-boundary", "Decision boundary",
     "Two columns, a dashed midline, crossing arrows", render_decision_boundary),
    ("ex-converge", "Converging axes",
     "Three inputs converge on one outcome", render_converge),
    ("ex-matrix", "Verdict matrix",
     "Rows by columns, each cell a verdict", render_matrix),
    ("ex-small-multiples", "Small multiples",
     "Four panels, same frame, pass or fail", render_small_multiples),
    ("ex-before-after", "Before and after",
     "The same scene twice, one change", render_before_after),
    ("ex-ladder", "Ladder",
     "Five rungs, climbing left to right", render_ladder),
    ("ex-pins", "Numbered pins",
     "Pins on a scene, legend beside", render_pins),
    ("ex-rule-box", "Rule box",
     "Ordered logic in a fenced ASCII box", render_rule_box),
    ("ex-decision-table", "Decision table",
     "Conditions down, outcomes across, one table", render_decision_table),
    ("ex-imagery", "Figure grid",
     "Committed images in a spec grid", render_imagery),
]
