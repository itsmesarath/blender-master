# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Coordinator skill `blender-master`: recognition of 15 project types, project brief with a
  part dependency graph and numeric acceptance checks, routing, headless / live MCP / manual
  execution, per-part verify loop (max 3 automatic fixes, then ask), final QA and export.
- Shared Blender 5.2 library (`lib/`): version guard, naming and collections, bmesh primitives,
  measurements and checks, cameras, preview renders and contact sheets, 5.x compositor helpers,
  layered-action keyframing, Geometry Nodes inputs, export presets, versioned saves.
- Core sub-skills: blockout-spatial-brief, modeling-topology, materials-shading,
  lighting-cameras, render-compositing, scripting-automation, qa-review, export-interchange,
  live-control-mcp.
- Headless test suite against Blender 5.2.3, reference scan, three text-only example projects.
- Phase 2 sub-skills, each with SKILL.md, a reference guide, `scripts/ops.py` and a headless
  Blender test: geometry-nodes, sculpting, retopology, uv-texturing-baking, hair-fur,
  rigging-body, rigging-face, animation, physics-simulation (incl. clothing from a body mesh),
  scene-environment, product-shots, npr-stylized (toon, outlines, line art, painterly),
  video-editing (sequencer cut, titles, sound, H.264/AAC encode).
- Examples 04 (full character run with FBX round-trip), 05 (procedural city block) and
  06 (product ad: cloth reveal, rigid bodies, logo, end card, MP4).
- `add_roles` in params; skin-modifier base figures, box-zone material assignment, texture
  wiring for baked maps, rig-aware export; procedural wood planks and two-scale paint wear.

- `hidden_until` check; logos stay hidden in renders until their reveal starts.
- Walk-through README for every example; CI checksum verification of the Blender download.

### Changed
- README and CONTRIBUTING rewritten for release (install per agent, how it works, limits).
- Routing: every role except 2D Grease Pencil routes to its own core sub-skill (no fallbacks).
- QA and still renders reset to the first frame; rig checks mute actions while posing.
- Materials assigned to geometry-nodes objects use object-linked slots so generated geometry
  shows them.
