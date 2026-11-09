# Export guide

## Target -> preset
| Target | Preset | Key settings |
|---|---|---|
| Unreal Engine 5 | `ue5_fbx` | FBX, -Y forward, Z up, unit scale applied, no leaf bones, tangent space, face smoothing, deform bones only |
| Unity | `unity_fbx` | FBX, -Z forward, Y up, scale "all" with bake space transform, no leaf bones |
| Godot 4 | `godot_gltf` | GLB, +Y up, modifiers applied, tangents, animations |
| web viewers, three.js, AR | `gltf_web` | GLB, +Y up, automatic image format; consider Draco only if the viewer supports it |
| other DCC tools, USD pipelines | `usd` | USDC, materials as preview surface, UVs, normals, relative paths |
| caches (simulation, deforming meshes, hair curves) | `alembic` | UVs, normals, hair curves; subdivision not applied |

## Pre-export checklist
- [ ] Scale applied (1, 1, 1), no negative scale (flipped normals in engines).
- [ ] Pivot (origin) where the engine expects it: base centre for props, hinge for doors.
- [ ] Real-world size in metres.
- [ ] Every mesh has a material; texture images exist and are packed or copied with the file.
- [ ] UV map present; second UV map for lightmaps if the engine needs it.
- [ ] No n-gons if the engine triangulates differently (or add a Triangulate modifier).
- [ ] Hard edges from sharp edges / weighted normals, not from split geometry.
- [ ] Armature: deform bones only, no leaf bones, rest pose clean, scale 1.
- [ ] Shape keys named; FBX exports shape-key normals with normals in 5.1+.
- [ ] Animations: one action per clip, named clearly; frame range set.

## Naming for engines
- Static mesh `SM_<name>`, skeletal `SK_<name>`, collision `UCX_<mesh>_01` (Unreal). Rename on
  export copies if the project uses `GEO_` internally.

## Verify
- Re-import in a clean Blender: counts, materials, bones, shape keys, size (automatic here).
- Then in the engine (manual, not covered by CI): scale against a 1.8 m reference, lighting
  build or lightmap UVs, material slots, collision.
