# Naming, collections, units

## Object prefixes (enforced by the `names_valid` check)

| Prefix | Use | Collection |
|---|---|---|
| `PRX_` | blockout proxies, real scale, hidden in final renders | BLOCKOUT |
| `GEO_` | final geometry | GEO |
| `LGT_` | lights | LIGHTS |
| `CAM_` | cameras (`CAM_hero` is the default hero) | CAMERAS |
| `REF_` | reference planes and images | REFS |
| `FX_` | simulation domains, effectors | FX |
| `CTRL_` | empties used as controls, focus targets, pivots | CONTROLS |
| `RIG_` | armatures | RIGS |
| `REV_` | review layers (Grease Pencil) | REVIEW |
| `TMP_` | temporary helpers; must not survive a part | - |

Pattern: `PREFIX_lower_or_Camel_parts`, e.g. `GEO_crate_body`, `GEO_bottle_cap`. Group related
objects under a shared stem so a selector like `GEO_crate_` reaches all of them.

Data-blocks: materials `MAT_`, worlds `WLD_`, compositor trees `COMP_`, actions `ACT_`, Grease
Pencil materials `GPM_`.

## Units and placement
- Metric, 1 unit = 1 m. Model at real size; never fake scale with object scale (apply it).
- Ground plane at z = 0. Floors may sit below 0 when the walkable surface is z = 0.
- Base-centre placement: an object's location is the centre of its bottom face, so `z = 0`
  means "standing on the ground". Lib helpers build meshes this way.
- Forward axis for characters and vehicles: -Y (faces the front camera). Up: +Z.

## Files
- `<project>/blend/<project>_v001.blend` ... one version per passed part.
- `<project>/blend/checkpoints/checkpoint_<part>_<what>.blend` before destructive steps.
- Exports: `<project>/exports/<project>_<preset>.<ext>`.
