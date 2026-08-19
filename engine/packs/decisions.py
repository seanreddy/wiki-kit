#!/usr/bin/env python3
"""decisions/*.md -> the site's decision archive.

A page-provider entry: `provider(tok)` returns an index page at
`decisions.html` plus one page per decision at `decisions/<stem>.html`, all
in site-root coordinates -- the site's own depth-shift pass moves them once
on the way out, so nothing here knows or cares that leaf pages sit one level
down.

RAW MODE IS THE POINT. Decisions are HISTORICAL DOCUMENTS and must render as
written, which means this module reuses the engine's block/inline machinery
but deliberately drops three things that are correct for prose and wrong for
an archive:

  1. NO {{token}} interpolation. A decision may document the directive syntax
     itself, or name a token that has since been renamed. A literal `{{...}}`
     renders as literal text -- it must neither resolve nor fail generation.
  2. NO image-citation validation. A decision cites files by whatever path it
     used at the time, and those files may not exist any more. An image
     reference renders as a plain `<code>` path; no `<img>` is emitted, so
     nothing 404s and nothing has to be kept alive to satisfy an old document.
  3. NO hex lint. A raw hex code in a decision is prose about a colour, not a
     styled swatch, and renders as plain text. Because those historical hexes
     are NOT in the token model, every decision page body opens with
     `markdown.RAW_ARCHIVE_MARKER` so a hand-typed-hex check elsewhere can
     skip archive pages without weakening the check on generated ones.

ALSO A GATE INTERACTION: the site's link gate fails generation on any
site-relative href that resolves to nothing. Decisions are full of repo paths
that are not emitted pages, so EVERY non-http link inside decision markdown
is rewritten to plain `<code>` text rather than an `<a>` -- a dead link in
one archived document would take the whole site down with it.

Beyond-subset markdown (nested lists, blockquotes, 5-level headings) degrades
to paragraphs/flat lists on purpose: best-effort rendering of an archive
beats a second markdown engine.

Determinism: sorted() file iteration, no timestamps, no set iteration.
"""
from __future__ import annotations

import collections
import html as h
import re

from .. import config
from .. import markdown

_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^()\s]+)\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^()\s]+)\)")

INDEX_REL = "decisions.html"
INDEX_TITLE = "Decisions"
INDEX_LEDE = "Every recorded decision, rendered exactly as written"
PAGE_SUBDIR = "decisions"

# The crumb label is written out rather than derived, so a decision page's
# trail reads sensibly even for an adopter whose hub isn't literally titled
# "Hub".
CRUMBS_INDEX = (("index.html", "Hub"),)
CRUMBS_LEAF = (("index.html", "Hub"), (INDEX_REL, INDEX_TITLE))

NO_STATUS = "—"
NO_DATE = "—"

_H1 = re.compile(r"^#\s+(.*)$")
_STATUS = re.compile(r"^\s*\*\*Status:\*\*\s*(.*)$")
_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_FENCE = "```"

_Entry = collections.namedtuple(
    "_Entry", "date stem name title status lede rel body")


# ==========================================================================
# ledes, proved rather than trusted
# ==========================================================================

def _lede(*parts):
    """Assemble a page lede and PROVE its word count here.

    The site gates every lede at its configured word bounds and fails
    generation on a miss, so a lede built from data may only come from a
    template whose word count is CONSTANT. Every interpolated piece is
    collapsed to a single word first (see `_one_word`); this helper is where
    the template itself is checked, so a bad template fails naming this
    module instead of somewhere in the emitter.
    """
    words = " ".join(parts).split()
    cfg = config.current()
    low, high = cfg.lede_min, cfg.lede_max
    if not low <= len(words) <= high:
        raise ValueError(
            f"decisions pack lede template is {len(words)} words, must be "
            f"{low}-{high} ({' '.join(words)!r})")
    return " ".join(words)


def _one_word(value, fallback):
    """Collapse a data value to exactly one word, so a template built around
    it has a fixed word count no matter what the data says."""
    token = "-".join(str(value).split())
    return token or fallback


def _decision_lede(date):
    """A fixed word count by construction: both branches are fixed-length
    templates and the only variable, the date, is a single word."""
    if date:
        return _lede("Decision of", _one_word(date, "undated"), "— rendered as written")
    return _lede("Undated decision — rendered here as written")


# ==========================================================================
# reading the archive
# ==========================================================================

def _outside_fences(text):
    """(index, line) for every line NOT inside a fenced block.

    Metadata scans run through here so a fenced example containing a `#
    Title` or `**Status:**` line cannot be mistaken for the document's own.
    """
    inside = False
    for i, line in enumerate(text.split("\n")):
        if line.strip().startswith(_FENCE):
            inside = not inside
            continue
        if not inside:
            yield i, line


def _plain_heading(raw):
    """Heading markdown -> bare text, for a page title or an anchor id.

    `markdown._flatten` cannot be reused here: it resolves `{{tokens}}` on
    the way through, which is exactly what raw mode must not do. A literal
    `{{...}}` in a title stays literal here and is escaped by the shell.
    """
    flat = _IMAGE.sub(r"\1", raw)
    flat = _LINK.sub(r"\1", flat)
    return flat.replace("**", "").replace("*", "").replace("`", "").strip()


