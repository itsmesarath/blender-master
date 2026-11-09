---
name: modeling-topology
description: Builds clean polygon models in Blender 5.2 at real scale - hard-surface props with bevel and weighted-normal stacks, booleans, panel insets, lathed products, room shells with openings, simple furniture, and organic base meshes with deformation-ready edge loops. Use when a part needs final geometry, topology cleanup, mirror or subdivision modelling, or a topology report (quads, poles, n-gons, manifold).
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Part of blender-master; scripts expect its lib/ on sys.path.
metadata:
  parent: blender-master
  status: core
---

# Modelling and topology

Replace proxies with real geometry that matches the brief's sizes, reads well from the hero
camera, and has topology suited to what happens next (render only, subdivision, deformation,
game export).

## Decide the topology target first

| Downstream use | Target |
|---|---|
| still render, rigid object | anything clean: n-gons on flat faces are fine, no shading artefacts |
| subdivision surface | all quads, support loops near edges that must stay sharp |
| deforms (character, cloth) | quads, loops following muscles and folds, poles away from bends |
| game asset | triangle budget, flat-shaded hard edges via weighted normals, no hidden faces |
| boolean-heavy hard surface | keep cutters live until the shape is final, then apply on a checkpoint |

Write the target into the part's facts (`allow_ngons`, `min_quad_ratio`, `tri_budget`,
`closed_meshes`), so the default checks match it.

## Procedure
1. **Start from the proxy** (`from_proxy`) or build at the proxy's size (`box`, `cylinder`,
   `lathe` with a profile of `(radius, z)` pairs for anything turned: bottles, vases, cups,
   lamp bases). All ops build base-centred with scale 1.
2. **Primary forms only**, then check against the hero preview before any detail.
3. **Hard-surface finish** (`hs_bevel`): angle-limited Bevel -> Weighted Normal, smooth by angle.
   Bevel width ~0.5-2 % of the object's size; 2-3 segments for renders, 1 for games.
4. **Detail**: `panel_inset` for recessed panels (give the recess its own material index so it
   reads), `boolean_cut` for holes and cut-outs (EXACT solver; checkpoint saved before apply).
5. **Architecture**: `room_shell` (walls, floor, ceiling as one closed shell with openings),
   `window_frame`, `cyclorama` for seamless studio sweeps, `furniture` (bed, desk, chair, shelf,
   table, rug) as quick parametric pieces.
6. **Symmetry and smoothness**: `mirror` (clip on) while modelling; `subdivide` for smooth forms.
7. **Hand-off**: `apply_modifiers` only where the next step needs real geometry (export,
   sculpt, booleans that follow); `uv_quick` for automatic UVs when no dedicated UV part exists;
   `hide_proxies` at the end.

Characters: `skin_figure` builds a clean all-quad humanoid base (A-pose, facing -Y, feet on
z = 0) with joint positions stored as a property; sculpting refines it, rigging-body reads the
joints.

Topology guidance for organic and hard-surface work, loop layouts for faces and limbs, and
pole rules: [references/topology-guide.md](references/topology-guide.md).

## Acceptance (default)
`GEO_` objects exist, scale applied, names valid, size within tolerance of the brief, sitting on
the ground, no n-gons (unless allowed), manifold and outward normals for closed meshes, triangle
budget if set. Visual: silhouette and proportions match the goal from the hero camera.

## Report a mesh
`blender -b file.blend --python scripts/topology_report.py -- --objects GEO_ --out report.json`
prints quads/tris/n-gons, poles by valence, non-manifold and boundary edges, and islands.

## Pitfalls
- Object scale not applied before bevels and booleans: widths become uneven. Apply first.
- Boolean cutters overlapping coplanar faces: offset by a millimetre or use EXACT.
- Shade smooth on a low-poly hard-surface mesh without weighted normals: gradients on flat faces.
- Joining parts that each have scale or rotation: transforms must be baked into the mesh.
- Ultra-thin walls (under ~2 mm at real scale) disappear or flicker; give glass real thickness.

## Scripts
- `scripts/ops.py`: `box`, `sphere`, `cylinder`, `lathe`, `from_proxy`, `hide_proxies`, `hs_bevel`,
  `panel_inset`, `boolean_cut`, `room_shell`, `window_frame`, `cyclorama`, `furniture`, `mirror`,
  `subdivide`, `apply_modifiers`, `uv_quick`, `place`, `skin_figure` (humanoid base mesh from a
  joint skeleton via the Skin modifier; joints stored on the object for rigging).
- `scripts/topology_report.py`: standalone topology report.
