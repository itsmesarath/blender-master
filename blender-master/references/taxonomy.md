# Project types and recognition

`taxonomy.json` is the machine-readable source; this page explains it.

## How scoring works

- Each type has signal phrases with weights (whole-word, case-insensitive). The request's score per type is the sum of matched weights.
- **Primary** = highest score. Types listed in `modifier_roles` that score at least `modifier_threshold` become **modifiers** and add their roles (e.g. a *game asset* modifier adds `uv` and `export`).
- If the top two scores differ by less than `ambiguity_margin` and their part lists differ, ask one question; otherwise write the assumption into the brief.
- Nothing matches: treat as look-dev on the user's scene and ask what they want changed.
- The agent may override the result (`type_override` in params) when the user says what it is.

## Types

| Type | Strong signals | Default roles (in order) | Notes |
|---|---|---|---|
| **Character (humanoid)** (`character`) | character, t-pose, a-pose, person, human, girl, boy, woman | blockout -> model -> sculpt -> retopo -> uv -> bake -> materials -> hair -> rig_face -> rig_body -> animation -> lighting -> render -> qa -> export | Topology must be finished before UVs, shape keys and rig. Confirm style (realistic, stylised, toy) and height. |
| **Creature / furry** (`creature`) | creature, animal, fur, furry, paws, muzzle, mane, tail | blockout -> model -> sculpt -> uv -> materials -> hair -> rig_body -> lighting -> render -> qa | As character, plus hair/fur. Density masks and grooming are partly hand work (manual mode). |
| **Hard-surface prop** (`hard_surface_prop`) | hard-surface, hard surface, crate, weapon, gun, vehicle, gadget, barrel | blockout -> model -> uv -> materials -> lighting -> render -> qa | Bevel/weighted-normal stack, booleans with exact solver, real dimensions from the brief. |
| **Product / ad shot** (`product_shot`) | packshot, pack shot, product, commercial, advert, turntable, perfume, showcase | blockout -> model -> materials -> product -> render -> qa | The camera and light language matter more than polycount. Clean reflections, seamless sweep, 50-100 mm lenses. |
| **Environment / scene** (`environment`) | environment, landscape, street, city, forest, village, terrain, alley | blockout -> environment -> model -> materials -> lighting -> render -> qa | Proxy-first layout with hero cameras; dress only what cameras see. |
| **Architecture / interior** (`interior`) | interior, bedroom, kitchen, living room, bathroom, floor plan, archviz, studio apartment | blockout -> model -> materials -> lighting -> render -> qa | Real units, wall thickness, openings, wide lens (18-28 mm) at eye height, daylight through windows. |
| **Procedural / geometry-nodes system** (`procedural`) | geometry nodes, procedural, parametric, generator, scatter, node system, randomize, randomise | blockout -> procedural -> materials -> lighting -> render -> qa | Exposed parameters are the deliverable; test that inputs change the result. |
| **VFX / simulation** (`vfx_sim`) | simulation, rigid body, soft body, explode, explosion, smoke, fire, liquid | blockout -> model -> simulation -> materials -> lighting -> render -> qa | Apply scale first, simulate low-res short ranges, bake, then scale up. |
| **Motion graphics / animation** (`motion_graphics`) | logo sting, motion graphics, animate, animation, animated, keyframes, keyframe, camera move | blockout -> model -> materials -> animation -> lighting -> render -> edit -> qa | Layered-action keyframing, seamless loops, frame-range checks. |
| **Stylised / NPR** (`stylized`) | toon, anime, cel, cel-shaded, painterly, 2d look, outline, outlines | blockout -> model -> materials -> npr -> lighting -> render -> qa | Base scene first, then toon/painterly shading and line work. |
| **Game asset** (`game_asset`) | game-ready, game ready, ue5, low-poly, low poly, lowpoly, lod, unreal | blockout -> model -> retopo -> uv -> bake -> materials -> lighting -> render -> qa -> export | Triangle budget, UVs, sane pivots and scale, export presets with a re-import round-trip. |
| **Rigging only** (`rigging`) | rig this, rigging, weight paint, skinning, shape keys, blendshapes, armature, rig | rig_body -> rig_face -> qa -> export | Inspect the mesh first; refuse to rig unfinished topology. |
| **Look-dev / render only** (`lookdev`) | make it look good, look-dev, lookdev, render settings, improve the render, existing .blend, relight, existing scene | lighting -> materials -> render -> qa | Audit before changing anything; keep the user's file untouched and work on a copy. |
| **Scripting / automation** (`scripting`) | bpy, script, python, batch, add-on, addon, operator, automate | script -> qa | Spec, script, headless test, idempotent re-run. |
| **2D / Grease Pencil** (`grease_pencil_2d`) | grease pencil, 2d animation, storyboard, hand-drawn, line drawing, animatic, drawing, sketch | gp2d -> render -> qa | Planned sub-skill; manual guidance until then. |

## Roles

A role is a kind of part. Its dependencies (only those present in the project are used):

| Role | Depends on |
|---|---|
| `blockout` | - |
| `environment` | blockout |
| `procedural` | blockout, environment, model |
| `model` | blockout, environment |
| `sculpt` | model |
| `retopo` | sculpt, model |
| `uv` | retopo, model |
| `bake` | uv |
| `materials` | bake, uv, model, procedural |
| `npr` | materials |
| `hair` | materials |
| `rig_face` | uv, model |
| `rig_body` | rig_face, model, hair |
| `simulation` | model |
| `animation` | model, rig_body |
| `lighting` | model, environment, procedural |
| `product` | model, materials, lighting |
| `render` | materials, npr, hair, lighting, animation, simulation, product |
| `edit` | render |
| `script` | - |
| `gp2d` | - |
| `qa` | render, edit, script, rig_body, rig_face |
| `export` | qa |

Modifier roles: `game_asset` adds uv, export; `stylized` adds npr; `motion_graphics` adds animation; `vfx_sim` adds simulation; `creature` adds hair; `rigging` adds rig_body; `procedural` adds procedural.

## Skipping roles

A default role can be dropped with `skip_roles` in params when it truly does not apply, with the reason in `assumptions` (for example: a low-poly prop modelled directly at game resolution needs no retopology).
