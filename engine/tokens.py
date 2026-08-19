"""tokens.yaml, resolved and validated. Fails loudly rather than guessing.

A role resolves to exactly one ink or one ramp stop; no arithmetic. A ramp named
after an ink must contain that ink's hex verbatim (the same colour named twice is
how palettes drift apart)."""

from __future__ import annotations

import pathlib

from . import minyaml


# ==========================================================================
# model
# ==========================================================================

class Tokens:
    """tokens.yaml, resolved and validated. Fails loudly rather than guessing."""

    def __init__(self, raw: dict):
        self.raw = raw
        self.inks = dict(raw["ink"])
        self.ramps = {k: list(v) for k, v in raw["ramp"].items()}
        self.roles = self._resolve_roles(raw["role"])
        self._validate()

    # -- resolution --------------------------------------------------------

    def _resolve_roles(self, block: dict) -> dict:
        """Each role resolves to exactly one ink or ramp stop. No arithmetic."""
        out = {}
        for name, body in block.items():
            if not isinstance(body, dict):
                raise ValueError(f"role {name!r}: expected a mapping, got {body!r}")
            scope = body.get("scope", "any")
            indicator = bool(body.get("indicator", False))

            if "ink" in body:
                ink = body["ink"]
                if ink not in self.inks:
                    raise ValueError(f"role {name!r} names unknown ink {ink!r}")
                out[name] = Role(name, ink, self.inks[ink], scope, indicator)
            elif "ramp" in body:
                ramp = body["ramp"]
                if ramp not in self.ramps:
                    raise ValueError(f"role {name!r} names unknown ramp {ramp!r}")
                stop = body.get("stop")
                if not isinstance(stop, int):
                    raise ValueError(f"role {name!r}: ramp needs an integer `stop`")
                stops = self.ramps[ramp]
                if not 0 <= stop < len(stops):
                    raise ValueError(
                        f"role {name!r}: stop {stop} out of range for ramp "
                        f"{ramp!r} ({len(stops)} stops)"
                    )
                out[name] = Role(name, f"{ramp}[{stop}]", stops[stop], scope, indicator)
            else:
                raise ValueError(f"role {name!r} binds neither `ink` nor `ramp`")
        return out

    # -- validation --------------------------------------------------------

    def _validate(self) -> None:
        for name, value in self.inks.items():
            _parse_hex(value, f"ink {name!r}")
        for name, stops in self.ramps.items():
            for i, value in enumerate(stops):
                _parse_hex(value, f"ramp {name!r} stop {i}")

        # A ramp named after an ink MUST contain that ink verbatim: the ramps stay
        # hand-picked, so the relationship is asserted rather than computed.
        for ramp_name, stops in self.ramps.items():
            if ramp_name not in self.inks:
                continue                       # no ink of that name -- nothing to check
            base = self.inks[ramp_name]
            if base not in stops:
                raise ValueError(
                    f"ink '{ramp_name}' is {base} but ramp '{ramp_name}' does not "
                    f"contain it ({', '.join(stops)}). An ink and its ramp must "
                    f"agree; update the ramp stop too."
                )

    # -- convenience -------------------------------------------------------

    def section(self, key: str) -> dict:
        return self.raw.get(key, {}) or {}


class Role:
    __slots__ = ("name", "source", "hex", "scope", "indicator")

    def __init__(self, name, source, hex_value, scope, indicator):
        self.name = name
        self.source = source      # ink name, or "ramp[stop]"
        self.hex = hex_value
        self.scope = scope
        self.indicator = indicator


def _parse_hex(value: str, where: str):
    if not isinstance(value, str) or not value.startswith("#") or len(value) != 7:
        raise ValueError(
            f"{where}: expected a quoted '#RRGGBB' string, got {value!r}. "
            f"An unquoted hex is a YAML comment."
        )
    try:
        return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        raise ValueError(f"{where}: {value!r} is not valid hex") from None


def load(path):
    return Tokens(minyaml.parse(pathlib.Path(path).read_text(encoding="utf-8")))
