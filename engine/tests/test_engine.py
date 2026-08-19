#!/usr/bin/env python3
"""Engine gates. Run: python3 engine/tests/test_engine.py  (from the kit root).
Stdlib only. Every check prints PASS/FAIL; exit 1 on any failure."""
from __future__ import annotations
import pathlib, subprocess, sys, tempfile
KIT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT))
from engine import config  # noqa: E402
from engine import tokens as tokens_mod, minyaml  # noqa: E402
from engine import markdown  # noqa: E402
from engine import site  # noqa: E402

config.use(config.load(KIT / "wiki.yaml"))

FAILURES = []

def check(name, fn):
    try:
        fn()
        print(f"  PASS  {name}")
    except AssertionError as exc:
        FAILURES.append(name)
        print(f"  FAIL  {name}: {exc}")

def test_config_loads_defaults_and_resolves_paths():
    cfg = config.load(KIT / "wiki.yaml")
    assert isinstance(cfg.title, str) and cfg.title, cfg.title
    assert cfg.prose_dir == KIT / "prose", cfg.prose_dir
    assert cfg.out_dir == KIT / "site"
    assert cfg.lede_min == 6 and cfg.lede_max == 8 and cfg.require_h2_ledes is True
    assert cfg.fonts == {}

def test_config_missing_key_names_it():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "wiki.yaml"
        p.write_text("site:\n  title: X\n", encoding="utf-8")
        try:
            config.load(p)
        except ValueError as exc:
            assert "site.lede" in str(exc), exc
            return
        raise AssertionError("no ValueError")

def tok():
    return tokens_mod.Tokens(minyaml.parse((KIT / "tokens.yaml").read_text(encoding="utf-8")))

def test_tokens_load_neutral_file():
    t = tok()
    for ink in ("paper", "ink", "accent", "muted", "tint", "highlight", "positive", "deep"):
        assert ink in t.inks, f"missing ink {ink}"
    for role in ("text.primary", "text.reversed", "text.secondary", "surface.card",
                 "surface.band", "contour.line", "action.commit", "action.danger",
                 "state.locked", "ornament.rule"):
        assert role in t.roles, f"missing role {role}"
    assert t.section("spacing") == [4, 8, 12, 16, 24, 32, 48]

def test_ramp_named_after_ink_must_contain_it():
    raw = minyaml.parse((KIT / "tokens.yaml").read_text(encoding="utf-8"))
    raw["ramp"]["accent"] = ["#000000", "#111111"]
    try:
        tokens_mod.Tokens(raw)
    except ValueError as exc:
        assert "accent" in str(exc); return
    raise AssertionError("no ValueError")

def test_no_origin_palette_laws():
    raw = minyaml.parse((KIT / "tokens.yaml").read_text(encoding="utf-8"))
    raw["role"] = {"text.primary": {"ink": "ink"}}
    tokens_mod.Tokens(raw)   # must not raise

def md(text, t=None):
    return markdown.render(text, t or tok(), KIT / "images", source="test.md")

def test_inline():
    html = md("**b** and *i* and `c` and [x](http://y)")
    assert "<strong>b</strong>" in html and "<em>i</em>" in html, html
    assert "<code>c</code>" in html and '<a href="http://y">x</a>' in html, html

def test_escape():
    assert "&lt;script&gt;" in md("<script>")

