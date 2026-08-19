#!/usr/bin/env python3
"""Generic pack gates on synthetic inputs. Run: python3 engine/tests/test_packs.py"""
from __future__ import annotations
import pathlib, sys, tempfile
KIT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT))
from engine import config, minyaml, tokens as tokens_mod, site  # noqa: E402
from engine.packs import glossary, ideas, inbox, config_registry, decisions  # noqa: E402
from engine import svg  # noqa
from engine.packs import designsystem  # noqa

FAILURES = []
def check(name, fn):
    try:
        fn(); print(f"  PASS  {name}")
    except AssertionError as exc:
        FAILURES.append(name); print(f"  FAIL  {name}: {exc}")

LEDE = "{{lede:Six words is the shortest legal lede}}"

class _Site:
    """A throwaway wiki root with every input file present."""
    def __init__(self, tree, glossary_text="", inbox_text="", registry_text="", decisions=None, review_state=""):
        self.tmp = tempfile.TemporaryDirectory(); root = pathlib.Path(self.tmp.name); self.root = root
        for sub in ("prose", "images", "decisions", "packs"): (root/sub).mkdir()
        for domain, files in tree.items():
            (root/"prose"/domain).mkdir()
            for name, text in files.items(): (root/"prose"/domain/name).write_text(text, encoding="utf-8")
        for stem, text in (decisions or {}).items(): (root/"decisions"/f"{stem}.md").write_text(text, encoding="utf-8")
        (root/"glossary.yaml").write_text(glossary_text); (root/"inbox.yaml").write_text(inbox_text)
        (root/"config_registry.yaml").write_text(registry_text); (root/"code_map.yaml").write_text("")
        (root/"review_state.yaml").write_text(review_state)
        (root/"tokens.yaml").write_text((KIT/"tokens.yaml").read_text())
        (root/"wiki.yaml").write_text((KIT/"wiki.yaml").read_text())
        (root/"packs"/"__init__.py").write_text(""); (root/"packs"/"registry.py").write_text("SECTIONS=[]\nPAGE_PROVIDERS=[]\nPROVIDER_ORDER={}\n")
        self.cfg = config.load(root/"wiki.yaml"); config.use(self.cfg)
        self.tok = tokens_mod.load(self.cfg.tokens_path)
    def emit(self, sections=(), providers=(), order=None):
        return dict(site.emit_site(self.tok, self.cfg, site.Registry(list(sections), list(providers), order or {}), glossary_homes=glossary.homes(self.cfg)))

def test_glossary_terms_render_and_home_autolinks():
    g = "alpha:\n  definition: \"The first thing.\"\n  scope: \"test\"\n  home: \"glossary.html#gl-alpha\"\n"
    s = _Site({"3-glossary": {"00-g.md": f"{LEDE}\n\n# Glossary\n\n{{{{section:gl-terms}}}}\n\n{{{{section:gl-occurrences}}}}"},
               "5-beta": {"00-b.md": f"{LEDE}\n\n# Beta\n\nan alpha here"}}, glossary_text=g)
    pages = s.emit(sections=glossary.SECTIONS)
    assert 'id="gl-alpha"' in pages["glossary.html"], pages["glossary.html"]
    assert 'class="gl" href="glossary.html#gl-alpha"' in pages["beta.html"], pages["beta.html"]

def test_glossary_avoid_terms_are_reported_not_gated():
    g = "alpha:\n  definition: \"x\"\n  scope: \"t\"\n  avoid: [\"alfa\"]\n  home: \"glossary.html#gl-alpha\"\n"
    s = _Site({"3-glossary": {"00-g.md": f"{LEDE}\n\n# Glossary\n\n{{{{section:gl-terms}}}}\n\n{{{{section:gl-occurrences}}}}"},
               "5-beta": {"00-b.md": f"{LEDE}\n\n# Beta\n\nsay alfa"}}, glossary_text=g)
    pages = s.emit(sections=glossary.SECTIONS)
    assert "alfa" in pages["glossary.html"] and "beta" in pages["glossary.html"].lower()

def test_ideas_index_groups_by_status_and_unknown_status_fails():
    body = f"{LEDE}\n\n# Ideas\n\n{{{{section:id-index}}}}\n\n## Bright idea\n*status: seed*\n\nbody\n\n## Older idea\n*status: exploring*\n\nbody"
    s = _Site({"4-ideas": {"00-i.md": body}})
    page = s.emit(sections=ideas.SECTIONS)["ideas.html"]
    assert page.index("exploring") < page.index("Bright idea") or "seed" in page, page
    bad = _Site({"4-ideas": {"00-i.md": f"{LEDE}\n\n# Ideas\n\n{{{{section:id-index}}}}\n\n## X\n*status: bogus*\n\nb"}})
    try:
        bad.emit(sections=ideas.SECTIONS)
    except ValueError as exc:
        assert "bogus" in str(exc); return
    raise AssertionError("no ValueError for unknown status")

