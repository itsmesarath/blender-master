# Routing

`routing.json` maps each role to a sub-skill. Status: **core** = available now (all 22 sub-skills); **later** = backlog. A role whose sub-skill is not available goes to its fallback, and the brief records `routed_via`.

| Role | Sub-skill | Status | Fallback |
|---|---|---|---|
| `blockout` | `blockout-spatial-brief` | core | - |
| `environment` | `scene-environment` | core | - |
| `procedural` | `geometry-nodes` | core | - |
| `model` | `modeling-topology` | core | - |
| `sculpt` | `sculpting` | core | - |
| `retopo` | `retopology` | core | - |
| `uv` | `uv-texturing-baking` | core | - |
| `bake` | `uv-texturing-baking` | core | - |
| `materials` | `materials-shading` | core | - |
| `npr` | `npr-stylized` | core | - |
| `hair` | `hair-fur` | core | - |
| `rig_face` | `rigging-face` | core | - |
| `rig_body` | `rigging-body` | core | - |
| `simulation` | `physics-simulation` | core | - |
| `animation` | `animation` | core | - |
| `lighting` | `lighting-cameras` | core | - |
| `product` | `product-shots` | core | - |
| `render` | `render-compositing` | core | - |
| `edit` | `video-editing` | core | - |
| `script` | `scripting-automation` | core | - |
| `gp2d` | `grease-pencil-2d` | later | manual |
| `qa` | `qa-review` | core | - |
| `export` | `export-interchange` | core | - |
| `live` | `live-control-mcp` | core | - |

## Fallback meanings

- `manual`: the part becomes numbered UI steps for the user (exact menus and values for Blender 5.2). The runner marks it MANUAL and continues with parts that do not depend on hand work.
- another sub-skill: use the closest core tool (e.g. `uv` -> `modeling-topology` `uv_quick` for automatic UVs; `animation` -> `lighting-cameras` for camera orbits and turntables).

## Part kind -> sub-skill (for hand-written briefs)

| Part kind | Sub-skill |
|---|---|
| Stand-in layout, named shot cameras, red/green review marks | blockout-spatial-brief |
| Mesh building: bevelled hard edges, body base meshes, rooms with openings | modeling-topology |
| Fine organic detail, voxel rebuild, subdivision levels | sculpting |
| Clean light mesh fitted to a dense one, level-of-detail chains | retopology |
| Cuts, flattening, island layout, pixel density, map transfer | uv-texturing-baking |
| Node-driven generators, scattering, rows of copies | geometry-nodes |
| PBR, glass, metal, fabric, emission, procedural textures, texture wiring | materials-shading |
| Cel bands, ink lines, brush-stroke finishes | npr-stylized |
| Strands on heads and bodies, styling, strand shading | hair-fur |
| Armature, IK/FK, weights | rigging-body |
| Shape keys, face controls, drivers | rigging-face |
| Keyframes, cycles, noise, paths, NLA | animation; camera orbits also in lighting-cameras |
| Rigid, cloth and clothing, soft body, particles, fluid, smoke | physics-simulation |
| Lights, world, cameras, lenses, depth of field | lighting-cameras |
| Engine, samples, passes, denoise, compositor, output | render-compositing |
| Streets, landscapes, modular kits, set dressing | scene-environment |
| Packshots, turntables, reveals, logo and end cards | product-shots |
| Clip assembly, titles, audio, MP4 | video-editing |
| Batch jobs, generators, operators, add-ons | scripting-automation |
| Driving a live Blender | live-control-mcp |
| Final re-checks, contact sheets, written report | qa-review |
| Files for game engines and other apps, re-import proof | export-interchange |
