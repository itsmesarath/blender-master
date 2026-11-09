---
name: hair-fur
description: Strand hair and fur in Blender 5.2 using hair-curves objects generated from Python - scalp or body regions, guide strands with length variation, gravity, curl and clumping, dense short fur by density per square metre - with a Principled Hair material and checks for strand counts, roots on the surface and materials. Use for character hair, beards, eyebrows, animal fur, grass-like strands and fuzzy props; covers when to switch to hair cards for games.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Renders in Cycles and EEVEE. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Hair and fur

## Procedure
1. **Surface ready**: final low mesh, scale applied, UVs if the hair should later be edited
   with the curve sculpt tools (they read `surface_uv_map`).
2. **Material first**: `hair_material` - melanin 0 (platinum) ... 1 (black), redness for
   auburn/ginger, or `color` for dyed and stylized hair.
3. **Region**: where strands grow. `region` takes any of `z_min`/`z_max`, `direction` +
   `min_dot` (faces pointing that way, e.g. up-and-back for a scalp), `center` + `radius`, or
   a painted `vertex_group` (most control: paint a scalp, a beard, eyebrows).
4. **Groom** with `groom`: count, length and `length_var`, `gravity`, `curl` (turns along the
   strand) and `curl_radius`, `clump` (strands gather toward guides at the tips), number of
   `guides`. Long hair: 8-16 segments; short: 4-6.
5. **Fur** with `fur`: density per m2 (capped), short length, low gravity.
6. **Attach**: the hair object is parented to its surface. For rigged characters,
   rigging-body re-parents it to the head bone (rigid follow) - see the reference for
   deforming attachments.
7. **Check**: `curve_count`, `hair_roots_on_surface`, `hair_material`; render a close-up.

Grooming styles, density figures, viewport speed and game hair cards:
[references/hair-guide.md](references/hair-guide.md).

## Acceptance (default)
`curve_count` on the hair prefix (`hair_prefix`, `min_curves` facts).

## Pitfalls
- Too few strands with thick radius reads as spaghetti; more strands, thinner radius.
- Hair growing from the face: restrict the region (direction or painted group).
- Strands through the head: raise `lift`, lower `gravity`, or add a few guide-only passes in
  the curve sculpt tools (UI).
- Game engines do not import strand curves through FBX: export hair cards (meshes) instead.
- Huge counts in the viewport: hide the hair object or use a low-count copy while working.

## Scripts
`scripts/ops.py`: `groom`, `fur`, `hair_material`; checks `curve_count`,
`hair_roots_on_surface`, `hair_material`.
