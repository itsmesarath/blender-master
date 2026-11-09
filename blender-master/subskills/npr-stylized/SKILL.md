---
name: npr-stylized
description: Non-photoreal looks in Blender 5.2 - toon and cel materials with 2-4 flat bands (a fixed-light version that renders identically in Cycles and EEVEE, or a Shader-to-RGB version driven by real lights in EEVEE), rim bands, inverted-hull outlines, Grease Pencil Line Art and Freestyle ink lines, painterly and poster finishes in the compositor (Kuwahara brush strokes, posterize, glare, saturation), flat backgrounds - with checks for a complete setup and a render that reads as flat bands. Use for anime and cartoon styles, comic and ink looks, painterly stills, stylized ads and game-like renders.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Shader to RGB works in EEVEE only; the other ops work in both engines. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# NPR and stylized looks

Decide the look in one sentence first ("flat 3-tone anime, black outlines, warm paper
background" or "oil-painted dusk, soft strokes, no lines") and pick the ops from it.

## Procedure
1. **Shapes first**: stylized looks expose silhouettes; simplify and exaggerate forms.
2. **Shading**: `toon_material` per colour - `steps` (2 hard anime, 3-4 softer), `shadow`
   colour (shift the hue toward blue/purple instead of just darker), `rim` edge band, mode
   `any` (fixed `light_dir`, engine independent) or `eevee` (reacts to scene lights).
3. **Lines** (choose one or combine):
   - `outline` inverted hull - cheap, any engine, per-object width;
   - `line_art` - Grease Pencil strokes from contours and creases (scene or collection);
   - `freestyle` - ink lines in either engine, slower, technical/comic looks.
4. **Background**: `flat_world` (plain colour, Standard view transform so picked colours stay
   true).
5. **Finish** in the compositor: `painterly` (Kuwahara brush size, optional posterize bands,
   glare bloom, saturation).
6. **Check**: `npr_setup` (every object styled, outlines present) and `npr_flat` on the render.

Style recipes (anime, comic, watercolour-like, painterly) and toon hair and faces:
[references/npr-guide.md](references/npr-guide.md).

## Acceptance (default)
`materials_filled`; add `npr_setup` and `npr_flat` (on the final render) for toon looks.

## Pitfalls
- Filmic/AgX view transforms desaturate toon colours; use Standard for flat looks.
- Toon shading on dense noisy normals gives speckled bands; smooth shading, clean normals,
  or a normal edit (data transfer from a sphere for faces).
- Outline width in metres: scale it with the object (larger for big objects, thinner for
  small props); hide outlines on tiny details.
- Kuwahara on a noisy render paints noise; denoise first, then stylize.
- Emission-based toon materials do not cast or receive scene shadows; use `eevee` mode for
  cast shadows.

## Scripts
`scripts/ops.py`: `toon_material`, `outline`, `line_art`, `freestyle`, `painterly`,
`flat_world`; checks `npr_setup`, `npr_flat`.
