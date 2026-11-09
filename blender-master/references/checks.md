# Check catalogue

Checks live in `lib/bm_checks.py` (generic) and in sub-skill `scripts/ops.py` files (specialised).
Each returns `(passed, value, expected, detail)` and is written into the part report.
`objects` selectors: a prefix ending in `_` (`"GEO_crate_"`), an exact name, a list, or `"*"`.

| Check | Args (defaults) | Passes when | Auto-fix |
|---|---|---|---|
| `objects_exist` | `names`, `prefix`, `min_count=1`, `types` | the named / prefixed objects exist | - |
| `names_valid` | `ignore_prefixes=("TMP_",)` | every object uses a known prefix | renames by type (mesh -> GEO_, light -> LGT_ ...) |
| `bounds_size` | `objects="GEO_"`, `target=[x,y,z]` (null = any), `tol=0.05` | group's world size within tol (relative) | - |
| `max_dimension` | `objects`, `max_m=1.0`, `min_m=0` | largest side in range | - |
| `no_overlaps` | `objects`, `allow=[[a,b],...]` | no two meshes intersect (BVH), except allowed pairs | - |
| `on_ground` | `objects`, `ground_z=0`, `eps=0.002` | lowest point of the group touches ground | moves the group down/up |
| `no_floating` | `objects`, `ground_z=0` | every object touches the ground or another object | - |
| `scale_applied` | `objects` | scale is (1,1,1), none negative | applies scale |
| `quad_ratio` | `objects`, `min_ratio=0.9` | share of quads in evaluated faces | - |
| `no_ngons` | `objects` | no faces with more than 4 sides | - |
| `manifold` | `objects`, `allow_open=[names]` | no boundary or non-manifold edges | - |
| `normals_outward` | `objects` | closed meshes have positive signed volume | recalculates normals outward |
| `tri_budget` | `objects`, `max_tris=10000`, `evaluated=True` | triangle count after modifiers within budget | - |
| `materials_filled` | `objects` | every mesh has materials, no empty slots, no missing image files | magenta placeholder (still visible in renders, so it gets noticed) |
| `uv_present` | `objects` | every mesh has a UV map | - |
| `modifier_present` | `objects`, `types=["BEVEL"]`, `min_objects=1` | at least N objects carry those modifiers | - |
| `cameras_exist` | `names=["CAM_hero"]` | cameras exist | - |
| `camera_frames` | `camera`, `objects`, `margin=0.04`, `min_fill=0.15` | all bounding-box corners inside the frame with margin; subject fills enough | dolly an auto-placed camera (lighting-cameras); hand-placed cameras -> ASK |
| `lights_exist` | `min_count=1` | at least N lights (or an emissive world) | - |
| `exposure` | `camera`, `mean_min=0.12`, `mean_max=0.75`, `max_clipped=0.02`, `max_black=0.35` | probe render's mean luminance and clipped/black fractions in range | scales lights and world strength (lighting-cameras) |
| `render_ok` | `pattern="renders/*.png"`, `min_count=1`, `size`, `need_alpha` | files exist, right size, not near-black, alpha present if asked | - |
| `files_exist` | `patterns=[...]` | each glob under the project folder matches | - |
| `compositor_chain` | `contains=["CompositorNodeDenoise"]` | compositor contains these nodes and ends in Group Output | - |
| `custom_prop` | `objects="PRX_"`, `key="brief_note"` | every object has the custom property | - |
| `roundtrip_match` | `size_tol=0.01` | re-imported exports match object count, sizes and material count (export-interchange) | - |
| `qa_all_pass` | - | every row of the final QA passed (qa-review) | - |
| `script_ran` | - | the part's script ran without error (scripting-automation) | - |

## Sub-skill checks

