# Physics guide

## Rigid bodies
| Setting | Start | Raise when |
|---|---|---|
| substeps per frame | 10 | small or fast objects pass through others |
| solver iterations | 10 | stacks jitter or sink |
| collision margin | 1 mm | contacts show gaps (lower) or jitter (raise slightly) |
| friction | 0.5 | objects slide too much |
| bounciness | 0.0-0.3 | it is a ball |
| damping (linear/angular) | 0.04-0.1 | objects never settle |
Mass matters only relative to other bodies (a heavy box pushes a light one).
Animated (kinematic) bodies: key the object, enable `animated`, switch to dynamic at a frame by
keying the `kinematic` flag off.

## Cloth
| Preset | Use |
|---|---|
| cotton | shirts, sheets, product reveals |
| silk | light scarves, flowing reveals |
| denim | trousers, jackets, heavy canvas |
| leather | stiff jackets, bags |
| rubber | balloons and inflatables (with pressure) |
| flag | flags and banners (pin the pole edge) |
- Resolution: 1-3 cm edges for garments; a 2 m sheet at 40-80 subdivisions.
- Quality 5-10; raise for fast motion. Collision distance 3-10 mm.
- Self collision only when folds stack (costly).
- Product reveal: drape the cloth over the product, then animate a pinned corner (hook or
  pinned group on an animated empty) pulling it away, or play a fall in reverse.

## Clothes on characters
1. Garment mesh: from the body (`garment_from_body`) or modelled from flat pattern pieces
   sewn together (cloth sewing springs) for tailored clothes.
2. Pin the parts held by the body (waistband, collar) and give them the armature too
   (garment parented with the same armature modifier first, cloth second).
3. Body collision on the deforming body, distance 5-10 mm.
4. Start the sim a few frames before the shot in the rest pose (pre-roll), blending to the
   first animated pose.
5. Games: bake the cloth to shape keys or bones, or use the engine's cloth.

## Soft bodies
Goal 0.6-0.9 for jiggle, lower for floppy; goal vertex group limits motion to belly or
antennae. Edges and stiff quads keep the shape.

## Particles
Emitter for sparks, dust, confetti, rain; render as instanced objects (hidden source).
Hair particles are legacy: use hair curves (hair-fur) for hair and fur.

## Fluids (Mantaflow)
- Domain box around the action, flow objects inside. Resolution 32 preview, 64-128 final.
- Smoke: fire + smoke flow types, render with a volume shader (Principled Volume).
- Liquid: flow behavior geometry (initial volume) or inflow; mesh on for rendering.
- Cache on disk: keep it next to the project; bake once, render many times.

## Stability checklist
- No overlaps at frame 1, applied scale, sane masses, enough substeps.
- `no_explosion` growth limit 3x; `sim_settled` for things that must end at rest.
