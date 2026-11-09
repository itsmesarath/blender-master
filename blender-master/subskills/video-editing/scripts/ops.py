"""video-editing ops: assemble an edit in Blender's sequencer (rendered frame sequences, movie
files, colour cards, titles, sound), transitions and fades, a generated tone or click track for
tests, and an H.264/AAC MP4 encode - plus checks that the encoded file exists with the expected
duration, frame rate and resolution."""
from __future__ import annotations

import glob
import math
import os
import struct
import wave

import bpy

import bm_checks


def _sc():
    return bpy.context.scene


def _se():
    sc = _sc()
    return sc.sequence_editor or sc.sequence_editor_create()


def _abs(ctx, path):
    return path if os.path.isabs(path) else ctx.path(path)


def _end():
    strips = list(_se().strips_all)
    return max((s.right_handle for s in strips), default=_sc().frame_start)


def _resolve_start(start):
    return _end() if start in (None, "end") else int(start)


def edit_setup(ctx, fps=24, res=(1920, 1080), clear=True):
    """Prepare the scene for editing: frame rate, resolution at 100%, optionally remove
    existing strips. The sequencer is only switched on while ``encode`` runs, so stills and
    QA renders of the 3D scene in later parts are not replaced by the cut."""
    sc = _sc()
    sc.render.fps, sc.render.fps_base = int(fps), 1.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.use_sequencer = False   # on by default; with strips present it would replace 3D renders
    se = _se()
    if clear:
        for s in list(se.strips):
            se.strips.remove(s)
    sc.frame_start = 1
    return f"edit {res[0]}x{res[1]} @ {fps} fps"


def add_frames(ctx, pattern="renders/*.png", name="SEQ_frames", channel=1, start=None, fit="FIT"):
    """Image-sequence strip from rendered frames (sorted file names in one folder)."""
    files = sorted(glob.glob(_abs(ctx, pattern)))
    if not files:
        raise FileNotFoundError(pattern)
    s = _se().strips.new_image(name, files[0], channel, _resolve_start(start), fit_method=fit)
    for f in files[1:]:
        s.elements.append(os.path.basename(f))
    return f"{name}: {len(files)} frames from {s.left_handle}"


def add_movie(ctx, path, name="SEQ_movie", channel=1, start=None, sound=True, fit="FIT"):
    """Movie strip (and its audio on the channel above when present)."""
    p = _abs(ctx, path)
    start = _resolve_start(start)
    s = _se().strips.new_movie(name, p, channel, start, fit_method=fit)
    if sound:
        try:
            _se().strips.new_sound(name + "_snd", p, channel + 1, start)
        except Exception:
            pass
    return f"{name}: {s.duration} frames"


def add_color(ctx, color=(0.05, 0.05, 0.06), seconds=1.0, name="SEQ_card", channel=1, start=None):
    """Solid colour card (title backgrounds, gaps, fade-to-colour)."""
    n = max(1, round(seconds * _sc().render.fps))
    s = _se().strips.new_effect(name, "COLOR", channel, _resolve_start(start), length=n)
    s.color = color[:3]
    return f"{name}: {n} frames"


def add_text(ctx, text, start=1, seconds=2.0, name="SEQ_title", channel=3, size=80,
             location=(0.5, 0.5), color=(1, 1, 1, 1), shadow=True, fade=0.0):
    """Title / caption strip; ``location`` is normalized (0.5, 0.5 = centre; keep captions
    above 0.08 for safe area)."""
    n = max(1, round(seconds * _sc().render.fps))
    s = _se().strips.new_effect(name, "TEXT", channel, int(start), length=n)
    s.text = text
    s.font_size = size
    s.location = location
    s.color = color
    s.alignment_x = "CENTER"
    s.anchor_x, s.anchor_y = "CENTER", "CENTER"
    s.use_shadow = shadow
    s.blend_type = "ALPHA_OVER"
    if fade:
        _fade_alpha(s, fade, fade)
    return f"{name}: '{text[:30]}' {n} frames"


