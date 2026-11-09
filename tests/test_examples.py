"""End to end: one-line request -> brief -> parts -> PASS reports -> renders, for each example."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from conftest import OUTPUT, ROOT, SKILL

EXAMPLES = ["01-product-packshot", "02-game-prop-crate", "03-small-interior", "04-character-full-run",
            "05-procedural-city-block", "06-product-ad-shot"]


@pytest.mark.slow
@pytest.mark.parametrize("name", EXAMPLES)
def test_example_end_to_end(blender, name):
    ex = ROOT / "examples" / name
    out = OUTPUT / "examples" / name
    if out.exists():
        import shutil
        shutil.rmtree(out)
    env = dict(os.environ, BLENDER_BIN=blender)
    req = (ex / "request.txt").read_text().strip()
    subprocess.run([sys.executable, str(SKILL / "scripts" / "plan_project.py"), "--request", req,
                    "--params", str(ex / "params.json"), "--out", str(out)], check=True, capture_output=True, env=env)
    p = subprocess.run([sys.executable, str(SKILL / "scripts" / "run_project.py"), "--brief",
                        str(out / "brief" / "brief.json"), "--out", str(out)],
                       capture_output=True, text=True, env=env, timeout=2400)
    assert p.returncode == 0, p.stdout[-3000:]
    summ = json.loads((out / "run_summary.json").read_text())
    assert summ["pass"] and all(x["status"] == "PASS" for x in summ["parts"])
    renders = list((out / "renders").glob("*.png"))
    assert renders
    qa = json.loads((out / "brief" / "qa_report.json").read_text())
    assert qa["pass"], qa["failed"]
