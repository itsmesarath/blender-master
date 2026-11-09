---
name: video-editing
description: Cut and deliver video in Blender 5.2's sequencer - rendered frame sequences and movie files, colour cards, titles and captions, music and sound with fades, crossfades and wipes, fades to black, frame range fitting, and H.264/AAC MP4 encodes - with checks that the cut has no gaps and the encoded file has the expected frames, frame rate, size and audio. Use for assembling renders into a finished clip, ads with end cards, turntable deliverables, social cutdowns and simple trailers.
license: MIT
compatibility: Blender 5.2 (tested 5.2.3, FFmpeg build). Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Video editing (sequencer)

Edit from rendered frames, not from live 3D scenes: render image sequences first (safe to
resume, re-encode freely), then cut and encode here.

## Procedure
1. `edit_setup` - delivery fps and resolution (match the renders), clean slate. The sequencer
   is switched on only inside `encode`, so later still or QA renders still see the 3D scene.
2. Lay picture: `add_frames` (image sequences), `add_movie`, `add_color` cards; `start="end"`
   appends after the last strip.
3. Transitions: `crossfade` (overlaps the second strip onto the first by the transition length
   and adds CROSS / GAMMA_CROSS / WIPE); `fade` for fade in/out over black.
4. Type: `add_text` titles and captions (normalized location; keep inside the title-safe area,
   readable size about 4-6% of frame height; short on-screen times need short text).
5. Sound: `add_sound` with fades; `tone` generates a rights-free placeholder track for tests.
   Use only music the project has rights to.
6. `fit_range`, then `encode` (H.264 MP4, AAC audio).
7. Check: `edit_no_gaps` before encoding, `video_ok` on the file.

Pacing, platform specs and audio levels: [references/edit-guide.md](references/edit-guide.md).

## Acceptance (default)
`edit_no_gaps`, `video_ok` (frames = scene range, size = delivery size, audio when a sound
strip exists).

## Pitfalls
- Frame rate set after strips are placed shifts timing; set it first.
- Image strips default to the original size; use `fit="FIT"` when render size differs.
- In 5.x set `image_settings.media_type = "VIDEO"` before `file_format = "FFMPEG"`.
- H.264 needs even width and height.
- Sound past the last picture frame is cut by `fit_range` (picture defines the length).

## Scripts
`scripts/ops.py`: `edit_setup`, `add_frames`, `add_movie`, `add_color`, `add_text`, `tone`,
`add_sound`, `fade`, `crossfade`, `fit_range`, `encode`; checks `edit_no_gaps`, `video_ok`.