def tone(ctx, path="audio/tone.wav", seconds=4.0, freq=220.0, volume=0.3, rate=48000, beats=0.0):
    """Generate a simple sine tone (optionally pulsed ``beats`` per second) as a WAV - a
    rights-free placeholder track for tests and timing."""
    p = _abs(ctx, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    n = int(seconds * rate)
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            t = i / rate
            env = min(1.0, t * 20, (seconds - t) * 20)
            if beats:
                env *= math.exp(-8 * ((t * beats) % 1.0))
            frames += struct.pack("<h", int(32767 * volume * env * math.sin(2 * math.pi * freq * t)))
        w.writeframes(bytes(frames))
    return p


def add_sound(ctx, path, name="SND_music", channel=5, start=1, volume=1.0, fade_in=0.0, fade_out=0.0):
    """Sound strip with optional volume fades (seconds)."""
    s = _se().strips.new_sound(name, _abs(ctx, path), channel, int(start))
    s.volume = volume
    fps = _sc().render.fps
    a, b = s.left_handle, s.right_handle
    if fade_in:
        s.volume = 0.0
        s.keyframe_insert("volume", frame=a)
        s.volume = volume
        s.keyframe_insert("volume", frame=a + fade_in * fps)
    if fade_out:
        s.volume = volume
        s.keyframe_insert("volume", frame=b - fade_out * fps)
        s.volume = 0.0
        s.keyframe_insert("volume", frame=b)
        s.volume = volume
    return f"{name}: {b - a} frames"


def _fade_alpha(s, fin, fout):
    fps = _sc().render.fps
    a, b = s.left_handle, s.right_handle
    for f, v in ((a, 0.0), (a + fin * fps, 1.0), (b - fout * fps, 1.0), (b, 0.0)):
        s.blend_alpha = v
        s.keyframe_insert("blend_alpha", frame=f)


def fade(ctx, strip, fade_in=0.5, fade_out=0.5):
    """Fade a visual strip in and out over black (seconds)."""
    s = _se().strips_all[strip]
    _fade_alpha(s, fade_in, fade_out)
    return f"{strip}: fades {fade_in}/{fade_out}s"


def crossfade(ctx, a, b, seconds=0.5, kind="CROSS"):
    """Transition from strip ``a`` to ``b``: ``b`` is moved to overlap ``a``'s tail by the
    transition length, then a CROSS (or GAMMA_CROSS / WIPE) effect is placed on top."""
    se = _se()
    sa, sb = se.strips_all[a], se.strips_all[b]
    n = max(1, round(seconds * _sc().render.fps))
    if sb.channel == sa.channel:
        sb.channel = sa.channel + 1
    sb.frame_start += (sa.right_handle - n) - sb.left_handle
    ch = max(sa.channel, sb.channel) + 1
    while any(s.channel == ch for s in se.strips):
        ch += 1
    fx = se.strips.new_effect(f"FX_{a}_{b}", kind, ch, sb.left_handle, length=n, input1=sa, input2=sb)
    return f"{fx.name}: {n} frames"


def fit_range(ctx):
    """Scene frame range = the extent of the picture (visual strips); sound running past the
    last picture frame is cut by the range."""
    sc = _sc()
    strips = [s for s in _se().strips_all if s.type != "SOUND"] or list(_se().strips_all)
    sc.frame_start = min(s.left_handle for s in strips)
    sc.frame_end = max(s.right_handle for s in strips) - 1
    return f"range {sc.frame_start}-{sc.frame_end}"


def encode(ctx, path="video/edit.mp4", quality="HIGH", audio=True, preset="GOOD", bitrate_audio=192):
    """Render the sequencer to an H.264 MP4 (AAC audio). ``quality``: LOW/MEDIUM/HIGH/
    PERC_LOSSLESS. Sets the media type before the file format (5.x order)."""
    sc = _sc()
    fit_range(ctx)
    p = _abs(ctx, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    r = sc.render
    keep = (r.use_sequencer, r.image_settings.media_type, r.image_settings.file_format,
            r.image_settings.color_mode, r.filepath, r.use_file_extension, sc.frame_current)
    r.use_sequencer = True
    r.image_settings.media_type = "VIDEO"
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format = "MPEG4"
    r.ffmpeg.codec = "H264"
    r.ffmpeg.constant_rate_factor = quality
    r.ffmpeg.ffmpeg_preset = preset
    r.ffmpeg.audio_codec = "AAC" if audio else "NONE"
    if audio:
        r.ffmpeg.audio_bitrate = bitrate_audio
        r.ffmpeg.audio_channels = "STEREO"
    r.use_file_extension = False
    r.filepath = p
    try:
        bpy.ops.render.render(animation=True)
    finally:   # leave still-image output settings as they were for later parts
        r.use_sequencer = keep[0]
        r.image_settings.media_type = keep[1]
        r.image_settings.file_format = keep[2]
        r.image_settings.color_mode = keep[3]
        r.filepath, r.use_file_extension = keep[4], keep[5]
        sc.frame_set(keep[6])
    return f"{os.path.relpath(p, ctx.out_dir)}: frames {sc.frame_start}-{sc.frame_end}"


def _probe(path):
    clip = bpy.data.movieclips.load(path, check_existing=False)
    info = {"frames": clip.frame_duration, "fps": round(clip.fps, 3), "size": tuple(clip.size)}
    bpy.data.movieclips.remove(clip)
    return info


@bm_checks.register("video_ok")
def _video_ok(ctx, path="video/edit.mp4", fps=None, min_seconds=0.5, frames=None, size=None, audio=None):
    """Encoded movie exists, decodes, and has the expected fps / length / size; ``audio``
    True/False also asserts an AAC track is present/absent (MP4 container)."""
    p = _abs(ctx, path)
    if not os.path.exists(p) or os.path.getsize(p) < 1024:
        return False, None, path, "missing or empty"
    info = _probe(p)
    sc = _sc()
    want_fps = fps or sc.render.fps
    ok = abs(info["fps"] - want_fps) < 0.05 and info["frames"] >= min_seconds * want_fps
    if frames is not None:
        ok = ok and abs(info["frames"] - frames) <= 1
    if size is not None:
        ok = ok and tuple(info["size"]) == tuple(size)
    if audio is not None:
        with open(p, "rb") as fh:
            info["audio"] = b"mp4a" in fh.read()
        ok = ok and info["audio"] == bool(audio)
    return ok, info, f"fps {want_fps}, >= {min_seconds}s" + (f", {frames} frames" if frames else ""), ""


@bm_checks.register("edit_no_gaps")
def _edit_no_gaps(ctx, channels=None):
    """Every frame of the scene range is covered by at least one visual strip (no black
    holes in the cut)."""
    se = _se()
    vis = [s for s in se.strips_all if s.type != "SOUND" and (channels is None or s.channel in channels)]
    sc = _sc()
    holes = [f for f in range(sc.frame_start, sc.frame_end + 1)
             if not any(s.left_handle <= f < s.right_handle for s in vis)]
    return not holes, len(holes), "0 uncovered frames", (f"first gap at {holes[0]}" if holes else "")


OPS = {"edit_setup": edit_setup, "add_frames": add_frames, "add_movie": add_movie, "add_color": add_color,
       "add_text": add_text, "tone": tone, "add_sound": add_sound, "fade": fade, "crossfade": crossfade,
       "fit_range": fit_range, "encode": encode}
FIXES = {}
