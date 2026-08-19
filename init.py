#!/usr/bin/env python3
"""Install the wiki kit into a project.

    python3 init.py <target-repo> --name "Project Name" [--dir wiki]

Copies the kit into <target-repo>/<dir>/ (default wiki/), writes the site title,
installs the two skills into <target-repo>/.claude/skills/, adds an @<dir>/WIKI.md
import to <target-repo>/CLAUDE.md (created if absent), builds the site, runs the
gates, and prints the sentence to say to Claude next. Refuses to overwrite an
existing <dir>/."""
from __future__ import annotations
import argparse, pathlib, shutil, subprocess, sys

KIT = pathlib.Path(__file__).resolve().parent
SKIP = {"init.py", "__pycache__", ".DS_Store"}
SKILLS = ("wiki-init", "wiki-curate")


def copy_kit(dest):
    if dest.exists():
        raise SystemExit(f"refusing to overwrite {dest}")
    def ignore(_d, names): return [n for n in names if n in SKIP or n == "skills"]
    shutil.copytree(KIT, dest, ignore=ignore)


def write_title(dest, name):
    p = dest / "wiki.yaml"
    text = p.read_text(encoding="utf-8").replace('title: "Wiki"', f'title: "{name} — Wiki"', 1)
    p.write_text(text, encoding="utf-8")


def install_skills(repo):
    root = repo / ".claude" / "skills"; root.mkdir(parents=True, exist_ok=True)
    for name in SKILLS:
        src, dst = KIT / "skills" / name, root / name
        if dst.exists(): shutil.rmtree(dst)
        shutil.copytree(src, dst)


def point_claude_md(repo, rel):
    p = repo / "CLAUDE.md"; line = f"@{rel}/WIKI.md"
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    if line not in text:
        text = (text.rstrip("\n") + "\n\n" if text else "") + f"# The wiki — rulebook (imported)\n{line}\n"
        p.write_text(text, encoding="utf-8")


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr); raise SystemExit(f"{' '.join(str(c) for c in cmd)} failed ({r.returncode})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", type=pathlib.Path)
    ap.add_argument("--name", required=True)
    ap.add_argument("--dir", default="wiki")
    a = ap.parse_args()
    repo = a.target.resolve(); dest = repo / a.dir
    copy_kit(dest); write_title(dest, a.name); install_skills(repo); point_claude_md(repo, a.dir)
    py = sys.executable
    run([py, str(dest / "engine" / "build.py")], repo)
    for t in ("engine/tests/test_engine.py", "engine/tests/test_packs.py", "tests/test_site.py", "tests/test_example_pack.py"):
        run([py, str(dest / t)], repo)
    print(f"\nInstalled {dest}\n"
          f"Open {dest / 'site' / 'index.html'} to see the seed pages.\n\n"
          f"Now tell Claude:  I want to build out a wiki for my project about ...\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
