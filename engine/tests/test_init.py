#!/usr/bin/env python3
"""init.py installs a working wiki into a fresh repo."""
from __future__ import annotations
import pathlib, subprocess, sys, tempfile
KIT = pathlib.Path(__file__).resolve().parents[2]

def test_init_installs_and_builds():
    with tempfile.TemporaryDirectory() as d:
        target = pathlib.Path(d) / "repo"; target.mkdir()
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        r = subprocess.run([sys.executable, str(KIT / "init.py"), str(target), "--name", "Demo"], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        wiki = target / "wiki"
        assert (wiki / "engine" / "build.py").is_file() and not (wiki / "init.py").exists()
        assert (target / ".claude" / "skills" / "wiki-init" / "SKILL.md").is_file()
        assert (target / ".claude" / "skills" / "wiki-curate" / "SKILL.md").is_file()
        assert "@wiki/WIKI.md" in (target / "CLAUDE.md").read_text()
        assert 'title: "Demo — Wiki"' in (wiki / "wiki.yaml").read_text()
        assert (wiki / "site" / "index.html").is_file()
        chk = subprocess.run([sys.executable, str(wiki / "engine" / "build.py"), "--check"], capture_output=True, text=True)
        assert chk.returncode == 0, chk.stdout
        for t in ("engine/tests/test_engine.py", "engine/tests/test_packs.py", "tests/test_site.py", "tests/test_example_pack.py"):
            tr = subprocess.run([sys.executable, str(wiki / t)], capture_output=True, text=True)
            assert tr.returncode == 0, t + "\n" + tr.stdout
        assert "I want to build out a wiki" in r.stdout

if __name__ == "__main__":
    test_init_installs_and_builds(); print("  PASS  test_init_installs_and_builds")
