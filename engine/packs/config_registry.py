#!/usr/bin/env python3
"""config_registry.yaml -> the site's config registry page.

A page-provider entry: `provider(tok)` returns a single depth-0 page at
`config.html` -- the whole registry fits on one page, so unlike a multi-leaf
pack there is no per-entry leaf page.

THE POINT OF THIS FILE: a curated manifest names every knob worth knowing
about -- name, where it lives, a symbol that must appear there, and its
current value -- and generation VERIFIES the pointer rather than trusting it.
A renamed or deleted knob fails the build naming the entry, so the page can
never claim a knob lives somewhere it does not.

TWO KINDS OF "current value" (config_registry.yaml's header names the full
field list):
  default  hand-typed prose, curated by whoever wrote the entry. Verified only
           in that its `where`/`symbol` pointer resolves -- the VALUE itself
           is not machine-checked, so it can drift from the constant it
           describes.
  token    a dotted tokens.yaml path, resolved LIVE through the shared token
           model -- this value cannot drift, because it is read out of
           tokens.yaml at generation time, not typed by hand.

`where` is resolved relative to the wiki root (`cfg.root`); an adopter whose
knobs live outside the wiki directory writes a `../`-relative path.

READ-ONLY: no write path exists from this page back into any of the files it
cites. The "how to change" column names the file (and, typically, the test
suite to run after) -- changing a knob still means opening that file in an
editor.

Determinism: config_registry.yaml is parsed by the minimal YAML reader, which
returns mappings in FILE order (not sorted) -- so area order and entry order
both come from the manifest's own layout.
"""
from __future__ import annotations

import collections
import html as h

from .. import config, minyaml
from ..markdown import resolve_token

INDEX_REL = "config.html"
INDEX_TITLE = "Config Registry"
INDEX_LEDE = "Every tuning knob that matters, verified against source"

REQUIRED_FIELDS = ("name", "where", "symbol", "scope", "how")

Entry = collections.namedtuple(
    "Entry", "key area name where symbol kind value scope how")


# ==========================================================================
# reading and validating the manifest
# ==========================================================================

def _parse_entry(path, area, entry_key, body):
    where = f"{area}.{entry_key}"
    if not isinstance(body, dict):
        raise ValueError(f"{path}: entry {where!r} must be a mapping, got {body!r}")
    missing = [f for f in REQUIRED_FIELDS if f not in body]
    if missing:
        raise ValueError(
            f"{path}: entry {where!r} is missing {', '.join(missing)}")
    has_default = "default" in body
    has_token = "token" in body
    if has_default == has_token:
        raise ValueError(
            f"{path}: entry {where!r} must carry exactly one of `default` or "
            f"`token`, not {'neither' if not has_default else 'both'}")
    kind = "token" if has_token else "default"
    value = body["token"] if has_token else body["default"]
    return Entry(
        key=where,
        area=area,
        name=str(body["name"]),
        where=str(body["where"]),
        symbol=str(body["symbol"]),
        kind=kind,
        value=str(value),
        scope=str(body["scope"]),
        how=str(body["how"]),
    )


def load_manifest(cfg=None):
    """The manifest -> [Entry], area order then entry order, both as written
    in the file.

    Every input problem raises ValueError naming the file and the offending
    entry -- the same discipline every other hand-edited input holds to.
    """
    cfg = cfg or config.current()
    path = cfg.config_registry_path
    if not path.is_file():
        raise ValueError(
            f"{path} is missing -- the config registry has no manifest to render")
    raw = minyaml.parse(path.read_text(encoding="utf-8"))
    if not raw:
        raise ValueError(f"{path}: parsed to nothing -- the manifest needs at "
                         f"least one area")
    entries = []
    for area, area_body in raw.items():
        if not isinstance(area_body, dict) or not area_body:
            raise ValueError(
                f"{path}: area {area!r} must be a non-empty mapping of entries")
        for entry_key, body in area_body.items():
            entries.append(_parse_entry(path, area, entry_key, body))
    return entries


def verify_entry(entry, root):
    """An Entry's `where`/`symbol` pointer -> None, or ValueError naming the
    entry, the file, and what went wrong.

    THE VERIFICATION GREP. This is the whole reason the manifest exists as
    data instead of prose: a renamed or deleted knob makes this substring
    search fail, and the page cannot be generated claiming a knob lives where
    it no longer does.
    """
    path = root / entry.where
    if not path.is_file():
        raise ValueError(
            f"config registry entry {entry.key!r} ({entry.name}): {entry.where} "
            f"does not exist -- the knob moved, was deleted, or the manifest's "
            f"`where` is stale")
    text = path.read_text(encoding="utf-8", errors="replace")
    if entry.symbol not in text:
        raise ValueError(
            f"config registry entry {entry.key!r} ({entry.name}): symbol "
            f"{entry.symbol!r} does not appear in {entry.where} -- the knob was "
            f"renamed or removed and the manifest's `symbol` is stale")


def verify_all(entries, root):
    for entry in entries:
        verify_entry(entry, root)


# ==========================================================================
# rendering
# ==========================================================================

def _area_title(area):
    """"user-guide" -> "User Guide", "api-reference" -> "Api Reference". Areas are
    hyphenated in the manifest so they double as anchor fragments unchanged."""
    return " ".join(word.capitalize() for word in area.split("-"))


