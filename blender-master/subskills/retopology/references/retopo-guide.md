# Retopology guide

## Budgets (triangles, rough guides)
| Use | Budget |
|---|---|
| hero game character (current-gen) | 30k-80k |
| secondary / NPC | 8k-25k |
| mobile or crowd character | 2k-8k |
| hero prop | 5k-20k |
| small prop | 300-3k |
| film / offline render | whatever the subdivision cage needs (often 5k-20k quads cage) |

## Edge flow for deformation
- Joints: 3 loops across elbows and knees, extra loop on the inside of the bend.
- Shoulders: loops following the deltoid; avoid a pole on top of the shoulder.
- Face: concentric loops around eyes and mouth, a loop from nose wing to mouth corner
  (nasolabial), a loop under the lower lip; keep poles off the lip and eyelid edges.
- Hands: 3 loops per knuckle, a clean quad grid on the palm.
- Place 5-edge and 3-edge poles in flat, non-deforming areas.

## Manual retopo in the UI
1. New mesh object, Snap to Face (Project individual elements), Shrinkwrap modifier on top.
2. Poly Build or extrude edges along the surface; X mirror on.
3. Draw the main loops (eyes, mouth, joints) first, then fill between them.
4. Relax brush / LoopTools-style relax for even spacing; check quads in wireframe.

## Checks to read
- `surface_distance`: mean under a few mm for a 1.8 m figure; max shows spikes (snapped to the
  wrong side).
- `quad_ratio`: >= 0.85 typical for animation meshes; 1.0 for subdivision cages.
- Pole count (`bm_verify.poles`) as a quick flow smell test.

## LODs
- LOD1 50%, LOD2 25%, LOD3 10% are common starting ratios; keep silhouettes.
- Name `<object>_LOD1..`; engines (UE, Unity) pick them up as LOD groups by suffix.
