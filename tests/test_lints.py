"""api_lint (5.x API + unsafe habits) and the live chunk linter."""
from __future__ import annotations

import subprocess
import sys

import pytest

from conftest import ROOT, SKILL

sys.path.insert(0, str(SKILL / "subskills" / "scripting-automation" / "scripts"))
sys.path.insert(0, str(SKILL / "subskills" / "live-control-mcp" / "scripts"))
import api_lint  # noqa: E402
import lint_chunks  # noqa: E402

BAD = {
    "eevee_next": "sc.render.engine = 'BLENDER_EEVEE_NEXT'",  # api-lint: ok
    "node_tree": "tree = bpy.context.scene.node_tree",  # api-lint: ok
    "composite": "n = tree.nodes.new('CompositorNodeComposite')",  # api-lint: ok
    "fcurves": "for fc in obj.animation_data.action.fcurves: pass",  # api-lint: ok
    "gn_dict": "mod['Socket_2'] = 3",  # api-lint: ok
    "fast_solver": "m.solver = 'FAST'",  # api-lint: ok
    "sequences": "for s in ed.sequences_all: pass",  # api-lint: ok
    "bgl": "import bgl",  # api-lint: ok
    "exec": "exec(code)",  # api-lint: ok
    "overwrite": "bpy.ops.wm.save_mainfile()",  # api-lint: ok
    "autorun": "prefs.filepaths.use_scripts_auto_execute = True",  # api-lint: ok
}


@pytest.mark.parametrize("case", BAD)
def test_api_lint_flags(case):
    assert api_lint.lint_text(BAD[case]), case


def test_api_lint_allows_good_code():
    good = "bpy.ops.wm.save_as_mainfile(filepath=p, copy=True)\nsc.render.engine = 'BLENDER_EEVEE'\n"
    assert api_lint.lint_text(good) == []


def test_repo_passes_api_lint():
    p = subprocess.run([sys.executable, str(SKILL / "subskills" / "scripting-automation" / "scripts" / "api_lint.py"),
                        str(SKILL), str(ROOT / "tests")], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout


def test_chunk_templates_pass():
    assert lint_chunks.main([]) == 0


@pytest.mark.parametrize("chunk,why", [
    ("import bpy, json\nprint(json.dumps({}))\n", "header"),
    ("# SCOPE: x\nimport bpy\nbpy.ops.object.delete()\n", "json print"),
    ("# SCOPE: x\nimport subprocess, json\nprint(json.dumps({}))\n", "subprocess"),
    ("# SCOPE: x\nimport os, json\nos.remove('a')\nprint(json.dumps({}))\n", "delete"),
    ("# SCOPE: x\nimport json\n" + "a = 1\n" * 60 + "print(json.dumps({}))\n", "length"),
    ("# SCOPE: x\nimport bpy, json\nbpy.context.scene.node_tree\nprint(json.dumps({}))\n", "api"),  # api-lint: ok
])
def test_bad_chunks_fail(chunk, why):
    assert lint_chunks.lint_chunk(chunk, why), why
