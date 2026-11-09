import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import _harness as H  # noqa: E402
import bpy  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402

import bm_checks  # noqa: E402

TEMPLATE = os.path.join(H.SKILL, "subskills", "scripting-automation", "scripts", "part_script_template.py")


def body():
    ctx = H.make_ctx(project="script_test", subskill="scripting-automation")
    A = H.ops("scripting-automation")
    script = os.path.join(H.OUT, "gen_rows.py")
    with open(script, "w") as f:
        f.write(
            "import bpy\n"
            "for o in [o for o in bpy.data.objects if o.name.startswith('GEO_row_')]:\n"
            "    bpy.data.objects.remove(o, do_unlink=True)\n"
            "for i in range(4):\n"
            "    m = bpy.data.meshes.new(f'GEO_row_{i}')\n"
            "    m.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])\n"
            "    o = bpy.data.objects.new(f'GEO_row_{i}', m)\n"
            "    bpy.context.scene.collection.objects.link(o)\n"
            "    o.location.x = i\n"
            "RESULT = 'rows=4'\n")
    A.run_script(ctx, "gen_rows.py")
    A.run_script(ctx, "gen_rows.py")      # idempotent rerun
    n = len([o for o in bpy.data.objects if o.name.startswith("GEO_row_")])
    H.expect("idempotent_rerun", n == 4, n, 4)
    ok, v, e, d = bm_checks.run(ctx, {"check": "script_ran"})
    H.expect("script_ran_check", ok)

    try:
        A.run_script(ctx, "../outside.py")
        H.expect("outside_path_refused", False)
    except PermissionError:
        H.expect("outside_path_refused", True)

    bad = os.path.join(H.OUT, "bad.py")
    with open(bad, "w") as f:
        f.write("import bpy\nbpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'\n")  # api-lint: ok (test fixture)
    try:
        A.run_script(ctx, "bad.py")
        H.expect("lint_blocks_old_api", False)
    except ValueError:
        H.expect("lint_blocks_old_api", True)

    # the template runs headless twice with the same result
    tdir = os.path.join(H.OUT, "template")
    for i in range(2):
        p = subprocess.run([bpy.app.binary_path, "-b", "--factory-startup", "--python-exit-code", "1",
                            "--python", TEMPLATE, "--", "--out", tdir], capture_output=True, text=True, timeout=300)
        H.expect(f"template_run_{i + 1}", p.returncode == 0, p.returncode, 0, p.stderr[-300:])


H.run(body)
