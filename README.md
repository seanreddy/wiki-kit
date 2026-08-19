# Wiki Kit

A generated, drift-gated wiki you can install into any repository in one command and
grow from a conversation. Stdlib Python, static HTML, no server, no pip.

## Quickstart (TL;DR)

Three steps to a living wiki:

1. **Install it** — one command, from anywhere:

       python3 wiki-kit/init.py /path/to/your/repo --name "Your Project"

   Copies the kit to `your-repo/wiki/`, installs two Claude skills into
   `.claude/skills/`, adds `@wiki/WIKI.md` to your `CLAUDE.md`, builds the seed site,
   and runs the gates. Open `your-repo/wiki/site/index.html` to see it.

2. **Grow it from a conversation** — open your repo in Claude Code and say:

   > *I want to build out a wiki for my project about …*

   That triggers the `wiki-init` skill: it interviews you (what the project is, its
   domains, where truth lives, your vocabulary), then writes the first real pages,
   glossary and decision record from your answers, builds, and hands you the result to
   correct. This is a one-time bootstrap.

3. **Keep it true as you work** — from then on the `wiki-curate` skill is the standing
   rule: any change that touches a documented system updates its prose in the same
   commit. Edit `wiki/prose/…`, then rebuild:

       python3 wiki/engine/build.py

That's it. No server to run, no account, no dependencies to install — the output is
plain HTML you open in a browser or commit and host anywhere.

> **Not using Claude Code?** Step 1 still gives you a working wiki. Steps 2–3 are
> Claude skills, but you can drive the same flow by hand: read `wiki/WIKI.md` (the
> rulebook), write pages under `wiki/prose/<nn>-<slug>/`, and run
> `python3 wiki/engine/build.py`. The gates work the same either way.

## What you get

- `engine/` — the generator. Never edit it; replace it wholesale to upgrade.
- `wiki.yaml` — every project fact: title, paths, fonts, lede bounds.
- `tokens.yaml` — the design tokens the whole site is styled from.
- `prose/` — one directory per page; plain markdown with a few directives.
- `packs/` — your section renderers and the one registry file the engine reads.
- `glossary.yaml`, `review_state.yaml`, `inbox.yaml`, `config_registry.yaml`,
  `code_map.yaml`, `decisions/` — the owner-memory inputs.
- `site/` — the generated output; commit it.
- `WIKI.md` — the rulebook. `skills/` — the two Claude skills.

Seed pages: **About** (how it works), **Design System** (the tokens, drawn live),
**Example** (every diagram idiom once — copy, then delete).

## Commands

    python3 wiki/engine/build.py            # build
    python3 wiki/engine/build.py --check    # drift gate: exit 1 if site is stale
    python3 wiki/engine/build.py drift      # which pages your change may falsify
    python3 wiki/engine/tests/test_engine.py && python3 wiki/engine/tests/test_packs.py
    python3 wiki/tests/test_site.py && python3 wiki/tests/test_example_pack.py

## Origin

Extracted from an earlier project's generated wiki; every rule in `WIKI.md` was paid
for at least once. Nothing here is specific to that project.
