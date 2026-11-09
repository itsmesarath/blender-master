"""Uniform part report: {part, subskill, attempt, checks[], pass, artefacts[], errors[]}.

Every part script writes one JSON file so the coordinator (and tests) can decide PASS / FIX / ASK
without parsing logs.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path


def script_args(argv: list[str] | None = None) -> list[str]:
    """Arguments after the ``--`` separator of a ``blender -b ... --python x.py -- args`` call."""
    argv = sys.argv if argv is None else argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


class Report:
    def __init__(self, part: str, subskill: str, attempt: int = 1):
        self.data = {
            "part": part, "subskill": subskill, "attempt": attempt, "checks": [], "pass": None,
            "artefacts": [], "errors": [], "notes": [], "fixes": [], "started": time.time(),
        }

    # -- checks ---------------------------------------------------------------------
    def check(self, name: str, passed: bool, value=None, expected=None, detail: str = "") -> bool:
        self.data["checks"].append({"name": name, "pass": bool(passed), "value": _jsonable(value),
                                    "expected": _jsonable(expected), "detail": detail})
        return bool(passed)

    def failed(self) -> list[dict]:
        return [c for c in self.data["checks"] if not c["pass"]]

    def reset_checks(self) -> None:
        self.data["checks"] = []

    # -- extras ---------------------------------------------------------------------
    def artefact(self, path, kind: str = "file") -> None:
        self.data["artefacts"].append({"path": str(path), "kind": kind})

    def note(self, text: str) -> None:
        self.data["notes"].append(text)

    def fix(self, text: str) -> None:
        self.data["fixes"].append(text)

    def error(self, exc: BaseException | str) -> None:
        if isinstance(exc, BaseException):
            self.data["errors"].append("".join(traceback.format_exception(exc)))
        else:
            self.data["errors"].append(str(exc))

    @property
    def passed(self) -> bool:
        return not self.data["errors"] and all(c["pass"] for c in self.data["checks"])

    def finish(self, path) -> dict:
        try:
            import bpy
            self.data["blender"] = bpy.app.version_string
        except ImportError:
            pass
        self.data["pass"] = self.passed
        self.data["seconds"] = round(time.time() - self.data.pop("started", time.time()), 2)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.data, indent=2))
        return self.data


def _jsonable(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    try:
        return [_jsonable(x) for x in v]
    except TypeError:
        return str(v)
