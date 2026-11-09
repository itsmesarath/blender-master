# Sculpt workflow notes

## Resolution ladder
| Stage | Typical density (human-sized figure) | Tools |
|---|---|---|
| primary forms | 5k-50k verts | grab/snake hook, inflate, clay strips, voxel remesh to re-even |
| secondary forms | 100k-500k | crease, clay, pinch, layer; multires level 2-3 |
| tertiary detail | 1M+ | noise/alpha stamps, draw sharp, multires top level |
Move up only when the current stage reads correctly from the camera distance that matters.

## Interactive brush plan (UI session)
1. Symmetry X on; dyntopo off while blocking (voxel remesh to re-even instead).
2. Grab / Elastic Deform for silhouette; check from front, side, 3/4 and from below.
3. Clay Strips to build planes (cheekbones, chest, pelvis); Smooth sparingly.
4. Crease / Pinch for folds and edges; Draw Sharp for fine cuts.
5. Masks + Layer for raised panels, scales, straps.
6. Turn symmetry off at the end for asymmetry (hair parting, posture, scars).
7. Save versioned copies before remesh, multires apply or symmetrize.

## Proportion checks for figures
- Height in heads: about 7-7.5 realistic, 4-6 stylized, 2-3 chibi.
- Elbows near the waist, wrists near the crotch line in a relaxed pose.
- Shoulder width about 2 heads (realistic male), less for stylized or young characters.
- Look at the silhouette in flat black; a readable silhouette beats surface detail.

## Detail and baking
- Detail must be bigger than one texel: at 2048 px on a 1.8 m figure with ~60% UV usage,
  one texel is roughly 1-2 mm. Pores need either a higher-resolution face map or a tiling
  detail normal map.
- Cavities read through AO and curvature bakes; exaggerate slightly for stylized looks.

## Hard-surface sculpting
- Use voxel remesh to fuse, then planar trims and polish to flatten; or model hard parts in
  modeling-topology and only sculpt damage and wear.

## Scripted brush equivalents (headless)
| Brush intent | Op |
|---|---|
| move a mass | `grab` (soft sphere falloff) |
| add volume | `inflate` (along normals) |
| groove / fold | `crease` (polyline) |
| surface texture | `surface_noise` (symmetric option) |
| relax | `smooth` (volume-preserving Laplacian) |
| mirror repair | `symmetrize` |
