#!/usr/bin/env python3
"""Glossary pack: canonical vocabulary, rendered as a table, plus a report of
where words the glossary asks writers to avoid still turn up in prose.

Registers two sections (SECTIONS, the same `(slug, title, lede, renderer)`
shape every section provider uses) and exports `homes(cfg)`, the {term: home}
map the site's auto-linker and home-link gate both need. `homes` lives here
rather than being computed by the site module because this pack owns the one
source of truth for what a "home" is: a `page.html#anchor` parsed straight out
of glossary.yaml, with its own shape check.

    gl-terms         the glossary table itself, parsed from glossary.yaml
    gl-occurrences   REPORT-ONLY: where each avoid-word still appears in prose

The occurrence report never fails a build on its own -- it exists so a stale
avoid-word is visible, not so it is enforced before anyone has agreed a rename
is worth doing. Tightening it into a gate is an adopter decision, not this
pack's.

Determinism: glossary.yaml is a mapping, so parse order gives entry order for
anything not explicitly re-sorted; the occurrence scan sorts avoid-words,
scanned files, and file/line hits, so two runs over the same corpus produce
byte-identical output.
"""
from __future__ import annotations

import collections
import html as h
import os
import re

from .. import config, minyaml

DISPLAY_CAP = 5

_FENCE = "```"
_INLINE_CODE = re.compile(r"`[^`]*`")

Entry = collections.namedtuple("Entry", "term definition scope avoid see home")

# `home` is the page#anchor where the term is DEFINED, in the same site-root
# coordinates every other href in a page body is written in
# ("design-system.html#s-inks"). Shape is checked here; that the page is
# actually emitted and actually carries that id is checked by the site's own
# link gate, which is the only place that knows the emitted set. The
# auto-linker reads the map this module builds.
_HOME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9./_-]*\.html#[A-Za-z0-9._-]+$")


# ==========================================================================
# glossary.yaml
# ==========================================================================

def _need(block, key, where):
    if not isinstance(block, dict) or key not in block:
        raise ValueError(f"{where}: missing {key!r}")
    return block[key]


def _optional_list(block, key):
    value = block.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key!r} must be a list")
    return [str(item).strip() for item in value]


def load_glossary(cfg=None):
    """glossary.yaml -> [Entry], sorted case-insensitively by term.

    Every input problem raises ValueError naming the file and the offending
    term, so a broken glossary fails generation rather than shipping a page
    that quietly says the wrong thing.
    """
    cfg = cfg or config.current()
    path = cfg.glossary_path
    if not path.is_file():
        raise ValueError(f"{path} is missing")
    raw = minyaml.parse(path.read_text(encoding="utf-8"))
    where_file = str(path)
    if not isinstance(raw, dict):
        raise ValueError(f"{where_file}: must be a mapping of terms")
    # An empty file is a valid, empty glossary -- a synthetic site or a
    # freshly-adopted project may not have written any terms yet.

    entries = []
    for term, body in raw.items():
        where = f"{where_file}: {term}"
        if not isinstance(body, dict):
            raise ValueError(f"{where} must be a mapping, not {type(body).__name__}")
        definition = str(_need(body, "definition", where)).strip()
        scope = str(_need(body, "scope", where)).strip()
        home = str(_need(body, "home", where)).strip()
        if not _HOME.match(home):
            raise ValueError(
                f"{where}: 'home' is {home!r} -- it must be a page-and-anchor in "
                f"site-root coordinates, e.g. 'design-system.html#s-inks'")
        entries.append(Entry(
            term=str(term).strip(),
            definition=definition,
            scope=scope,
            avoid=_optional_list(body, "avoid"),
            see=_optional_list(body, "see"),
            home=home,
        ))

    terms = {e.term for e in entries}
    for entry in entries:
        for target in entry.see:
            if target not in terms:
                raise ValueError(
                    f"{where_file}: {entry.term!r} 'see' references unknown term "
                    f"{target!r}")
        for word in entry.avoid:
            if word in terms:
                raise ValueError(
                    f"{where_file}: {entry.term!r} avoid-word {word!r} is itself "
                    f"another entry's canonical term -- pick a real ambiguous word, "
                    f"not the correct one")

    return sorted(entries, key=lambda e: e.term.lower())


def homes(cfg) -> dict:
    """{term: 'page.html#anchor'} for the auto-linker and the home-link gate."""
    return {entry.term: entry.home for entry in load_glossary(cfg)}


# ==========================================================================
# small render helpers
# ==========================================================================

