# Animation guide

## Timing (24 fps)
| Action | Frames |
|---|---|
| blink | 4-8 (close 2, open 3-4) |
| head turn | 8-16 |
| arm raise | 10-16 |
| wave cycle (one back-and-forth) | 10-16 |
| walk cycle | 24-32 per two steps |
| run cycle | 14-18 |
| breathing idle | 72-120 |
| product spin (360 deg) | 120-240 |
| logo reveal | 24-48, then hold 24+ |

## Principles in practice
- **Spacing**: ease in and out of holds (Bezier auto-clamped); linear only for mechanical
  motion and constant spins.
- **Overlap**: secondary parts lag the main motion by 2-4 frames (forearm after upper arm,
  hair after head). With `wave`, use a phase offset of 0.05-0.15 periods.
- **Arcs**: hands and heads travel on arcs; check by tracking a point across frames.
- **Holds**: keep a slight drift (noise at low strength) so held poses do not look frozen.
- **Anticipation**: a small opposite move before a big one (crouch before a jump).

## Loops
- First key equals last key; make curves cyclic; set the clip end one frame before the
  repeat frame (frame_end + 1 equals frame_start in value).
- Avoid noise modifiers in clips meant for engines (they are not exported); bake them.

## Camera moves
- Dolly / truck on a path or two keys with easing; 3-6 s for product shots.
- Handheld: noise on rotation at strength 0.002-0.01 rad, scale 15-40 frames.
- Rack focus: key the focus distance (lighting-cameras depth of field).

## Game clips
- One action per clip, named for the engine (Idle, Walk, Wave), root motion decided up front.
- Bake constraints and drivers to keys; export with NLA strips off.
