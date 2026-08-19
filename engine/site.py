"""The site: prose domains + page providers -> [(rel, html)], stylesheet first, then hub, then pages.

PAGE COORDINATES. Every page is BUILT with its hrefs and srcs relative to the site
root, whatever depth the page sits at, and shifted exactly once by at_depth() on the
way out. No renderer or provider needs to know how deep its page is, and the link gate
resolves every target against one directory.

Every input problem raises ValueError; the driver turns that into exit 2."""
from __future__ import annotations

import base64
import collections
import html as html_mod
import importlib.util
import os
import pathlib
import re
import string
import sys

from . import config
from . import markdown
from . import minyaml
from .markdown import _esc

# Fonts + CSS live in ONE shared stylesheet rather than inside every page: the
# base64 TTFs (when a project registers any) are the bulk of the bytes and a site
# would otherwise carry one copy per page. Still no server and no network --
# `open index.html` is unchanged.
CSS_REL = "wiki.css"
HUB_REL = "index.html"

# Where a page provider with no PROVIDER_ORDER entry sorts: after every ordered
# domain and provider, in registration order. Only test fakes land here -- a real
# provider that forgets its order key would silently drift to the end of the book,
# which is visible on the hub the moment anyone looks.
UNORDERED_PROVIDER_ORDER = 1000

_DOMAIN_DIR = re.compile(r"^(\d+)-(.+)$")

# Attributes the site links through, and the anchored headings a TOC can reach.
# Both scan EMITTED HTML, where html.escape has turned every prose quote into
# &quot; -- so a literal `"` can only be an attribute delimiter, never content.
_ATTR = re.compile(r'\b(href|src)="([^"]*)"')
_ID_ATTR = re.compile(r'\bid="([^"]+)"')
_H_WITH_ID = re.compile(r'<h([12]) id="([^"]+)">(.*?)</h\1>', re.DOTALL)
_TAG = re.compile(r"<[^>]+>")

# The glossary auto-linker's tag-aware scanner. It walks EMITTED HTML, which
# html.escape has already been over, so a `<` can only open a tag and everything
# between tags is text -- the same guarantee _ATTR relies on. A term is never
# linked inside these elements: a link inside a link is invalid, a term inside code
# or a code sample is a literal, and a heading that grows an <a> stops being a
# plain TOC label.
_TAG_OPEN_OR_CLOSE = re.compile(r"</?\s*([A-Za-z][A-Za-z0-9]*)")
_NO_AUTOLINK_TAGS = frozenset({"a", "code", "pre", "h1", "h2", "h3", "h4"})


# ==========================================================================
# the adopter-owned registry
# ==========================================================================

class Registry:
    """The SECTIONS / PAGE_PROVIDERS / PROVIDER_ORDER a build renders."""

    def __init__(self, sections, providers, order):
        self.sections, self.providers, self.order = list(sections), list(providers), dict(order)


def load_registry(cfg):
    """Exec the adopter's packs/registry.py and read its three lists.

    The registry's own `from engine.packs import ...` / `from packs import ...`
    must resolve, so the wiki root goes on sys.path before it is executed.
    Single-root-per-process: the adopter's intra-`packs` imports are cached by
    sys.modules on first load, so a second root in the same process would reuse
    the first root's modules.
    """
    root = str(cfg.root)
    if root not in sys.path:
        sys.path.insert(0, root)
    spec = importlib.util.spec_from_file_location("packs.registry", cfg.packs_registry_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return Registry(mod.SECTIONS, mod.PAGE_PROVIDERS, mod.PROVIDER_ORDER)


# ==========================================================================
# CSS
# ==========================================================================

def _font_face_css(cfg):
    out = []
    for family, path in cfg.fonts.items():
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        out.append(
            f"@font-face{{font-family:'{family}';"
            f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}"
        )
    return "\n".join(out)