def _value_cell(entry, tok):
    """The "current value" column. A token entry is resolved LIVE through the
    same token machinery every `{{token}}` on the site uses, so a
    config-registry token entry and a design-system swatch can never
    disagree about what a token resolves to, and an unknown/renamed token
    fails generation naming this entry exactly like a bad `{{token}}`
    anywhere else."""
    if entry.kind == "default":
        return h.escape(entry.value)
    try:
        kind, value = resolve_token(tok, entry.value)
    except ValueError as exc:
        raise ValueError(f"{entry.key}: {exc}") from None
    if kind == "hex":
        return (f'<span class="tk"><span class="sw" style="background:{value}">'
                f"</span><code>{value}</code></span>")
    return f"<code>{h.escape(str(value))}</code>"


def _row(entry, tok):
    return (
        "<tr>"
        f"<td>{h.escape(entry.name)}</td>"
        f"<td>{_value_cell(entry, tok)}</td>"
        f"<td>{h.escape(entry.scope)}</td>"
        f"<td><code>{h.escape(entry.where)}:{h.escape(entry.symbol)}</code></td>"
        f"<td>{h.escape(entry.how)}</td>"
        "</tr>"
    )


def _area_table(area, entries, tok):
    rows = "".join(_row(entry, tok) for entry in entries)
    anchor = f"cfg-{area}"
    return (
        f'<h2 id="{h.escape(anchor)}">{h.escape(_area_title(area))} '
        f"— {len(entries)}</h2>"
        "<table><thead><tr>"
        "<th>Name</th><th>Default</th><th>Scope</th><th>Where</th>"
        "<th>How to change</th>"
        "</tr></thead><tbody>"
        f"{rows}"
        "</tbody></table>"
    )


def _grouped(entries):
    """[Entry] -> [(area, [Entry])], area order = first-seen order in the
    manifest (the manifest itself iterates in file order, so this is stable
    without a sort)."""
    groups = collections.OrderedDict()
    for entry in entries:
        groups.setdefault(entry.area, []).append(entry)
    return list(groups.items())


def _intro(entries, by_area):
    token_count = sum(1 for e in entries if e.kind == "token")
    return "\n".join([
        "<p>Every toggle and variable in this project worth knowing about lives "
        "in exactly one file: a constant a programmer edits in source, or a "
        "value in <code>tokens.yaml</code>. This page is neither of "
        "those — it is a generated INDEX pointing at both, and unlike a page "
        "someone writes by hand, it is <strong>verified</strong> at generation "
        "time: every entry's file must exist and a literal symbol must appear "
        "in it, so a renamed or deleted knob fails the build instead of quietly "
        "going stale here.</p>",
        "<p>This page has no edit control and no write path. The "
        "<strong>How to change</strong> column names the file to open and, "
        "typically, the test suite to run after — changing a knob still means "
        "editing that file by hand. This page is the evidence a debug panel "
        "would eventually need, not the panel itself.</p>",
        f'<p class="gen-note">{len(entries)} knobs across {len(by_area)} areas '
        f"({token_count} resolved live from <code>tokens.yaml</code>, "
        f"{len(entries) - token_count} hand-curated defaults). Every entry "
        "below survived generation, which means its file exists and its "
        "symbol was found there today.</p>",
    ])


def _closing_notes():
    return "\n".join([
        '<h2 id="cfg-adding">Adding an entry</h2>',
        "<p>Add a key under the right area in "
        "<code>config_registry.yaml</code> — or a new top-level area, "
        "if none of the existing ones fit. Every entry needs "
        "<code>name</code>, <code>where</code>, <code>symbol</code>, "
        "<code>scope</code>, <code>how</code>, and exactly one of "
        "<code>default</code> (prose you write) or <code>token</code> (a "
        "dotted <code>tokens.yaml</code> path resolved live). Pick "
        "<code>token</code> whenever the value truly lives in "
        "<code>tokens.yaml</code> — it cannot go stale the way a hand-typed "
        "<code>default</code> can.</p>",
        "<p>Regenerate after editing. If <code>symbol</code> does not appear "
        "verbatim in <code>where</code>, or <code>where</code> does not exist, "
        "generation fails naming the entry — fix the pointer, not the check. "
        "The manifest file's own header documents the minimal YAML subset it "
        "must stay inside (no anchors, no multi-line scalars, and "
        "<code>&amp; * &gt; |</code> are rejected even inside quotes).</p>",
        '<h2 id="cfg-sources">How this page is built</h2>',
        "<p class=\"gen-note\">Generated from "
        "<code>config_registry.yaml</code> by this pack. Prose values are "
        "exactly what a curator typed; token values are read live from "
        "<code>tokens.yaml</code> through the same resolver every "
        "<code>{{token}}</code> on this site uses. Edit the manifest, not this "
        "page — this page is output.</p>",
    ])


def _index_body(entries, tok):
    by_area = _grouped(entries)
    parts = [_intro(entries, by_area)]
    for area, area_entries in by_area:
        parts.append(_area_table(area, area_entries, tok))
    parts.append(_closing_notes())
    return "\n".join(parts)


# ==========================================================================
# the provider
# ==========================================================================

def provider(tok):
    """(tok) -> [Page]: one page, config.html."""
    cfg = config.current()
    entries = load_manifest(cfg)
    verify_all(entries, cfg.root)
    return [(INDEX_REL, INDEX_TITLE, INDEX_LEDE, [], _index_body(entries, tok))]
