"""A deliberately small YAML reader for the engine's configuration files.

WHY THIS EXISTS INSTEAD OF `import yaml`
----------------------------------------
The engine must run anywhere with the standard library alone -- no PyYAML or
other third-party dependency. Config and content files are flat documents, so
the subset below is enough and costs one small file.

SUPPORTED SUBSET
----------------
  * nested block mappings, indentation-delimited
  * block sequences of scalars      (- a / - b)
  * flow sequences of scalars       ([a, b, c])
  * flow mappings of scalars        ({k: v, k2: v2})
  * scalars: single/double-quoted strings, ints, floats, true/false/null
  * `#` comments, at line start or preceded by whitespace

NOT SUPPORTED (raises MiniYamlError rather than guessing)
---------------------------------------------------------
  * anchors/aliases, tags, multi-line scalars, sequences of mappings,
    nested flow collections, tabs for indentation

THE HEX TRAP: `paper: #F2E9D8` parses as an empty value plus a comment, which
is exactly what YAML proper does too. Hex values MUST be quoted. `_check_hex`
below turns the silent-empty case into a loud error, because the failure mode
otherwise is a black UI rather than a crash.
"""

from __future__ import annotations

import re


class MiniYamlError(ValueError):
    """Raised with a 1-based line number for anything outside the subset."""


_UNSUPPORTED = ("&", "*", "!!", ">", "|")


def parse(text: str) -> dict:
    """Parse the supported YAML subset into plain dicts/lists/scalars."""
    lines = _significant_lines(text)
    value, index = _parse_block(lines, 0, _indent_of(lines[0][1]) if lines else 0)
    if index != len(lines):
        lineno, raw = lines[index]
        raise MiniYamlError(f"line {lineno}: unexpected indentation in {raw.strip()!r}")
    return value if isinstance(value, dict) else {}


# --------------------------------------------------------------------------
# lexing
# --------------------------------------------------------------------------

def _significant_lines(text: str):
    """(lineno, raw) for every line that is not blank or comment-only."""
    out = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise MiniYamlError(f"line {lineno}: tab indentation is not supported")
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        for token in _UNSUPPORTED:
            if token in stripped:
                raise MiniYamlError(
                    f"line {lineno}: {token!r} is outside the supported subset"
                )
        out.append((lineno, stripped))
    return out


def _strip_comment(raw: str) -> str:
    """Drop a trailing comment, respecting quotes.

    A `#` only opens a comment at the start of the line or after whitespace, so
    `"#F2E9D8"` and a bare `999px` survive. An UNQUOTED leading `#` still opens
    a comment -- see the hex trap in the module docstring.
    """
    out, quote = [], None
    for i, ch in enumerate(raw):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (i == 0 or raw[i - 1].isspace()):
            break
        out.append(ch)
    if quote:
        raise MiniYamlError(f"unterminated {quote} string in {raw.strip()!r}")
    return "".join(out)


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def _parse_block(lines, index: int, indent: int):
    """Parse the block at `indent` starting at `index`; return (value, index)."""
    if index >= len(lines):
        return {}, index
    if lines[index][1].lstrip().startswith("- "):
        return _parse_sequence(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines, index: int, indent: int):
    result = {}
    while index < len(lines):
        lineno, raw = lines[index]
        current = _indent_of(raw)
        if current < indent:
            break
        if current > indent:
            raise MiniYamlError(f"line {lineno}: unexpected indent in {raw.strip()!r}")

        key, _, rest = raw.strip().partition(":")
        if not _:
            raise MiniYamlError(f"line {lineno}: expected 'key: value' in {raw.strip()!r}")
        key, rest = key.strip(), rest.strip()
        if key in result:
            raise MiniYamlError(f"line {lineno}: duplicate key {key!r}")

        if rest:
            result[key] = _scalar_or_flow(rest, lineno)
            index += 1
            continue

        # Empty value -> a nested block, or genuinely nothing.
        index += 1
        if index < len(lines) and _indent_of(lines[index][1]) > indent:
            child_indent = _indent_of(lines[index][1])
            result[key], index = _parse_block(lines, index, child_indent)
        else:
            _check_hex(key, lineno)
            result[key] = None
    return result, index


def _parse_sequence(lines, index: int, indent: int):
    result = []
    while index < len(lines):
        lineno, raw = lines[index]
        current = _indent_of(raw)
        if current < indent:
            break
        body = raw.strip()
        if not body.startswith("- "):
            break
        item = body[2:].strip()
        if not item:
            raise MiniYamlError(f"line {lineno}: empty sequence item")
        if item.endswith(":") or re.match(r"^[\w.]+:\s", item):
            raise MiniYamlError(
                f"line {lineno}: sequences of mappings are outside the supported subset"
            )
        result.append(_scalar_or_flow(item, lineno))
        index += 1
    return result, index


def _check_hex(key: str, lineno: int) -> None:
    """Loudly reject the classic `paper: #F2E9D8` mistake."""
    raise MiniYamlError(
        f"line {lineno}: key {key!r} has no value. If you meant a hex colour, "
        f"QUOTE IT -- an unquoted '#RRGGBB' is a YAML comment."
    )


# --------------------------------------------------------------------------
# scalars and flow collections
# --------------------------------------------------------------------------

def _scalar_or_flow(text: str, lineno: int):
    if text.startswith("["):
        if not text.endswith("]"):
            raise MiniYamlError(f"line {lineno}: unterminated flow sequence")
        return [_scalar(p, lineno) for p in _split_flow(text[1:-1], lineno)]
    if text.startswith("{"):
        if not text.endswith("}"):
            raise MiniYamlError(f"line {lineno}: unterminated flow mapping")
        out = {}
        for part in _split_flow(text[1:-1], lineno):
            key, sep, value = part.partition(":")
            if not sep:
                raise MiniYamlError(f"line {lineno}: expected 'key: value' in {part!r}")
            out[key.strip()] = _scalar(value, lineno)
        return out
    return _scalar(text, lineno)


def _split_flow(body: str, lineno: int):
    """Split on commas that are not inside quotes. Nested flow is rejected."""
    parts, buf, quote = [], [], None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch in "[]{}":
            raise MiniYamlError(f"line {lineno}: nested flow collections are not supported")
        if ch == ",":
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _scalar(text: str, lineno: int):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    lowered = text.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    if lowered in ("null", "~", ""):
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text
