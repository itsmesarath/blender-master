# Hair guide

## Starting values (metres)
| Look | count | length | gravity | curl | clump | segments |
|---|---|---|---|---|---|---|
| short cropped | 4k-15k | 0.02-0.04 | 0.2 | 0 | 0.2 | 4 |
| medium straight | 5k-30k | 0.1-0.2 | 0.6 | 0 | 0.4 | 8 |
| long wavy | 10k-50k | 0.3-0.5 | 0.9 | 2-4, radius 0.01 | 0.5 | 12-16 |
| tight curls | 10k-40k | 0.08-0.15 | 0.3 | 5-8, radius 0.004 | 0.3 | 16 |
| beard | 2k-10k | 0.01-0.05 | 0.4 | 0.5 | 0.2 | 4-6 |
| eyebrows | 200-600 | 0.006-0.012 | 0.1 | 0 | 0.1 | 3 |
| short animal fur | 30k-100k per m2 | 0.01-0.03 | 0.15 | 0 | 0.15 | 4 |
Real heads have ~100k hairs; renders get away with 10-30% of that by using thicker strands.

## Stylized hair
- Large clumps (clump 0.8+, few guides) read as locks; strong colour and a toon material
  (npr-stylized) read as anime-like hair.
- Alternative: modelled hair shells (meshes), sculpted, for clay or cartoon styles.

## Shading
- Melanin: 0.1 blond, 0.5 brown, 0.85-1.0 dark brown to black; redness 0.6+ ginger.
- Roughness 0.25-0.4 healthy hair; 0.5+ dry or matte.
- Random Color 0.05-0.15 to avoid a plastic, single-tone look.
- EEVEE: hair strands render; enable shadows on lights and use a soft rim light.

## Attaching to a rig
- Rigid (head) hair: parent to the head bone (rigging-body `bind_extras`).
- Deforming surfaces (fur on a bending body): use the hair object's surface deform
  (Geometry Nodes "Deform Curves on Surface" in the node modifier) with the surface UV map set;
  the surface needs UVs and must be the evaluated, deformed mesh.

## Game hair cards
1. Render or bake strand clumps to a texture (colour, alpha, depth/flow).
2. Model strips (cards) following the groom, UVs mapped to card textures.
3. Alpha clip or dither in the engine; sort order matters for alpha blend.
4. Budget: 5k-30k triangles for hero hair.
