---
name: lighting-cameras
description: Sets up lighting, worlds and cameras in Blender 5.2 - three-point and softbox studio rigs sized from the subject, physical sky and interior daylight, practical lamps, colour temperature, camera views and lenses, framing, depth of field with a focus empty, track-to and turntable orbits - and fixes framing and exposure from probe renders. Use when a part needs lights, a world/HDRI, cameras, lens choice, composition, DoF or a camera orbit.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Part of blender-master; scripts expect its lib/ on sys.path.
metadata:
  parent: blender-master
  status: core
---

# Lighting and cameras

Light so the subject's form and materials read, at a sane exposure, through cameras that frame
it with intent.

## Procedure
1. **World first** (`world`): `studio` (dark flat colour), `sky` (physical sky with sun
   elevation and rotation), `night`, `gradient`. The world sets the fill level and what shiny
   surfaces reflect.
2. **Pick a rig for the project type**:
   - props and characters: `three_point` (key, fill, rim around the camera's view; key/fill
     ratio, warm key and cool rim by colour temperature);
   - products: `softbox_studio` (large top softbox, two tall strip lights for long reflections,
     a kicker);
   - exteriors: `sun` + `world(kind="sky")`;
   - interiors: `interior_daylight` (sky + sun through the window + a soft area light in the
     opening) plus `practical` lamps.
   Energies scale with the subject size, so one rig works from a perfume bottle to a room.
3. **Cameras** (`camera`): named view or explicit location/target, lens by subject. Auto-placed
   cameras may be refitted; hand-placed ones are respected.
4. **Optional**: `depth_of_field` (focus empty at the subject; f/1.8-4 for products, f/5.6+ for
   rooms), `track_to`, `turntable` (camera on a keyed pivot empty, linear and cyclic).
5. **Probe and fix**: the exposure check renders a small probe and measures mean brightness,
   clipped and black fractions; the fixer scales every light and the world toward mid-grey.
   The framing check projects the subject's bounds into the camera.

Rig layouts, lens table, exposure targets and look recipes:
[references/lighting-guide.md](references/lighting-guide.md).

## Acceptance (default)
At least one light, deliverable cameras exist, the subject fully inside the hero frame with
margin and a minimum fill, probe exposure within mean 0.12-0.75, clipped <= 2 %, black <= 35 %
(override per project, e.g. a dark mood piece). Visual: clear key direction, separation from the
background, no blown highlights on the subject.

## Pitfalls
- Lighting before materials are roughly right: you light around wrong albedo values.
- Point lights for products: hard, tiny reflections. Use large area lights.
- Huge energy numbers to fight a too-small light far away: move it closer or make it bigger.
- Camera clipping: raise `clip_start` for close-ups only as far as needed; set `clip_end` for
  large scenes.
- Moving a hand-placed camera to "fix" framing: ask instead.

## Scripts
- `scripts/ops.py`: `world`, `three_point`, `softbox_studio`, `sun`, `interior_daylight`,
  `practical`, `camera`, `depth_of_field`, `track_to`, `turntable`; fixers for `camera_frames`
  and `exposure`.
