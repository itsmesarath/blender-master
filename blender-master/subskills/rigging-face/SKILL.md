---
name: rigging-face
description: Facial rigs in Blender 5.2 built on shape keys - regional keys with soft falloff (move, hinge rotation for the jaw, inflate, squash for lids), left/right splits, corrective combination keys, small face control objects, and drivers that map a control channel to a key value (clamped 0-1, rest-offset aware) - with checks that keys deform sanely and every driver resolves and responds. Use for expressions, lip sync shapes, blinks, correctives and any blend-shape set an engine will import.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Drivers use simple expressions (no Python auto-run needed). Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Face rigging

Shape keys travel to every engine (FBX/glTF blend shapes); bone-based faces need a matching
engine rig. Start with keys; add face bones only for jaw and eyes when the target needs them.

## Procedure
1. **Mesh**: final face topology (loops around eyes and mouth), scale applied, enough
   resolution in the face (the shapes cannot be finer than the edges).
2. **Keys** with `region_key` - centre, radius and one of:
   - `offset` (brows up, cheek raise, smile corners),
   - `rotate` = (axis, degrees, pivot) with `below` (jaw open around the hinge),
   - `inflate` (cheek puff), `squash` (lids closing).
   Centres snap to the nearest surface vertex; `mirror` makes a symmetric key.
3. **Sides**: `split_lr` turns a symmetric key into `_L`/`_R` with a soft blend at the centre.
4. **Controls**: `face_control` empties in front of the face; `drive` maps a control channel
   to a key (`full` = distance for value 1; negative for downward moves).
5. **Correctives**: `combo_key` for shapes that only appear together (jaw open + smile).
   Drive the source keys first.
6. **Attach** the controls to the head bone (rigging-body `bind_extras`); drivers keep working.
7. **Check** `shape_keys_valid` and `drivers_resolve`; render the extremes.

Shape lists (expressions, visemes, engine standards) and sculpting keys by hand:
[references/face-guide.md](references/face-guide.md).

## Acceptance (default)
`shape_keys_valid` and `drivers_resolve` on the face mesh (`face_mesh` fact).

## Pitfalls
- A driver on a key that reads other keys of the same mesh forms a dependency cycle;
  `combo_key` copies the controls instead.
- Python-expression drivers do not run when auto-run is off; keep to simple expressions
  (arithmetic, min, max) as these ops do.
- Shape keys added after the armature modifier are fine, but keys must be made on the rest
  pose (no pose applied).
- Topology changes after keys exist destroy them; finish topology first.
- Engines import keys, not drivers: bake the driven animation to key values when exporting
  facial animation (animation `bake_shape_keys`).

## Scripts
`scripts/ops.py`: `region_key`, `split_lr`, `face_control`, `drive`, `combo_key`; checks
`shape_keys_valid`, `drivers_resolve`.
