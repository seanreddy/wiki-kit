"""Change-set to wiki-domain mapping: flag wiki prose domains a code change may falsify.

Maps a change set against `code_map.yaml` and prints, per hit domain, the prose
directory to re-read. A flag is a prompt to verify, not proof of drift.

Usage (via the build driver, from anywhere):
    python3 engine/build.py drift                # working tree vs HEAD, incl. untracked
    python3 engine/build.py drift HEAD~3..HEAD    # a commit range

Stdlib only. Map entries are PATH PREFIXES, not globs.
"""
from __future__ import annotations
import subprocess
from . import minyaml


def flag(changed_paths, code_map) -> dict:
    """Pure: {domain: [changed prefixes matched]} for every domain with a hit.

    `code_map` maps domain -> list of path prefixes. A changed path counts as a
    hit for a domain if it starts with any of that domain's prefixes.
    """
    hits: dict = {}
    for domain, prefixes in code_map.items():
        matched = [p for p in changed_paths if any(p.startswith(prefix) for prefix in prefixes)]
        if matched:
            hits[domain] = matched
    return hits


def _repo_root(start) -> "object":
    cur = start
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    return start


def _git_lines(repo_root, *args: str) -> list:
    out = subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def changed(range_spec, repo_root=None) -> list:
    """The list of changed paths for a git range, or the working tree vs HEAD
    (plus untracked adds) when `range_spec` is falsy."""
    if repo_root is None:
        repo_root = _repo_root_default()
    if range_spec:
        return _git_lines(repo_root, "diff", "--name-only", range_spec)
    tracked = _git_lines(repo_root, "diff", "--name-only", "HEAD")
    untracked = _git_lines(repo_root, "ls-files", "--others", "--exclude-standard")
    return sorted(set(tracked + untracked))


def _repo_root_default():
    import pathlib
    return _repo_root(pathlib.Path.cwd())


def main(cfg, range_spec) -> int:
    repo_root = _repo_root(cfg.root)
    code_map = minyaml.parse(cfg.code_map_path.read_text(encoding="utf-8")) if cfg.code_map_path.exists() else {}
    if not code_map:
        print("drift: no code map entries -- nothing to flag.")
        return 0
    paths = changed(range_spec, repo_root)
    hits = flag(paths, code_map)
    if not hits:
        print(f"drift: {len(paths)} changed file(s), no documented domain touched.")
        return 0
    for domain in sorted(hits):
        matched = hits[domain]
        print(f"{domain}: re-read prose/{domain}/  ({len(matched)} paths)")
    return 0
