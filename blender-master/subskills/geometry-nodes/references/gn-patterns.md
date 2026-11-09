# Geometry Nodes patterns

## Building blocks
| Goal | Chain |
|---|---|
| scatter on a surface | Object Info (surface) -> Distribute Points on Faces -> Instance on Points (Object Info of the instance, Original) |
| even spacing, no clumps | Distribute with method Poisson Disk, Distance Min |
| scatter by mask | vertex group / painted attribute -> Density Factor or Selection |
| align to surface | Distribute's Rotation output -> Instance Rotation (then add random Z) |
| row / array | Mesh Line (Count, Offset) -> Instance on Points |
| grid layout | Mesh Grid -> Mesh to Points -> Instance on Points |
| along a curve | Curve -> Resample Curve (Length) -> Instance on Points with Curve Tangent -> Align Rotation to Vector |
| profile sweep (rails, pipes, kerbs) | Curve to Mesh with a Profile Curve, Fill Caps |
| random per instance | Random Value (ID = Index, Seed input) -> Scale / Rotation / Store Named Attribute (Instance domain) |
| shading variation | Store Named Attribute -> material Attribute node (Instancer or Geometry type) -> colour ramp |
| boolean in nodes | Mesh Boolean (Exact or Manifold); expensive, keep inputs low-poly |

## Inputs worth exposing
Count or density, seed, size ranges, toggles for optional details, a material input for the
generated surfaces. Give every float a sensible min/max so a slider cannot break the result.

## Order of operations
1. Generate points.
2. Filter points (selection, masks, distance to roads or buildings).
3. Instance.
4. Per-instance variation and attributes.
5. Realize only if a later operation needs real geometry.
6. Set Material at the end of each branch, then Join Geometry.

## Simulation zones (5.x)
- Simulation Input / Output pair; state passes between frames.
- Bake the zone (modifier panel > Bake) before rendering or sharing.
- Start with few points and a short frame range; check the step's delta time handling.
- Good for: growth, accumulation, particle-like motion, simple flocking. Use the physics sub-skill
  for rigid, cloth and fluid solvers.

## Performance
- Instances are cheap; realized geometry is not.
- Avoid Mesh Boolean per instance; boolean once on a merged mesh, or model the detail into the
  instance shape.
- Turn off viewport display of the modifier while tweaking heavy groups.
- Use `Viewer` sparingly in final groups (it is ignored in render but clutters the graph).

## Exporting procedural results
Apply (realize and bake) to real mesh data first. Instance attributes become face/point
attributes on realize; check that UVs survive (the source objects need UV maps).
