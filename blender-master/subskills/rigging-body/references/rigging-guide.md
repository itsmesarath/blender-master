# Rigging guide

## Bone layout (humanoid)
| Chain | Bones | Notes |
|---|---|---|
| spine | hips -> spine -> chest -> neck -> head | hips is the parent of legs and spine |
| arms | clavicle -> upper_arm -> forearm -> hand | slight elbow bend backwards in rest |
| legs | thigh -> shin -> foot (-> toe) | slight knee bend forwards in rest |
| fingers | 3 bones each, thumb from the hand base | curl around local X |
| root | at ground, non-deforming | moves the whole character |

Engines: a single root, deform bones only in the export, no constraints baked into the
rest pose, consistent L/R suffixes. Humanoid retargeting (UE IK Retargeter, Unity Humanoid)
matches by hierarchy and names; keep a mapping table if names differ.

## Bone collections
- DEF: deforming bones (exported).
- CTRL: what animators touch (IK targets, poles, root, face controls).
- MCH: helpers (twist, stretch, IK/FK switches); hidden.

## Weights
- 4 influences per vertex (engines), normalised.
- Elbow and knee: blend over 2-3 edge loops; shoulders over a wider area.
- Twist: forearm twist bones carry 50% of the hand roll to avoid candy-wrapper collapse.
- Check by posing extremes; fix with smooth and blur on weights rather than hand-painting
  hard values.
- Preserve Volume (dual quaternion) on the armature modifier helps elbows and wrists;
  engines use linear skinning, so test without it for game assets.

## Constraints
| Need | Constraint |
|---|---|
| leg/arm IK | IK (chain 2) + pole |
| look-at eyes | Damped Track to a target, or Locked Track |
| foot roll | MCH bones with Copy Rotation and Transform constraints |
| props in hand | Child Of with animated influence |
| stretchy limbs | Stretch To on MCH bones |

## Correctives
Shape keys driven by joint rotation (elbow 90 deg, shoulder up) fix volume loss. Use a
driver on the key value from the bone's local rotation, clamped 0-1 (rigging-face drivers).
