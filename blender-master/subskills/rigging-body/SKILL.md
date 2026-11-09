---
name: rigging-body
description: Body rigs in Blender 5.2 - armatures from stored joints or a bone list, DEF/CTRL/MCH bone collections, two-bone IK with poles that keep the rest pose, skinning with automatic weights and a distance-weight fallback, weight cleanup (influence limit, normalise), rigid attachments (hair, props, face controls) to bones, and an optional Rigify metarig - with checks for weights, pose deformation and IK stability. Use for characters, creatures and mechanical rigs before animation or game export.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Rigify path needs the bundled add-on. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Body rigging

## Procedure
1. **Mesh ready**: final topology, scale and rotation applied, A- or T-pose, facing -Y,
   feet on z = 0. Shape keys may already exist (rigging-face); the armature modifier goes on top.
2. **Skeleton**: `armature_from_joints` reads the `joints` property (from `skin_figure`) or a
   `joints` dict and builds deform bones following a spec (default humanoid: hips, spine,
   chest, neck, head, clavicles, arms, hands, legs, feet) under a non-deforming `root`.
   Bones are rolled so limbs bend around their local X.
3. **Controls**: `ik_limbs` adds IK targets and pole bones (CTRL collection) for arms and legs.
   The pole angle is solved so the rest pose stays put (`ik_rest_stable`).
4. **Skin**: `bind` - automatic heat weights, falling back to distance weights where heat
   fails; `clean_weights` limits influences (4 for game engines) and normalises.
5. **Attach rigid parts**: `bind_extras` (hair, eyes, hats, held props, face control empties)
   to a bone without moving them.
6. **Test poses**: `pose_deform_ok` bends knees, elbows, spine and head and measures edge
   stretch; look at a posed render of shoulders, hips and elbows.
7. **Rigify** (optional, UI): `rigify_metarig` adds the human metarig to fit by hand and
   generate; the generated rig has FK/IK switching and face controls.

Weight-painting rules, bone naming for engines, constraints and corrective shapes:
[references/rigging-guide.md](references/rigging-guide.md).

## Acceptance (default)
`RIG_` armature exists, `weights_valid` (all verts weighted, <= 4 influences, normalised;
auto-fix cleans then re-weights), `pose_deform_ok`.

## Pitfalls
- Unapplied mesh scale or rotation: bones and mesh disagree after binding.
- Automatic weights fail on non-manifold, intersecting or tiny-scale meshes ("bone heat"
  error): the distance fallback runs, but fix the mesh for production.
- Straight limbs: IK cannot know the bend direction; keep a slight bend in the rest pose.
- Engines need one root bone at the origin and no scale on bones; keep `root` at z = 0.
- `bake_anim_use_nla_strips=False` for UE FBX (export-interchange presets do this).

## Scripts
`scripts/ops.py`: `armature_from_joints`, `ik_limbs`, `bind`, `clean_weights`, `bind_extras`,
`rigify_metarig`; checks `weights_valid` (auto-fix), `pose_deform_ok`, `ik_rest_stable`.
