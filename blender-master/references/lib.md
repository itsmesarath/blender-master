# Shared library (`lib/`)

Modules run inside Blender. `part_entry.py` puts `lib/` on `sys.path`; in your own scripts:
`import sys; sys.path.insert(0, "<skill>/lib")`.

| Module | Purpose | Main functions |
|---|---|---|
| `bm_version` | refuse old Blender, feature flags | `require_blender((5,0))`, `eevee_id()`, `has("layered_actions")` |
| `bm_report` | structured JSON report per script | `script_args()`, `Report.check/artefact/note/fix/error/finish` |
| `bm_scene` | prefixes, collections, units, cleanup | `ensure_collection`, `link_exclusive`, `get_or_create_object`, `set_units`, `clear_scene(keep_prefixes)`, `purge_orphans`, `bad_names`, `set_note` |
| `bm_mesh` | primitives built with bmesh, base-centred | `box`, `cylinder`, `sphere`, `plane`, `lathe(profile)`, `join_parts` |
| `bm_verify` | measurements | `world_bounds`, `size_within`, `on_ground`, `floating`, `face_stats`, `poles`, `manifold_report`, `normals_outward`, `overlaps`, `material_report`, `frame_coverage`, `image_stats`, `exposure_ok` |
| `bm_checks` | named checks + fixers | `CHECKS`, `FIXES`, `register`, `register_fix`, `select`, `run` |
| `bm_camera` | cameras that frame a subject | `make_camera(view, lens, fill)`, `aim`, `refit` |
| `bm_render` | preview / final settings and renders | `preview_settings`, `final_settings`, `render_still`, `render_cameras`, `contact_sheet`, `render_frames`, `preview_scope()` |
| `bm_compositor` | 5.x compositor node-group helpers | `ensure_tree`, `add_denoise`, `add_mist`, `add_glare`, `chain_types` |
| `bm_anim` | layered-action keyframing | `channelbag`, `ensure_fcurve`, `key`, `set_interpolation`, `make_cyclic`, `add_noise`, `value_at` |
| `bm_gn` | Geometry Nodes modifier inputs by name | `set_input`, `get_input` |
| `bm_export` | presets + round-trip | `PRESETS`, `pre_export_report`, `export`, `import_file`, `summary` |
| `bm_io` | never overwrite | `next_version_path`, `versioned_save`, `open_duplicate`, `checkpoint` |
| `bm_shots` | look at the scene | `look(path)`: viewport screenshot with a UI, render otherwise |
| `bm_part` | the per-part runner | `run_part`: ops -> checks -> fixes -> previews -> save -> report |

## Export presets

| Preset | Format | Notes |
|---|---|---|
| `ue5_fbx` | FBX | -Y forward, Z up, unit scale applied, face smoothing, tangents, no leaf bones, deform bones only |
| `unity_fbx` | FBX | -Z forward, Y up, scale "all" + bake space transform, face smoothing, no leaf bones |
| `godot_gltf` | glTF binary (.glb) | +Y up, modifiers applied, tangents, animations |
| `gltf_web` | glTF binary (.glb) | +Y up, modifiers applied, automatic image format |
| `usd` | USD (.usdc) | materials with preview surface, UVs, normals, relative paths |
| `alembic` | Alembic | UVs, normals, hair; subdivision not applied (for caches) |

## Script conventions

- One script = one job, idempotent: get-or-create by name, never "add another".
- Arguments after `--` (`script_args()`), output paths inside the project folder.
- End with `Report.finish(path)`, which writes JSON with `pass` and `status`; exit non-zero on
  failure via `--python-exit-code 1`.
