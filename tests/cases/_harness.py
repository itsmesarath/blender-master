"""Imported by every Blender-side test case.

Gives a case: the skill's lib on sys.path, a project-like context (``ctx``) for calling sub-skill
ops and checks, ``expect`` for assertions, and ``finish`` which writes OUT/result.json.
"""
from __future__ import annotations

import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SKILL = os.path.join(ROOT, "blender-master")
sys.path.insert(0, os.path.join(SKILL, "lib"))

import bm_checks  # noqa: E402
import bm_part  # noqa: E402
import bm_report  # noqa: E402


def _args():
    a = bm_report.script_args()
    out = a[a.index("--out") + 1] if "--out" in a else os.path.join(ROOT, "tests", "_output", "adhoc")
    rest = [x for i, x in enumerate(a) if x != "--out" and (i == 0 or a[i - 1] != "--out")]
    return os.path.abspath(out), rest


OUT, ARGS = _args()
os.makedirs(OUT, exist_ok=True)
_RESULT = {"checks": [], "errors": [], "data": {}}


def make_ctx(project="test", facts=None, part_id="T01-test", subskill="qa-review", parts=None, deliverables=None):
    brief = {"project": project, "facts": facts or {}, "parts": parts or [], "deliverables": deliverables or []}
    part = {"id": part_id, "role": "test", "subskill": subskill}
    rep = bm_report.Report(part_id, subskill)
    return bm_part.Ctx(brief, part, OUT, 1, rep, SKILL)


def ops(name):
    return bm_part.load_subskill(SKILL, name)


def check(ctx, name, **args):
    """Run a registered check; returns (passed, value)."""
    ok, value, expected, detail = bm_checks.run(ctx, {"check": name, "args": args})
    ctx.report.check(name, ok, value, expected, detail)   # fixers read the latest probe from here
    return bool(ok), value


def expect(name, cond, value=None, expected=None, detail=""):
    _RESULT["checks"].append({"name": name, "pass": bool(cond), "value": _j(value), "expected": _j(expected),
                              "detail": detail})
    return bool(cond)


def data(key, value):
    _RESULT["data"][key] = _j(value)


def _j(v):
    try:
        json.dumps(v)
        return v
    except TypeError:
        return repr(v)


def run(fn):
    """Run the case body, record exceptions, always write result.json."""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        _RESULT["errors"].append(f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-1500:]}")
    _RESULT["pass"] = not _RESULT["errors"] and all(c["pass"] for c in _RESULT["checks"])
    with open(os.path.join(OUT, "result.json"), "w") as f:
        json.dump(_RESULT, f, indent=2)
    print("[case]", "PASS" if _RESULT["pass"] else "FAIL", os.path.join(OUT, "result.json"))
