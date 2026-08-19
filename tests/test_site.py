#!/usr/bin/env python3
"""Project-side site gates: rule-book order, emitted set, hub cards. Edit RULE_BOOK when
you add, remove or reorder a page — the site must match it exactly."""
from __future__ import annotations
import pathlib, re, sys
KIT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
from engine import config, tokens as tokens_mod, site  # noqa: E402

RULE_BOOK = ["design-system.html", "example.html", "glossary.html", "ideas.html",
             "config.html", "decisions.html", "inbox.html", "about.html"]

FAILURES = []
def check(name, fn):
    try: fn(); print(f"  PASS  {name}")
    except AssertionError as exc: FAILURES.append(name); print(f"  FAIL  {name}: {exc}")

def _site():
    cfg = config.load(KIT / "wiki.yaml")
    return dict(site.emit_site(tokens_mod.load(cfg.tokens_path), cfg))

def test_hub_and_rail_follow_the_rule_book_order():
    pages = _site()
    hub_order = re.findall(r'<a class="hub-card" href="([^"]+)"', pages["index.html"])
    assert hub_order == RULE_BOOK, hub_order
    rail = re.findall(r'<nav class="rail">.*?</nav>', pages["about.html"], re.S)[0]
    rail_order = re.findall(r'href="([^"]+\.html)"', rail)
    assert rail_order == ["index.html"] + RULE_BOOK, rail_order

def test_emitted_set_head():
    rels = [rel for rel, _ in site.emit_site(tokens_mod.load(KIT/"tokens.yaml"), config.load(KIT/"wiki.yaml"))]
    assert rels[:3] == ["wiki.css", "index.html", "design-system.html"], rels[:3]

def test_hub_cards_carry_title_lede_and_stat():
    hub = _site()["index.html"]
    for title in ("Design System", "Example", "Glossary", "Ideas", "About"):
        assert f"<h2>{title}</h2>" in hub, title
    assert re.search(r'class="stat">\d+ (sections|pages)<', hub), hub

if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")): check(name, fn)
    print(f"\n{len(FAILURES)} failure(s)"); sys.exit(1 if FAILURES else 0)
