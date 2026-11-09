import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402

import bm_mesh  # noqa: E402
import bm_scene  # noqa: E402

QA = os.path.join(H.SKILL, "subskills", "qa-review", "scripts", "qa_run.py")


def run_qa(blend, out, *extra):
    p = subprocess.run([bpy.app.binary_path, "-b", blend, "--factory-startup", "--python", QA, "--",
                        "--out", out, *extra], capture_output=True, text=True, timeout=300)
    rep = os.path.join(out, "brief", "qa_report.json")
    return p.returncode, (json.load(open(rep)) if os.path.exists(rep) else None), p.stderr[-400:]


def body():
    ctx = H.make_ctx(project="qa_test", subskill="qa-review")
    S = H.ops("materials-shading")

    # good scene
    bm_scene.clear_scene()
    bm_mesh.box("GEO_good", (0.5, 0.5, 0.5))
    S.material(ctx, "clay", "clay")
    S.assign(ctx, "clay", "GEO_good")
    good = os.path.join(H.OUT, "good.blend")
    bpy.ops.wm.save_as_mainfile(filepath=good, copy=True)
    code, rep, err = run_qa(good, os.path.join(H.OUT, "qa_good"), "--size", "0.5", "0.5", "0.5")
    H.expect("good_scene_passes", code == 0 and rep and rep["pass"], [code, rep and rep["failed"], err])

    # seeded bad scene: unapplied scale, empty slot, bad name
    bad_obj = bm_mesh.box("GEO_bad", (0.2, 0.2, 0.2), (1, 0, 0))
    bad_obj.scale = (2, 2, 2)
    bad_obj.data.materials.append(None)
    stray = bm_mesh.box("GEO_stray", (0.1, 0.1, 0.1), (2, 0, 0))
    stray.name = "Cube"
    bad = os.path.join(H.OUT, "bad.blend")
    bpy.ops.wm.save_as_mainfile(filepath=bad, copy=True)
    mtime = os.path.getmtime(bad)
    code, rep, err = run_qa(bad, os.path.join(H.OUT, "qa_bad"))
    failed = {r["check"] for r in (rep or {}).get("failed", [])}
    H.expect("bad_scene_exit_3", code == 3, code, 3)
    H.expect("bad_scene_names_each_problem", {"scale_applied", "materials_filled", "names_valid"} <= failed, sorted(failed))
    H.expect("input_not_written", os.path.getmtime(bad) == mtime)
    H.expect("contact_sheet", os.path.exists(os.path.join(H.OUT, "qa_bad", "brief", "qa_contact_sheet.png")))
    H.expect("markdown_report", os.path.exists(os.path.join(H.OUT, "qa_bad", "brief", "qa_report.md")))


H.run(body)
