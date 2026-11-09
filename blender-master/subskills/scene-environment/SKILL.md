---
name: scene-environment
description: Environments and sets in Blender 5.2 - noise terrain with a flat set area, streets with sidewalks, curbs and lane markings, modular kit pieces on a grid with linked-copy layouts, prop scattering through geometry nodes, and proxy-to-asset swaps - with checks for z-fighting and camera coverage. Use for exteriors, city blocks, landscapes, game levels and backgrounds around a hero subject, from blockout proxies to dressed sets.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Scattering uses the geometry-nodes sub-skill. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Scene and environment

Build from the camera outward: the hero area gets detail, the rest gets silhouettes.

## Procedure
1. **Blockout** (blockout-spatial-brief): proxies for the big masses, the hero camera, scale
   references. Decide what the camera sees before modelling anything.
2. **Ground**: `terrain` (hills with a flat set area) or a street layout with `street`
   (road, sidewalks, curbs, dashed lines; rotate and place copies to form junctions).
3. **Structure**: `modular_kit` makes grid-sized pieces (wall, floor, pillar, step) with
   origins on grid corners; `kit_layout` places linked copies cell by cell (edit one piece, every
   copy updates). Procedural buildings: geometry-nodes `building_block` / `facade`.
4. **Dress**: `scatter_props` (rocks, trees, litter) over a surface with density and seed;
   `swap_proxy` replaces a blockout proxy with an asset scaled to the proxy height.
5. **Depth**: atmosphere and mist (render-compositing), background cards or a sky
   (lighting-cameras `world`).
6. **Check**: `no_zfight` (coplanar overlaps), `camera_coverage` (the listed set pieces are in
   frame), then a render from the hero camera.

Layout rules, scale references, kit grids and level-design checks:
[references/environment-guide.md](references/environment-guide.md).

## Acceptance (default)
`GEO_` objects exist and names are valid; add `no_zfight` and `camera_coverage` for the shot.

## Pitfalls
- Everything at the same detail level: the eye has nowhere to go. Detail near the camera and
  the focal point, simple shapes far away.
- Kit pieces with origins in the middle: snapping drifts. Keep origins on grid corners.
- Repeating scatter: vary scale and rotation, mix 2-4 source variants, use several seeds.
- Coplanar floors and roads flicker; offset one by a centimetre (the street op does).
- Real-world scale cues (doors 2.0-2.1 m, steps 17-18 cm, lanes 3-3.5 m) sell the size.

## Scripts
`scripts/ops.py`: `terrain`, `street`, `modular_kit`, `kit_layout`, `scatter_props`, `swap_proxy`;
checks `no_zfight`, `camera_coverage`.
