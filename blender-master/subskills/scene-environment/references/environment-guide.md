# Environment guide

## Scale references
| Thing | Size |
|---|---|
| door | 0.9 x 2.05 m |
| storey height | 2.8-3.2 m (residential), 3.5-4.5 m (commercial) |
| stair step | 17-18 cm rise, 28 cm tread |
| road lane | 3.0-3.6 m |
| sidewalk | 1.8-3 m, curb 12-15 cm |
| street lamp | 6-10 m, spaced 25-35 m |
| car | 4.5 x 1.8 x 1.5 m |
| tree (street) | 6-12 m |

## Composition for sets
- Foreground / midground / background layers; overlap them to read depth.
- Leading lines (roads, walls, rails) toward the subject.
- Darker or desaturated foreground frames, brightest values near the subject.
- Fog and mist separate layers (render-compositing mist pass).

## Modular kits
- One grid (1, 2 or 4 m) for the whole kit; heights in fixed steps.
- Origins on grid corners, pieces facing +Y, pivot at floor level.
- Trim pieces (corners, caps, skirting) hide seams between modules.
- Use linked copies (shared mesh) for repeated pieces; Geometry Nodes for big repetitions.
- Game levels: keep collision simple (boxes), lightmap UVs on every piece.

## Terrain
- Large forms first (noise scale small), then detail with a second, finer layer or sculpt.
- Flatten where the action is; paths and roads cut into the terrain read better than ones
  floating on top.
- Materials: blend by slope (rock on steep faces) and height (snow on peaks) with the
  geometry normal and position in the shader.

## Performance
- Instances for vegetation and props; realize only what must be edited.
- Distant objects: low-poly, simple materials, or image cards.
- Camera clipping: clip start 0.1 m, end just past the far background.
