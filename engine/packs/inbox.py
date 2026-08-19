#!/usr/bin/env python3
"""The owner's inbox: definition-change flags plus inbox.yaml action items.

A page-provider entry: `provider(tok)` returns a single depth-0 page at
`inbox.html`, carrying two independent kinds of note:

  1. Definition-change flags -- computed by re-deriving the tracked page set
     (domain pages + every OTHER provider's depth-0 page) and running it
     through `site.definition_flags`, the SAME comparison the site itself
     uses to decide which pages carry the in-page banner. There is one
     comparison implementation; this module does not keep a second copy.
  2. inbox.yaml action items, grouped suggested -> accepted -> dismissed.
     Anyone may add a `suggested` entry; only the owner changes a status or
     clears a flag (by editing review_state.yaml) -- this page renders the
     file, it does not police who edited it.

WHY THE FLAGS ARE RECOMPUTED HERE rather than read off the site's in-progress
run: the provider contract is frozen at `(tok) -> list[Page]`, so this module
cannot receive the site's already-built tracked list as an argument.
Recomputing from `tok` and the committed inputs is pure and cheap enough for
a generator, and it means this page is exactly as trustworthy tested alone
as it is wired into the real site.

SELF-EXCLUSION. `_tracked_pages` walks the registry's page providers and
skips `provider` (this module's own entry) by identity -- otherwise
computing the inbox's tracked set would call this module's own provider
function, which would try to compute its tracked set, forever. inbox.html
still gets a snapshot line in review_state.yaml like every other tracked
page; it is simply not part of the set THIS page reports on.

Determinism: inbox.yaml entries render in file order (the minimal YAML reader
preserves insertion order); flags are sorted by `rel` inside
`site.definition_flags`.
"""
from __future__ import annotations

import collections
import html as h

from .. import config, minyaml, site

INDEX_REL = "inbox.html"
INDEX_TITLE = "Inbox"
INDEX_LEDE = "Definition changes and suggested fixes, gathered here"
CRUMBS_INDEX = (("index.html", "Hub"),)

STATUSES = ("suggested", "accepted", "dismissed")
STATUS_LABELS = {"suggested": "Suggested", "accepted": "Accepted",
                  "dismissed": "Dismissed"}

_Item = collections.namedtuple("_Item", "id status title body source")


# ==========================================================================
# inbox.yaml
# ==========================================================================

def _load_inbox_items(cfg):
    """inbox.yaml -> [_Item] in file order. Real input problems raise
    ValueError naming the entry -- an inbox item nobody can trust is worse
    than no inbox item."""
    path = cfg.inbox_path
    if not path.is_file():
        raise ValueError(f"{path} is missing -- the inbox page has nothing to "
                         f"render for its action items")
    raw = minyaml.parse(path.read_text(encoding="utf-8"))
    items = []
    for entry_id, fields in raw.items():
        if not isinstance(fields, dict):
            raise ValueError(f"{path}: entry {entry_id!r} is not a mapping")
        status = fields.get("status")
        if status not in STATUSES:
            raise ValueError(
                f"{path}: entry {entry_id!r} has unknown status {status!r} -- "
                f"must be one of {', '.join(STATUSES)}")
        for field in ("title", "body", "source"):
            if not fields.get(field):
                raise ValueError(
                    f"{path}: entry {entry_id!r} is missing {field!r}")
        items.append(_Item(
            id=entry_id,
            status=status,
            title=site.unescape_minyaml_gap(str(fields["title"])),
            body=site.unescape_minyaml_gap(str(fields["body"])),
            source=site.unescape_minyaml_gap(str(fields["source"])),
        ))
    return items


# ==========================================================================
# definition-change flags -- reuses site.definition_flags
# ==========================================================================