def test_table():
    html = md("| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<table>" in html and "<th>a</th>" in html and "<td>2</td>" in html, html

def test_lists_and_fence():
    html = md("- one\n- two\n\n1. first\n\n```\nx = 1\n```")
    assert "<ul><li>one</li><li>two</li></ul>" in html.replace("\n", ""), html
    assert "<ol><li>first</li></ol>" in html.replace("\n", ""), html
    assert "<pre><code>x = 1" in html, html

def test_interp_ink_swatch():
    html = md("the {{ink.accent}} heading")
    assert "#7A2E3B" in html and 'class="sw"' in html, html

def test_interp_role_and_scalar_and_rampstop():
    html = md("{{action.commit}} {{type.title.size}} {{motion.quick}} {{ramp.positive[1]}}")
    assert "#1F7A63" in html, html
    assert "<code>26</code>" in html, html
    assert "<code>90</code>" in html, html
    assert "#6FBFA9" in html, html

def test_interp_unknown_fails():
    try:
        md("{{ink.nonexistent}}")
    except ValueError as exc:
        assert "ink.nonexistent" in str(exc); return
    raise AssertionError("no ValueError")

def test_missing_image_fails():
    try:
        md("![x](nope.png)")
    except ValueError as exc:
        assert "nope.png" in str(exc); return
    raise AssertionError("no ValueError")

def test_code_spans_are_inert():
    assert "{{ink.accent}}" in md("`{{ink.accent}}`")

def test_link_target_interpolation_refused():
    try:
        md("[x]({{ink.accent}})")
    except ValueError:
        return
    raise AssertionError("no ValueError")

def test_notes_block_renders_as_a_details_element():
    html = md("para\n\n{{notes:begin}}\nhidden\n{{notes:end}}\n")
    assert '<details class="eng-notes">' in html and "<summary>Engineering notes</summary>" in html, html

def test_unbalanced_notes_markers_name_the_file():
    try:
        md("{{notes:begin}}\nx\n")
    except ValueError as exc:
        assert "test.md" in str(exc); return
    raise AssertionError("no ValueError")

def test_notes_markers_inside_a_fence_stay_literal():
    html = md("```\n{{notes:begin}}\n```\n")
    assert "{{notes:begin}}" in html and "<details" not in html, html

def test_section_lede_renders_under_its_h2():
    html = md("## Alpha\n{{lede:Six words is the shortest legal lede}}\n\nbody")
    assert '<p class="lede section-lede">Six words is the shortest legal lede</p>' in html, html

def test_section_lede_wrong_word_count_names_file_and_heading():
    try:
        md("## Alpha\n{{lede:Too short}}\n\nbody")
    except ValueError as exc:
        assert "test.md" in str(exc) and "Alpha" in str(exc); return
    raise AssertionError("no ValueError")

def test_missing_section_lede_fails_when_required():
    try:
        markdown.render("## Alpha\n\nbody", tok(), KIT / "images", source="t.md", require_ledes=True)
    except ValueError as exc:
        assert "Alpha" in str(exc); return
    raise AssertionError("no ValueError")

def test_idea_card_status_line_exempts_the_lede():
    markdown.render("## Idea\n*status: seed*\n\nbody", tok(), KIT / "images", source="t.md", require_ledes=True)

def test_take_lede_and_title():
    lede, rest = markdown.take_lede("{{lede:Six words is the shortest legal lede}}\n\n# Title\n\nbody", "t.md")
    assert lede == "Six words is the shortest legal lede"
    title, rest2 = markdown.take_title(rest, tok(), "t.md")
    assert title == "Title" and rest2.strip() == "body", (title, rest2)

def test_lede_five_words_fails_with_count():
    try:
        markdown.check_lede("one two three four five", "t.md")
    except ValueError as exc:
        assert "5" in str(exc); return
    raise AssertionError("no ValueError")

def test_split_on_section_directives():
    chunks = markdown.split_on_section_directives("a\n{{section:x}}\nb")
    assert chunks == ["a", "{{section:x}}", "b"], chunks

def test_render_raw_leaves_tokens_literal():
    out = markdown.render_raw("a {{ink.accent}} and [x](y.md)", "t.md")
    assert "{{ink.accent}}" in out and "<code>y.md</code>" in out, out

def _emit_with_prose(tree, sections=None, providers=None, order=None, review_state=None):
    """tree: {"<nn>-<slug>": {"<mm>-name.md": text}} -> [(rel, content)]."""
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "prose").mkdir(); (root / "images").mkdir(); (root / "decisions").mkdir()
        for domain, files in tree.items():
            (root / "prose" / domain).mkdir()
            for name, content in files.items():
                (root / "prose" / domain / name).write_text(content, encoding="utf-8")
        (root / "review_state.yaml").write_text(review_state or "", encoding="utf-8")
        (root / "glossary.yaml").write_text("", encoding="utf-8")
        (root / "wiki.yaml").write_text((KIT / "wiki.yaml").read_text(encoding="utf-8")
                                        .replace("tokens: tokens.yaml", f"tokens: {KIT/'tokens.yaml'}"), encoding="utf-8")
        cfg = config.load(root / "wiki.yaml")
        reg = site.Registry(sections=sections or [], providers=providers or [], order=order or {})
        return site.emit_site(tok(), cfg, reg, glossary_homes={})

