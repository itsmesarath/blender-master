# Example 05: procedural city block

A procedural set: geometry-nodes buildings with seeded random heights, trees scattered over a park, a row of street lamps, a street with sidewalks, and hills in the distance.

## Request

> A procedural city block for a previs shot: a 3 x 3 grid of buildings with random heights driven by geometry nodes, a two-lane street with sidewalks along one side, a row of street lamps, a small park with scattered trees, gentle hills in the distance, late-afternoon sun, one high wide establishing render. Changing the seed should give a new skyline.

## Recognition

Type: **environment** + modifiers procedural (pinned with `type_override` in params).

## Assumptions written into the brief

- 3 x 3 lots of 8 m with 4 m alleys (32 m square block) centred on the origin
- street along Y west of the block, park south of it (towards camera); terrain flat inside 45 m
- trees and lamps are simple stand-ins for previs, instanced by geometry nodes
- model checks target the instance sources (GEO_src_*); open meshes (terrain, street lines) are not held to closed-mesh checks

## Parts

| Part | Sub-skill | Ops | Checks |
|---|---|---|---|
| P01-blockout | blockout-spatial-brief | `setup_scene`, `resolution`, `proxy`, `camera`, `write_spatial_brief` | `objects_exist`, `cameras_exist`, `custom_prop`, `names_valid` |
| P02-environment | scene-environment | `terrain`, `street` | `objects_exist`, `names_valid` |
| P04-model | modeling-topology | `box`, `lathe`, `hide_proxies` | `objects_exist`, `scale_applied`, `names_valid`, `manifold`, `normals_outward`, `on_ground` |
| P03-procedural | geometry-nodes | `building_block`, `scatter`, `instance_row` | `objects_exist`, `gn_evaluates`, `gn_instances`, `gn_input_changes` |
| P05-materials | materials-shading | `material`, `assign`, `assign_box` | `materials_filled` |
| P06-lighting | lighting-cameras | `world`, `sun` | `lights_exist`, `cameras_exist`, `camera_frames`, `exposure` |
| P07-render | render-compositing | `render_preset`, `compositor`, `render_deliverables` | `render_ok` |
| P08-qa | qa-review | `qa_run` | `files_exist`, `qa_all_pass` |

Parts run in dependency order. Parts with no edge between them may run in either order.

## What to look at

- Changing the building seed gives a new skyline (`gn_input_changes`).
- The tree count stays in the planned range (`gn_instances`).
- Materials applied to the node-built geometry show in the render (object-linked slots).

## Run it

```
export BLENDER_BIN=/path/to/blender
python3 blender-master/scripts/plan_project.py --request "$(cat examples/05-procedural-city-block/request.txt)" \
    --params examples/05-procedural-city-block/params.json --out out/05-procedural-city-block
python3 blender-master/scripts/run_project.py --brief out/05-procedural-city-block/brief/brief.json --out out/05-procedural-city-block
```

Outputs: `out/05-procedural-city-block/renders/`, `out/05-procedural-city-block/brief/qa_report.md`, `out/05-procedural-city-block/reports/`, `out/05-procedural-city-block/blend/`.
