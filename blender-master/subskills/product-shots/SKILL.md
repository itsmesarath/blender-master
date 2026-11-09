---
name: product-shots
description: Product imagery and short ad shots in Blender 5.2 - studio setups sized to the product (seamless sweep, softbox and strip lights, long-lens hero camera), product turntables and eased motion beats on a pivot, cloth reveals, logo reveals and end cards - with the lighting and camera ops included and checks for title/action-safe framing and a cleared reveal. Use for packshots, e-commerce stills, hero renders, 5-15 s product ads and social loops.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Uses lighting-cameras, modeling-topology, materials-shading and physics-simulation ops. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Product shots

The product is the hero: clean silhouette, controlled reflections, readable label, nothing
competing in the frame.

## Procedure
1. **Real size** product (modeling) with bevelled edges (highlights need edges) and real
   materials; the label facing the camera axis.
2. **Studio**: `studio` builds a sweep scaled to the product, a backdrop colour (`style`
   white, grey, dark, warm, cool or `color`), soft top and strip lights and an 85 mm hero camera
   if none exists. Or compose your own with `world`, `softbox_studio`, `three_point`, `camera`,
   `depth_of_field` (re-exported lighting ops).
3. **Stills**: hero 3/4 (slightly low), front, top-down flat lay, detail crop with shallow
   depth of field. Check `safe_area` for text-safe framing.
4. **Motion** (ads, loops):
   - `turntable` spins the product (camera still; reflections travel) - seamless loop;
   - `camera_orbit` moves the camera instead;
   - `motion_beats` for hero moves (lift, tilt, rotate, scale) with eased holds;
   - `cloth_reveal` drapes a sheet and pulls it away (baked cloth); check `reveal_clear`;
   - `logo_reveal` (rise or scale with overshoot; hidden in renders until its move starts, check
     `hidden_until`) and `end_card` (title, subtitle) to finish.
5. **Render** frames (render-compositing) and **assemble** with video-editing (music, titles,
   fades, mp4).

Lighting recipes per material, shot list and ad timing:
[references/product-guide.md](references/product-guide.md).

## Acceptance (default)
Lights and cameras exist, `camera_frames`, `exposure` (with the lighting auto-fixes). Add
`safe_area` and, for reveals, `reveal_clear`.

## Pitfalls
- Small products at default light sizes: tiny hard highlights. The rig scales light size and
  distance with the product.
- Wide lenses distort products; 70-135 mm for hero shots.
- Pure white backdrops clip; keep the sweep at 0.7-0.8 albedo and let exposure decide.
- Logos as text objects need a font with the right licence; convert to mesh for export.
- Cloth reveals need the cloth baked before rendering in another process (the op bakes).

## Scripts
`scripts/ops.py`: `studio`, `turntable`, `camera_orbit`, `motion_beats`, `cloth_reveal`,
`logo_reveal`, `end_card`, plus `world`, `three_point`, `softbox_studio`, `sun`, `practical`,
`camera`, `depth_of_field`, `track_to`; checks `safe_area`, `reveal_clear`, `hidden_until`.
