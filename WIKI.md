# WIKI.md — the rulebook for a generated, drift-gated wiki

This file is the law for the wiki that lives beside it. The wiki is generated from
hand-edited prose, a token file and committed sources; every generated statement is
gated so it cannot go stale silently. This document says how to write the prose, how
to draw the diagrams, where each kind of knowledge goes, and which checks must be
green before any change is handed over.

**How to use it.** Point your project's working agreement at this file — Claude Code
inlines imports, so a single line `@wiki/WIKI.md` in that agreement pulls the whole
rulebook into every session. Then fill in the **Bindings** table below once: the
rules here are stated in terms of a handful of named things, and the bindings say
what each one is in this project. A rulebook with empty bindings is advice; with
bindings it is procedure.

Extracted from an earlier project's generated wiki; every rule here was paid for at
least once. Rules read as obvious only after someone paid for them.

---

## Bindings — fill these in per project

| Term | What it means in THIS project |
| --- | --- |
| THE WORKING AGREEMENT | _The file every session reads first (e.g. `CLAUDE.md`). It points at this rulebook with `@wiki/WIKI.md`; it never copies it._ |
| THE DECISIONS DIR | _`wiki.yaml paths.decisions` (default `wiki/decisions/`). The immutable record — one file per decision, rendered exactly as written, forever._ |
| THE QUEUE | _Where engineering tasks live and the only sanctioned way to read/write them (a board, a tracker — never hand-editing its store)._ |
| THE GATE | _How work is accepted as done (e.g. the owner exercises the running project; the task itself says how to verify it)._ |
| THE FLOOR | _The checks that must pass before any handover: `python3 wiki/engine/build.py --check` returns 0, and the four test files run clean — `wiki/engine/tests/test_engine.py`, `wiki/engine/tests/test_packs.py`, `wiki/tests/test_site.py`, `wiki/tests/test_example_pack.py`._ |
| THE OBSERVATION LOOP | _How a diagram is actually LOOKED at: the rasterize recipe in "The observation loop" below (name the rasterizer on this platform — `qlmanage` on macOS, `rsvg-convert` or a headless browser elsewhere)._ |
| THE LESSONS FILE | _Where a correction becomes a written rule for next time. Create it if it is missing._ |
| THE CODE ROOTS | _What `code_map.yaml` maps: each domain directory to the source path prefixes whose change may falsify its prose. A living file — fix a wrong flag in the same change that exposes it._ |
| THE OPERATING PROCEDURE | _A codex-style transferable procedure file the project keeps beside its working agreement, if any. "None" is a valid answer._ |

When a rule here conflicts with a binding or any project instruction, the project
wins — record the exception in THE LESSONS FILE and move on.

---

## Why generated and gated

A hand-written wiki goes stale within a day; a reader cannot tell a true sentence
from one that was true last month. This wiki is built so that going stale is a
**failing build**, not a quiet rot: every derived value — a swatch, a table, a
diagram, an index — is emitted from its source at build time, and `build.py --check`
byte-compares the committed site against a fresh render. The machinery keeps the
derived half honest on its own; the narrative half — why a decision was made, what a
system is for, what should happen next — is yours to keep true.

---

## Structure

- **One directory is one page.** `prose/<nn>-<slug>/` emits `<slug>.html`. The
  numeric prefix `<nn>` is book order — the hub, the rail and the crumbs all follow
  it, and it is *rule-book order* (what a reader needs first comes first), never
  alphabetical.
- **The first file is the page.** Inside a page directory the files sort by name;
  the first file's first line is the page **lede** and its `#` heading is the page
  **title**. Later files in the same directory append in order.
- **Sections vs providers.** A generated block reaches a page one of two ways. A
  **section** is a small renderer registered in `packs/registry.py` under `SECTIONS`
  and dropped into prose by a `{{section:slug}}` line. A **page provider** is a
  callable `tok -> [Page]` listed under `PAGE_PROVIDERS`, which emits whole pages of
  its own (the glossary, the decisions, the config registry are providers).
  `PROVIDER_ORDER` interleaves a provider's pages among the prose domains by number.
- **Sub-pages** come from providers too — a provider that returns several `Page`
  objects gives one domain many rendered pages.
- **The chrome is automatic.** The hub cards, the left rail, the per-page table of
  contents and the breadcrumbs are all generated from the page set and the headings.
  You never hand-write navigation.
- **`RULE_BOOK` must match.** `tests/test_site.py` holds a `RULE_BOOK` list — the
  exact emitted-page order. Add, remove or reorder a page and you edit `RULE_BOOK` in
  the same change, or the suite fails.

---

## Voice

Write every page as a rules book someone runs the project from.

- **Present tense, declarative, no hedging.** State the rule as it is. No "we plan
  to", no "currently", no "should probably".
- **No history in the main flow.** The main flow says what is true now. How it came
  to be true, what it replaced, when it changed — that is provenance.
- **Never a ticket, a class name, a file path or a date in the main flow.** All
  provenance lives in one collapsed `{{notes:begin}}…{{notes:end}}` block, usually at
  page end.
