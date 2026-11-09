# Face guide

## Minimal expressive set (stylized characters)
| Key | Region | Move |
|---|---|---|
| jaw_open | lower face | hinge rotation ~15-25 deg about a point below the ears |
| smile_L/R | mouth corners | up and back, cheek raise |
| frown_L/R | mouth corners | down |
| pucker | lips | forward and in |
| blink_L/R | upper lids | down to meet lower lids |
| brow_up_L/R, brow_down_L/R | brows | up / down and in |
| cheek_puff | cheeks | inflate |

## Visemes (lip sync)
A small set covers most speech: rest, AA (open), EE (wide), OH (round), OO (pucker),
FV (lower lip to teeth), MBP (closed, pressed), L/TH (tongue). Drive them from audio-timed
keyframes in animation, or import a generated viseme track.

## Engine standards
- ARKit-style 52 blend shapes (eyeBlinkLeft, jawOpen, mouthSmileLeft ...) for live capture.
- Keep names consistent and ASCII; FBX keeps shape key names.

## Sculpting keys by hand (UI)
1. Add key, set it active, enter sculpt mode (the key is edited, not the basis).
2. Symmetry on for symmetric keys, then `split_lr`.
3. Check each key at 0.5 as well as 1.0; in-betweens reveal bad paths (rotation shapes like
   the jaw need the hinge so the chin travels on an arc).

## Correctives
- Combination shapes: jaw_open + smile, blink + brow_down.
- Joint correctives (neck turn, shoulder raise) are driven by bone rotation instead (drive with
  `bone=` and LOCAL_SPACE rotation channels).

## Controls
- Small objects in front of the face, limited to the channels they drive (lock the rest).
- Range: about 1-3 cm of travel for full value at human scale; consistent across controls.
