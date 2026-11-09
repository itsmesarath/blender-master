---
name: animation
description: Keyframe animation in Blender 5.2 with layered-action-safe helpers - frame range and rate, keys on any property, pose keys for rigs, sine waves for idles and cycles, noise, cyclic loops, path following, NLA strips, and baking driven shape keys to keyframes for export - with checks for animation presence, clean loops and pops. Use for character motion, camera moves, product spins, motion-graphics beats, looping game clips and anything that changes over time.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Uses 5.x layered actions (channelbags) via lib/bm_anim. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Animation

## Procedure
1. **Timing first**: `frame_range` (start, end, fps). Write the beats down in the brief
   (e.g. "frames 1-12 raise arm, 12-36 wave, 36-48 lower").
2. **Block** key poses on the main beats: `pose_keys` for rigs (bone-local XYZ degrees),
   `keyframes` for objects, data (light energy, lens) and constraint values.
3. **Cycles and secondary motion**: `wave` (breathing, sway, bob, waving hands) with phase
   offsets between body parts; `noise` for handheld cameras and flicker; `cycle` makes any
   curves loop.
4. **Paths**: `follow_path` (vehicles, flying cameras, conveyor items).
5. **Layer and reuse**: `nla_push` moves the action to an NLA strip (clips for games,
   layering a wave over a walk).
6. **Faces for export**: `bake_shape_keys` keys driven shape keys per frame (engines do not
   import drivers).
7. **Check**: `anim_present`, `loop_ok` (for loops), `no_pops`; render a low-res playblast
   (render-compositing frames) and look at arcs and spacing.

Principles (spacing, overlap, arcs, holds), clip conventions for engines and camera moves:
[references/animation-guide.md](references/animation-guide.md).

## Acceptance (default)
`anim_present` on the animated objects (`animated` fact); `loop_ok` when `loop` is true.

## Pitfalls
- 5.x actions are layered: never use `action.fcurves`; go through the channelbag (lib).
- Euler flips: keep rotations continuous (no jump from 179 to -179 deg); `no_pops` finds them.
- Keys on the rest pose of the root bone move the whole export; animate `root` deliberately.
- FBX for Unreal: one action per clip, NLA strips off at export (presets handle it).
- Constraints (Follow Path, IK) are not exported; bake them to keys for engines.

## Scripts
`scripts/ops.py`: `frame_range`, `keyframes`, `pose_keys`, `wave`, `cycle`, `noise`,
`follow_path`, `nla_push`, `bake_shape_keys`; checks `anim_present`, `loop_ok` (auto-fix:
cyclic), `no_pops`.
