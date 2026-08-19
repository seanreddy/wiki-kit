{{lede:How this wiki works, and when you act}}

# About

Every page here is generated. That is not a production detail — it is the reason this
site can be trusted: a hand-written wiki goes stale within a day; this one is built so
that going stale is a **failing build**, not a quiet rot. The machinery keeps the
*derived* half true on its own. The *narrative* half — why a decision was made, what a
system is for, what should happen next — is yours.

## When you are needed

{{lede:Six moments that need a person}}

- **Rationale changes.** Edit the prose under `prose/`, rebuild, commit both together.
- **A definition changes.** Retitle a page or rewrite its lede and the site flags it
  for re-review until you clear it in `review_state.yaml`; flags collect on the
  [inbox](inbox.html).
- **Action items arrive.** Suggested items land on the inbox; only you promote or
  dismiss them, in `inbox.yaml`.
- **An idea strikes.** Park it on the [ideas](ideas.html) page with a status tag.
- **A word turns ambiguous.** Rule on it in `glossary.yaml`; the
  [glossary](glossary.html) reports where the old usage lives.
- **A decision is made.** Record it under `decisions/`; the
  [decisions](decisions.html) page renders it exactly as written, forever.

## How it is built

{{lede:Three hand-edited inputs, one generator, one site}}

Three kinds of hand-edited input exist, and only three: `tokens.yaml` (the design
values), `prose/` (these words — one directory per page, plain markdown), and
committed source and asset files that section packs read where they live. One
command turns those into this site: `python3 wiki/engine/build.py`.

## What maintains itself

{{lede:Every table and diagram is derived}}

Every table, swatch, diagram and index is derived at build time. Change a source
without rebuilding and `build.py --check` turns red. Prose cannot smuggle stale
values either: it names tokens by `{{ink.accent}}`-style interpolation and the
generator resolves them. An unknown name, a dead internal link, a missing cited
image, a lede of the wrong length or an unplaced section fails the build loudly.

## The rules of the page

{{lede:Rules-book voice, ledes, diagrams before paragraphs}}

Pages read like a rules book: present tense, most-important-first, short titles.
Every page and every section opens with a six-to-eight word lede. A drawn mechanism
or a compact table beats paragraphs. Tickets, class names and history live in
collapsed engineering notes, one click away. The full rulebook is `WIKI.md` beside
this wiki's inputs.

## Where it grows next

{{lede:One directory per page, packs for diagrams}}

A new page is a new `prose/<nn>-<slug>/` directory; a diagram is a renderer in a
pack registered in `packs/registry.py`; a test file beside it copies the idiom in
`tests/test_example_pack.py`. The [example](example.html) page is the pattern
library — copy from it, then delete it.
