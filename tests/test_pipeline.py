"""The headless runner: PASS path, ASK path (failing check with no fixer blocks dependants),
NEEDS_INPUT for unfilled parts, and never writing the user's input file."""
from __future__ import annotations

import json
import os
import subprocess
import sys

from conftest import ROOT, SKILL

PLAN = SKILL / "scripts" / "plan_project.py"
RUN = SKILL / "scripts" / "run_project.py"


def run(blender, brief, out, *extra):
    env = dict(os.environ, BLENDER_BIN=blender)
    p = subprocess.run([sys.executable, str(RUN), "--brief", str(brief), "--out", str(out), *extra],
                       capture_output=True, text=True, env=env, timeout=1200)
    summ = json.loads((out / "run_summary.json").read_text()) if (out / "run_summary.json").exists() else {}
    return p, summ


def test_template_brief_runs(blender, outdir):
    brief = json.loads((SKILL / "templates" / "project_brief.json").read_text())
    path = outdir / "brief.json"
    path.write_text(json.dumps(brief))
    p, summ = run(blender, path, outdir)
    assert p.returncode == 0, p.stdout + p.stderr
    assert [x["status"] for x in summ["parts"]] == ["PASS", "PASS"]
    assert (outdir / "blend" / "my-project_v002.blend").exists()
    assert list((outdir / "previews").glob("*.png"))


def test_ask_blocks_dependants(blender, outdir):
    brief = json.loads((SKILL / "templates" / "project_brief.json").read_text())
    model = brief["parts"][1]
    model["acceptance"] = [{"check": "bounds_size", "args": {"objects": "GEO_subject_", "target": [2.0, 2.0, 2.0],
                                                            "tol": 0.05}, "desc": "deliberately impossible"}]
    brief["parts"].append({"id": "P03-materials", "role": "materials", "subskill": "materials-shading",
                           "depends_on": ["P02-model"], "mode": "headless",
                           "ops": [{"op": "material", "args": {"name": "clay", "preset": "clay"}}],
                           "acceptance": [{"check": "materials_filled"}]})
    path = outdir / "brief.json"
    path.write_text(json.dumps(brief))
    p, summ = run(blender, path, outdir)
    assert p.returncode == 2
    st = {x["part"]: x["status"] for x in summ["parts"]}
    assert st == {"P01-blockout": "PASS", "P02-model": "ASK", "P03-materials": "BLOCKED"}, st
    rep = json.loads((outdir / "reports" / "P02-model.json").read_text())
    assert rep["status"] == "ASK" and rep.get("question")
    assert rep.get("fix_rounds", 0) <= 3


def test_needs_input_stops(blender, outdir):
    env = dict(os.environ)
    subprocess.run([sys.executable, str(PLAN), "--request", "a hard surface sci-fi crate prop", "--out", str(outdir)],
                   check=True, capture_output=True, env=env)
    p, summ = run(blender, outdir / "brief" / "brief.json", outdir)
    assert p.returncode == 2
    assert summ["parts"][-1]["status"] == "NEEDS_INPUT"


def test_input_blend_is_never_written(blender, outdir):
    src = outdir / "user.blend"
    subprocess.run([blender, "-b", "--factory-startup", "--python-expr",
                    f"import bpy; bpy.ops.wm.save_as_mainfile(filepath=r'{src}')"], check=True, capture_output=True)  # api-lint: ok (test fixture)
    before = (src.stat().st_mtime, src.stat().st_size)
    brief = json.loads((SKILL / "templates" / "project_brief.json").read_text())
    brief["parts"] = brief["parts"][:1]
    path = outdir / "brief.json"
    path.write_text(json.dumps(brief))
    p, summ = run(blender, path, outdir / "proj", "--input-blend", str(src))
    assert p.returncode == 0, p.stdout + p.stderr
    assert (src.stat().st_mtime, src.stat().st_size) == before
