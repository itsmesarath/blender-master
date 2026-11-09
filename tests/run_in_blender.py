"""Run a test case inside headless Blender and return its JSON result.

python tests/run_in_blender.py CASE.py OUT_DIR [--blend FILE] [-- extra args]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_case(blender: str, case: str | Path, out_dir: str | Path, blend: str | None = None,
             extra: list[str] | None = None, timeout: int = 600) -> dict:
    case = Path(case)
    if not case.is_absolute():
        case = ROOT / "tests" / "cases" / case
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [blender, "-b"] + ([str(blend)] if blend else []) + [
        "--factory-startup", "--python-exit-code", "1", "--python", str(case), "--",
        "--out", str(out_dir)] + list(extra or [])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    (out_dir / "blender_log.txt").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    res_path = out_dir / "result.json"
    result = json.loads(res_path.read_text()) if res_path.exists() else {}
    result["_returncode"] = proc.returncode
    result["_log"] = str(out_dir / "blender_log.txt")
    return result


def failures(result: dict) -> list[str]:
    """Readable list of failed assertions from a case result."""
    out = [f"{c['name']}: got {c.get('value')!r} expected {c.get('expected')!r} {c.get('detail', '')}"
           for c in result.get("checks", []) if not c["pass"]]
    out += [f"error: {e}" for e in result.get("errors", [])]
    if result.get("_returncode"):
        out.append(f"blender exit code {result['_returncode']} (log: {result.get('_log')})")
    if not result.get("checks") and not result.get("errors"):
        out.append(f"no result written (log: {result.get('_log')})")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    extra = args[args.index("--") + 1:] if "--" in args else []
    args = args[:args.index("--")] if "--" in args else args
    blend = None
    if "--blend" in args:
        i = args.index("--blend")
        blend = args[i + 1]
        del args[i:i + 2]
    res = run_case(os.environ.get("BLENDER_BIN", "blender"), args[0], args[1], blend, extra)
    print(json.dumps(res, indent=2))
    sys.exit(1 if failures(res) else 0)