def _tracked_pages(tok, cfg):
    """[(rel, title, lede)] for every page review_state.yaml snapshots: every
    domain page, every OTHER page provider's depth-0 page, and this module's
    OWN page -- added directly as (INDEX_REL, INDEX_TITLE, INDEX_LEDE) rather
    than through a recursive call into `provider`, because those three are
    fixed constants with nothing to recompute. Skipping this module's
    provider entirely (instead of substituting the constants) would make
    inbox.html permanently read as "no longer exists" against its own
    review_state.yaml line -- correct self-tracking needs the tuple, just not
    the recursion.

    Recomputed rather than read off shared state, so this is safe to call
    directly in a test with no site build in progress.
    """
    registry = site.load_registry(cfg)
    smap = site.section_map(registry)
    placed = {}
    tracked = []
    for kind, payload in site.site_sequence(cfg, registry):
        if kind == "domain":
            slug, directory = payload
            page, _stat = site.domain_page(tok, slug, directory, placed, smap)
            tracked.append((page[0], page[1], page[2]))
        else:
            provider_fn = payload
            if provider_fn is provider:
                continue
            _pages, index = site.provider_pages(tok, provider_fn)
            tracked.append((index[0], index[1], index[2]))
    tracked.append((INDEX_REL, INDEX_TITLE, INDEX_LEDE))
    return tracked


# ==========================================================================
# rendering
# ==========================================================================

def _flag_row(flag, tracked_by_rel):
    if flag.reason == "removed":
        return (f"<li><code>{h.escape(flag.rel)}</code> is recorded in "
                f"<code>review_state.yaml</code> but the page no "
                f"longer exists.</li>")
    title, _lede = tracked_by_rel[flag.rel]
    verb = ("has no review_state.yaml entry yet" if flag.reason == "missing"
            else "changed since it was last reviewed")
    return (f'<li><a href="{h.escape(flag.rel)}">{h.escape(title)}</a> '
            f"{verb}.</li>")


def _flags_body(flags, tracked):
    if not flags:
        return ('<p class="gen-note">Every tracked page matches its '
                '<code>review_state.yaml</code> snapshot -- nothing '
                'to re-review.</p>')
    tracked_by_rel = {rel: (title, lede) for rel, title, lede in tracked}
    rows = "".join(_flag_row(f, tracked_by_rel) for f in flags)
    return (f'<p class="gen-note">{len(flags)} page'
            f"{'' if len(flags) == 1 else 's'} need a look: a snapshot is "
            "missing, the title or lede moved since it was reviewed, or the "
            "snapshot names a page that is gone.</p>"
            f"<ul>{rows}</ul>")


def _item_card(item):
    return (
        f'<div class="spec" id="inbox-{h.escape(item.id)}">'
        f"<b>{h.escape(item.title)}</b>"
        f"<p>{h.escape(item.body)}</p>"
        f'<div class="gen-note">Source: <code>{h.escape(item.source)}</code>'
        "</div></div>")


def _items_body(items):
    parts = []
    for status in STATUSES:
        group = [i for i in items if i.status == status]
        if not group:
            continue
        parts.append(f'<h2 id="i-{status}">{STATUS_LABELS[status]}</h2>')
        parts.append('<div class="spec-grid">'
                     + "".join(_item_card(i) for i in group) + "</div>")
    return "\n".join(parts)


def _index_body(flags, tracked, items):
    return "\n".join([
        "<p>This page carries two kinds of note. The first is mechanical: "
        "every domain page and every page provider's index page has a "
        "reviewed title and lede snapshot in "
        "<code>review_state.yaml</code>, and a page whose current "
        "title or lede no longer matches its snapshot is flagged below "
        "automatically at generation time, with the same banner shown on the "
        "page itself. The second is editorial: action items in "
        "<code>inbox.yaml</code>, added as <code>suggested</code> and "
        "moved to <code>accepted</code> or <code>dismissed</code> only by "
        "the owner.</p>",
        '<h2 id="i-flags">Definitions changed since last review</h2>',
        _flags_body(flags, tracked),
        _items_body(items),
    ])


# ==========================================================================
# the provider
# ==========================================================================

def provider(tok):
    """(tok) -> [Page]: the single inbox.html page."""
    cfg = config.current()
    tracked = _tracked_pages(tok, cfg)
    review_state = site.load_review_state(cfg)
    flags = site.definition_flags(tracked, review_state)
    items = _load_inbox_items(cfg)
    body = _index_body(flags, tracked, items)
    return [(INDEX_REL, INDEX_TITLE, INDEX_LEDE, list(CRUMBS_INDEX), body)]
