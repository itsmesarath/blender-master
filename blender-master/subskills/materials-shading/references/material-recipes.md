# Material recipes (Principled BSDF, Blender 5.x names)

Colours are linear RGB. Values are starting points; judge under the final lighting.

| Material | Base Color | Metallic | Roughness | Other |
|---|---|---|---|---|
| matte plastic | any, 0.05-0.8 | 0 | 0.45-0.65 | - |
| glossy plastic | any | 0 | 0.1-0.25 | Coat Weight 0.2-0.4 for a lacquered look |
| rubber | 0.02-0.05 | 0 | 0.7-0.9 | - |
| polished metal | steel 0.9, gold (1, 0.72, 0.33), copper (0.95, 0.6, 0.45) | 1 | 0.05-0.15 | - |
| brushed metal | as above | 1 | 0.25-0.4 | Anisotropic 0.5-0.8 + tangent along the brush direction |
| painted metal | paint colour | 0 | 0.3-0.5 | Coat Weight 0.3-0.6; wear mask mixing to bare metal |
| clear glass | 1, 1, 1 | 0 | 0-0.02 | Transmission Weight 1, IOR 1.45-1.52 |
| tinted glass | colour of the tint, keep above 0.3 | 0 | 0-0.05 | Transmission Weight 1 |
| water | 1, 1, 1 | 0 | 0-0.05 | Transmission 1, IOR 1.33; volume absorption for deep water |
| ceramic / porcelain | 0.8-0.9 | 0 | 0.2-0.35 | Coat Weight 0.5 |
| fabric | any, 0.1-0.6 | 0 | 0.7-0.95 | Sheen Weight 0.3-0.8 |
| paper / backdrop | 0.6-0.85 | 0 | 0.85-0.95 | - |
| plaster / painted wall | 0.6-0.8 | 0 | 0.85-0.95 | slight bump from noise |
| wood (finished) | brown range | 0 | 0.35-0.55 | grain from waves/noise; Coat for varnish |
| concrete | 0.3-0.5 grey | 0 | 0.75-0.9 | noise colour and bump at two scales |
| skin (basic) | (0.8, 0.6, 0.5) range | 0 | 0.4-0.5 | Subsurface Weight 0.2-0.4, Radius (1, 0.35, 0.2), Scale 0.005-0.02 |
| emissive panel | black | 0 | any | Emission Color + Strength 2-20 |

## Procedural patterns (no image files)

- **Wood grain**: a Wave texture in bands mode along the board's long axis, distorted by noise,
  through a colour ramp between a dark and a light brown; a fine noise into Bump. Scale so a
  board shows 6-20 grain lines across its width.
- **Concrete**: two Noise textures (large blotches, fine speckle) mixed into the base colour and
  into roughness; the fine one also drives Bump at low strength.
- **Worn paint on metal**: a noise or edge mask decides where paint is missing; where it is,
  metallic 1 and lower roughness. Keep the wear subtle on hero props.

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| magenta surface | missing image file, or the placeholder from the fixer | relink or replace the image; assign the real material |
| black glass | no environment or backdrop to refract; too few transmission bounces | add a world or backdrop; raise transmission bounces |
| plastic looks like clay | roughness too high, no reflections in scene | lower roughness; add a large soft light or reflective world |
| metal looks grey and flat | nothing to reflect | studio strip lights or an environment |
| noisy subsurface | tiny scale and few samples | raise samples or reduce SSS scale |
| tiled pattern visible | texture scale too large on big surfaces | add a second noise at a different scale |
