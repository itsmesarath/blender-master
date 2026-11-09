---
name: uv-texturing-baking
description: UV layout and texture baking in Blender 5.2 - seams by angle or along a plane, smart, angle-based, conformal and lightmap unwraps, island packing, texel-density reports, and Cycles bakes (AO, normal, diffuse colour, roughness, emit, combined; high-to-low projection) saved as PNG and wired back into materials - with checks for UV bounds, overlaps, texel spread and non-empty bakes. Use before texturing, for game assets, for exporting procedural looks as images, and whenever a mesh needs UVs that hold up.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Baking uses Cycles on CPU headless. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# UV, texturing and baking

## Procedure
1. **Topology final first** (retopo done, modifiers that change topology applied).
2. **Seams**:
   - Hard-surface: `mark_seams` by angle (and material borders).
   - Organic: seams where they hide: inner arms and legs, under the hair line, behind the
     ears, the body side or back. `seam_loop` marks edges on a plane (e.g. x = 0 for a split
     down the back).
3. **Unwrap** with `unwrap`:
   - `smart` for props and quick results;
   - `angle` or `conformal` to follow your seams;
   - `lightmap` for a second, non-overlapping light-bake layout.
   It packs by default; `pack` re-packs several objects into one atlas.
4. **Texel density**: `texel_report` (px/m at a texture size). Objects seen together should
   be within about 2x of each other (`texel_density`, `max_spread`).
5. **Bake** with `bake` (Cycles):
   - `ao`, `normal` (needs `high` for sculpt detail), `diffuse` (colour only), `roughness`,
     `emit`, `combined` (lighting baked in, for mobile or lightmaps).
   - Files go to `textures/<object>_<map>.png`; `wire` hooks them into the material
     (normal map, AO multiply, base colour, roughness).
6. **Verify**: `uv_in_bounds`, `uv_no_overlap`, `bake_nonempty`, then a render.

Map conventions, cage settings, padding and engine channel packing:
[references/uv-bake-guide.md](references/uv-bake-guide.md).

## Acceptance (default)
uv role: `uv_present`, `uv_in_bounds`. bake role: `bake_nonempty`. Add `uv_no_overlap`
(except deliberate mirrored/stacked islands) and `texel_density` for game assets.

## Pitfalls
- Baking normals without UVs or with overlapping islands: garbage. Check first.
- Cage extrusion too small (missed detail) or too large (wrong surface hit); start at
  1-3% of object size.
- Normal maps need Non-Color; colour maps sRGB. The op sets this per map.
- Stacked/mirrored islands save space but break AO and lightmaps; offset them by 1 UDIM
  tile while baking or bake on a unique layout.
- A bake without margin (padding) bleeds seams at lower mip levels; 8-16 px at 1-2k.

## Scripts
`scripts/ops.py`: `mark_seams`, `seam_loop`, `unwrap`, `pack`, `texel_report`, `bake`; checks
`uv_in_bounds` (auto-fix: re-pack), `uv_no_overlap`, `texel_density`, `bake_nonempty`.
