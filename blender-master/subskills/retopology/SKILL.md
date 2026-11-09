---
name: retopology
description: Turns dense sculpts, scans and booleans into clean, animation- or game-ready low-poly meshes in Blender 5.2 - shrinkwrap fitting of an existing base, automatic quad remesh (QuadriFlow) with a voxel+decimate fallback, LOD chains - and checks that the low mesh stays on the high surface within tolerance. Use after sculpting, before UV unwrap and baking, and whenever a mesh has too many or messy polygons for its use.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Retopology

The low mesh must (1) sit on the high surface, (2) have edge flow that deforms where it will
bend, (3) fit the polygon budget, (4) be all quads except where the engine triangulates anyway.

## Choose a method
| Situation | Op |
|---|---|
| sculpt was made from a clean base (subdivided copy) | `shrinkwrap_fit` the base onto it |
| props, rocks, background characters, scans | `quad_remesh` (QuadriFlow) with a face budget |
| QuadriFlow fails (non-manifold, holes) | `voxel_decimate` (automatic fallback) |
| hero face / hands | manual loops in the UI (see reference), then `shrinkwrap_fit` to snap |
| game distances | `lod_chain` (LOD1.. at decreasing ratios) |

## Procedure
1. Decide the **budget** from the use (see the table in the reference) and record it as
   `tri_budget` facts.
2. Run the method; keep the high mesh, hidden from render, for baking.
3. Check `surface_distance` (mean and optionally max BVH distance from low verts to high).
4. Check `quad_ratio` and `tri_budget`; deforming characters also need loops around joints:
   at least 3 edge loops at elbows and knees, concentric loops around eyes and mouth.
5. Hand over to uv-texturing-baking (seams, unwrap, bake high -> low).

## Acceptance (default)
objects exist, scale applied, `quad_ratio` >= 0.85, `surface_distance` (when `retopo_high` is
given; `retopo_max_mean`, default 3 mm), `tri_budget`.

## Pitfalls
- Shrinkwrap on thin parts (ears, fingers) can snap to the wrong side; use Project mode with
  a small limit or fix those regions by hand.
- QuadriFlow ignores UVs and vertex groups; redo them on the result.
- Decimate produces triangles and poor flow; fine for LODs and static props, not for faces.
- Retopo after rigging means re-weighting; finish topology first.

## Scripts
`scripts/ops.py`: `shrinkwrap_fit`, `quad_remesh`, `voxel_decimate`, `lod_chain`; check
`surface_distance` (auto-fix: re-fit by shrinkwrap).
Details: [references/retopo-guide.md](references/retopo-guide.md).