Registered when the owning sub-skill is loaded (the QA part loads every part's sub-skill).

| Check | Sub-skill | Args (defaults) | Passes when | Auto-fix |
|---|---|---|---|---|
| `gn_evaluates` | geometry-nodes | `objects="GEO_"` | every node-based object evaluates to non-empty geometry | - |
| `gn_instances` | geometry-nodes | `target`, `min_count=1`, `max_count` | instance / point count in range | - |
| `gn_input_changes` | geometry-nodes | `target`, `input`, `value` | changing the exposed input changes the result | - |
| `sculpt_detail` | sculpting | `objects`, `min_verts=20000` | enough resolution for the sculpt | - |
| `symmetry_ok` | sculpting | `objects`, `tol=0.002` | every vertex has a mirror partner across X | symmetrize |
| `surface_distance` | retopology | `low`, `high`, `max_mean=0.003`, `max_max` | low-poly lies on the high-poly surface | re-shrinkwrap |
| `uv_in_bounds` | uv-texturing-baking | `objects`, `eps=1e-3` | all UVs inside 0-1 | pack islands |
| `uv_no_overlap` | uv-texturing-baking | `objects`, `max_ratio=0.01`, `res=256` | overlapping UV area below the ratio | - |
| `texel_density` | uv-texturing-baking | `objects`, `tex=1024`, `min_px_m`, `max_spread=2.0` | density even across objects (and above the minimum) | - |
| `bake_nonempty` | uv-texturing-baking | `pattern="textures/*.png"`, `min_std=0.003` | baked maps exist and are not flat | - |
| `curve_count` | hair-fur | `prefix`, `min_curves=100`, `max_curves` | strand count in range | - |
| `hair_roots_on_surface` | hair-fur | `prefix`, `tol=0.004` | strand roots sit on the surface | - |
| `hair_material` | hair-fur | `prefix` | hair objects carry a hair shader | - |
| `weights_valid` | rigging-body | `objects`, `max_influences=4`, `tol=0.01` | every vertex weighted, normalised, within the influence limit | clean weights |
| `pose_deform_ok` | rigging-body | `objects`, `rig="RIG_char"`, `pose`, `max_stretch=3.0` | test poses deform without collapse or explosion | - |
| `ik_rest_stable` | rigging-body | `rig`, `tol=0.002` | IK does not move bones at rest | - |
| `shape_keys_valid` | rigging-face | `objects`, `min_keys=1`, `max_move=0.2` | every key moves vertices and stays bounded | - |
| `drivers_resolve` | rigging-face | `objects` | all drivers valid and respond to their controls | - |
| `anim_present` | animation | `objects="*"`, `min_curves=1`, `min_range` | animated channels in the frame range | - |
| `loop_ok` | animation | `objects`, `tol=1e-3` | first and last frames match | make cyclic |
| `no_pops` | animation | `objects`, `ratio=6.0`, `floor` | no single-frame jumps | - |
| `sim_moved` | physics-simulation | `objects`, `frame`, `min_move=0.01` | simulated objects move | - |
| `no_explosion` | physics-simulation | `objects`, `max_growth=3.0`, `floor_z`, `max_height=50` | simulation stays bounded | - |
| `sim_settled` | physics-simulation | `objects`, `tail=3`, `max_speed=0.02` | objects come to rest at the end | - |
| `no_zfight` | scene-environment | `objects`, `eps=2e-4`, `max_faces=1500`, `allow` | no coplanar overlapping faces between objects | - |
| `camera_coverage` | scene-environment | `camera`, `objects`, `min_fraction=0.8` | the set covers the frame behind the subject | - |
| `reveal_clear` | product-shots | `subject`, `cloth`, `frame` | the reveal cloth no longer covers the product | - |
| `safe_area` | product-shots | `camera`, `objects`, `safe=0.9`, `frame` | the product stays inside the safe area | - |
| `npr_setup` | npr-stylized | `objects`, `need_outline=False` | every object has a toon material (and outline) | - |
| `npr_flat` | npr-stylized | `pattern`, `levels=24`, `top=6`, `min_share=0.6` | the render reads as flat bands | - |
| `edit_no_gaps` | video-editing | `channels` | every frame of the scene range has picture | - |
| `video_ok` | video-editing | `path`, `fps`, `min_seconds=0.5`, `frames`, `size`, `audio` | the encoded file decodes with the expected frames, fps, size and audio | - |

## Default acceptance per role

`scripts/bm_plan.py::default_acceptance` fills these in; params may add (`acceptance_extra`) or
replace (`acceptance_override`) them.

| Role | Default checks |
|---|---|
| blockout | objects_exist(PRX_), cameras_exist, custom_prop(brief_note), names_valid, bounds_size on the subject proxy (if `subject_size`) |
| environment | objects_exist(GEO_), names_valid |
| procedural | objects_exist(GEO_), gn_evaluates |
| model | objects_exist(GEO_), scale_applied, names_valid, no_ngons (unless `allow_ngons`), quad_ratio (if `min_quad_ratio`), manifold + normals_outward (unless `closed_meshes: false`), bounds_size (if `subject_size`), on_ground (unless `grounded: false`), tri_budget (if set) |
| sculpt | objects_exist(`sculpt_target`), sculpt_detail(`sculpt_min_verts`) |
| retopo | objects_exist, scale_applied, quad_ratio on `retopo_low`; surface_distance to `retopo_high`; tri_budget |
| uv | uv_present, uv_in_bounds |
| bake | bake_nonempty |
| materials / npr | materials_filled |
| hair | curve_count(`hair_prefix`, `min_curves`) |
| rig_face | shape_keys_valid, drivers_resolve on `face_mesh` |
| rig_body | objects_exist(RIG_ armature), weights_valid, pose_deform_ok on `skin_mesh` |
| animation | anim_present(`animated`); loop_ok if `loop` |
| simulation | sim_moved, no_explosion on `sim_objects` |
| lighting / product | lights_exist, cameras_exist, camera_frames on the hero camera, exposure |
| render | render_ok for every deliverable camera |
| edit | edit_no_gaps, video_ok(`video`, `fps`, `video_audio`) |
| qa | files_exist(qa_report), qa_all_pass |
| export | files_exist(exports/*), roundtrip_match |
| script | script_ran |

## Writing a new check

```python
import bm_checks

@bm_checks.register("bevel_width_ok")
def _bevel_width_ok(ctx, objects="GEO_", max_w=0.01):
    objs = bm_checks.select(objects)
    bad = [o.name for o in objs for m in o.modifiers if m.type == "BEVEL" and m.width > max_w]
    return not bad, bad, f"bevel width <= {max_w}", ""
```

Register fixers with `@bm_checks.register_fix(name)` taking `(ctx, args, attempt)`; return a
short description of what changed, or a string starting with `SKIP` if nothing safe can be done.
