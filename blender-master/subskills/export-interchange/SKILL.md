---
name: export-interchange
description: Exports Blender 5.2 assets to FBX, glTF/GLB, USD and Alembic with presets for Unreal Engine 5, Unity, Godot and the web, runs pre-export checks (applied scale, axes, materials, UVs, n-gons, leaf bones, tangents) and verifies each file by re-importing it in a clean Blender process. Use when the user wants an export, a game-engine-ready asset, a file for another 3D app, or to check why an import looks wrong.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3). Engine-side imports are not tested. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Export and interchange

Hand over files that open in the target application at the right size, orientation, materials
and animation, and prove it with a re-import.

## Procedure
1. **Pick the preset** from the target (table in
   [references/export-guide.md](references/export-guide.md)): `ue5_fbx`, `unity_fbx`,
   `godot_gltf`, `gltf_web`, `usd`, `alembic`.
2. **Prepare** (`prepare`): apply scale (and rotation if asked), optional live Triangulate for
   engines that need Blender's exact split; the pre-export report lists unapplied or negative
   scale, missing materials, n-gons and missing UVs.
3. **Export** (`export`) selected objects to `exports/<project>_<preset>.<ext>`; a manifest
   records what each file should contain (meshes, materials, armatures, shape keys, animation,
   size).
4. **Round-trip** (`roundtrip_match` check): every file is imported into an empty factory scene
   in a separate Blender process and compared with the manifest. Sizes compare axis-sorted, so
   Y-up formats still match.
5. **Tell the user what was not tested**: the engine's own importer, its material conversion,
   and LOD/collision setup.

## Acceptance (default)
Export files exist and every file re-imports with meshes, materials, rig, shape keys,
animation (where the format carries it) and size intact.

## Pitfalls
- Unapplied scale: the engine shows the object 100x too small or large, or physics misbehaves.
- Leaf bones on FBX for engines: extra bones at chain ends. Presets turn them off.
- Procedural materials do not export: bake to image textures first (UV/baking part) when the
  target must match the Blender look.
- Modifiers: glTF and FBX presets apply them at export; USD/Alembic depend on settings.
- Multiple UV maps: engines usually use the first for textures and the second for lightmaps.

## Scripts
- `scripts/ops.py`: `prepare`, `export`, `roundtrip()`, `roundtrip_match` check.
- `scripts/roundtrip_check.py`: import one file into a clean scene and write a JSON summary.
- `lib/bm_export.py`: presets, pre-export report, import helper.