def rgba(hex_value, alpha):
    """An ink at partial alpha, computed from the token rather than typed as a
    second hex -- a hand-typed rgba() is drift the gate cannot see."""
    r, g, b = (int(hex_value[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


# `$name` placeholders, not f-string braces: CSS is mostly braces, and doubling
# every one of them is how a stylesheet becomes unreadable.
_CSS = string.Template("""
*{box-sizing:border-box}
body{margin:0;background:$paper;color:$ink;
  font-family:$f_body,system-ui,-apple-system,sans-serif;
  font-size:${t_body}px;line-height:1.55;
  -webkit-font-smoothing:antialiased}
.wrap{display:flex;align-items:flex-start;gap:${sp32}px;
  max-width:1240px;margin:0 auto;padding:${sp24}px}

aside.side{position:sticky;top:0;flex:0 0 250px;max-height:100vh;overflow-y:auto;
  padding:${sp24}px ${sp16}px ${sp24}px 0;
  border-right:${hair_th}px solid $hairline}
nav.rail{margin-bottom:${sp24}px}
nav.rail .rail-title,nav.toc .toc-title{font-family:$f_display;
  font-size:${t_micro}px;text-transform:uppercase;color:$accent;
  letter-spacing:.06em;margin-bottom:${sp12}px}
nav.rail a,nav.toc a{display:block;color:$ink;text-decoration:none;
  font-size:${t_micro}px;padding:3px 0;border-left:${rule_th}px solid transparent;
  padding-left:${sp8}px}
nav.toc a.lv2{padding-left:${sp16}px;color:$muted}
nav.rail a:hover,nav.toc a:hover{color:$accent;border-left-color:$highlight}
nav.rail a[aria-current]{color:$accent;border-left-color:$highlight;
  background:$tint}

nav.crumbs{font-size:${t_micro}px;color:$muted;margin-top:${sp24}px}
nav.crumbs a{color:$muted}

/* a lede is body face: 6-8 words is a sentence, not a display run */
p.lede{font-family:$f_body;font-size:${t_subtitle}px;line-height:1.35;
  color:$muted;margin:0 0 ${sp16}px;max-width:60ch}
p.page-lede{color:$ink;margin-bottom:${sp24}px}
/* a prose section's own subtitle: quieter than the page lede */
p.lede.section-lede{font-size:${t_label}px;color:$muted;margin:0 0 ${sp12}px}

/* engineering notes: kept but demoted, one click away */
details.eng-notes{background:$tint;border-radius:${c_card}px;
  padding:${sp8}px ${sp16}px;margin:${sp16}px 0;font-size:${t_micro}px}
details.eng-notes summary{font-family:$f_display;font-size:${t_micro}px;
  text-transform:uppercase;letter-spacing:.06em;color:$muted;cursor:pointer}
details.eng-notes[open] summary{margin-bottom:${sp8}px}

/* a link the emitter added, not the author */
a.gl{text-decoration-style:dotted}

/* a page whose title/lede drifted from its review_state.yaml snapshot */
.review-flag{background:$tint;border-left:${rule_th}px solid $accent;
  color:$ink;border-radius:0 ${c_card}px ${c_card}px 0;
  padding:${sp8}px ${sp16}px;margin:0 0 ${sp16}px;font-size:${t_label}px}

.hub-grid{display:grid;gap:${sp16}px;
  grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
a.hub-card{display:block;text-decoration:none;color:$ink;background:$tint;
  border-left:${rule_th}px solid $highlight;
  border-radius:0 ${c_card}px ${c_card}px 0;padding:${sp16}px}
a.hub-card:hover{background:$paper}
a.hub-card h2{margin:0 0 ${sp8}px;font-size:${t_subtitle}px}
a.hub-card .lede{font-size:${t_label}px;margin:0 0 ${sp8}px}
a.hub-card .stat{font-family:$f_display;font-size:${t_micro}px;
  text-transform:uppercase;letter-spacing:.06em;color:$highlight}

main{flex:1 1 auto;min-width:0;max-width:900px}
h1,h2,h3{font-family:$f_display;text-transform:uppercase;
  line-height:1.1;letter-spacing:.01em}
h1{font-size:${t_display}px;color:$ink;margin:${sp32}px 0 ${sp16}px}
h2{font-size:${t_title}px;color:$accent;margin:${sp48}px 0 ${sp12}px}
h3{font-size:${t_subtitle}px;color:$ink;margin:${sp24}px 0 ${sp8}px}
h4{font-size:${t_label}px;text-transform:uppercase;letter-spacing:.08em;
  color:$muted;margin:${sp16}px 0 ${sp4}px}
p{margin:0 0 ${sp12}px}
a{color:$positive}
ul,ol{margin:0 0 ${sp12}px;padding-left:${sp24}px}
li{margin-bottom:${sp4}px}
strong{font-weight:600}
hr{border:0;border-top:${rule_th}px solid $highlight;margin:${sp32}px 0}

code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;
  background:$tint;border-radius:${c_tile}px;padding:1px 5px;white-space:nowrap}
pre{background:$deep;color:$paper;padding:${sp16}px;border-radius:${c_card}px;
  overflow-x:auto;font-size:${t_micro}px;line-height:1.5}
pre code{background:none;color:$paper;padding:0;white-space:pre}

table{border-collapse:collapse;width:100%;margin:${sp16}px 0;
  font-size:${t_label}px}
th,td{text-align:left;padding:6px ${sp12}px;
  border-bottom:${hair_th}px solid $hairline;vertical-align:top}
th{font-family:$f_display;font-size:${t_micro}px;text-transform:uppercase;
  color:$accent;letter-spacing:.04em}

figure{margin:${sp24}px 0}
figure img{display:block;max-width:100%;border-radius:${c_card}px;
  border:${hair_th}px solid $hairline}
figcaption{font-size:${t_micro}px;color:$muted;padding-top:${sp8}px}

section.gen{background:$tint;border-left:${rule_th}px solid $highlight;
  border-radius:0 ${c_card}px ${c_card}px 0;
  padding:${sp8}px ${sp24}px ${sp24}px;margin:${sp24}px 0}
section.gen h2{margin-top:${sp16}px}
.gen-note{font-size:${t_label}px;color:$muted}

.tk{white-space:nowrap}
.sw{display:inline-block;width:.72em;height:.72em;border-radius:2px;
  margin-right:.25em;vertical-align:-.02em;
  border:${hair_th}px solid $hairline}

.swatch-grid{display:grid;gap:${sp12}px;
  grid-template-columns:repeat(auto-fill,minmax(190px,1fr))}
.swatch{background:$paper;border-radius:${c_tile}px;padding:${sp8}px;
  display:flex;flex-direction:column;gap:2px}
.swatch .chip{height:${sp48}px;border-radius:${c_tile}px;
  border:${hair_th}px solid $hairline}
.swatch b{font-family:$f_display;font-size:${t_micro}px;
  text-transform:uppercase;letter-spacing:.03em}
.swatch code{background:none;padding:0;font-size:${t_micro}px}
.swatch .note{font-size:${t_micro}px;color:$muted;white-space:normal}

.ramp-row{display:flex;margin:${sp4}px 0 ${sp16}px;border-radius:${c_tile}px;
  overflow:hidden;border:${hair_th}px solid $hairline}
.ramp-stop{flex:1 1 0;min-height:${sp48}px;padding:${sp4}px;
  font-size:${t_micro}px;font-family:ui-monospace,Menlo,monospace}

.spec-grid{display:grid;gap:${sp12}px;
  grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.spec{background:$paper;border-radius:${c_tile}px;padding:${sp8}px;
  font-size:${t_micro}px}
.spec b{display:block;font-family:$f_display;text-transform:uppercase}

.specimen{background:$paper;border-radius:${c_tile}px;padding:${sp12}px;
  margin-bottom:${sp8}px;overflow:hidden}
.specimen .meta{font-size:${t_micro}px;color:$muted;
  text-transform:none;font-family:$f_body}

.bar{background:$ink;height:${sp12}px;border-radius:2px}
.demo{display:flex;flex-wrap:wrap;gap:${sp24}px;align-items:flex-end;
  margin:${sp16}px 0}
.chip-demo{background:$positive;color:$paper;font-family:$f_display;
  font-size:${t_micro}px;text-transform:uppercase;padding:${sp8}px ${sp16}px}
svg{max-width:100%;height:auto}
dl{margin:${sp12}px 0}
dt{font-family:$f_display;font-size:${t_micro}px;text-transform:uppercase;
  color:$accent;margin-top:${sp8}px}
dd{margin:0 0 0 ${sp16}px;font-size:${t_label}px}

@keyframes ds-slide{from{transform:translateX(0)}to{transform:translateX(${sp32}px)}}
@keyframes ds-fade{from{opacity:.25}to{opacity:1}}
@media (prefers-reduced-motion: reduce){
  *{animation:none !important;transition:none !important}
}
@media (max-width:880px){
  .wrap{flex-direction:column;gap:0}
  aside.side{position:static;flex:1 1 auto;max-height:none;width:100%;
    border-right:0;border-bottom:${hair_th}px solid $hairline}
  main{max-width:none}
}
""")


def _css_family(name, cfg):
    """A CSS font-family value: quote a multi-word name or one the project ships
    a font file for; leave a bare system family or generic keyword unquoted."""
    return f"'{name}'" if (" " in name or name in cfg.fonts) else name


def _page_css(tok, cfg):
    """The page is its own first specimen: it is styled BY the tokens it documents,
    so no colour, size or radius below is typed by hand."""
    ink = tok.inks
    type_block = tok.section("type")
    shape = tok.section("shape")
    orn = tok.section("ornament")

    values = {
        "f_display": _css_family(type_block["face.display"], cfg),
        "f_body": _css_family(type_block["face.body"], cfg),
        "hairline": rgba(ink["ink"], round(orn["hairline.alpha"] / 100, 2)),
        "hair_th": orn["hairline.thickness"],
        "rule_th": orn["rule.thickness"],
        "c_card": shape["corner.card"],
        "c_tile": shape["corner.tile"],
    }
    values.update({name: value for name, value in ink.items()})
    values.update({f"t_{step}": body["size"]
                   for step, body in type_block.items()
                   if isinstance(body, dict)})
    values.update({f"sp{step}": step for step in tok.section("spacing")})
    return _CSS.substitute(values)


# ==========================================================================
# shell: rail, crumbs, TOC, the whole document
# ==========================================================================

def toc_of(body_html):
    """(anchor, already-escaped label, level) for every anchored h1/h2 in a body.

    Derived from the finished HTML rather than tracked alongside it, so a page
    provider's own markup gets a TOC on the same terms as prose does -- there is
    one TOC path, not one per page kind. The label is lifted straight out of the
    heading, so it is escaped exactly once (re-escaping would turn `&amp;` into
    `&amp;amp;` in the sidebar).
    """
    return [
        (m.group(2), _TAG.sub("", m.group(3)).strip(), int(m.group(1)))
        for m in _H_WITH_ID.finditer(body_html)
    ]


def _rail(nav, current_rel):
    """The persistent site rail. The current page is still a link to itself --
    aria-current is what marks it, for the stylesheet and for a screen reader."""
    links = []
    for rel, label in nav:
        mark = ' aria-current="page"' if rel == current_rel else ""
        links.append(f'<a href="{rel}"{mark}>{_esc(label)}</a>')
    return ('<nav class="rail"><div class="rail-title">Wiki</div>'
            + "".join(links) + "</nav>")


def _crumbs(crumbs, title):
    """Ancestors as links, the current page as text. Empty for depth-0 pages:
    a breadcrumb whose only entry is the page itself is noise."""
    if not crumbs:
        return ""
    trail = [f'<a href="{rel}">{_esc(label)}</a>' for rel, label in crumbs]
    trail.append(f"<span>{_esc(title)}</span>")
    return '<nav class="crumbs">' + " › ".join(trail) + "</nav>"


def shell(page, nav, flagged=False):
    """A Page -> a whole document, with hrefs still relative to the site root.

    The h1 and the lede are emitted HERE, once, for every page kind -- which is
    why a domain's own `# h1` is lifted out of its prose body and a page provider
    must not emit one either. `flagged` inserts the review banner directly under
    the lede, on the same terms for every page kind.
    """
    rel, title, lede, crumbs, body = page
    toc = toc_of(body)
    links = "".join(f'<a class="lv{level}" href="#{anchor}">{text}</a>'
                    for anchor, text, level in toc)
    toc_block = ('<nav class="toc"><div class="toc-title">Contents</div>'
                 f"{links}</nav>") if toc else ""
    banner = (f'<div class="review-flag">{_esc(REVIEW_BANNER_TEXT)}</div>\n'
              if flagged else "")
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<title>{_esc(title)}</title>\n"
        f'<link rel="stylesheet" href="{CSS_REL}">\n'
        "</head>\n<body>\n"
        f'<div class="wrap">\n<aside class="side">{_rail(nav, rel)}{toc_block}'
        "</aside>\n"
        f"<main>\n{_crumbs(crumbs, title)}"
        f"<h1>{_esc(title)}</h1>\n"
        f'<p class="lede page-lede">{_esc(lede)}</p>\n'
        f"{banner}"
        f"{body}\n</main>\n</div>\n</body>\n</html>\n"
    )


# ==========================================================================
# site plumbing: depth, links
# ==========================================================================

def depth(rel):
    return rel.count("/")


def _is_site_relative(target):
    """False for anything at_depth must leave alone and the link gate cannot
    resolve: absolute URLs, same-page anchors, root paths, inline data."""
    return bool(target) and not target.startswith(
        ("http://", "https://", "//", "#", "/", "data:", "mailto:"))


def at_depth(doc, page_depth):
    """Shift every site-relative target from site-root coordinates to this page's.

    One pass over the finished document is what lets a citation, a rail link and a
    provider-leaf src all be written once at depth 0 and still resolve from a page
    that sits in a subdirectory.
    """
    if page_depth == 0:
        return doc
    prefix = "../" * page_depth
    return _ATTR.sub(
        lambda m: (f'{m.group(1)}="{prefix}{m.group(2)}"'
                   if _is_site_relative(m.group(2)) else m.group(0)),
        doc,
    )


# ==========================================================================
# glossary auto-linking
# ==========================================================================

def _linkable_spans(html):
    """[(start, end)] of every text run in `html` a term may be linked into.

    A TAG-AWARE walk rather than a regex over the whole document: attribute
    values, tag names and suppressed elements all look like ordinary words to a
    naive pattern, and rewriting one of them would corrupt the page silently.
    The scan is sound because the input is EMITTED html -- html.escape has
    already turned prose `<` into `&lt;`, so every `<` here opens a real tag.

    Everything inside _NO_AUTOLINK_TAGS is skipped, nesting included: the depth
    counter only moves on those tags, so `<a><strong>x</strong></a>` stays
    suppressed for the whole span.
    """
    spans, depth_count, pos = [], 0, 0
    for tag in _TAG.finditer(html):
        if depth_count == 0 and tag.start() > pos:
            spans.append((pos, tag.start()))
        pos = tag.end()
        name = _TAG_OPEN_OR_CLOSE.match(tag.group(0))
        if name is None or name.group(1).lower() not in _NO_AUTOLINK_TAGS:
            continue
        if tag.group(0).startswith("</"):
            depth_count = max(0, depth_count - 1)
        elif not tag.group(0).rstrip().endswith("/>"):
            depth_count += 1
    if depth_count == 0 and pos < len(html):
        spans.append((pos, len(html)))
    return spans


def _term_pattern(term):
    """Whole-word, case-insensitive, and tolerant of a line break inside a
    multi-word term (prose wraps; the rendered text keeps the newline). `s?`
    catches the simple plural and nothing cleverer -- an irregular plural is a
    missed link, which is invisible, where an over-eager stem would be a wrong
    one, which is not."""
    return re.compile(
        r"\b" + r"\s+".join(re.escape(word) for word in term.split()) + r"s?\b",
        re.IGNORECASE)


def autolink_glossary(body, rel, homes):
    """(body, links added) -- link the FIRST plain-text mention of each term.

    Determinism is the whole design: terms are processed in SORTED order, and
    for each the leftmost surviving match wins, so the result cannot depend on
    dict order or on which term happened to be looked at first. Once a term is
    linked its <a> becomes a suppressed span, so a later term mentioned inside
    that link text is simply not linked there -- deterministically.

    A page never links to itself. The home page is where the term is DEFINED,
    so the term's own home section is never auto-linked: the section is on the
    home page, and the home page is skipped whole.

    `homes` values are site-root coordinates, the same coordinates every other
    href in a body is written in, so at_depth shifts them like the rest.
    """
    added = 0
    for term in sorted(homes):
        home = homes[term]
        if home.partition("#")[0] == rel:
            continue
        pattern = _term_pattern(term)
        for start, end in _linkable_spans(body):
            # search(pos, endpos) rather than searching a slice: `\b` is then
            # evaluated against the real neighbouring characters, so a term
            # butted against a tag is still a word boundary and a term
            # straddling the end of the span is correctly NOT a match.
            hit = pattern.search(body, start, end)
            if hit is None:
                continue
            body = (f"{body[:hit.start()]}"
                    f'<a class="gl" href="{html_mod.escape(home, quote=True)}">'
                    f"{hit.group(0)}</a>{body[hit.end():]}")
            added += 1
            break
    return body, added


def _glossary_homes():
    """{term: 'page.html#anchor'} for the auto-linker and the home gate."""
    # glossary auto-linking is optional: no pack -> no auto-links. Checked by
    # spec lookup (not a bare try/except ImportError) so a real error while
    # importing a PRESENT glossary pack still propagates loudly.
    if importlib.util.find_spec(".packs.glossary", __package__) is None:
        return {}
    from .packs import glossary
    return glossary.homes(config.current())


def _check_glossary_homes(homes, emitted, ids_by_page):
    """Every declared home must resolve -- page emitted AND anchor present.

    Checked for EVERY term, not only the ones a page happened to mention: a home
    nobody currently reaches is still a promise glossary.yaml makes, and a
    renamed section must fail here rather than the first time someone writes the
    word.
    """
    for term in sorted(homes):
        page, _, frag = homes[term].partition("#")
        if page not in emitted:
            raise ValueError(
                f"glossary.yaml: term {term!r} declares home "
                f"{homes[term]!r}, but the site emits no page {page!r}")
        if frag not in ids_by_page.get(page, frozenset()):
            raise ValueError(
                f"glossary.yaml: term {term!r} declares home "
                f"{homes[term]!r}, but {page} carries no id {frag!r}")


def _check_links(rel, doc, emitted, ids_by_page, cfg):
    """Link rot fails generation. Targets are checked in site-root coordinates --
    at_depth shifts them by exactly this page's depth afterwards, so resolving
    here and resolving from the page are the same question.

    `ids_by_page` is every emitted page's anchor ids, which is what lets a
    CROSS-page fragment (the shape every glossary home takes) be resolved as
    strictly as a same-page one. It is why the docs are all built before any of
    them is checked.
    """
    for attr, target in _ATTR.findall(doc):
        path, _, frag = target.partition("#")
        if not path:
            if frag not in ids_by_page[rel]:
                raise ValueError(
                    f"{rel}: {attr} {target!r} points at no id on that page")
            continue
        if not _is_site_relative(path):
            continue
        norm = os.path.normpath(path)
        if norm in emitted:
            if frag and frag not in ids_by_page.get(norm, frozenset()):
                raise ValueError(
                    f"{rel}: {attr} {target!r} points at no id on {norm}")
            continue
        # Lexical join, not Path.resolve(): the output directory may not exist yet
        # on a first run or under --out, and a `..` walk through a missing
        # directory does not stat. Joins on `path`, not `target` -- a fragment is
        # never part of a filesystem path, and joining the raw target here would
        # make a committed page with an anchor fail this fallback purely because
        # "#anchor" is not a path segment, even though the file itself is right
        # there. The anchor is not re-checked for a committed-but-not-freshly-
        # emitted file, matching this fallback's job: prove the link doesn't leave
        # the site, not re-derive an old file's anchor set.
        on_disk = pathlib.Path(os.path.normpath(str(cfg.out_dir / path)))
        if on_disk.is_file() and on_disk.is_relative_to(cfg.root):
            continue
        raise ValueError(
            f"{rel}: {attr} target {target!r} resolves to neither an emitted "
            f"page nor a committed file -- the site does not link out of the tree")


# ==========================================================================
# review-state flags: a page whose title/lede no longer matches its owner-
# reviewed snapshot gets a banner, and the same comparison feeds the inbox page.
# ==========================================================================

REVIEW_BANNER_TEXT = (
    "Definition changed since last review — body may need re-reading. "
    "Clear by updating review_state.yaml.")

# The minimal YAML reader rejects '&' '*' '>' '|' anywhere in a line, even inside
# quotes, so a tracked title/lede that needs one of them is stored percent-encoded
# (RFC 3986) in review_state.yaml/inbox.yaml and decoded through here -- the one
# unescape path both files' readers share.
_MINYAML_GAP = {"%26": "&", "%2A": "*", "%3E": ">", "%7C": "|"}


def unescape_minyaml_gap(text):
    for encoded, literal in _MINYAML_GAP.items():
        text = text.replace(encoded, literal)
    return text


ReviewFlag = collections.namedtuple("ReviewFlag", "rel reason")


def load_review_state(cfg):
    """review_state.yaml -> {rel: {"title": str, "lede": str}}.

    A malformed file fails generation naming the file, same as every other
    hand-edited input -- the flag machinery must not go quietly wrong.
    """
    path = cfg.review_state_path
    if not path.is_file():
        raise ValueError(
            f"{path} is missing -- every tracked page needs a reviewed snapshot "
            f"to compare against")
    raw = minyaml.parse(path.read_text(encoding="utf-8"))
    state = {}
    for rel, entry in raw.items():
        if not isinstance(entry, dict) or "title" not in entry or "lede" not in entry:
            raise ValueError(
                f"{path}: entry {rel!r} must be a mapping with 'title' and 'lede'")
        state[rel] = {
            "title": unescape_minyaml_gap(str(entry["title"])),
            "lede": unescape_minyaml_gap(str(entry["lede"])),
        }
    return state


def definition_flags(tracked, review_state):
    """[(rel, title, lede)], {rel: {"title", "lede"}} -> [ReviewFlag], rel-sorted.

    THE ONE comparison implementation: emit_site calls this to decide which pages
    carry the in-page banner, and the inbox pack calls it again with an
    independently-recomputed `tracked` to build the inbox listing -- same function
    underneath, so the banner and the inbox page can never disagree about what
    changed.

    Pure -- no filesystem, no timestamps -- so two calls on equal inputs always
    agree. Three reasons:
      missing -- a tracked page has no review_state.yaml entry at all.
      changed -- the entry exists but the live title or lede no longer matches.
      removed -- review_state.yaml names a page that is not in `tracked` any more
                 (deleted or renamed) -- an inbox flag, not a generation error
                 (no page exists to raise about).
    """
    tracked_rels = set()
    flags = []
    for rel, title, lede in tracked:
        tracked_rels.add(rel)
        entry = review_state.get(rel)
        if entry is None:
            flags.append(ReviewFlag(rel, "missing"))
        elif entry["title"] != title or entry["lede"] != lede:
            flags.append(ReviewFlag(rel, "changed"))
    for rel in review_state:
        if rel not in tracked_rels:
            flags.append(ReviewFlag(rel, "removed"))
    return sorted(flags, key=lambda f: f.rel)


# ==========================================================================
# domains, providers, the one ordered sequence
# ==========================================================================

def domains(cfg):
    """prose/<nn>-<slug>/ -> [(slug, dir)] in <nn> order. One dir, one page."""
    found = []
    for path in sorted(cfg.prose_dir.iterdir()):
        if path.is_file():
            if path.suffix == ".md":
                raise ValueError(
                    f"{path} sits outside a domain directory -- prose lives in "
                    f"<nn>-<slug>/ directories, and a loose file would be a page "
                    f"nothing publishes")
            continue
        if not path.is_dir():
            continue
        m = _DOMAIN_DIR.match(path.name)
        if not m:
            raise ValueError(
                f"{path} is not named <nn>-<slug> -- <nn> is the nav order and "
                f"<slug> is the output filename")
        found.append((int(m.group(1)), m.group(2), path))
    if not found:
        raise ValueError(f"no <nn>-<slug> prose directories in {cfg.prose_dir}")
    # Sorted on the PARSED number, not the string: 10- must follow 9-.
    found.sort(key=lambda entry: (entry[0], entry[1]))
    return [(slug, path) for _n, slug, path in found]


def _domain_order(directory):
    """The <nn> of prose/<nn>-<slug>/ -- this domain's place in the book.

    Re-parsed from the directory name rather than threaded out of domains(),
    whose two-tuple shape is depended on outside this module (the inbox pack
    recomputes the tracked-page list from it).
    """
    return int(_DOMAIN_DIR.match(directory.name).group(1))


def site_sequence(cfg, registry):
    """One ordered rule-book sequence over domains AND providers.

    Yields ("domain", (slug, directory)) / ("provider", provider) in the order
    the hub cards, the nav rail and the tracked-page list all use -- there is one
    sequence, not one per surface. Domains sort by their directory's <nn>,
    providers by PROVIDER_ORDER, and the two interleave.
    """
    entries = [(_domain_order(directory), f"prose/{slug}", "domain", (slug, directory))
               for slug, directory in domains(cfg)]
    for index, provider in enumerate(registry.providers):
        module = getattr(provider, "__module__", "") or ""
        order = registry.order.get(module)
        # Unordered providers keep their registration order behind everything
        # ordered; the index in the tiebreak is what makes that stable.
        key = module if order is not None else f"{index:04d}"
        entries.append((UNORDERED_PROVIDER_ORDER if order is None else order,
                        key, "provider", provider))
    entries.sort(key=lambda entry: (entry[0], entry[1]))
    return [(kind, payload) for _order, _key, kind, payload in entries]


def domain_page(tok, slug, directory, placed, section_map):
    """One prose directory -> (Page, hub stat). `placed` is shared across ALL
    domains: a generated section belongs to exactly one page, site-wide."""
    files = sorted(directory.glob("*.md"))
    if not files:
        raise ValueError(f"{directory} holds no *.md -- a domain directory is a page")
    body_parts, lede, title = [], None, None
    for path in files:
        source = f"{directory.name}/{path.name}"
        text = path.read_text(encoding="utf-8")
        if path == files[0]:
            lede, text = markdown.take_lede(text, source)
            title, text = markdown.take_title(text, tok, source)
        for chunk in markdown.split_on_section_directives(text):
            if chunk.startswith("{{section:"):
                section_slug = chunk[len("{{section:"):-2].strip()
                if section_slug not in section_map:
                    raise ValueError(f"{source}: unknown section {section_slug!r}")
                if section_slug in placed:
                    raise ValueError(
                        f"{source}: section {section_slug!r} already placed in "
                        f"{placed[section_slug]} -- every section appears exactly once"
                    )
                placed[section_slug] = source
                sec_title, sec_lede, fn = section_map[section_slug]
                body_parts.append(
                    f'<section class="gen">'
                    f'<h2 id="s-{section_slug}">{_esc(sec_title)}</h2>'
                    f'<p class="lede">{_esc(sec_lede)}</p>'
                    f"{fn(tok)}</section>")
            else:
                body_parts.append(markdown.render(
                    chunk, tok, config.current().images_dir, source))

    body = "\n".join(body_parts)
    toc = toc_of(body)
    anchors = [anchor for anchor, _text, _level in toc]
    dupes = sorted({a for a in anchors if anchors.count(a) > 1})
    if dupes:
        raise ValueError(
            f"{slug}.html: duplicate page anchors: {', '.join(dupes)} -- two "
            f"headings in one prose file share a title, so the TOC would link to "
            f"only one of them")
    stat = f"{sum(1 for _a, _t, level in toc if level == 2)} sections"
    return (f"{slug}.html", title, lede, [], body), stat


def _hub_body(cards):
    cells = "".join(
        f'<a class="hub-card" href="{rel}"><h2>{_esc(title)}</h2>'
        f'<p class="lede">{_esc(lede)}</p>'
        f'<div class="stat">{_esc(stat)}</div></a>'
        for rel, title, lede, stat in cards
    )
    return f'<div class="hub-grid">{cells}</div>'


def section_map(registry):
    """slug -> (title, lede, renderer). Ledes are checked for EVERY registered
    section, not only the placed ones, so a bad lede cannot hide behind an
    unplaced entry."""
    smap = {}
    for entry in registry.sections:
        if len(entry) != 4:
            raise ValueError(
                f"a registered section entry {entry[0]!r} is not a "
                f"(slug, title, lede, renderer) 4-tuple")
        slug, title, lede, fn = entry
        smap[slug] = (title, markdown.check_lede(lede, f"SECTIONS[{slug!r}]"), fn)
    return smap


def provider_pages(tok, provider):
    """A page provider -> (its pages, its hub-card index page).

    Convention: the provider's FIRST depth-0 page is the one the hub links to.
    Everything deeper is reached from there.
    """
    name = getattr(provider, "__name__", repr(provider))
    pages = list(provider(tok))
    if not pages:
        raise ValueError(f"page provider {name!r} returned no pages")
    for page in pages:
        if len(page) != 5:
            raise ValueError(
                f"page provider {name!r} returned {page!r}, not a "
                f"(rel, title, lede, crumbs, body) 5-tuple")
        rel = page[0]
        if not rel.endswith(".html") or rel.startswith("/") or ".." in rel:
            raise ValueError(
                f"page provider {name!r}: {rel!r} must be a relative *.html path "
                f"under the site root")
    index = next((p for p in pages if depth(p[0]) == 0), None)
    if index is None:
        raise ValueError(
            f"page provider {name!r} returned no top-level page -- its first "
            f"depth-0 page is its hub card")
    return pages, index


# ==========================================================================
# the emitter
# ==========================================================================

def emit_site(tok, cfg, registry=None, glossary_homes=None):
    """The whole site: [(rel, content)], stylesheet first, then hub, then pages.

    Output rels are relative to the site root (`wiki.css`, `index.html`,
    `alpha.html`, `sub/leaf.html`); the driver joins each with the output dir.
    """
    config.use(cfg)
    registry = registry or load_registry(cfg)
    homes = glossary_homes if glossary_homes is not None else _glossary_homes()
    smap = section_map(registry)
    placed = {}
    # Tracked: domain pages and each provider's depth-0 page ONLY -- the same set
    # review_state.yaml snapshots and the inbox pack's index lists. The hub and
    # the provider leaf pages are not tracked.
    pages, cards, nav, tracked = [], [], [(HUB_REL, "Hub")], []

    # ONE pass over ONE sequence: the rail, the hub cards and the tracked set are
    # all built here, in the same rule-book order, so they cannot disagree about
    # where a page sits.
    for kind, payload in site_sequence(cfg, registry):
        if kind == "domain":
            slug, directory = payload
            page, stat = domain_page(tok, slug, directory, placed, smap)
            pages.append(page)
        else:
            provided, page = provider_pages(tok, payload)
            pages.extend(provided)
            stat = f"{len(provided)} pages"
        nav.append((page[0], page[1]))
        cards.append((page[0], page[1], page[2], stat))
        tracked.append((page[0], page[1], page[2]))

    missing = [slug for slug in smap if slug not in placed]
    if missing:
        raise ValueError(
            f"prose places no {{{{section:...}}}} for: {', '.join(missing)} -- "
            f"every generated section must appear exactly once")

    flagged_rels = {f.rel for f in definition_flags(tracked, load_review_state(cfg))
                    if f.reason != "removed"}

    ordered = [(HUB_REL, cfg.title, cfg.lede, [], _hub_body(cards))] + pages
    seen = {CSS_REL}
    for page in ordered:
        if page[0] in seen:
            raise ValueError(f"two site outputs claim {page[0]!r}")
        seen.add(page[0])

    docs = []
    for rel, title, lede, crumbs, body in ordered:
        markdown.check_lede(lede, rel)
        # Raw archives are exempt: the decisions pack renders historical documents
        # AS WRITTEN, and a link their author never typed is an edit.
        if markdown.RAW_ARCHIVE_MARKER not in body:
            body, _added = autolink_glossary(body, rel, homes)
        docs.append((rel, shell((rel, title, lede, crumbs, body), nav,
                                flagged=rel in flagged_rels)))

    # Every page is BUILT before any is CHECKED: a cross-page fragment (every
    # glossary home is one) can only be resolved against the finished set.
    ids_by_page = {rel: frozenset(_ID_ATTR.findall(doc)) for rel, doc in docs}
    _check_glossary_homes(homes, seen, ids_by_page)

    out = [(CSS_REL, f"{_font_face_css(cfg)}\n{_page_css(tok, cfg)}")]
    for rel, doc in docs:
        _check_links(rel, doc, seen, ids_by_page, cfg)
        out.append((rel, at_depth(doc, depth(rel))))
    return out
