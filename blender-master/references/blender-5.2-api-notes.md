# Blender 5.x API notes (target 5.2 LTS)

Scripts written for 4.x often fail on 5.x in the places below. Each line: what changed and what to
write instead. `subskills/scripting-automation/scripts/api_lint.py` detects most of these.

## Rendering
- EEVEE's engine id is `"BLENDER_EEVEE"` again (the 4.2-4.5 id `BLENDER_EEVEE_NEXT` raises an
  error). `lib/bm_version.eevee_id()` returns the right one.
- In background mode the engine enum may list only EEVEE, but assigning `"CYCLES"` works.
- Set `image_settings.media_type` (`IMAGE`, `MULTI_LAYER_IMAGE`, `VIDEO`) before `file_format`.
- Pass names are spelled out: `Depth` (not `Z`), `Diffuse Color`, `Material Index`...
- Background GPU drawing may need `gpu.init()` (5.2) before offscreen work.
- Lights have `use_temperature` / `temperature` (Kelvin) in addition to colour.

## Compositor
- The compositor is a node-group data-block: create `bpy.data.node_groups.new(name,
  "CompositorNodeTree")` and assign `scene.compositing_node_group`. `scene.node_tree` is gone and
  `scene.use_nodes` does nothing.
- There is no Composite node. Add an output socket on the tree interface
  (`tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")`) and link
  the final image into a `NodeGroupOutput` node.
- Many node options are input sockets now: `glare.inputs["Type"].default_value = "Fog Glow"`,
  `denoise.inputs["Prefilter"].default_value = "Accurate"`.
- Removed compositor-specific Mix / Map Range / Gamma nodes: use `ShaderNodeMix`
  (`data_type="RGBA"`), `ShaderNodeMapRange`, `ShaderNodeGamma`.
- Alpha Over inputs are `Background` / `Foreground`. Denoising passes appear on Render Layers as
  `Denoising Albedo` / `Denoising Normal` once `view_layer.cycles.denoising_store_passes` is on.
- File Output node: `directory`, `file_name`, `file_output_items`.

## Materials and worlds
- New materials and worlds already have node trees; `use_nodes = True` is a deprecated no-op.
- Principled BSDF socket names: `Base Color`, `Metallic`, `Roughness`, `IOR`, `Alpha`, `Normal`,
  `Subsurface Weight/Radius/Scale`, `Specular IOR Level`, `Anisotropic`, `Transmission Weight`,
  `Coat Weight/Roughness`, `Sheen Weight/Roughness/Tint`, `Emission Color/Strength`,
  `Thin Film Thickness/IOR`.
- Sky Texture types: `SINGLE_SCATTERING`, `MULTIPLE_SCATTERING` (default), `PREETHAM`,
  `HOSEK_WILKIE`.

## Animation
- Actions are layered: layers -> strips -> channelbags per slot. `action.fcurves` and
  `action.groups` do not exist. Use `bpy_extras.anim_utils.action_ensure_channelbag_for_slot(
  action, slot)` and `channelbag.fcurves.ensure(data_path, index=..., group_name=...)`.
  `lib/bm_anim.py` wraps this.
- `keyframe_insert()` still works and creates action, slot and channelbag as needed.
- Bone visibility/selection in pose mode: `pose_bone.hide`, `pose_bone.select`.
- The preference "Only Insert Available" is on by default: auto-keying may skip new channels.

## Geometry nodes and modifiers
- Geometry Nodes modifier inputs (5.2): `getattr(mod.properties.inputs, identifier).value`; for
  attribute inputs set `.type = "ATTRIBUTE"` and `.attribute_name`. Dict access such as
  `mod["Socket_2"]` fails. Identifiers come from `node_group.interface.items_tree`.
  `lib/bm_gn.py` sets inputs by display name.
- Boolean solvers: `FLOAT` (was "Fast"), `EXACT`, `MANIFOLD`.
- `bpy.ops.object.shade_smooth_by_angle(angle=...)` marks sharp edges and smooths in one step.

## Sequencer
- `sequence_editor.strips` (not `sequences`); 5.1 handle names `duration`, `left_handle`,
  `right_handle`, `left_handle_offset`, `right_handle_offset`. Scripts adding strips should pass
  `move_strips=False`.

## Grease Pencil and annotations
- Grease Pencil v3 is `bpy.types.GreasePencil` / `bpy.data.grease_pencils`. Strokes live on
  `layer.frames[i].drawing`: `drawing.add_strokes([n_points])`, then set `points[i].position`.
- Annotations are separate (`scene.annotation`).

## Sculpt and paint
- `brush.sculpt_tool` -> `brush.sculpt_brush_type`; brush size is a diameter (halve old radius
  values); stroke options are `brush.stroke_method`; automasking moved to
  `mesh_automasking_settings`.

## Import / export
- FBX export is still `bpy.ops.export_scene.fbx`; FBX import defaults to the native
  `bpy.ops.wm.fbx_import`. Shape-key normals are exported with normals (5.1+).
- USD export: `export_textures_mode`, `selected_objects_only`; Alembic export: `selected`.
- Collada (.dae) is gone.

## Python and files
- Bundled Python 3.13: extension wheels must be built for cp313. User site-packages are not loaded
  unless Blender starts with `--python-use-user-env`.
- `bgl` is removed (use `gpu`); several helper modules became private.
- Files saved in 5.x open in 4.5 only partially: hair and newer node features can fail or crash.
  Keep a project on 5.2 once started.
