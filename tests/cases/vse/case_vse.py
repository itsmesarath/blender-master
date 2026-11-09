import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402



def _frames(ctx, n, color):
    os.makedirs(ctx.path("renders"), exist_ok=True)
    for i in range(n):
        img = bpy.data.images.new("f", 64, 36)
        v = 0.2 + 0.6 * i / max(n - 1, 1)
        img.pixels = [color[0] * v, color[1] * v, color[2] * v, 1.0] * (64 * 36)
        img.filepath_raw = ctx.path("renders", f"shot_{i + 1:04d}.png")
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)


def body():
    ctx = H.make_ctx(project="vse_test", subskill="video-editing")
    V = H.ops("video-editing")
    _frames(ctx, 24, (0.9, 0.5, 0.2))
    V.edit_setup(ctx, fps=24, res=(320, 180))
    V.add_frames(ctx, "renders/shot_*.png", name="SEQ_shot", start=1)
    V.add_color(ctx, (0.05, 0.05, 0.08), seconds=1.0, name="SEQ_card", start="end")
    V.crossfade(ctx, "SEQ_shot", "SEQ_card", seconds=0.25)
    V.add_text(ctx, "Example title", start=1, seconds=1.0, size=24, fade=0.2)
    V.fade(ctx, "SEQ_shot", 0.25, 0.0)
    wav = V.tone(ctx, "audio/tone.wav", seconds=2.0, beats=2)
    V.add_sound(ctx, wav, start=1, fade_out=0.3)
    H.data("range", V.fit_range(ctx))
    ok, v = H.check(ctx, "edit_no_gaps")
    H.expect("no_gaps", ok, v)
    H.data("encode", V.encode(ctx, "video/edit.mp4", quality="MEDIUM"))
    sc = bpy.context.scene
    n = sc.frame_end - sc.frame_start + 1
    H.expect("sequencer_restored", not sc.render.use_sequencer and sc.render.image_settings.media_type == "IMAGE")
    ok, v = H.check(ctx, "video_ok", path="video/edit.mp4", frames=n, size=(320, 180), audio=True)
    H.expect("video_ok", ok, v)


H.run(body)