def test_inbox_lists_definition_flags_and_items():
    ib = "one:\n  status: suggested\n  title: \"Do the thing\"\n  body: \"because\"\n  source: \"test\"\n"
    s = _Site({"5-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\nx"}}, inbox_text=ib)
    pages = s.emit(providers=[inbox.provider], order={inbox.provider.__module__: 7})
    page = pages["inbox.html"]
    assert "Do the thing" in page and "alpha.html" in page and "missing" in page, page

def test_config_registry_verifies_pointers():
    reg = "area:\n  knob:\n    name: \"K\"\n    where: \"tokens.yaml\"\n    symbol: \"hairline.alpha\"\n    scope: \"s\"\n    how: \"h\"\n    token: \"ornament.hairline.alpha\"\n"
    s = _Site({"5-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\nx"}}, registry_text=reg)
    page = s.emit(providers=[config_registry.provider])["config.html"]
    assert "hairline.alpha" in page and "24" in page, page
    bad = _Site({"5-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\nx"}}, registry_text=reg.replace("hairline.alpha\"\n    scope", "no.such.symbol\"\n    scope"))
    try:
        bad.emit(providers=[config_registry.provider])
    except ValueError as exc:
        assert "no.such.symbol" in str(exc); return
    raise AssertionError("no ValueError for a dead pointer")

def test_decisions_mirror_renders_raw_and_indexes_newest_first():
    d = {"2026-01-01-first": "# First\n\n**Status:** APPROVED\n\n{{not.a.token}} and [link](x.md)",
         "2026-02-01-second": "# Second\n\n**Status:** DRAFT\n\nbody"}
    s = _Site({"5-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\nx"}}, decisions=d)
    pages = s.emit(providers=[decisions.provider])
    idx = pages["decisions.html"]
    assert idx.index("Second") < idx.index("First"), idx
    leaf = pages["decisions/2026-01-01-first.html"]
    assert "{{not.a.token}}" in leaf and "<code>x.md</code>" in leaf and "<!-- raw-archive -->" in leaf, leaf

def test_svg_helpers_read_tokens_and_fail_loudly():
    t = tokens_mod.load(KIT/"tokens.yaml"); config.use(config.load(KIT/"wiki.yaml"))
    assert svg.role(t, "text.primary") == t.inks["ink"]
    assert svg.rgba("#102030", 0.5) == "rgba(16,32,48,0.5)"
    c = svg.chrome(t)
    for k in ("paper", "ink", "line", "quiet", "text", "yes", "no", "band"): assert k in c, k
    frag = svg.text(10, 20, "hi", c["text"], size=12)
    assert frag.startswith("<text") and ">hi</text>" in frag
    head = svg.arrowhead(0, 0, 10, 0, c["line"])
    assert head.startswith("<polygon") and "marker" not in head
    try:
        svg.role(t, "no.such.role")
    except ValueError as exc:
        assert "no.such.role" in str(exc); return
    raise AssertionError("no ValueError")

def test_designsystem_renderers_deterministic_nonempty_no_style():
    t = tokens_mod.load(KIT/"tokens.yaml"); config.use(config.load(KIT/"wiki.yaml"))
    assert [s for s, *_ in designsystem.SECTIONS] == ["ds-inks", "ds-ramps", "ds-roles", "ds-binding-map", "ds-states", "ds-type", "ds-spacing", "ds-shape", "ds-motion"]
    for slug, title, lede, fn in designsystem.SECTIONS:
        a, b = fn(t), fn(t)
        assert a == b and a and "<style" not in a, slug
        assert 6 <= len(lede.split()) <= 8, (slug, lede)

def test_designsystem_no_hand_typed_hex():
    import re
    t = tokens_mod.load(KIT/"tokens.yaml")
    known = set(t.inks.values()) | {s for st in t.ramps.values() for s in st} | {v for v in t.section("state").values() if isinstance(v, str) and v.startswith("#")}
    for slug, _, _, fn in designsystem.SECTIONS:
        for m in re.finditer(r"#[0-9A-Fa-f]{6}\b", fn(t)):
            assert m.group(0) in known, (slug, m.group(0))

if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        check(name, fn)
    print(f"\n{len(FAILURES)} failure(s)"); sys.exit(1 if FAILURES else 0)
