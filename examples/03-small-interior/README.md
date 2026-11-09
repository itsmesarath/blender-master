# Example 03: small interior

An interior: a room shell with a window opening, furniture, a planked wood floor, and daylight through the window plus a warm desk lamp.

## Request

> A small cosy bedroom interior with one window, a bed, a desk and chair, a bookshelf and a rug; warm afternoon daylight; one wide 24 mm shot from the doorway corner.

## Recognition

Type: **interior** (recognised from the request).

## Assumptions written into the brief

- room 4.0 x 3.5 m, ceiling 2.6 m, 12 cm walls, 10 cm floor slab
- window 1.2 x 1.3 m on the north wall above the bed, sill 0.9 m
- flat walls may carry n-gons around the opening: they never deform

## Parts

| Part | Sub-skill | Ops | Checks |
|---|---|---|---|
| P01-blockout | blockout-spatial-brief | `setup_scene`, `resolution`, `proxy`, `camera`, `review_layer`, `write_spatial_brief` | `objects_exist`, `cameras_exist`, `custom_prop`, `names_valid`, `bounds_size` |
| P02-model | modeling-topology | `room_shell`, `window_frame`, `furniture`, `hide_proxies` | `objects_exist`, `scale_applied`, `names_valid`, `manifold`, `normals_outward`, `bounds_size`, `on_ground` |
| P03-materials | materials-shading | `material`, `assign`, `assign_by_normal` | `materials_filled` |
| P04-lighting | lighting-cameras | `interior_daylight`, `practical` | `lights_exist`, `cameras_exist`, `camera_frames`, `exposure` |
| P05-render | render-compositing | `render_preset`, `render_deliverables` | `render_ok` |
| P06-qa | qa-review | `qa_run` | `files_exist`, `qa_all_pass` |

Parts run in dependency order. Parts with no edge between them may run in either order.

## What to look at

- The floor is staggered planks with their own tint and grain, not one continuous texture.
- The camera sees the bed, desk and chair (`camera_frames` on `frame_objects`).
- The room is not crushed to black away from the window (`exposure` `max_black`).

## Run it

```
export BLENDER_BIN=/path/to/blender
python3 blender-master/scripts/plan_project.py --request "$(cat examples/03-small-interior/request.txt)" \
    --params examples/03-small-interior/params.json --out out/03-small-interior
python3 blender-master/scripts/run_project.py --brief out/03-small-interior/brief/brief.json --out out/03-small-interior
```

Outputs: `out/03-small-interior/renders/`, `out/03-small-interior/brief/qa_report.md`, `out/03-small-interior/reports/`, `out/03-small-interior/blend/`.
