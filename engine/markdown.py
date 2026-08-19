"""Prose -> HTML. A deliberately small markdown subset (headings, paragraphs,
bold/italic/code, links, images, tables, bullet/ordered lists, fenced code) plus the
site's directives:

  {{lede:...}}         page/section subtitle, word-count gated
  {{section:slug}}     places one registered generated section (a lone line)
  {{notes:begin}}/{{notes:end}}   a collapsed engineering-notes block
  {{token.path}}       a design-token value: ink swatch, role hex, scalar, ramp stop

Everything is HTML-escaped first; there is no inline HTML and no inline SVG in prose
(diagrams come from section packs). Every input problem raises ValueError naming the
source file."""
from __future__ import annotations

import html as html_mod
import os
import pathlib
import re

from . import config

# ==========================================================================
# constants and directive markers
# ==========================================================================

# A marker line is alone on its own line; a marker inside a fenced block is
# inert, because `blocks` lifts fences out before it looks for one.
_NOTES_BEGIN = "{{notes:begin}}"
_NOTES_END = "{{notes:end}}"
NOTES_SUMMARY = "Engineering notes"

# The historical-document renderer stamps this into every page it renders from
# an archived source. It is used for exactly one decision: the raw-archive path
# renders a document AS WRITTEN, and a link the author never typed is an edit to
# a historical document.
RAW_ARCHIVE_MARKER = "<!-- raw-archive -->"

_INTERP = re.compile(r"\{\{([^{}]+)\}\}")
_RAMP_STOP = re.compile(r"^ramp\.([a-z_]+)\[(\d+)\]$")

_SECTION_LINE = re.compile(r"^\{\{section:([A-Za-z0-9._-]+)\}\}$")
_LEDE_LINE = re.compile(r"^\{\{lede:(.*)\}\}$")
_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
_FENCE = "```"

_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^()\s]+)\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^()\s]+)\)")
_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"\*([^*]+)\*")

_TABLE_RULE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
_BULLET = re.compile(r"^\s*[-*]\s+(.*)$")
_ORDERED = re.compile(r"^\s*\d+\.\s+(.*)$")

# A sentinel pair no prose can contain (both chars are stripped by the escape
# pass, which turns them into nothing at all -- see `protect`).
_MARK_OPEN = "\x00"
_MARK_CLOSE = "\x01"

# Public names for the regexes/consts other modules in the kit will need.
BULLET = _BULLET
ORDERED = _ORDERED
TABLE_RULE = _TABLE_RULE
MARK_OPEN = _MARK_OPEN
MARK_CLOSE = _MARK_CLOSE


def image_prefix(img_dir):
    import os
    return os.path.relpath(img_dir, config.current().out_dir).replace(os.sep, "/")


# ==========================================================================
# token interpolation
# ==========================================================================

def resolve_token(tok, name):
    """{{name}} -> ('hex', '#RRGGBB') | ('value', scalar). ValueError if unknown."""
    name = name.strip()
    m = _RAMP_STOP.match(name)
    if m:
        ramp, stop = m.group(1), int(m.group(2))
        if ramp in tok.ramps and 0 <= stop < len(tok.ramps[ramp]):
            return ("hex", tok.ramps[ramp][stop])
        raise ValueError(f"unknown ramp stop {name!r}")
    if name in tok.roles:
        return ("hex", tok.roles[name].hex)
    # Greedy dotted-path walk over tok.raw: tokens.yaml keys THEMSELVES contain
    # dots (e.g. `face.display`), so a plain split-and-descend cannot find them.
    # At each level take the longest key that matches, then backtrack.
    node = tok.raw
    segs = name.split(".")
    while segs:
        if not isinstance(node, dict):
            raise ValueError(f"unknown token {name!r}")
        for take in range(len(segs), 0, -1):
            key = ".".join(segs[:take])
            if key in node:
                node = node[key]
                segs = segs[take:]
                break
        else:
            raise ValueError(f"unknown token {name!r}")
    if isinstance(node, str) and node.startswith("#"):
        return ("hex", node)
    if isinstance(node, (int, float, str)):
        return ("value", node)
    raise ValueError(f"token {name!r} is a block, not a value")


