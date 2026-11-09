# NPR guide

## Recipes
| Look | Shading | Lines | Finish |
|---|---|---|---|
| anime / cel | 2 steps, shadow hue-shifted, small rim | outline 1-2% of object size | none or slight glare |
| cartoon (TV) | 3 steps, saturated | outline thicker, uniform | flat world |
| comic / ink | 2 steps, strong contrast | freestyle or line art with creases | posterize 4-6 |
| painterly | realistic or 4-step shading | none | Kuwahara 6-12 anisotropic, saturation 1.1-1.2 |
| watercolour-like | light toon, pale shadow | thin, grey lines | Kuwahara 4 + low posterize, paper-coloured background |
| low-poly flat | flat shading (no smooth), 3 steps | none | none |

## Shadow colours
Shadows read better as a hue shift: warm lit colour -> cooler shadow (toward blue/purple),
cool lit colour -> slightly warmer, less saturated shadow. Value drop 35-55%.

## Faces and hair in toon styles
- Face normals: transfer normals from a smooth proxy (sphere or simplified head) so the
  shadow shape stays clean; or paint a face shadow mask.
- Hair: big clumps with 2-step shading and a strong specular band (rim with high threshold).
- Eyes: emission materials or textures; outlines off on eyes.

## Line choices
- Inverted hull: fast, per-object, shows on silhouettes only (no inner creases).
- Line Art: contours, creases, intersections and material borders; tune crease angle.
- Freestyle: most control (line styles, thickness by distance), slowest.

## Painterly finish
- Kuwahara size scales with resolution: about 0.5-1% of image width.
- Anisotropic follows edges (stroke-like); classic gives blockier patches.
- Add a paper or canvas texture overlay in the compositor for print-like results.
