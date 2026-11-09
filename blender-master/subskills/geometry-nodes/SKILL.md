---
name: geometry-nodes
description: Builds procedural systems with Blender 5.2 Geometry Nodes from Python - surface scatter, instance rows, building blocks with per-instance attributes, facades, and any custom node group with exposed inputs - and verifies they evaluate, count right and respond to their inputs. Use for procedural assets, scattering, parametric generators, city or crowd layouts, and anything the user should be able to tweak with sliders.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Uses mod.properties.inputs (5.2). Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Geometry Nodes

The deliverable of a procedural part is a **node group with good inputs**, not a one-off mesh.
The user (or the next part) changes a slider and gets a valid new result.

## Procedure
1. **Name the inputs first**: what should be adjustable (count, density, seed, sizes, ranges).
   Everything else is a constant inside the group.
2. **Build the graph** in small stages: source geometry -> points -> instances -> attributes ->
   (optional) realize. Ops here cover the common patterns:
   - `scatter`: Distribute Points on Faces over a surface object, random scale and Z rotation,
     instances of a source object. Inputs Density (per m2), Seed, Scale Min/Max.
   - `instance_row`: a Mesh Line of instances (lamps, posts, columns). Inputs Count, Spacing.
   - `building_block`: grid of boxes with random heights, base on z = 0, and a per-instance
     `height_factor` attribute for shading variation. Inputs Rows, Columns, Height Min/Max, Seed.
   - `facade`: wall with windows on a floors x bays grid. Inputs Floors, Bays.
3. **Hide source objects** (instance shapes, scatter surfaces used only as reference) from render.
4. **Set inputs** with `set_param` (display name; uses `mod.properties.inputs` in 5.2 - never
   `mod["Socket_2"]`).
5. **Keep instances** as long as possible (memory, speed). Realize only when a later node needs
   real geometry or when exporting; `apply_nodes` bakes the result into mesh data (checkpoint first).
6. **Verify**: it evaluates, counts are in range, and changing an input changes the result.

Graph patterns, attribute flow to shaders, simulation zones and performance:
[references/gn-patterns.md](references/gn-patterns.md).

## Acceptance (default)
`gn_evaluates` on generated objects. Add `gn_instances` (count range) and `gn_input_changes`
(an input really drives the result) for each exposed input that matters.

## Pitfalls
- Densities are per square metre of the surface's *evaluated* area: apply scale on the surface.
- Object Info in Relative mode moves geometry with the source object; Original keeps the
  source's own space (right for instance shapes modelled at the origin).
- Random values without an ID/seed input change when topology changes; expose Seed.
- Realizing millions of instances before render or export: memory blow-up.
- Named attributes read in shaders through an Attribute node (type Instancer for instance
  attributes kept as instances, Geometry once realized).

## Scripts
- `scripts/ops.py`: `scatter`, `instance_row`, `building_block`, `facade`, `set_param`,
  `apply_nodes`; checks `gn_evaluates`, `gn_instances`, `gn_input_changes`; a `Tree` builder for
  custom groups.
- `lib/bm_gn.py`: get/set inputs by display name.
