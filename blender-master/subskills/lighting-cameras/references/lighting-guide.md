# Lighting and camera guide

## Rigs

**Three-point**
- Key: 30-45 deg to the side of the camera, 20-40 deg above the subject. Largest light, sets
  the shadow direction. Warm (4500-5500 K) for a friendly look.
- Fill: opposite side, lower, 2-4x weaker than the key (the ratio sets the mood: 2:1 soft,
  8:1 dramatic). Large and soft.
- Rim / back: behind the subject opposite the key, high, cooler (6500-8000 K). Separates the
  silhouette from the background.

**Product softbox studio**
- One large overhead softbox, slightly behind the product: defines the top and gives a soft
  shadow.
- Two tall, narrow strip lights left and right, angled back: long vertical reflections that
  describe the shape of glossy and glass objects.
- A small kicker from behind for an edge highlight on glass or metal.
- Seamless sweep backdrop; camera 70-100 mm.

**Exterior daylight**
- Sun with angle 0.5-2 deg (shadow softness) at 5000-6000 K; elevation 15-30 deg for long,
  warm shadows; 45-70 deg for midday.
- Physical sky world; match sun direction to the sky's sun rotation.

**Interior daylight**
- Sky world + sun angled through the window so a patch of sunlight lands on the floor or a wall.
- A soft area light filling the window opening, pointing inward (helps sampling and lifts the
  room). Warm practical lamps (2700-3000 K) for evening.
- Expect a wide brightness range: allow more clipping in the window than on the subject.

**Night / mood**
- Low world, a few motivated sources (street lamps, screens, windows), strong colour contrast
  (warm practicals against a cool ambient).

## Light power (starting points, Watts)
| Light | Small product (~0.1 m) | Prop (~1 m) | Room |
|---|---|---|---|
| area key | 3-15 | 100-400 | 200-800 |
| point practical | - | 20-60 | 40-100 |
| sun (strength) | 2-5 | 2-5 | 3-6 |

Power falls off with distance squared: doubling the distance needs ~4x the energy for the same
brightness. The rigs here compute energy from the subject's size for that reason.

## Cameras
| Need | Settings |
|---|---|
| natural perspective | 35-50 mm |
| product / portrait compression | 70-135 mm |
| interiors | 18-28 mm, camera level, use lens shift Y to frame tall rooms |
| technical | orthographic, scale = largest side x 1.1 |
| shallow focus | f/1.4-2.8, focus on an empty at the point of interest |
| deep focus | f/8+ or DoF off |

Composition: rule of thirds or centred symmetry on purpose; leave space in the direction the
subject faces; avoid tangents between silhouettes.

## Exposure targets (filmic / AgX view)
- Mean luminance 0.15-0.6 for most scenes; 0.08-0.2 for night scenes (override the check).
- Clipped pixels <= 2 % on the subject; windows and light sources may clip.
- Fix brightness with light power or world strength, not with the exposure slider, unless the
  look is intentionally graded.

## Turntables
- Pivot empty at the subject's centre, camera parented to it, rotation keyed linear 0 -> 360 deg
  over N frames with the end frame excluded so the loop does not stutter.
- 48-120 frames at 24-30 fps; keep the camera slightly above the product's middle.