- **Titles are short.** A page `#` is one or two words.
- **Every printed number is a stated fact, and a test asserts it against its
  source.** A number in the main flow ("five stages", "sixty ticks") is a claim; the
  domain's pack-test must assert it against the file it comes from. A cited number
  with no drift test is not polish to add later — it is the page being allowed to
  lie.
- **Most-important-first.** Lead with what the reader acts on; push machinery down
  the page or onto a sub-page.

---

## Directive grammar

Every directive is a marker the generator resolves; unescaped project text around it
is HTML-escaped first, so a directive is the only way to inject anything structural.

- `{{lede:…}}` — the six-to-eight-word subtitle. Required as the first line of every
  page and on every `##` heading. It is gated: outside the word range, or missing on
  a `##`, fails the build. A lede is the section compressed, not a teaser.
- `{{section:slug}}` — places one registered section. A lone line, its own paragraph.
  Each registered slug is placed **exactly once across the whole site**; zero or two
  placements fail the build.
- `{{notes:begin}}` / `{{notes:end}}` — open and close a collapsed engineering-notes
  block. Each is a lone line. They do not nest, must close exactly once, and are
  inert inside a fenced code block.
- `{{token.path}}` — a design value read live from `tokens.yaml`. An ink name renders
  as a swatch plus its hex; a role renders as its resolved hex; a scalar (a size, a
  duration) renders as code; `{{ramp.name[n]}}` renders the n-th stop of a ramp. An
  unknown name fails the build.
- **Images** are referenced by bare filename — `![caption](diagram.png)` resolves
  against `paths.images`. Only a committed image resolves; a missing one fails the
  build.
- `*status: seed|exploring|promoted*` — the status line of an idea card, on the line
  immediately after the card's `##` heading. It owns the lede slot for that heading;
  an unknown status fails the build.
- `<!-- raw-archive -->` — marks a page as a historical document rendered exactly as
  written: no token interpolation, no image validation, no lede gate. Use it only for
  archived material that must not be edited into the present tense.

---

## Diagrams

Prefer a drawn mechanism or a compact table over paragraphs. Reach for them in this
order:

1. **An SVG section pack** — a renderer that returns an SVG fragment.
2. **An ASCII rule box** in a fenced code block, for ordered logic.
3. **A markdown table**, for prices, knobs, catalogs.
4. **Prose**, last, and simplified — short sentences carrying one rule each.

**Inline SVG in prose is impossible.** Prose HTML is escaped before anything else, so
every drawing exists only as a section renderer, placed by `{{section:slug}}`. That
is exactly what lets the build guarantee no colour was typed by hand.

**The pack idiom.** A pack is a Python module under `packs/`:

- A module docstring naming the domain and what each renderer draws.
- `SECTIONS` — a list of 4-tuples `(slug, title, lede, renderer)`. Slugs are unique
  and stable; the lede obeys the 6–8-word gate.
- Every renderer draws with `engine.svg` primitives **only**. Every colour comes from
  a role (or an ink where no role exists) read through `svg`; a hand-typed hex is
  drift the gate catches. Structural geometry — box widths, arc heights — is not a
  token.