LEDE = "{{lede:Six words is the shortest legal lede}}"

def _one_domain(body, slug="5-alpha"):
    return {slug: {"00-a.md": f"{LEDE}\n\n# A\n\n{body}"}}

def _expect_valueerror(fn, *needles):
    try:
        fn()
    except ValueError as exc:
        for n in needles:
            assert n in str(exc), f"error lacks {n!r}: {exc}"
        return
    raise AssertionError(f"no ValueError (wanted {needles})")

def _sec(slug, html="<p>gen</p>"):
    return (slug, slug.title(), "Six words is the shortest legal lede", lambda t: html)

def test_deterministic():
    tree = _one_domain("alpha\n\n{{section:x}}")
    a = _emit_with_prose(tree, sections=[_sec("x")]); b = _emit_with_prose(tree, sections=[_sec("x")])
    assert a == b

def test_emitted_set_order():
    rels = [rel for rel, _ in _emit_with_prose(_one_domain("alpha"))]
    assert rels[:3] == ["wiki.css", "index.html", "alpha.html"], rels

def test_unknown_slug_fails():
    _expect_valueerror(lambda: _emit_with_prose(_one_domain("{{section:nope}}")), "5-alpha/00-a.md", "nope")

def test_placed_twice_names_both_files():
    tree = {"5-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\n{{{{section:x}}}}"},
            "6-beta": {"00-b.md": f"{LEDE}\n\n# B\n\n{{{{section:x}}}}"}}
    _expect_valueerror(lambda: _emit_with_prose(tree, sections=[_sec("x")]), "5-alpha/00-a.md", "6-beta/00-b.md")

def test_never_placed_names_slug():
    _expect_valueerror(lambda: _emit_with_prose(_one_domain("alpha"), sections=[_sec("x")]), "x")

def test_loose_prose_file_fails():
    def go():
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root/"prose").mkdir(); (root/"prose"/"loose.md").write_text("x")
            (root/"images").mkdir(); (root/"decisions").mkdir()
            (root/"review_state.yaml").write_text(""); (root/"glossary.yaml").write_text("")
            (root/"wiki.yaml").write_text((KIT/"wiki.yaml").read_text().replace("tokens: tokens.yaml", f"tokens: {KIT/'tokens.yaml'}"))
            site.emit_site(tok(), config.load(root/"wiki.yaml"), site.Registry([], [], {}), glossary_homes={})
    _expect_valueerror(go, "loose.md")

def test_lede_missing_names_file():
    _expect_valueerror(lambda: _emit_with_prose({"5-alpha": {"00-a.md": "# A\n\nbody"}}), "5-alpha/00-a.md")

def test_lede_nine_words_fails_with_count():
    _expect_valueerror(lambda: _emit_with_prose({"5-alpha": {"00-a.md": "{{lede:one two three four five six seven eight nine}}\n\n# A\n\nbody"}}), "9")

def test_dead_internal_link_names_page_and_target():
    _expect_valueerror(lambda: _emit_with_prose(_one_domain("[x](nope.html)")), "alpha.html", "nope.html")

def test_dead_anchor_names_page_and_target():
    _expect_valueerror(lambda: _emit_with_prose(_one_domain("[x](alpha.html#nope)")), "alpha.html", "#nope")

def test_cross_domain_link_and_anchor_resolve():
    tree = {"5-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\n## Sub\n{LEDE}\n\n[b](beta.html#h-00-b-sub-b)"},
            "6-beta": {"00-b.md": f"{LEDE}\n\n# B\n\n## Sub B\n{LEDE}\n\n[a](alpha.html#h-00-a-sub)"}}
    dict(_emit_with_prose(tree))

