# Example 04: character full run

The full character pipeline, in one run: skin-modifier body, sculpt detail, retopology back onto the sculpt, UVs, normal and AO bakes, clothing zones, groomed hair, face shapes with controls, a body rig with leg IK, a wave animation, a render and an FBX round-trip.

## Request

> A friendly stylized explorer character for a game: A-pose body sculpted and baked down to a clean low-poly mesh, short dark hair, a simple face rig (jaw, smile, brows), a body rig with IK, a short waving-hello animation, one hero render and an FBX for Unreal.

## Recognition

Type: **character** (pinned with `type_override` in params).

## Assumptions written into the brief

- type fixed to character (the request also reads as a game asset); stylized means proportions and colour here, so no toon-shading part
- 1.8 m stylized adult proportions (about 7.5 heads), A-pose, facing -Y, feet on z = 0
- base mesh from a joint skeleton (Skin modifier); the sculpt is a subdivided copy with surface detail, so retopology fits the clean base back onto it
- clothing is material zones on the body mesh (shirt, trousers, boots), not separate garments
- face rig uses shape keys driven by four control empties; eyes are separate spheres parented to the head bone
- animation: 48 frames at 24 fps, wave hello with the right arm, small head tilt, breathing, a spoken 'hi' on the jaw
- arms are FK for the wave; legs get IK so the feet stay planted

## Parts

| Part | Sub-skill | Ops | Checks |
|---|---|---|---|
| P01-blockout | blockout-spatial-brief | `setup_scene`, `resolution`, `proxy`, `ground`, `camera`, `write_spatial_brief` | `objects_exist`, `cameras_exist`, `custom_prop`, `names_valid`, `bounds_size` |
| P02-model | modeling-topology | `skin_figure`, `sphere`, `box`, `hide_proxies` | `objects_exist`, `scale_applied`, `names_valid`, `no_ngons`, `quad_ratio`, `manifold`, `normals_outward`, `bounds_size`, `on_ground`, `tri_budget` |
| P03-sculpt | sculpting | `make_high`, `inflate`, `grab`, `crease`, `surface_noise`, `smooth` | `objects_exist`, `sculpt_detail`, `symmetry_ok` |
| P12-lighting | lighting-cameras | `world`, `three_point` | `lights_exist`, `cameras_exist`, `camera_frames`, `exposure` |
| P04-retopo | retopology | `shrinkwrap_fit` | `objects_exist`, `scale_applied`, `quad_ratio`, `surface_distance`, `tri_budget` |
| P05-uv | uv-texturing-baking | `unwrap`, `texel_report` | `uv_present`, `uv_in_bounds`, `uv_no_overlap` |
| P06-bake | uv-texturing-baking | `bake` | `bake_nonempty` |
| P09-rig_face | rigging-face | `region_key`, `split_lr`, `face_control`, `drive` | `shape_keys_valid`, `drivers_resolve` |
| P07-materials | materials-shading | `material`, `assign`, `assign_box`, `use_textures`, `assign_by_normal` | `materials_filled` |
| P08-hair | hair-fur | `hair_material`, `groom` | `curve_count`, `hair_roots_on_surface` |
| P10-rig_body | rigging-body | `armature_from_joints`, `ik_limbs`, `bind`, `bind_extras` | `objects_exist`, `weights_valid`, `pose_deform_ok`, `ik_rest_stable` |
| P11-animation | animation | `frame_range`, `pose_keys`, `wave`, `keyframes`, `bake_shape_keys` | `anim_present`, `no_pops` |
| P13-render | render-compositing | `render_preset`, `compositor`, `render_deliverables` | `render_ok` |
| P14-qa | qa-review | `qa_run` | `files_exist`, `qa_all_pass` |
| P15-export | export-interchange | `export` | `files_exist`, `roundtrip_match` |

Parts run in dependency order. Parts with no edge between them may run in either order.

## What to look at

- The low mesh hugs the sculpt (`surface_distance`), and the baked maps are not flat (`bake_nonempty`).
- Every vertex is weighted to at most 4 bones, and the test poses deform cleanly (`weights_valid`, `pose_deform_ok`).
- The face controls drive jaw, smile and brow shapes (`drivers_resolve`).
- The render at frame 24 shows the wave. The FBX re-imports with the meshes, the armature, the shape keys and the animation.

## Run it

```
export BLENDER_BIN=/path/to/blender
python3 blender-master/scripts/plan_project.py --request "$(cat examples/04-character-full-run/request.txt)" \
    --params examples/04-character-full-run/params.json --out out/04-character-full-run
python3 blender-master/scripts/run_project.py --brief out/04-character-full-run/brief/brief.json --out out/04-character-full-run
```

Outputs: `out/04-character-full-run/renders/`, `out/04-character-full-run/brief/qa_report.md`, `out/04-character-full-run/reports/`, `out/04-character-full-run/blend/`. Exports go to `exports/`.
