---
name: render-compositing
description: Configures Blender 5.2 rendering and compositing - Cycles vs EEVEE choice, preview and final presets, AgX colour management, denoising in the renderer or the compositor, mist and glare in the 5.x node-group compositor, transparent film and shadow catchers, PNG/EXR output, and rendering every deliverable camera or frame range. Use when a part needs render settings, passes, denoise, compositor work, output formats or final renders.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Part of blender-master; scripts expect its lib/ on sys.path.
metadata:
  parent: blender-master
  status: core
---

# Rendering and compositing

Turn a lit scene into the files the user asked for, as fast as the quality bar allows, and prove
the files are right.

## Procedure
1. **Engine** (see [references/render-guide.md](references/render-guide.md)):
   - Cycles: accurate glass, caustic-ish light, interiors, anything judged by realism. Works on
     CPU everywhere, including headless servers.
   - EEVEE (`BLENDER_EEVEE` in 5.x): fast look-dev, stylised, motion graphics. Background mode
     needs a GPU or software OpenGL; test one tiny frame before committing to it.
2. **Preset** (`render_preset`): `preview` (low samples, adaptive, denoised, small res) while
   iterating; `final` (more samples, full res) for deliverables. View transform AgX; `look` and
   `exposure` for grading.
3. **Compositor** (`compositor`): optional chain Denoise -> Mist -> Glare -> Group Output on the
   5.x node-group compositor. Use **one** denoiser: either the renderer's or the compositor's.
4. **Output** (`output_format`): `png8` for web, `png16` for grading in another tool,
   `exr_multilayer` to keep every pass for later compositing. `media_type` is set before
   `file_format`.
5. **Render** (`render_deliverables`): every deliverable camera to `renders/<camera>.png`, or
   frame lists for sequences.
6. **Verify**: files exist, right size, not near-black, alpha present when transparency was asked.

## Transparent and shadow-catcher shots
- `render_preset(transparent=True)` turns on transparent film; output PNG RGBA or EXR.
- For a product on a transparent background with a soft shadow: a ground plane with
  *Object > Visibility > Shadow Catcher* on (Cycles), transparent film on.

## Acceptance (default)
`render_ok` for each deliverable camera; `compositor_chain` when a compositor denoiser is used.
Visual: look at every final render at 100 % for fireflies, noise in shadows, banding and
denoiser smearing on fine textures.

## Pitfalls
- 4.x scripts touching `scene.node_tree` or a Composite node: both are gone in 5.x.
- Denoising twice (render + compositor): waxy look.
- EEVEE in CI with no display: may fail or render black; use Cycles CPU for checks.
- Huge sample counts to hide fireflies: clamp indirect light (e.g. 10) or fix the light source.
- Rendering at preview resolution and upscaling for delivery.

## Scripts
- `scripts/ops.py`: `render_preset`, `compositor`, `output_format`, `render_deliverables`,
  `eevee_preset`.
- `lib/bm_compositor.py`: tree, denoise, mist, glare helpers. `lib/bm_render.py`: settings,
  stills, frame ranges, contact sheets.