- **No `<style>` blocks** (page CSS is the site's) and **no SVG `<marker>`s**
  (arrowheads are explicit `<polygon>` triangles, because a marker needs an id and
  ids on a page belong to the table of contents).
- **Deterministic output** — iterate lists in file order, never a set; fixed-precision
  floats. `--check` byte-compares, so nondeterminism is a red build.

**The pack-test idiom.** Every pack ships a test file that copies
`tests/test_example_pack.py` — change its `PREFIX` and imported `MODULE`. That test
asserts the registry shape, the lede lengths, determinism, that nothing draws
without a required role, that no hand-typed hex leaks, and that prose places every
section exactly once.

**Parse, don't retype.** When a section states code truth — an enum, a transition
table, a catalog — the renderer parses the source, so a rename updates the page or
fails generation. A hand-copied constant is a number waiting to drift.

---

## Linking and vocabulary

- **Link the first mention to its owning page.** The first time a page names a
  concept that lives elsewhere, link it. A dead internal link or anchor fails the
  build.
- **The glossary owns the anchors.** A new or ambiguous term goes in `glossary.yaml`
  with a `home:` anchor (`page.html#anchor`); the auto-linker sends first mentions
  site-wide to that home.
- **Only reference committed files.** Never cite a path under an ignored or untracked
  directory — it is not there for the next reader, and the drift map cannot see it.
- **One atomic change.** Prose, the tokens it names, and the assets it cites are one
  commit. A page that references a token or image that lands in a later commit is a
  broken build in between.

---

## Routing — where each kind of knowledge goes

| Content | Destination |
| --- | --- |
| Current truth of a system | That domain's prose (`prose/<nn>-<slug>/*.md`) |
| An unproven idea, no ruling yet | An ideas-page card: a `##` heading with `*status: seed\|exploring\|promoted*` on the next line |
| A rule that was paid for — a way of working | THE OPERATING PROCEDURE, or THE LESSONS FILE if there is none |
| An owner decision | A file in THE DECISIONS DIR (immutable, rendered read-only) — then update the prose it changes |
| Raw historical material | A page marked `<!-- raw-archive -->` |

---

## Gates — and what trips each

| Gate | What trips it |
| --- | --- |
| Lede count | A page or `##` with no lede, or a lede outside 6–8 words |
| Section placement | An unknown slug, a duplicate placement, or a registered section placed nowhere |
| Internal links | A link or anchor whose target page or heading does not exist |
| Images | An `![…](file)` whose file is not in `paths.images` |
| Tokens | A `{{name}}` that resolves to no ink, role, ramp stop or scalar |
| Notes balance | A `{{notes:begin}}` that never closes, closes twice, or nests |
| Hex leak | A hand-typed `#RRGGBB` in a renderer that is not a known token value |
| Glossary home | A glossary term whose `home:` anchor does not exist on the target page |
| Review-state banner | A page whose title or lede differs from `review_state.yaml` (flags for re-review) |
| `--check` drift | Any committed output byte differs from a fresh render |
| `RULE_BOOK` | The emitted page order differs from the list in `tests/test_site.py` |

---

## Owner-only files

Two files are the owner's alone; a session never edits them as part of ordinary
curation:

- `review_state.yaml` — the reviewed title and lede for every tracked page. When a
  page's title or lede changes, the site banners it for re-review until the owner
  clears it here.
- `inbox.yaml` — action items. Anyone may **add** an item with `status: suggested`;
  only the owner flips a status to `accepted` or `dismissed`.

These are single-user conventions: the owner is the one human reviewer. **The one
exception:** `wiki-init` seeds `review_state.yaml` a single time during bootstrap,
because a fresh wiki has no reviewed baseline yet. After that first seeding it is
owner-only.

---

## The observation loop

A Python gate proves a diagram is well-formed; it cannot prove it reads well. Label
collisions, overflow, a line behind a box — every gate passes and the picture is
still wrong. Pixels are verified by pixels.

A `file://` preview of a generated page is a static snapshot and screenshots blank —
do not debug the page that way. Instead, for each diagram:

1. Extract each `<svg…</svg>` fragment from the generated HTML.
2. Add `xmlns="http://www.w3.org/2000/svg"` and a paper background rect, and write it
   to a scratch file.
3. Rasterize it to PNG — `qlmanage -t -s 1400 -o . file.svg` on macOS;
   `rsvg-convert` or a headless browser elsewhere.
4. Read the PNGs. Look.

**A caveat paid for on this build:** `qlmanage` letterboxes a *wide* SVG into a
*square* thumbnail, padding it with empty space that looks like real emptiness or an
edge that looks clipped. Before trusting an apparent clip, either wrap the SVG in a
minimal HTML file and rasterize the HTML (which preserves the true aspect ratio), or
check the `viewBox` math directly. An apparent edge-clip is often the thumbnailer,
not the drawing.

---

## Lessons — each one line, and why

- **A cited number with no drift test is the page allowed to lie** — nothing stops
  the source from moving out from under it.
- **A remembered rule is not a read rule** — a summary lags its source; until the
  full text is open, assume the strictest plausible reading.
- **The wiki is the contract — read the domain page before the code's legacy
  layers** — the code carries dead paths the page has already ruled out of the
  present.
- **Never source an ignored or untracked directory** — it is invisible to the next
  reader and to the drift map, so a citation into it rots unseen.
- **A diagram every gate passes can still be wrong — look** — the gates check
  well-formedness, not legibility.
- **A drift-map flag is a prompt to verify, not proof** — but skipping a flagged
  domain unread is the same bug as shipping a failing test.

---

## New-page checklist

1. Create `prose/<nn>-<slug>/` and its first file, whose first line is the lede and
   whose `#` is the title. Pick `<nn>` for rule-book position.
2. Add the page to `RULE_BOOK` in `tests/test_site.py`, in its emitted position.
3. If it carries diagrams: write a pack under `packs/`, and a test beside it copied
   from `tests/test_example_pack.py`.
4. Register the pack in `packs/registry.py` (append to `SECTIONS`, add a
   `PROVIDER_ORDER` entry if it is a provider).
5. Add glossary terms for any new vocabulary, with `home:` anchors on the new page.
6. Leave `review_state.yaml` for the owner — the page banners "missing" until they
   seed it. (Only `wiki-init` seeds it, once.)
7. Build: `python3 wiki/engine/build.py`.
8. Run the four test files.
9. Rasterize every diagram and look (the observation loop).
10. Sweep for drift: `python3 wiki/engine/build.py drift` names the domains a change
    set may falsify — re-read each and fix any prose it broke.

---

## Upgrade recipe

The `engine/` directory is the kit; the prose, tokens, packs and config are yours.
To take a newer kit: replace `engine/` wholesale, then run the four test files. If
they pass, the new engine renders your inputs identically; if one fails, it names the
input to adjust. Never fork `engine/` in place — a local edit there is lost on the
next upgrade and invisible to the gates that assume the shipped engine.