def _table(headers, rows, row_ids=None):
    out = ["<table><thead><tr>"]
    out += [f"<th>{h.escape(cell)}</th>" for cell in headers]
    out.append("</tr></thead><tbody>")
    row_ids = row_ids or [None] * len(rows)
    for row_id, row in zip(row_ids, rows):
        attr = f' id="{h.escape(row_id)}"' if row_id else ""
        out.append(f"<tr{attr}>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _codes(words):
    return ", ".join(f"<code>{h.escape(w)}</code>" for w in words)


# ==========================================================================
# gl-terms: the glossary table
# ==========================================================================

def render_terms(tok):
    entries = load_glossary()
    rows = [
        [
            f"<code>{h.escape(e.term)}</code>",
            h.escape(e.definition),
            h.escape(e.scope),
            _codes(e.avoid),
            _codes(e.see),
        ]
        for e in entries
    ]
    # Every row carries the anchor its own `home` fragment names, so the term's
    # declared home resolves to something concrete on the page -- the site's
    # home-link gate checks exactly this id is present.
    row_ids = [e.home.partition("#")[2] for e in entries]
    return (
        f'<p class="gen-note">{len(entries)} canonical terms, alphabetical, parsed '
        f"from <code>glossary.yaml</code>. “Avoid these” names words "
        f"a writer might reach for instead of the term in that row; “see” "
        f"names the OTHER entries this one is easily confused with.</p>"
        + _table(["term", "definition", "scope", "avoid these", "see"], rows, row_ids)
    )


# ==========================================================================
# gl-occurrences: REPORT-ONLY appendix
# ==========================================================================

def _outside_fences_and_spans(text):
    """(1-based lineno, line) for every line NOT inside a fenced (``` ```)
    block, with inline `code spans` blanked out first.

    A fence toggle line itself is never scanned (it carries no prose), and an
    avoid-word documented as a literal example inside a fence or a code span
    must not count as a real occurrence.
    """
    inside = False
    for lineno, raw in enumerate(text.split("\n"), start=1):
        if raw.strip().startswith(_FENCE):
            inside = not inside
            continue
        if inside:
            continue
        yield lineno, _INLINE_CODE.sub(" ", raw)


def _scan_files(cfg):
    prose_dir = cfg.prose_dir
    return sorted(prose_dir.rglob("*.md")) if prose_dir.is_dir() else []


_Hit = collections.namedtuple("Hit", "word count locations")


def scan_occurrences(avoid_words, files, root):
    """[_Hit] for the DEDUPED, sorted set of `avoid_words` -- deterministic:
    words sorted case-insensitively, files sorted, hits in file/line order.

    Matching is case-insensitive and whole-word; fenced blocks and inline
    code spans are stripped first via _outside_fences_and_spans, so a
    backticked example is never counted as prose usage.
    """
    scan_files = sorted(files)
    results = []
    for word in sorted({w for w in avoid_words}, key=str.lower):
        pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
        count = 0
        locations = []
        for path in scan_files:
            rel = os.path.relpath(path, root)
            text = path.read_text(encoding="utf-8")
            for lineno, line in _outside_fences_and_spans(text):
                found = pattern.findall(line)
                if not found:
                    continue
                count += len(found)
                locations.append((rel, lineno))
        results.append(_Hit(word=word, count=count, locations=locations))
    return results


def render_occurrences(tok):
    cfg = config.current()
    entries = load_glossary()
    avoid_words = [word for e in entries for word in e.avoid]
    scan_files = _scan_files(cfg)
    report = scan_occurrences(avoid_words, scan_files, cfg.root)

    rows = []
    for hit in report:
        shown = hit.locations[:DISPLAY_CAP]
        where = "; ".join(f"<code>{h.escape(rel)}:{lineno}</code>"
                          for rel, lineno in shown)
        remaining = len(hit.locations) - len(shown)
        if remaining > 0:
            where += f" +{remaining} more"
        rows.append([f"<code>{h.escape(hit.word)}</code>", str(hit.count),
                     where or "—"])

    total_hits = sum(hit.count for hit in report)
    return (
        '<p class="gen-note">REPORT-ONLY: these counts do not fail generation. '
        f"{len(report)} avoid-words from <code>glossary.yaml</code>, scanned "
        f"case-insensitively and whole-word across {len(scan_files)} prose "
        f"files, outside fenced and inline code -- {total_hits} occurrences "
        "total. Tightening this into a build-failing gate is an adopter "
        "decision.</p>"
        + _table(["avoid word", "occurrences", "where"], rows)
    )


# (slug, title, lede, renderer) -- slugs are FROZEN (prose cites them by
# `{{section:<slug>}}`) and prefixed `gl-` so this domain can never collide
# with another's. Every lede is within the site's configured word bounds.
SECTIONS = [
    ("gl-terms", "Glossary",
     "Canonical terms, definitions, scope, and words to avoid", render_terms),
    ("gl-occurrences", "Avoid-Term Occurrences",
     "Where ambiguous words still appear across the prose", render_occurrences),
]
