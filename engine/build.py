#!/usr/bin/env python3
"""Build the wiki.  Run from anywhere:

    python3 wiki/engine/build.py            # build into paths.out
    python3 wiki/engine/build.py --check    # verify committed output is current; write nothing
    python3 wiki/engine/build.py --out DIR  # redirect the output root (tests)
    python3 wiki/engine/build.py drift [RANGE]   # which pages' prose a change set may falsify

Exit codes: 0 clean, 1 --check found stale output, 2 an input failed a gate.
Determinism is load-bearing: --check byte-compares, so no timestamps, no set iteration."""
from __future__ import annotations
import argparse, pathlib, sys
KIT = pathlib.Path(__file__).absolute().parents[1]
sys.path.insert(0, str(KIT))
from engine import config, minyaml, tokens, site  # noqa: E402


def generate(cfg, out_root, check) -> int:
    tok = tokens.load(cfg.tokens_path)
    stale = []
    for rel, content in site.emit_site(tok, cfg):
        target = out_root / rel
        existing = target.read_text(encoding="utf-8") if target.exists() else None
        if existing == content:
            print(f"  ok       {rel}"); continue
        if check:
            stale.append(rel); print(f"  STALE    {rel}"); continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"  {'wrote' if existing is None else 'updated'}    {rel}")
    if stale:
        print("\nFAIL: generated site does not match its inputs.\n      Run:  python3 engine/build.py", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("verb", nargs="?", default="build", choices=["build", "drift"])
    ap.add_argument("range", nargs="?", default=None, help="git range for drift (default: working tree)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--config", type=pathlib.Path, default=KIT / "wiki.yaml")
    args = ap.parse_args()
    try:
        cfg = config.load(args.config)
        if args.verb == "drift":
            from engine import drift
            return drift.main(cfg, args.range)
        out = args.out or cfg.out_dir
        print(f"{args.config} -> {out}")
        return generate(cfg, out, args.check)
    except (minyaml.MiniYamlError, ValueError, KeyError, IndexError) as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