def _interpolate(text, tok, source):
    """Replace every {{name}} in already-escaped text. Runs LAST so the HTML it
    injects is never re-escaped and never re-scanned for markdown."""
    def sub(m):
        raw = m.group(1)
        try:
            kind, value = resolve_token(tok, raw)
        except ValueError as exc:
            raise ValueError(f"{source}: {exc}") from None
        if kind == "hex":
            return (f'<span class="tk"><span class="sw" style="background:{value}">'
                    f"</span><code>{value}</code></span>")
        return f"<code>{html_mod.escape(str(value))}</code>"
    return _INTERP.sub(sub, text)


def _plain_token(text, tok, source):
    """Same resolution, flattened to bare text -- for TOC entries and alt text,
    where markup would leak into an attribute."""
    def sub(m):
        try:
            _kind, value = resolve_token(tok, m.group(1))
        except ValueError as exc:
            raise ValueError(f"{source}: {exc}") from None
        return str(value)
    return _INTERP.sub(sub, text)


# ==========================================================================
# markdown subset
# ==========================================================================

def _esc(text):
    return html_mod.escape(text)


def _slug(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def heading_id(source, text):
    """Ids are file-scoped so two prose files may both carry an "Overview"
    heading. Two identical h1/h2 texts in ONE file would collide; this raises
    on that rather than emitting a duplicate anchor."""
    return f"h-{_slug(pathlib.Path(source).stem)}-{_slug(text)}"


def _check_notes_balance(blks, source):
    """{{notes:begin}}/{{notes:end}} must nest not at all and close exactly once.

    An unbalanced pair would emit a <details> that swallows the rest of the page
    (or a stray </details> that closes nothing), so it fails generation naming
    the file -- the same stance every other prose directive takes.
    """
    open_count = 0
    for kind, payload in blks:
        if kind != "notes":
            continue
        if payload:
            if open_count:
                raise ValueError(
                    f"{source}: nested {_NOTES_BEGIN} -- engineering-notes blocks "
                    f"do not nest, close the first one before opening another")
            open_count += 1
        else:
            if not open_count:
                raise ValueError(
                    f"{source}: {_NOTES_END} with no {_NOTES_BEGIN} before it")
            open_count -= 1
    if open_count:
        raise ValueError(f"{source}: {_NOTES_BEGIN} is never closed by {_NOTES_END}")


def blocks(text, source=None):
    """('code'|'h'|'md'|'notes', payload) in document order.

    Fenced blocks are lifted out FIRST so their content is never read as
    markdown, and heading lines become their own block so a heading needs no
    blank line around it. A lone {{notes:begin}}/{{notes:end}} line becomes a
    ('notes', True/False) block: it must never reach the interpolation pass,
    which would read `notes:begin` as a token name.

    `source` is the file being rendered, for the error messages -- and OMITTING
    it turns the notes directive off entirely. That is the archive contract, not
    laziness: a raw-archive render renders historical text as written, where a
    marker line is the author's text and not an instruction to this engine.
    """
    lines = text.split("\n")
    out, buf, i = [], [], 0

    def flush():
        chunk = "\n".join(buf).strip("\n")
        del buf[:]
        if chunk.strip():
            out.append(("md", chunk))

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith(_FENCE):
            flush()
            i += 1
            body = []
            while i < len(lines) and not lines[i].strip().startswith(_FENCE):
                body.append(lines[i])
                i += 1
            i += 1                                  # the closing fence
            out.append(("code", "\n".join(body)))
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        if source is not None and line.strip() in (_NOTES_BEGIN, _NOTES_END):
            flush()
            out.append(("notes", line.strip() == _NOTES_BEGIN))
            i += 1
            continue
        m = _HEADING.match(line)
        if m:
            flush()
            out.append(("h", (len(m.group(1)), m.group(2).strip())))
            i += 1
            continue
        buf.append(line)
        i += 1
    flush()
    if source is not None:
        _check_notes_balance(out, source)
    return out


def _attach_section_ledes(blks, source, require):
    """Lift each `##`-section's {{lede:...}} out of the body flow.

    The directive sits on the line after the heading, with or without a blank
    line between, so it is either the whole of the next md block or its first
    line -- both shapes land here as one ('lede', text) block placed directly
    after its heading. It never reaches the markdown or interpolation passes:
    left in place, `lede:...` would resolve as a token name, and the text would
    join the paragraph flow and the section's TOC entry.

    Word count is checked WHENEVER a lede is present, naming the file and the
    heading. Whether an ABSENT one is an error is `require`.
    """
    out = []
    for kind, payload in blks:
        if kind != "md":
            out.append((kind, payload))
            continue
        lines = payload.split("\n")
        after_h2 = bool(out) and out[-1][0] == "h" and out[-1][1][0] == 2
        first = _LEDE_LINE.match(lines[0].strip())
        if first and after_h2:
            heading = out[-1][1][1]
            out.append(("lede", check_lede(
                first.group(1), f"{source}: section {heading!r}")))
            rest = "\n".join(lines[1:]).strip("\n")
            if rest.strip():
                out.append(("md", rest))
            continue
        for line in lines:
            if _LEDE_LINE.match(line.strip()):
                raise ValueError(
                    f"{source}: {{{{lede:...}}}} must be the first line after a "
                    f"`##` heading (found {line.strip()[:48]!r} elsewhere) -- a "
                    f"page's own lede is lifted before rendering, and an h3 or a "
                    f"paragraph carries no lede")
        out.append((kind, payload))

    if require:
        cfg = config.current()
        for index, (kind, payload) in enumerate(out):
            if kind != "h" or payload[0] != 2:
                continue
            following = out[index + 1] if index + 1 < len(out) else None
            if following is not None and following[0] == "md" and \
                    following[1].lstrip().startswith("*status:"):
                # An `##` whose next line is a `*status: ...*` marker is a status
                # card, not a prose section -- the status line owns the
                # first-line slot, and the card's tl;dr is its title. Exempt.
                continue
            if following is None or following[0] != "lede":
                raise ValueError(
                    f"{source}: section `## {payload[1]}` declares no "
                    f"{{{{lede:...}}}} -- every prose section opens with a "
                    f"{cfg.lede_min}-{cfg.lede_max} word lede")
    return out


def _flatten(raw, tok, source):
    """Heading markdown -> bare text, for a page title or an id."""
    flat = _plain_token(raw, tok, source)
    flat = _IMAGE.sub(r"\1", flat)
    flat = _LINK.sub(r"\1", flat)
    return flat.replace("**", "").replace("*", "").replace("`", "")


def _heading_ids(text, source):
    """Anchor ids for the h1/h2 headings, in document order."""
    return [heading_id(source, raw)
            for kind, (level, raw) in ((k, p) for k, p in blocks(text, source)
                                       if k == "h")
            if level <= 2]


def protect(text, store):
    """Stash inline-code spans so the emphasis pass cannot read the asterisks
    inside them."""
    def sub(m):
        store.append(f"<code>{m.group(1)}</code>")
        return f"{_MARK_OPEN}{len(store) - 1}{_MARK_CLOSE}"
    return _CODE.sub(sub, text)


def restore(text, store):
    return re.sub(
        f"{_MARK_OPEN}(\\d+){_MARK_CLOSE}",
        lambda m: store[int(m.group(1))],
        text,
    )


def _figure(caption, filename, tok, img_dir, source):
    target = (img_dir / filename).resolve()
    # exists() alone would accept `../../anything` -- citations are bare
    # filenames INSIDE the imagery directory, nothing else.
    if not target.exists() or not target.is_relative_to(img_dir.resolve()):
        raise ValueError(
            f"{source}: cited image {filename!r} is not in {img_dir.name}/ -- "
            f"the page may only cite files that exist there"
        )
    alt = _plain_token(caption, tok, source)
    # The src is computed from the configured images/output directories rather
    # than spelled out, so the directory that is VALIDATED and the directory
    # that is LINKED cannot drift apart.
    src = f"{image_prefix(img_dir)}/{filename}"
    body = f'<figure><img src="{src}" alt="{alt}">'
    if caption.strip():
        body += f"<figcaption>{_inline(caption, tok, img_dir, source)}</figcaption>"
    return body + "</figure>"


def _inline(text, tok, img_dir, source):
    """Escaped text -> inline HTML. Images first (an image is a link with a
    bang), then links, then emphasis, then interpolation."""
    store = []
    text = protect(text, store)
    def _target(m):
        # A {{token}} in a link/image target would be interpolated into HTML
        # inside an attribute, terminating it early with no error. Refuse.
        if "{{" in m.group(2):
            raise ValueError(
                f"{source}: link/image target {m.group(2)!r} contains '{{{{' -- "
                f"targets must be literal paths or anchors"
            )
        return m.group(2)

    text = _IMAGE.sub(
        lambda m: _figure(m.group(1), _target(m), tok, img_dir, source), text)
    text = _LINK.sub(lambda m: f'<a href="{_target(m)}">{m.group(1)}</a>', text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    # Interpolate BEFORE restoring protected code spans, so `{{...}}` inside
    # backticks stays literal -- the same inertness fenced blocks already have,
    # and the only way the syntax itself can be documented on the page.
    text = _interpolate(text, tok, source)
    return restore(text, store)


def _render_table(lines, tok, img_dir, source):
    def cells(line):
        return [c.strip() for c in line.strip().strip("|").split("|")]

    head = cells(lines[0])
    rows = [cells(line) for line in lines[2:] if line.strip()]
    out = ["<table><thead><tr>"]
    for cell in head:
        out.append(f"<th>{_inline(cell, tok, img_dir, source)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_inline(cell, tok, img_dir, source)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _render_md_block(chunk, tok, img_dir, source):
    lines = chunk.split("\n")
    if len(lines) >= 2 and "|" in lines[0] and _TABLE_RULE.match(lines[1]):
        return _render_table(lines, tok, img_dir, source)

    bullets = [_BULLET.match(line) for line in lines]
    if all(bullets):
        items = "".join(
            f"<li>{_inline(m.group(1), tok, img_dir, source)}</li>" for m in bullets)
        return f"<ul>{items}</ul>"

    ordered = [_ORDERED.match(line) for line in lines]
    if all(ordered):
        items = "".join(
            f"<li>{_inline(m.group(1), tok, img_dir, source)}</li>" for m in ordered)
        return f"<ol>{items}</ol>"

    body = _inline("\n".join(lines), tok, img_dir, source)
    # A citation on its own line is a figure, and a figure inside <p> is invalid.
    if body.startswith("<figure>") and body.endswith("</figure>"):
        return body
    return f"<p>{body}</p>"


def render(text, tok, img_dir, source, require_ledes=None):
    """The markdown subset -> HTML. Raises ValueError for unknown tokens or
    missing cited images (message includes `source`).

    `require_ledes` defaults to the site's own configured policy
    (`config.current().require_h2_ledes`) when not given explicitly -- callers
    that render text which is not domain prose may pass `False` outright.
    """
    if require_ledes is None:
        require_ledes = config.current().require_h2_ledes
    ids = _heading_ids(text, source)
    out = []
    for kind, payload in _attach_section_ledes(
            blocks(text, source), source, require_ledes):
        if kind == "code":
            out.append(f"<pre><code>{_esc(payload)}</code></pre>")
            continue
        if kind == "notes":
            out.append(f'<details class="eng-notes"><summary>'
                       f"{_esc(NOTES_SUMMARY)}</summary>" if payload
                       else "</details>")
            continue
        if kind == "lede":
            # Emitted AFTER the </h2>, so the heading text -- and therefore the
            # TOC label lifted from it -- is untouched.
            out.append(f'<p class="lede section-lede">{_esc(payload)}</p>')
            continue
        if kind == "h":
            level, raw = payload
            attr = ""
            if level <= 2:
                attr = f' id="{ids.pop(0)}"'
            out.append(f"<h{level}{attr}>"
                       f"{_inline(_esc(raw), tok, img_dir, source)}</h{level}>")
            continue
        out.append(_render_md_block(_esc(payload), tok, img_dir, source))
    return "\n".join(out)


# ==========================================================================
# raw-archive rendering (no interpolation, no image validation, no lede gate)
# ==========================================================================

def _raw_stash(store, html):
    """Park finished HTML behind a mark so the bold/italic passes that still
    have to run cannot reach back into it -- the same guard `protect` gives
    code spans."""
    store.append(html)
    return f"{_MARK_OPEN}{len(store) - 1}{_MARK_CLOSE}"


def _raw_dead_ref(store, label, target):
    """A historical document's own relative reference -> plain code, never
    <a> and never <img>.

    The label is kept when it says something the path does not, so the
    archived sentence still reads as written; the path is what the reader
    needs to go find the thing themselves.
    """
    label, target = label.strip(), target.strip()
    if not label or label == target:
        return _raw_stash(store, f"<code>{target}</code>")
    return f"{label} ({_raw_stash(store, f'<code>{target}</code>')})"


def _raw_link(store, label, target):
    # Only real outbound URLs stay links. Everything else is a repo-relative
    # path a live site would (correctly) refuse to resolve.
    if target.startswith(("http://", "https://")):
        return _raw_stash(store, f'<a href="{target}">{label}</a>')
    return _raw_dead_ref(store, label, target)


def _raw_inline(text):
    """Already-escaped text -> inline HTML, with no interpolation pass at all.

    Order mirrors `_inline` (images before links -- an image is a link with a
    bang) so the two paths disagree about nothing except the features an
    archive must not have: token interpolation, image validation, and live
    non-http links.
    """
    store = []
    text = protect(text, store)
    text = _IMAGE.sub(lambda m: _raw_dead_ref(store, m.group(1), m.group(2)), text)
    text = _LINK.sub(lambda m: _raw_link(store, m.group(1), m.group(2)), text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    return restore(text, store)


def _raw_table(lines):
    def cells(line):
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    out = ["<table><thead><tr>"]
    for cell in cells(lines[0]):
        out.append(f"<th>{_raw_inline(cell)}</th>")
    out.append("</tr></thead><tbody>")
    for line in lines[2:]:
        if not line.strip():
            continue
        out.append("<tr>")
        for cell in cells(line):
            out.append(f"<td>{_raw_inline(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _raw_block(chunk):
    """One already-escaped markdown chunk -> a block element.

    No figure branch (raw mode emits no figures) and no source argument (raw
    mode raises for nothing a chunk can contain), which is the whole
    difference from `_render_md_block`.
    """
    lines = chunk.split("\n")
    if len(lines) >= 2 and "|" in lines[0] and _TABLE_RULE.match(lines[1]):
        return _raw_table(lines)

    bullets = [_BULLET.match(line) for line in lines]
    if all(bullets):
        items = "".join(f"<li>{_raw_inline(m.group(1))}</li>" for m in bullets)
        return f"<ul>{items}</ul>"

    ordered = [_ORDERED.match(line) for line in lines]
    if all(ordered):
        items = "".join(f"<li>{_raw_inline(m.group(1))}</li>" for m in ordered)
        return f"<ol>{items}</ol>"

    return f"<p>{_raw_inline(chunk)}</p>"


def _raw_plain_heading(raw):
    """Heading markdown -> bare text, for a raw page's title or anchor id.

    `_flatten` cannot be reused: it resolves {{tokens}} on the way through,
    which is exactly what raw mode must not do. A literal {{...}} in a title
    stays literal here and is escaped by the shell.
    """
    flat = _IMAGE.sub(r"\1", raw)
    flat = _LINK.sub(r"\1", flat)
    return flat.replace("**", "").replace("*", "").replace("`", "").strip()


def _raw_anchor_ids(text, source):
    """Anchor ids for h1/h2 in document order, de-duplicated.

    Prose gets a hard error on two identical headings in one file; an archive
    cannot -- the document is already written. Repeats are suffixed instead,
    so the page TOC still reaches every heading.
    """
    seen, ids = {}, []
    for kind, payload in blocks(text):
        if kind != "h":
            continue
        level, raw = payload
        if level > 2:
            continue
        base = heading_id(source, _raw_plain_heading(raw))
        seen[base] = seen.get(base, 0) + 1
        ids.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    return ids


def render_raw(text, source):
    """A historical document's markdown -> HTML, as written. Raises for
    nothing: an archive cannot be made to satisfy today's gates, only
    rendered honestly. No {{}} interpolation, no image-existence check, no
    lede requirement."""
    ids = _raw_anchor_ids(text, source)
    out = []
    for kind, payload in blocks(text):
        if kind == "code":
            out.append(f"<pre><code>{_esc(payload)}</code></pre>")
            continue
        if kind == "h":
            level, raw = payload
            attr = f' id="{ids.pop(0)}"' if level <= 2 else ""
            out.append(f"<h{level}{attr}>{_raw_inline(_esc(raw))}</h{level}>")
            continue
        out.append(_raw_block(_esc(payload)))
    return "\n".join(out)


# ==========================================================================
# lede and title extraction
# ==========================================================================

def check_lede(text, where):
    cfg = config.current()
    words = text.split()
    if not cfg.lede_min <= len(words) <= cfg.lede_max:
        raise ValueError(
            f"{where}: lede is {len(words)} words, must be {cfg.lede_min}-"
            f"{cfg.lede_max} ({text.strip()!r})")
    return " ".join(words)


def take_lede(text, source):
    """Lift the {{lede:...}} directive off the top of a page's first file.

    Removed from the prose before rendering: the shell emits it under the h1
    and reuses it as the hub card subtitle, and left in place the generic
    interpolation pass would read `lede:...` as a token name.
    """
    cfg = config.current()
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        m = _LEDE_LINE.match(line.strip())
        if not m:
            raise ValueError(
                f"{source}: first non-blank line must be {{{{lede:...}}}} "
                f"(found {line.strip()[:48]!r}) -- a page opens with a "
                f"{cfg.lede_min}-{cfg.lede_max} word lede")
        del lines[i]
        return check_lede(m.group(1), source), "\n".join(lines)
    raise ValueError(f"{source}: file is empty -- it carries the page's lede")


def take_title(text, tok, source):
    """Lift the page's `# h1` off the top; the shell emits it as the page title."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        m = _HEADING.match(line)
        if not m or len(m.group(1)) != 1:
            raise ValueError(
                f"{source}: the lede must be followed by an `# h1` -- it names "
                f"the page in the rail, the hub card and the title bar "
                f"(found {line.strip()[:48]!r})")
        del lines[i]
        return _flatten(m.group(2).strip(), tok, source), "\n".join(lines)
    raise ValueError(f"{source}: file has no `# h1` -- it names the page")


# ==========================================================================
# section directives
# ==========================================================================

def split_on_section_directives(text):
    """Prose text -> chunks, where a lone {{section:slug}} line is its own chunk.

    A directive inside a fenced block would also split -- documenting a
    directive verbatim is not something the prose needs to do, and the
    alternative is a second fence scanner here.
    """
    chunks, buf = [], []
    for line in text.split("\n"):
        if _SECTION_LINE.match(line.strip()):
            if buf:
                chunks.append("\n".join(buf))
                buf = []
            chunks.append(line.strip())
        else:
            buf.append(line)
    if buf:
        chunks.append("\n".join(buf))
    return [chunk for chunk in chunks if chunk.strip()]
