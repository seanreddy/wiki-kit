{{lede:The token model, rendered live from one file}}

# Design System

Every colour, size, radius and duration on this site — and in whatever the project
builds — comes from one file: `tokens.yaml`. This page is that file, drawn. Change a
value, rebuild, and every page retints, including this one.

## How to read this page

{{lede:Inks, roles, then everything sized or timed}}

Inks are the closed palette. Roles are the jobs a colour does; every drawing colour
goes through a role, so renaming an ink never silently changes a meaning. Below the
colour model come the sizes: type, spacing, shape and ornament — and finally motion.

{{notes:begin}}
The renderers on this page read `tokens.yaml` through the engine's token model; a
missing key fails the build naming the key. Hand-typed hex anywhere in a renderer
fails the hex-leak gate.
{{notes:end}}
