# QA checklists by project type

Every project: names valid, scale applied, no empty material slots, no missing images, no
`TMP_` objects left, proxies hidden from render, every deliverable rendered at the right size.

| Type | Add these checks | Look for |
|---|---|---|
| hard-surface prop | bounds vs brief, manifold, normals outward, bevel modifier present | shading artefacts on flat faces, uneven bevel widths |
| product shot | camera_frames on every camera, exposure, render_ok with alpha if transparent | dust-free clean reflections, label legible, no visible floor edge |
| interior | no_overlaps between furniture, on_ground per object, camera inside the room | light leaks at wall corners, z-fighting, furniture floating |
| environment | camera coverage, triangle count per camera view | repeated tiling, empty areas in frame, scale of props vs people |
| character / creature | quad_ratio, no_ngons, manifold, symmetry | pinching at joints, poles on bends, hair through skin |
| game asset | tri_budget, uv_present, scale_applied, export round-trip | hidden faces, pivot at base, smoothing correct after import |
| procedural system | inputs change the result, evaluation time | degenerate output at extreme inputs |
| simulation | cache exists, objects moved, bounds stay sane (no explosion) | intersections, jitter at rest |
| animation | frame range, loop continuity (first == last + 1), F-curve count | pops, sliding feet, camera bumps |
| render-only / look-dev | exposure, render_ok, compositor chain | noise in shadows, fireflies, denoiser smearing |

## Seeded-failure test
Run QA on a deliberately broken scene (an object with unapplied scale, an empty material slot,
a wrongly named mesh). It must fail and name each problem; a QA that passes a broken scene is
itself broken.

## Review notes format
```
[red] GEO_crate_lid - lid floats 4 mm above the body -> modeling-topology: place z=0.596
[green] CAM_hero - add a small rim light from back-left -> lighting-cameras
```