def test_every_page_has_rail_lede_and_marks_itself():
    pages = dict(_emit_with_prose({"5-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\nx"}, "6-beta": {"00-b.md": f"{LEDE}\n\n# B\n\ny"}}))
    for rel in ("alpha.html", "beta.html", "index.html"):
        doc = pages[rel]
        assert '<nav class="rail">' in doc and 'class="lede page-lede"' in doc, rel
        assert 'href="wiki.css"' in doc, rel
    assert 'href="alpha.html" aria-current="page"' in pages["alpha.html"]

def test_shared_stylesheet_not_duplicated():
    pages = dict(_emit_with_prose(_one_domain("x")))
    assert "body{" in pages["wiki.css"] and "<style" not in pages["alpha.html"]

def test_hub_cards_carry_title_lede_and_stat():
    hub = dict(_emit_with_prose(_one_domain("## One\n" + LEDE + "\n\nx")))["index.html"]
    assert 'class="hub-card"' in hub and "<h2>A</h2>" in hub and "1 sections" in hub, hub

def _fake_provider(_tok):
    return [("fake.html", "Fake", "Six words is the shortest legal lede", [], "<p>top</p>"),
            ("fake/leaf.html", "Leaf", "Six words is the shortest legal lede", [("fake.html", "Fake")], '<p><a href="fake.html">up</a></p>')]

def test_page_provider_pages_are_shelled_and_depth_shifted():
    pages = dict(_emit_with_prose(_one_domain("x"), providers=[_fake_provider], order={_fake_provider.__module__: 3}))
    leaf = pages["fake/leaf.html"]
    assert 'href="../wiki.css"' in leaf and 'href="../fake.html"' in leaf and 'class="crumbs"' in leaf, leaf

def test_provider_without_a_top_level_page_fails():
    bad = lambda t: [("d/x.html", "X", "Six words is the shortest legal lede", [], "")]
    bad.__name__ = "bad"
    _expect_valueerror(lambda: _emit_with_prose(_one_domain("x"), providers=[bad]), "bad", "top-level")

def test_providers_interleave_with_domains_by_order_key():
    tree = {"2-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\nx"}, "8-beta": {"00-b.md": f"{LEDE}\n\n# B\n\ny"}}
    hub = dict(_emit_with_prose(tree, providers=[_fake_provider], order={_fake_provider.__module__: 5}))["index.html"]
    assert hub.index("alpha.html") < hub.index("fake.html") < hub.index("beta.html"), hub

def test_provider_without_an_order_key_sorts_last():
    tree = {"2-alpha": {"00-a.md": f"{LEDE}\n\n# A\n\nx"}, "8-beta": {"00-b.md": f"{LEDE}\n\n# B\n\ny"}}
    hub = dict(_emit_with_prose(tree, providers=[_fake_provider]))["index.html"]
    assert hub.index("beta.html") < hub.index("fake.html"), hub

def test_review_state_missing_entry_flags_the_page():
    pages = dict(_emit_with_prose(_one_domain("x"), review_state="beta.html:\n  title: B\n  lede: x\n"))
    assert 'class="review-flag"' in pages["alpha.html"]

def test_review_state_matching_entry_does_not_flag():
    rs = "alpha.html:\n  title: A\n  lede: Six words is the shortest legal lede\n"
    pages = dict(_emit_with_prose(_one_domain("x"), review_state=rs))
    assert 'class="review-flag"' not in pages["alpha.html"]

def test_no_hand_typed_hex_leaks():
    import re
    t = tok()
    known = set(t.inks.values()) | {s for stops in t.ramps.values() for s in stops} \
        | {v for v in t.section("state").values() if isinstance(v, str) and v.startswith("#")}
    known_rgba = {site.rgba(h, a) for h in known for a in (round(t.section("ornament")["hairline.alpha"]/100, 2),)}
    for rel, doc in _emit_with_prose(_one_domain("x")):
        for m in re.finditer(r"#[0-9A-Fa-f]{6}\b|rgba?\([^)]*\)", doc):
            lit = m.group(0)
            assert lit in known or lit in known_rgba, f"{rel}: {lit} is not derivable from tokens"

