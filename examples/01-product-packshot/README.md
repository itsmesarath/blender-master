# Example 01: product packshot

A still packshot: two lathed parts, studio lighting and two deliverable cameras.

## Request

> Studio packshot of a perfume bottle on a seamless light-grey sweep, soft lighting, 85 mm hero shot plus a straight front view.

## Recognition

Type: **product_shot** (recognised from the request).

## Assumptions written into the brief

- bottle ~7 cm wide, 13 cm tall with cap (typical 50 ml size)
- still images only; no motion beat

## Parts

| Part | Sub-skill | Ops | Checks |
|---|---|---|---|
| P01-blockout | blockout-spatial-brief | `setup_scene`, `resolution`, `proxy`, `camera`, `review_layer`, `write_spatial_brief` | `objects_exist`, `cameras_exist`, `custom_prop`, `names_valid`, `bounds_size` |
| P02-model | modeling-topology | `lathe`, `cyclorama`, `hide_proxies` | `objects_exist`, `scale_applied`, `names_valid`, `no_ngons`, `manifold`, `normals_outward`, `bounds_size`, `on_ground` |
| P03-materials | materials-shading | `material`, `assign` | `materials_filled` |
| P04-product | product-shots | `world`, `softbox_studio`, `depth_of_field` | `lights_exist`, `cameras_exist`, `camera_frames`, `exposure` |
| P05-render | render-compositing | `render_preset`, `render_deliverables` | `render_ok` |
| P06-qa | qa-review | `qa_run` | `files_exist`, `qa_all_pass` |

Parts run in dependency order. Parts with no edge between them may run in either order.

## What to look at

- The glass reads amber and the cap reads gold, with highlights that are not clipped (`exposure`).
- The bottle stays inside the frame with a margin on both cameras (`camera_frames`).
- Depth of field is focused on the bottle on the hero camera.

## Run it

```
export BLENDER_BIN=/path/to/blender
python3 blender-master/scripts/plan_project.py --request "$(cat examples/01-product-packshot/request.txt)" \
    --params examples/01-product-packshot/params.json --out out/01-product-packshot
python3 blender-master/scripts/run_project.py --brief out/01-product-packshot/brief/brief.json --out out/01-product-packshot
```

Outputs: `out/01-product-packshot/renders/`, `out/01-product-packshot/brief/qa_report.md`, `out/01-product-packshot/reports/`, `out/01-product-packshot/blend/`.
