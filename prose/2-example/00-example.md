{{lede:Every diagram idiom the wiki draws, once each}}

# Example

This page exists to be copied and then deleted. Each section places one generated
diagram, drawn from placeholder data by a small renderer, so you can see the whole
repertoire before you write your first page — and lift the idiom you need.

## How a diagram gets onto a page

{{lede:A renderer, a registry entry, one placement}}

A diagram is a Python function that returns an SVG fragment. It is registered once
with a slug, a title and a lede, and placed once from prose with a
`{{section:slug}}` line. Prose cannot carry inline SVG; every drawing goes through a
renderer, which is what lets the build check that no colour was typed by hand.

{{notes:begin}}
The renderers live in `packs/example_pack.py`; the shared drawing helpers in
`engine/svg.py`. `tests/test_example_pack.py` is the pack-test idiom — copy it with
your pack.
{{notes:end}}
