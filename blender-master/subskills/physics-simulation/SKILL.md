---
name: physics-simulation
description: Physics in Blender 5.2 set up and baked from Python - rigid bodies (active, passive, animated), cloth with material presets, pin groups and pressure, character clothing cut from the body mesh, collisions, soft bodies, emitter particles, low-resolution smoke and liquid domains - plus cache baking that survives save/reload and checks that simulations move, stay bounded and settle. Use for falling and stacking objects, cloth drapes and reveals, garments on characters, jiggle, debris, sparks, smoke and splashes in ads and shots.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Mantaflow fluids bake to disk; other caches bake into the .blend. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Physics and simulation

## Procedure
1. **Real scale, applied transforms.** Solvers use metres and kilograms; a 10x scaled scene
   falls in slow motion.
2. **Frame range first** (scene start/end); caches follow it.
3. **Set up** the solver:
   - Rigid: `rigid_world`, then `rigid_body` (ACTIVE fall, PASSIVE floor/product, `animated`
     passive pushers). Primitive shapes re-centre the origin; CONVEX_HULL for irregular props,
     MESH only for static concave colliders.
   - Cloth: `cloth` with a preset (cotton, silk, denim, leather, rubber, flag), `pin_group` for
     held vertices, `collision` on everything it touches; `pressure` inflates closed meshes.
   - Character clothing: `garment_from_body` copies a body region (shirt, skirt, sleeve), offsets
     it, pins the waistband and makes it cloth colliding with the body.
   - Soft body: `soft_body` (goal = how firmly it keeps shape).
   - Particles: `particles` (count, timing, velocity, instanced object).
   - Fluids: `fluid` smoke or liquid domain + flow, low resolution for previews.
4. **Bake**: `bake` writes every point cache into the .blend and fluids to `cache/fluid`, so
   later parts (render, edit) and re-opens read the same result.
5. **Check**: `sim_moved`, `no_explosion` (finite, bounded, above the floor), `sim_settled`
   for rigid bodies that must come to rest; render a few frames.

Solver settings, stability fixes, cloth on rigs and cost of fluids:
[references/physics-guide.md](references/physics-guide.md).

## Acceptance (default)
`sim_moved` and `no_explosion` on the simulated objects (`sim_objects` fact).

## Pitfalls
- Overlapping bodies at frame 1 explode apart: space them or lower the starting overlap.
- Thin colliders and fast objects tunnel: more substeps (rigid) or quality steps (cloth),
  thicker collision distance.
- Cloth on a rig: pinned vertices follow the armature only if the cloth modifier comes after
  the armature modifier; keep the body collision on the deformed body.
- Unbaked caches recompute differently per process: always `bake` before rendering in a
  separate part.
- Fluid resolution cost grows with its cube; 32-64 for previews, 128+ only for finals.

## Scripts
`scripts/ops.py`: `rigid_world`, `rigid_body`, `pin_group`, `cloth`, `collision`, `soft_body`,
`garment_from_body`, `particles`, `fluid`, `bake`; checks `sim_moved`, `no_explosion`,
`sim_settled`.
