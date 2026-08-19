#!/usr/bin/env python3
"""Ideas domain index: a generated section that groups an ideas parking-lot's
headings by status and links to them.

The prose under the single `prose/<nn>-ideas/` directory is a parking lot:
every idea is an H2 heading carrying a status tag, authored freehand. This
module does not own that prose -- it owns exactly one thing, the generated
index section that groups those headings by status, so the grouping can
never drift from the headings themselves (there is one parser, read here and
nowhere else).

AUTHORING FORMAT (also worth documenting on the domain's own `00-*.md`, which
is the page a reader actually opens): an idea is

    ## Idea Title
    *status: seed*
    *explore: an optional one-line note on what to try next*

    Free markdown body.

`*status: ...*` is the line IMMEDIATELY after the heading -- no blank line --
and must be exactly `seed`, `exploring`, or `promoted`; anything else fails
generation naming the file and the heading. `*explore: ...*` is optional and,
if present, follows the status line with no blank line either. Everything
after that, up to the next heading, is the idea's free-form body.

PROMOTION: an idea's content moves into a real domain directory and the card
here keeps a one-line link/pointer stub in its body. A `promoted` idea whose
body carries no such link renders a "stub missing" note on the index -- that
is surfaced information, not a generation failure, because the idea heading
itself is still a true record that promotion happened even if the stub line
has not been written yet.

The anchor scheme matches the site's own heading-id scheme exactly (file-
scoped: `h-<file-stem>-<slugified-heading-text>`), so an anchor built here and
the id the heading actually gets can never disagree.
"""
from __future__ import annotations

import collections
import fnmatch
import html as h
import re

from .. import config
from ..markdown import heading_id

STATUSES = ("seed", "exploring", "promoted")
STATUS_LABELS = {"seed": "Seed", "exploring": "Exploring", "promoted": "Promoted"}

_H2 = re.compile(r"^##\s+(.*)$")
_HEADING_ANY = re.compile(r"^#{1,4}\s")
_STATUS_LINE = re.compile(r"^\*status:\s*([A-Za-z]+)\*\s*$")
_EXPLORE_LINE = re.compile(r"^\*explore:\s*(.*)\*\s*$")
_LINK = re.compile(r"\[([^\]]+)\]\(([^()\s]+)\)")

_IDEAS_GLOB = "*-ideas"

Idea = collections.namedtuple(
    "Idea", "title status explore body anchor source")


# ==========================================================================
# locating the ideas directory
# ==========================================================================

def ideas_dir(cfg=None):
    """The single child of the prose tree matching `*-ideas` -- raises a
    clear error if none or more than one match, so a rename or a duplicate
    is caught at generation time rather than silently picking the wrong one.
    """
    cfg = cfg or config.current()
    prose_dir = cfg.prose_dir
    matches = sorted(p for p in prose_dir.iterdir()
                      if p.is_dir() and fnmatch.fnmatch(p.name, _IDEAS_GLOB))
    if not matches:
        raise ValueError(
            f"{prose_dir}: no directory matching {_IDEAS_GLOB!r} -- the ideas "
            f"pack needs exactly one parking-lot directory")
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        raise ValueError(
            f"{prose_dir}: multiple directories match {_IDEAS_GLOB!r} ({names}) "
            f"-- the ideas pack needs exactly one")
    return matches[0]


# ==========================================================================
# parsing
# ==========================================================================

