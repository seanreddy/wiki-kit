---
name: wiki-curate
description: Use when adding or revising a page in the project's generated wiki (wiki/), when a change to code, assets or design falsifies existing wiki prose, or when new knowledge (a truth, an idea, a decision, a term, a lesson) needs a home. The standing curation discipline.
---

# Curating the Wiki

## Overview

The wiki (`wiki/`, built by `wiki/engine/build.py`) is the curated, current,
*readable* synthesis of the project. Generated sections are emitted from code,
tokens and committed assets and cannot lie; the prose around them is yours to keep
true. **Maintaining the wiki is part of DONE for every change that touches a
documented system** — prose that a change falsifies and ships anyway is a failing
test.

Division of labor: the decisions directory is the immutable record — cite it, never
re-litigate it; the working agreement is the standing rules — point at it, never copy
it into a page; the wiki says what is true NOW. The full rulebook is `wiki/WIKI.md`;
this skill is how you apply it.

## The voice: a rules book

Write every page as a rules book someone runs the project from — present tense,
declarative, no hedging, no history in the main flow.

- **The main flow never references a ticket, a class name, a file path or a date.**
  All provenance — identifiers, source names, decision citations, migration
  caveats — lives in one collapsed `{{notes:begin}}…{{notes:end}}` block, usually at
  page end.
- A page `#` heading is a one- or two-word name.
- **Every number printed in the main flow is a stated fact, and a test asserts it
  against its source.** A number with no drift test is not polish to add later — it
  is the page being allowed to lie.
- Most-important-first per page: lead with what the reader acts on, push machinery
  down the page or onto a sub-page.

## Ledes

- The first line of every prose file is `{{lede:Six to eight word page summary}}`.
- Every `##` heading carries its own `{{lede:…}}`, 6–8 words. The one exception is an
  idea card, whose `*status:*` line owns the slot.
- A lede is the section compressed, not a teaser — "Fixed prices, and what refuses a
  step", not "Read on to learn about pricing".

## Diagram-first, and where diagrams live

Prefer a drawn mechanism or a compact table over paragraphs. Reach in this order:

1. **An SVG section pack** — a renderer in `packs/`, placed from prose by
   `{{section:slug}}` (exactly once, site-wide, gated). Inline SVG in prose is
   impossible; prose HTML is escaped, so a drawing exists only through a renderer.
   Every colour and size reads from `tok` through `engine/svg.py` — one hand-typed
   hex fails the hex-leak gate. Output is deterministic: file order, never sets.
2. **An ASCII rule box** in a fenced code block, for ordered logic.
3. **A markdown table**, for prices, knobs, catalogs.
4. **Prose**, last, and simplified — short sentences carrying one rule each.

Parse, don't retype: when a section states code truth (an enum, a transition table, a
catalog), the renderer parses the source so a rename updates the page or fails
generation.

## Link relentlessly

- Link every concept to its owning page on first mention; an internal-link gate
  checks the target page and anchor.
- A new or ambiguous term goes in `glossary.yaml` with a `home:` anchor; the
  auto-linker links first mentions site-wide.
- Only reference committed files; never cite a path under an ignored or untracked
  directory. Prose, the tokens it names, and the assets it cites are one atomic
  change.

## Routing — where each kind of content goes

| Content | Destination |
| --- | --- |
| Current truth of a system | That domain's prose (`prose/<nn>-<slug>/*.md`) |
| An unproven idea, no ruling yet | An ideas-page card: a `##` heading with `*status: seed\|exploring\|promoted*` on the next line |
| A rule that was paid for — a way of working | The project's operating procedure, or its lessons file if there is none |
| An owner decision | A file in the decisions directory (immutable, rendered read-only) — then update the prose it changes |
| Raw historical material | A page marked `<!-- raw-archive -->` |

## Adding a new top-level page — checklist

1. Create `prose/<nn>-<slug>/` with a first file whose first line is the lede and
   whose `#` is the title. `<nn>` is rule-book position, not alphabetical.
2. Add the page to `RULE_BOOK` in `tests/test_site.py`, in its emitted position — the
   hub/rail test fails without it.
3. Diagrams → a new pack under `packs/` plus a test beside it copied from
   `tests/test_example_pack.py`; register the pack in `packs/registry.py` (append to
   `SECTIONS`, add a `PROVIDER_ORDER` entry if it is a provider).
4. Glossary entries for new terms, with `home:` anchors on the new page.
5. Leave `review_state.yaml` for the owner — the page banners "missing" until they
   seed it. Never edit it yourself.

## Verify before done

1. Build: `python3 wiki/engine/build.py`.
2. Run the pack and site gates: every test file under `wiki/engine/tests/` and
   `wiki/tests/`.
3. Confirm no committed output drifted: `python3 wiki/engine/build.py --check`
   returns 0.
4. **Look at diagrams — pixels are verified by pixels.** A `file://` preview
   screenshots blank; instead extract each `<svg…</svg>`, add `xmlns` and a paper
   rect, rasterize (the recipe in `wiki/WIKI.md` — name the rasterizer on this
   platform), and read the PNGs. This catches collisions and overflow that every gate
   passes. Note the wide-SVG-in-square-thumbnail caveat in `WIKI.md` before trusting
   an apparent edge-clip.
5. Sweep prose the change may falsify: `python3 wiki/engine/build.py drift` maps the
   change set against `code_map.yaml` and names the domains to re-read. A flag is a
   prompt to verify, not proof — but skipping a flagged domain unread is the same bug
   as shipping a failing test. Fix a wrong flag in the same change.

## Common mistakes

| Mistake | Reality |
| --- | --- |
| "The page auto-emits, no nav edit needed" | `RULE_BOOK` in `tests/test_site.py` must list it or the suite is red |
| Prose-only page, "diagrams later" | Diagram-first is the paradigm; a concept page ships with its mechanism drawn |
| Inline SVG in prose | Impossible — prose HTML is escaped; use a section pack |
| A ticket or class name in the main flow | Rules-book voice is law; provenance goes in `{{notes:…}}` |
| "Add the number drift test later" | A cited number without a gate is drift waiting to happen — same change |
| Seeding or editing `review_state.yaml` | Owner-only file, always (only `wiki-init` seeds it, once) |
| "Spot-check the page in the browser" | `file://` screenshots blank; use the rasterize-and-look loop |
| Hand-typed hex in a renderer or prose | The hex-leak and token gates fail the suite |
