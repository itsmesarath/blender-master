# Example 02: game prop crate

A game asset: modelled directly at low resolution, unwrapped, given a worn painted-metal look and exported for an engine.

## Request

> Game-ready low-poly sci-fi supply crate for Unity, under 3k tris, bevelled edges and recessed panels, painted metal with worn edges; export FBX and glTF.

## Recognition

Type: **game_asset** (recognised from the request); skipped roles: retopo, bake.

## Assumptions written into the brief

- modelled directly at game resolution, so no high-poly and no retopology pass
- procedural materials preview the look; texture baking is left for the UV/baking sub-skill
- crate 60 cm cube plus 2 cm corner guards (64 cm overall)

## Parts

| Part | Sub-skill | Ops | Checks |
|---|---|---|---|
| P01-blockout | blockout-spatial-brief | `setup_scene`, `resolution`, `proxy`, `ground`, `camera`, `write_spatial_brief` | `objects_exist`, `cameras_exist`, `custom_prop`, `names_valid`, `bounds_size` |
| P02-model | modeling-topology | `box`, `panel_inset`, `hs_bevel`, `hide_proxies` | `objects_exist`, `scale_applied`, `names_valid`, `no_ngons`, `quad_ratio`, `manifold`, `normals_outward`, `bounds_size`, `on_ground`, `tri_budget` |
| P03-uv | uv-texturing-baking | `unwrap` | `uv_present`, `uv_in_bounds` |
| P05-lighting | lighting-cameras | `world`, `three_point` | `lights_exist`, `cameras_exist`, `camera_frames`, `exposure` |
| P04-materials | materials-shading | `material`, `assign` | `materials_filled` |
| P06-render | render-compositing | `render_preset`, `compositor`, `render_deliverables` | `render_ok`, `compositor_chain` |
| P07-qa | qa-review | `qa_run` | `files_exist`, `qa_all_pass` |
| P08-export | export-interchange | `prepare`, `export` | `files_exist`, `roundtrip_match` |

Parts run in dependency order. Parts with no edge between them may run in either order.

## What to look at

- The model stays under 3000 triangles and is mostly quads (`tri_budget`, `quad_ratio`).
- The paint stays dark olive, and bare metal shows only in small chips (`worn_metal` with `wear` 0.25).
- The FBX and glTF files re-import with the same objects, sizes and materials (`roundtrip_match`).

## Run it

```
export BLENDER_BIN=/path/to/blender
python3 blender-master/scripts/plan_project.py --request "$(cat examples/02-game-prop-crate/request.txt)" \
    --params examples/02-game-prop-crate/params.json --out out/02-game-prop-crate
python3 blender-master/scripts/run_project.py --brief out/02-game-prop-crate/brief/brief.json --out out/02-game-prop-crate
```

Outputs: `out/02-game-prop-crate/renders/`, `out/02-game-prop-crate/brief/qa_report.md`, `out/02-game-prop-crate/reports/`, `out/02-game-prop-crate/blend/`. Exports go to `exports/`.