def _parse_file(path):
    """One prose file -> [Idea], document order. Every H2 is an idea card;
    nothing else in the ideas domain's files is scanned for cards."""
    lines = path.read_text(encoding="utf-8").split("\n")
    n = len(lines)
    ideas, i = [], 0
    while i < n:
        m = _H2.match(lines[i])
        if not m:
            i += 1
            continue
        title = m.group(1).strip()
        heading_line = i
        i += 1
        if i >= n or not _STATUS_LINE.match(lines[i].strip()):
            found = lines[i].strip()[:48] if i < n else "(end of file)"
            raise ValueError(
                f"{path}: idea {title!r} (line {heading_line + 1}) must be "
                f"followed immediately by `*status: seed|exploring|promoted*` "
                f"-- found {found!r}")
        status = _STATUS_LINE.match(lines[i].strip()).group(1)
        if status not in STATUSES:
            raise ValueError(
                f"{path}: idea {title!r} has unknown status {status!r} -- must "
                f"be one of {', '.join(STATUSES)}")
        i += 1
        explore = None
        if i < n and _EXPLORE_LINE.match(lines[i].strip()):
            explore = _EXPLORE_LINE.match(lines[i].strip()).group(1).strip()
            i += 1
        body_start = i
        while i < n and not _HEADING_ANY.match(lines[i]):
            i += 1
        body = "\n".join(lines[body_start:i]).strip()
        ideas.append(Idea(
            title=title, status=status, explore=explore, body=body,
            anchor=heading_id(path.stem, title), source=path.name))
    return ideas


def read_ideas(directory):
    """Every idea across every `*.md` in `directory`, file order then document
    order -- both already deterministic (sorted glob, then top-to-bottom
    scan), so no further sort is needed to satisfy the site's determinism
    rule."""
    files = sorted(directory.glob("*.md"))
    if not files:
        # An absent/empty dir renders an empty index rather than failing: on
        # the real site a vanished ideas dir already fails LOUDLY upstream
        # (its own {{section:id-index}} placement vanishes with it, tripping
        # the placed-exactly-once gate), while synthetic test trees that
        # place the section without ideas prose must not abort the whole
        # emit.
        return []
    ideas = []
    for path in files:
        ideas.extend(_parse_file(path))
    if not ideas:
        raise ValueError(
            f"{directory}: no `## ` idea headings found in {len(files)} file(s) "
            f"-- the parking lot has no cards to index")
    return ideas


# ==========================================================================
# the generated index
# ==========================================================================

def _has_pointer(body):
    """A promoted idea's stub: at least one markdown link in its body. That is
    the one-line link/pointer stub promotion is asked to leave behind."""
    return bool(_LINK.search(body))


def _idea_row(idea):
    link = f'<a href="#{idea.anchor}">{h.escape(idea.title)}</a>'
    if idea.status == "promoted":
        note = ("promoted — see the linked page" if _has_pointer(idea.body)
                else '<span class="gen-note">stub missing — no link in the '
                     "idea's body yet</span>")
    else:
        note = h.escape(idea.explore) if idea.explore else "—"
    return f"<tr><td>{link}</td><td>{h.escape(idea.source)}</td><td>{note}</td></tr>"


def render_id_index(tok):
    """The whole parking lot, grouped seed -> exploring -> promoted. `tok` is
    unused (the index carries no colour or size of its own) but kept for the
    same `(tok) -> html` shape every section renderer has."""
    ideas = read_ideas(ideas_dir())
    by_status = {status: [i for i in ideas if i.status == status]
                 for status in STATUSES}
    counts = ", ".join(f"{len(by_status[s])} {STATUS_LABELS[s].lower()}"
                       for s in STATUSES)
    parts = [f'<p class="gen-note">{len(ideas)} ideas: {counts}. Grouped by '
             f"status; promotion moves an idea's content into a real domain "
             f"and leaves a link stub here.</p>"]
    for status in STATUSES:
        group = by_status[status]
        if not group:
            continue
        rows = "".join(_idea_row(idea) for idea in group)
        parts.append(
            f"<h3>{STATUS_LABELS[status]}</h3>"
            "<table><thead><tr><th>idea</th><th>source</th><th>note</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>")
    return "".join(parts)


# (slug, title, lede, renderer) -- the slug is prefixed `id-` so the ideas
# domain can never collide with another domain's section slugs.
SECTIONS = [
    ("id-index", "Idea Index",
     "Every idea on file, grouped by how ready", render_id_index),
]
