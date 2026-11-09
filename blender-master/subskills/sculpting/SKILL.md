---
name: sculpting
description: Organic form and surface detail in Blender 5.2 - dense sculpt copies of a clean base, voxel remesh, multires, scripted brush-like moves (inflate, grab, crease, surface noise, smooth), symmetry and detail checks - plus a plan for an interactive sculpt session. Use for characters, creatures, organic props, rocks and any high-poly source that will be retopologized or baked.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Headless ops use bmesh/mesh data; interactive brushes need the UI. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Sculpting

Sculpt on a **copy**. The clean base stays as the future low-poly; the dense copy
(`GEO_<name>_high`) is the bake source.

## Procedure
1. **Start from proportions, not detail.** A good base (blockout or `skin_figure` from
   modeling-topology) at real scale, scale applied, facing -Y.
2. **Make the dense copy**: `make_high` (smooth subdivision applied, joints copied).
   Use `voxel_remesh` instead when the piece is several intersecting meshes that must fuse.
3. **Big forms first** (low resolution, large radius): `grab` to move masses, `inflate` for
   volume (cheeks, muscles, belly). Keep X symmetry on (`mirror_x`, default).
4. **Secondary forms** (medium radius): `crease` along a polyline for eyelids, muscle
   separations, wrinkles, panel grooves.
5. **Tertiary detail** last: `surface_noise` at small scale and strength (pores, cloth weave,
   stone grain). Detail that is smaller than a texel of the final bake is wasted.
6. **Relax** with `smooth` where forms got lumpy. Check `symmetry_ok`; `symmetrize` repairs.
7. **Interactive session** (person at the viewport): `multires` for layered detail,
   `setup_session` turns on mirror flags; follow the brush plan in
   [references/sculpt-workflow.md](references/sculpt-workflow.md).
8. Hand over to **retopology** (low mesh) and **uv-texturing-baking** (normal/AO bake).

## Acceptance (default)
`sculpt_detail` (vertex count on the sculpt target, `sculpt_min_verts` fact) and `symmetry_ok`
for symmetric subjects.

## Pitfalls
- Unapplied scale: brush radius and strength behave differently per axis.
- Voxel remesh deletes UVs, shape keys and vertex groups; do it before those exist.
- Noise before big forms: the detail stretches when forms move later.
- Multires plus topology edits on the base breaks the levels; finish the base first.
- Million-poly meshes in the .blend for every part: keep the high copy in its own collection
  and hide it from render once baked.

## Scripts
`scripts/ops.py`: `make_high`, `voxel_remesh`, `multires`, `inflate`, `grab`, `crease`,
`surface_noise`, `smooth`, `symmetrize`, `setup_session`; checks `sculpt_detail`, `symmetry_ok`
(auto-fix: symmetrize).