def _take_title(text, stem):
    """First `# h1` -> the page title, lifted OUT of the body.

    The shell emits the h1 for every page kind, so leaving it in would print
    the title twice. A decision with no h1 is not an error -- the filename
    stem names the page, and an archive is not something you can go back and
    fix.
    """
    for i, line in _outside_fences(text):
        m = _H1.match(line)
        if not m:
            continue
        lines = text.split("\n")
        del lines[i]
        return _plain_heading(m.group(1)) or stem, "\n".join(lines)
    return stem, text


def _take_status(text):
    """First `**Status:**` line's remainder, or an em dash. Many decisions
    predate the convention; a missing status is normal, not a fault."""
    for _i, line in _outside_fences(text):
        m = _STATUS.match(line)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return NO_STATUS


def _source_label(directory, name, root):
    """The decision's repo path, shown on its page as text. Deliberately NOT
    a link: the *.md is not an emitted page, and linking out of the site
    tree would couple an archive page to the link gate for no reader
    benefit."""
    try:
        base = directory.resolve().relative_to(root).as_posix()
    except ValueError:
        base = directory.name
    return f"{base}/{name}" if name else base


def _entries(directory):
    """Every decision in `directory`, newest first. Real input problems raise
    ValueError naming the file -- the driver turns that into a build
    failure.
    """
    if not directory.is_dir():
        raise ValueError(
            f"{directory}: the decision archive directory does not exist")
    files = sorted(directory.glob("*.md"))
    if not files:
        raise ValueError(
            f"{directory}: holds no *.md -- the decision archive would be an "
            f"empty index page, and a page provider must return an index")

    found = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(
                f"{path.name}: cannot be read as UTF-8 text ({exc}) -- every "
                f"decision in {directory.name}/ is rendered, so an unreadable "
                f"one fails generation rather than silently vanishing") from None
        if markdown.MARK_OPEN in text or markdown.MARK_CLOSE in text:
            raise ValueError(
                f"{path.name}: contains a NUL/SOH byte, which the inline "
                f"renderer uses as its protect-span sentinel -- it would come "
                f"back out as somebody else's markup")

        stem = path.stem
        title, body = _take_title(text, stem)
        date_match = _DATE_PREFIX.match(stem)
        date = date_match.group(1) if date_match else ""
        found.append(_Entry(
            date=date,
            stem=stem,
            name=path.name,
            title=title,
            status=_take_status(text),
            lede=_decision_lede(date),
            rel=f"{PAGE_SUBDIR}/{stem}.html",
            body=body,
        ))

    # Newest first by the filename date prefix. Ties break on the stem so the
    # order is total and deterministic; an undated file sorts to the bottom,
    # where an undated document belongs.
    return sorted(found, key=lambda e: (e.date, e.stem), reverse=True)


# ==========================================================================
# pages
# ==========================================================================

def _index_body(entries, directory, root):
    """The archive index: date, title, status, one row per decision.

    No h2 and therefore no one-item TOC -- the table IS the index.
    """
    rows = []
    for entry in entries:
        rows.append(
            "<tr>"
            f"<td>{h.escape(entry.date or NO_DATE)}</td>"
            f'<td><a href="{entry.rel}">{h.escape(entry.title)}</a></td>'
            f"<td>{h.escape(entry.status)}</td>"
            "</tr>")
    count = len(entries)
    where = h.escape(_source_label(directory, "", root).rstrip("/"))
    return (
        f'<p class="gen-note">{count} decision'
        f"{'' if count == 1 else 's'} in <code>{where}</code>, rendered as "
        f"written — no interpolation, no lint, no edits.</p>"
        "<table><thead><tr><th>Date</th><th>Decision</th><th>Status</th></tr>"
        f"</thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _leaf_body(entry, directory, root):
    """`markdown.RAW_ARCHIVE_MARKER` first, then a one-line provenance note,
    then the document."""
    return "\n".join([
        markdown.RAW_ARCHIVE_MARKER,
        f'<p class="gen-note">Status: {h.escape(entry.status)} · '
        f"Source: <code>{h.escape(_source_label(directory, entry.name, root))}"
        f"</code></p>",
        markdown.render_raw(entry.body, entry.name),
    ])


def decision_pages(directory, root):
    """[(rel, title, lede, crumbs, body)] -- index first, then newest-first
    decisions.

    Split out from `provider` so callers can drive it against a fixture
    directory without touching module state.
    """
    entries = _entries(directory)
    pages = [(INDEX_REL, INDEX_TITLE, _lede(INDEX_LEDE), list(CRUMBS_INDEX),
              _index_body(entries, directory, root))]
    for entry in entries:
        pages.append((entry.rel, entry.title, entry.lede, list(CRUMBS_LEAF),
                      _leaf_body(entry, directory, root)))
    return pages


def provider(_tok):
    """Page-provider entry.

    `tok` is unused BY DESIGN: raw mode never interpolates, so no decision
    page can depend on the token model -- which is what makes an archive
    page stable while tokens keep moving.
    """
    cfg = config.current()
    return decision_pages(cfg.decisions_dir, cfg.root)