# -- autolinker (pure function; homes are synthetic) --
def test_autolink_first_mention_only_skipping_code_headings_and_self():
    body = "<h2 id=\"x\">token</h2><p>a token and a token <code>token</code></p>"
    out, n = site.autolink_glossary(body, "page.html", {"token": "glossary.html#gl-token"})
    assert n == 1 and out.count('class="gl"') == 1 and "<h2 id=\"x\">token</h2>" in out, out
    out2, n2 = site.autolink_glossary("<p>token</p>", "glossary.html", {"token": "glossary.html#gl-token"})
    assert n2 == 0, out2

def test_autolink_matches_a_plural_and_never_nests_inside_a_link():
    out, n = site.autolink_glossary('<p>tokens <a href="q.html">token</a></p>', "p.html", {"token": "g.html#t"})
    assert n == 1 and out.count("<a") == 2, out

def test_autolink_ignores_attribute_values():
    out, n = site.autolink_glossary('<img alt="token" src="x.png">', "p.html", {"token": "g.html#t"})
    assert n == 0, out

def test_glossary_home_on_unemitted_page_fails():
    def go():
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); (root/"prose"/"5-alpha").mkdir(parents=True)
            (root/"prose"/"5-alpha"/"00-a.md").write_text(f"{LEDE}\n\n# A\n\nx")
            (root/"images").mkdir(); (root/"decisions").mkdir()
            (root/"review_state.yaml").write_text(""); (root/"glossary.yaml").write_text("")
            (root/"wiki.yaml").write_text((KIT/"wiki.yaml").read_text().replace("tokens: tokens.yaml", f"tokens: {KIT/'tokens.yaml'}"))
            site.emit_site(tok(), config.load(root/"wiki.yaml"), site.Registry([], [], {}), glossary_homes={"term": "nowhere.html#x"})
    _expect_valueerror(go, "term", "nowhere.html")

def test_build_check_roundtrip_on_synthetic_site():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        for sub in ("prose/5-alpha", "images", "decisions", "packs"):
            (root/sub).mkdir(parents=True)
        (root/"prose"/"5-alpha"/"00-a.md").write_text(f"{LEDE}\n\n# A\n\nx", encoding="utf-8")
        (root/"packs"/"__init__.py").write_text("")
        (root/"packs"/"registry.py").write_text("SECTIONS=[]\nPAGE_PROVIDERS=[]\nPROVIDER_ORDER={}\n")
        (root/"review_state.yaml").write_text("alpha.html:\n  title: A\n  lede: Six words is the shortest legal lede\n")
        for f in ("glossary.yaml", "inbox.yaml", "config_registry.yaml", "code_map.yaml"):
            (root/f).write_text("")
        (root/"tokens.yaml").write_text((KIT/"tokens.yaml").read_text())
        (root/"wiki.yaml").write_text((KIT/"wiki.yaml").read_text())
        (root/"engine").symlink_to(KIT/"engine")
        r1 = subprocess.run([sys.executable, str(root/"engine"/"build.py")], capture_output=True, text=True)
        assert r1.returncode == 0, r1.stderr + r1.stdout
        r2 = subprocess.run([sys.executable, str(root/"engine"/"build.py"), "--check"], capture_output=True, text=True)
        assert r2.returncode == 0, r2.stdout
        (root/"prose"/"5-alpha"/"00-a.md").write_text(f"{LEDE}\n\n# A\n\ny", encoding="utf-8")
        r3 = subprocess.run([sys.executable, str(root/"engine"/"build.py"), "--check"], capture_output=True, text=True)
        assert r3.returncode == 1 and "STALE" in r3.stdout, r3.stdout
        (root/"prose"/"5-alpha"/"00-a.md").write_text("# A\n\ny", encoding="utf-8")   # no lede -> gate
        r4 = subprocess.run([sys.executable, str(root/"engine"/"build.py")], capture_output=True, text=True)
        assert r4.returncode == 2 and "FAIL" in r4.stderr, r4.stderr


def test_drift_maps_paths_to_domains():
    from engine import drift
    cm = {"1-design-system": ["wiki/tokens.yaml"], "9-about": ["wiki/engine/"]}
    hits = drift.flag(["wiki/engine/site.py", "src/other.py"], cm)
    assert hits == {"9-about": ["wiki/engine/site.py"]}, hits


if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        check(name, fn)
    print(f"\n{len(FAILURES)} failure(s)")
    sys.exit(1 if FAILURES else 0)
