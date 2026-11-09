"""scripting-automation ops: run a project-local script as a part (after the user approved it),
and lint scripts for 5.x API use."""
from __future__ import annotations

import os
import runpy
import sys

import bm_checks

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import api_lint  # noqa: E402


def run_script(ctx, path, args=None, lint=True):
    """Execute a .py inside this Blender session. Only paths inside the project folder are
    accepted: the coordinator copies an approved script there first."""
    full = os.path.realpath(os.path.join(ctx.out_dir, path))
    if not full.startswith(os.path.realpath(ctx.out_dir) + os.sep):
        raise PermissionError("scripts must live inside the project folder")
    if lint:
        findings = api_lint.lint_paths([full])
        if findings:
            raise ValueError("api-lint findings: " + "; ".join(findings[:5]))
    saved = sys.argv
    sys.argv = [full, "--"] + list(args or [])
    try:
        g = runpy.run_path(full, run_name="__blender_master_part__")
    finally:
        sys.argv = saved
    ctx.script_ran = True
    ctx.report.artefact(full, "script")
    return f"ran {path}: {g.get('RESULT', 'ok')}"


@bm_checks.register("script_ran")
def _script_ran(ctx):
    return bool(getattr(ctx, "script_ran", False)), getattr(ctx, "script_ran", False), True, ""


OPS = {"run_script": run_script}
FIXES = {}
