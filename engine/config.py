"""Site configuration: wiki.yaml -> WikiConfig. One object holds every project fact
the engine needs; nothing else in engine/ hardcodes a path or a title.

`current()` returns the config the running build uses. The site emitter calls `use()`
before rendering so section renderers (signature `fn(tok)`) can reach paths without
threading a second argument through every pack."""
from __future__ import annotations
import pathlib
from . import minyaml

_REQUIRED_PATHS = ("prose", "packs_registry", "decisions", "images", "out", "tokens",
                   "glossary", "review_state", "inbox", "config_registry", "code_map")


class WikiConfig:
    def __init__(self, root: pathlib.Path, raw: dict):
        self.root = root
        site = _need(raw, "site", "wiki.yaml")
        self.title = str(_need(site, "title", "site"))
        self.lede = str(_need(site, "lede", "site"))
        paths = _need(raw, "paths", "wiki.yaml")
        for key in _REQUIRED_PATHS:
            setattr(self, f"{key}_path", root / str(_need(paths, key, "paths")))
        self.prose_dir = self.prose_path
        self.decisions_dir = self.decisions_path
        self.images_dir = self.images_path
        self.out_dir = self.out_path
        fonts = raw.get("fonts") or {}
        self.fonts = {str(k): root / str(v) for k, v in fonts.items()}
        ledes = raw.get("ledes") or {}
        self.lede_min = int(ledes.get("min", 6))
        self.lede_max = int(ledes.get("max", 8))
        self.require_h2_ledes = bool(ledes.get("require_h2", True))


def _need(block, key, where):
    if not isinstance(block, dict) or key not in block:
        raise ValueError(f"{where}.{key} is missing from wiki.yaml")
    return block[key]


def load(path) -> WikiConfig:
    path = pathlib.Path(path).resolve()
    return WikiConfig(path.parent, minyaml.parse(path.read_text(encoding="utf-8")))


_CURRENT = None

def use(cfg: WikiConfig) -> None:
    global _CURRENT
    _CURRENT = cfg

def current() -> WikiConfig:
    if _CURRENT is None:
        raise RuntimeError("engine.config.use(cfg) has not been called")
    return _CURRENT
