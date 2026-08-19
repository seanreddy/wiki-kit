---
name: wiki-init
description: Use when the owner says "build out a wiki for my (new) project about …", "start the wiki", or "initialize the wiki" in a repo where wiki/ exists (installed by init.py). Runs a brainstorm, then curates a first-pass wiki from the answers — front page, domain pages, glossary, ideas, decision #1, bindings — builds it, checks it, and hands over.
---

# Initializing a Wiki

This is a one-time bootstrap. It runs a structured brainstorm, then curates a
first-pass wiki from the answers, builds it, checks it, and hands the standing
discipline over to `wiki-curate`. Follow the numbered flow in order — do not skip
ahead, and do not write a word of prose before the brainstorm is done.

## 0. Preconditions

- `wiki/wiki.yaml` exists. If it does not, stop and tell the owner: "run
  `python3 <kit>/init.py <repo> --name X` first" — the wiki is not installed yet.
- `python3 wiki/engine/build.py --check` returns 0 on the untouched kit.
- The four test files pass: `wiki/engine/tests/test_engine.py`,
  `wiki/engine/tests/test_packs.py`, `wiki/tests/test_site.py`,
  `wiki/tests/test_example_pack.py`.
- **Read `wiki/WIKI.md` in full before asking the owner anything.** It is the
  rulebook you are about to apply.

## 1. Brainstorm

Invoke the project's brainstorming skill first, then work the fixed question set
below **one question at a time**, offering multiple choice wherever you can so the
owner picks rather than composes. Record every answer; you will distill them into the
bootstrap decision file.

- **(a) The project in one paragraph, plus 3–5 identity facts.** What is it, for
  whom, and the handful of facts that define it (its shape, its constraints, its
  headline numbers).
- **(b) Who reads the wiki, and for what workflows.** The audience and the tasks they
  open it to do.
- **(c) The domains.** Propose a rule-book-ordered list derived from (a) — what a
  reader needs first comes first — and let the owner add, cut and reorder. Each
  domain becomes one page.
- **(d) Where truth lives.** The code roots (source path prefixes per domain), the
  decisions directory (the kit's, or an existing one), the task queue, the test
  runner — and, explicitly, **what THE GATE is** (how work is accepted as done).
- **(e) Vocabulary.** The canonical terms already in use, and the terms to avoid
  (the near-synonyms that cause confusion).
- **(f) What is unproven today.** The ideas and open questions that have no ruling
  yet — these become idea cards, never rules.
- **(g) Diagram idioms.** Walk the Example page's repertoire and ask which idiom the
  owner expects to reach for in each domain — so each domain that needs a drawing
  gets one.

## 2. Curate

Write in this order, and **build after each group** so a gate failure is local and
cheap to place.

1. **Front page** — `prose/0-<slug>/00-<slug>.md`: the lede; `# <Name>`; a pitch
   paragraph; then `## At a glance` with its own lede and a markdown table of the
   identity facts from (a).
2. **One domain page per (c)** — `prose/<nn>-<domain>/00-<domain>.md`: rules-book
   prose distilled from the answers (present tense; `##` sections each with a lede;
   all provenance in a `{{notes}}` block). Where the owner did not state a fact,
   write the gap as a `{{notes}}` question — never invent a fact as a rule.
3. **A pack per domain that named an idiom in (g)** — copy the matching renderer from
   `packs/example_pack.py` into `packs/<domain>_pack.py`, relabel it with the
   domain's real labels, register it in `packs/registry.py`, place it once from the
   domain's prose, and copy `tests/test_example_pack.py` beside it as
   `tests/test_<domain>_pack.py` (change its `PREFIX` and `MODULE`).
4. **`glossary.yaml` from (e)** — each canonical term with its definition, its terms
   to avoid, and a `home:` anchor pointing at a heading on the page just written.
5. **Idea cards from (f)** — appended to `prose/4-ideas/00-ideas.md`, each a `##`
   heading with `*status: seed*` on the next line.
6. **`decisions/<today>-wiki-bootstrap.md`** — distills the brainstorm: the identity
   table, the domain list, the decisions taken, the options rejected, and
   `**Status:** APPROVED`.
7. **`code_map.yaml` from (d)** — each domain directory mapped to its source path
   prefixes.
8. **`WIKI.md` bindings** — fill the bindings table from (d): the working agreement,
   the decisions dir, the queue, the gate, the floor, the observation loop, the
   lessons file, the code roots, the operating procedure.
9. **`RULE_BOOK` in `tests/test_site.py`** — rewrite it to the new emitted-page
   order.
10. **`review_state.yaml`** — seed it for every tracked page (the reviewed title and
    lede). This is the one time seeding it is allowed; after bootstrap it is
    owner-only.
11. **`wiki.yaml`** — set `site.title` and `site.lede` to the project.

## 3. Retire the example

Unless the owner says to keep it as a permanent pattern library: delete
`prose/2-example/`, `packs/example_pack.py` and `tests/test_example_pack.py`; remove
the example's lines from `packs/registry.py`; and drop its term from `glossary.yaml`.
Renumber nothing else.

## 4. Verify

- Build: `python3 wiki/engine/build.py`.
- `python3 wiki/engine/build.py --check` returns 0.
- Run every test file under `wiki/engine/tests/` and `wiki/tests/`.
- Rasterize every SVG on every page and LOOK — the recipe is in `wiki/WIKI.md`,
  including the wide-SVG-in-square-thumbnail caveat. Fix what reads wrong.
- `python3 wiki/engine/build.py drift` — confirm the map flags the right domains.

## 5. Hand over

Report to the owner: the pages written (with their ledes), the terms added, the ideas
parked, the bootstrap decision file, the packs added — and the three things to read
first. State that `wiki-curate` binds from now on: this bootstrap is the only time
`review_state.yaml` is seeded and the only time prose is written ahead of a review
baseline. Commit by explicit file list only if the owner asked for commits.

## Red flags

| Red flag | What to do instead |
| --- | --- |
| Writing prose before the brainstorm is done | Finish the question set first; the answers are the prose |
| Inventing a fact the owner did not state | Mark the gap as a `{{notes}}` question, never as a rule |
| A page with no lede | Every page and every `##` opens with a 6–8 word lede |
| Leaving the Example page registered but unplaced | Retire it fully (step 3), or the section-placement gate fails |
| Editing `engine/` | The engine is the kit; adjust inputs, never the engine |
