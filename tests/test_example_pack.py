#!/usr/bin/env python3
"""The pack-test idiom. Copy this file when you add a pack; change PREFIX and MODULE."""
from __future__ import annotations
import html, pathlib, re, sys
KIT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT))
from engine import config, tokens as tokens_mod, markdown  # noqa: E402
from packs import example_pack as MODULE  # noqa: E402
PREFIX = "ex-"

FAILURES = []
def check(name, fn):
    try: fn(); print(f"  PASS  {name}")
    except AssertionError as exc: FAILURES.append(name); print(f"  FAIL  {name}: {exc}")

config.use(config.load(KIT / "wiki.yaml"))
TOK = tokens_mod.load(KIT / "tokens.yaml")

def test_registry_shape_and_slug_prefix():
    seen = set()
    for entry in MODULE.SECTIONS:
        assert len(entry) == 4, entry
        slug = entry[0]
        assert slug.startswith(PREFIX) and slug not in seen, slug
        seen.add(slug)

def test_every_lede_is_six_to_eight_words_and_escape_safe():
    for slug, title, lede, _ in MODULE.SECTIONS:
        markdown.check_lede(lede, f"SECTIONS[{slug}]")
        assert html.escape(lede) == lede and html.escape(title) == title, slug

def test_renderers_are_deterministic_nonempty_draw_and_never_style():
    for slug, _, _, fn in MODULE.SECTIONS:
        a, b = fn(TOK), fn(TOK)
        assert a == b, slug
        assert a and "<style" not in a, slug
        if slug not in ("ex-rule-box", "ex-decision-table", "ex-imagery"):
            assert "<svg" in a, slug

def test_no_hand_typed_hex_leaks():
    known = set(TOK.inks.values()) | {s for st in TOK.ramps.values() for s in st} \
        | {v for v in TOK.section("state").values() if isinstance(v, str) and v.startswith("#")}
    for slug, _, _, fn in MODULE.SECTIONS:
        for m in re.finditer(r"#[0-9A-Fa-f]{6}\b", fn(TOK)):
            assert m.group(0) in known, (slug, m.group(0))

def test_missing_role_fails_loudly():
    class Stripped:
        def __init__(self, t, gone): self._t, self._gone = t, gone
        @property
        def roles(self): return {k: v for k, v in self._t.roles.items() if k != self._gone}
        @property
        def inks(self): return self._t.inks
        @property
        def ramps(self): return self._t.ramps
        def section(self, k): return self._t.section(k)
    for slug, _, _, fn in MODULE.SECTIONS:
        if slug == "ex-imagery": continue
        try:
            fn(Stripped(TOK, "contour.line"))
        except ValueError as exc:
            assert "contour.line" in str(exc), slug; continue
        raise AssertionError(f"{slug} drew without contour.line")

def test_prose_places_every_section_exactly_once():
    placed = []
    for md in sorted((KIT / "prose" / "2-example").glob("*.md")):
        placed += re.findall(r"^\{\{section:(" + PREFIX + r"[a-z0-9-]+)\}\}$", md.read_text(), re.M)
    registered = [s for s, *_ in MODULE.SECTIONS]
    assert sorted(placed) == sorted(registered), (placed, registered)
    assert len(placed) == len(set(placed)), placed

if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")): check(name, fn)
    print(f"\n{len(FAILURES)} failure(s)"); sys.exit(1 if FAILURES else 0)
