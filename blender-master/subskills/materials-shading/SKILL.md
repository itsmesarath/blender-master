---
name: materials-shading
description: Creates and assigns Blender 5.2 materials - Principled BSDF presets for plastic, metal, glass, liquid, ceramic, fabric, paper, plaster, skin and emission, procedural wood, concrete and worn paint that need no image files, and per-face material slots. Use when a part needs materials, shaders, PBR values, texture setup, or fixing pink/missing textures and empty slots.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Part of blender-master; scripts expect its lib/ on sys.path.
metadata:
  parent: blender-master
  status: core
---

# Materials and shading

Give every surface a believable, physically plausible material that reads from the hero camera
under the planned lighting, with no empty slots and no missing image files.

## Procedure
1. **List surfaces** from the brief and the model: each distinct real material is one `MAT_`.
   Parts of one object that differ (label band, recessed panel, rubber foot) use extra slots.
2. **Create** with `material(name, preset, color=..., overrides={...})`. Presets cover the common
   cases; overrides take any Principled input by its 5.x name (`Base Color`, `Roughness`,
   `Transmission Weight`, `Coat Weight`, `Sheen Weight`, `Subsurface Weight`, `Emission Color`,
   `Emission Strength`...). Procedural presets (`wood`, `concrete`, `worn_metal`) take
   `procedural_args` (colours, scale, wood `axis`).
3. **Assign** with `assign(material, targets)` (names or a prefix). `replace=False` adds a slot
   instead of clearing; face indices are preserved. Per-face: `assign_by_normal` (tops, fronts)
   and `assign_band` (a height range, e.g. a label), `assign_box` (faces inside a box: clothing
   zones on one body mesh). Baked or painted maps: `use_textures` wires image files in.
4. **Preview** under the real lighting. Materials judged under the default grey world lie.
5. **Check**: no empty slots or missing images, and the preview shows the intended contrast
   between materials.

Values, ranges and recipes: [references/material-recipes.md](references/material-recipes.md).

## Rules of thumb
- Metallic is 0 or 1. In between only for transitions such as dust or wear masks.
- Real colours are rarely pure: keep base colour between about 0.02 and 0.9 (linear) except
  for emission. Pure black or white surfaces render unnaturally.
- Roughness carries realism more than colour: vary it with a noise texture on large surfaces.
- Glass needs thickness (two surfaces) and something to refract: a backdrop or environment.
- Thin film, coat and sheen are off unless the real material has them.
- Subsurface scale is in scene units (metres): skin ~0.005-0.02, wax ~0.02-0.05.
- Emission for practicals (screens, bulbs): strength in a range that keeps exposure sane; light
  the scene with real lights, not only emissive surfaces.

## Acceptance (default)
`materials_filled` on `GEO_` (every mesh has materials, no empty slots, no missing image files).
The fixer assigns a bright magenta placeholder so the gap is obvious and reported, never hidden.
Visual: materials distinguishable and plausible in the hero preview.

## Manual mode
Material Properties > New. In the Shader Editor, set Principled inputs by name. Shift+A >
Texture > Noise/Wave for procedural variation; Ctrl+T (with the Node Wrangler extension, if
the user has it) adds mapping nodes.

## Scripts
- `scripts/ops.py`: `PRESETS`, `material`, `assign`, `assign_by_normal`, `assign_band`,
  `assign_box`, `use_textures`.
