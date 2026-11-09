# Example 06: product ad shot

A short ad: a silk sheet is pulled off a speaker, pebbles drop and settle, the brand name rises, an end card follows, and the frames are cut to an MP4 with a placeholder tone.

## Request

> A 3.5-second product ad for a small cylindrical smart speaker: it starts hidden under a red silk sheet that is pulled away to reveal it on a warm seamless sweep, three small pebbles drop and settle beside it, the brand name rises in gold behind it, then a dark end card with the name and a tagline. Deliver the frames and an MP4 with a placeholder music track.

## Recognition

Type: **product_shot** + modifiers vfx_sim (pinned with `type_override` in params); extra roles: edit.

## Assumptions written into the brief

- speaker 10.4 cm wide, 16 cm tall; pebbles 2-2.5 cm
- the cloth settles over the speaker during a 24-frame pre-roll that is simulated but not rendered; frames 25-108 make the 3.5 s cut (reveal from 36, pebbles from 40, logo 66-86, end card from 94)
- the sound is a generated placeholder tone; swap in licensed music for delivery
- a hidden collider box under the sweep floor catches the pebbles (the sweep itself is rebuilt by the studio op)

## Parts

| Part | Sub-skill | Ops | Checks |
|---|---|---|---|
| P01-blockout | blockout-spatial-brief | `setup_scene`, `resolution`, `proxy`, `camera`, `write_spatial_brief` | `objects_exist`, `cameras_exist`, `custom_prop`, `names_valid`, `bounds_size` |
| P02-model | modeling-topology | `lathe`, `sphere`, `box`, `hide_proxies` | `objects_exist`, `scale_applied`, `names_valid`, `no_ngons`, `manifold`, `normals_outward`, `bounds_size`, `on_ground` |
| P03-materials | materials-shading | `material`, `assign` | `materials_filled` |
| P04-simulation | physics-simulation | `rigid_world`, `rigid_body`, `bake` | `sim_moved`, `no_explosion`, `sim_settled` |
| P05-product | product-shots | `studio`, `cloth_reveal`, `logo_reveal`, `end_card` | `lights_exist`, `cameras_exist`, `camera_frames`, `exposure`, `reveal_clear`, `safe_area`, `hidden_until` |
| P06-render | render-compositing | `render_preset`, `compositor`, `render_deliverables` | `render_ok` |
| P07-edit | video-editing | `edit_setup`, `add_frames`, `fade`, `tone`, `add_sound`, `encode` | `edit_no_gaps`, `video_ok` |
| P08-qa | qa-review | `qa_run` | `files_exist`, `qa_all_pass` |

Parts run in dependency order. Parts with no edge between them may run in either order.

## What to look at

- The cloth settles over the speaker during a pre-roll that is simulated but not rendered.
- The sheet clears the product (`reveal_clear`), and the logo stays hidden until it rises (`hidden_until`).
- The pebbles come to rest (`sim_settled`).
- The MP4 has 84 frames at 24 fps and an AAC track (`video_ok`). The tone is a placeholder; use licensed music for delivery.

## Run it

```
export BLENDER_BIN=/path/to/blender
python3 blender-master/scripts/plan_project.py --request "$(cat examples/06-product-ad-shot/request.txt)" \
    --params examples/06-product-ad-shot/params.json --out out/06-product-ad-shot
python3 blender-master/scripts/run_project.py --brief out/06-product-ad-shot/brief/brief.json --out out/06-product-ad-shot
```

Outputs: `out/06-product-ad-shot/renders/`, `out/06-product-ad-shot/brief/qa_report.md`, `out/06-product-ad-shot/reports/`, `out/06-product-ad-shot/blend/`. The video goes to `video/`.
