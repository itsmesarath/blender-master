#!/usr/bin/env python3
"""Execute a project brief headless, part by part, in dependency order.

Usage:
  python run_project.py --brief project/brief/brief.json --out project [--blender PATH] [--only P03-...]

For every part: launch Blender on a copy of the latest saved version, run the part's ops, check,
auto-fix (max 3 rounds inside the part), preview, save ``<project>_v###.blend``. A crash is retried
from the same input up to 3 attempts. A part that ends in ASK or ERROR blocks its dependants, and
the run stops with a question for the user instead of guessing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from bm_plan import topo_order, validate_brief  # noqa: E402

MAX_ATTEMPTS = 3


def find_blender(explicit: str | None) -> str:
    cand = explicit or os.environ.get("BLENDER_BIN") or shutil.which("blender")
    if not cand or not os.path.exists(cand):
        raise SystemExit("Blender not found: pass --blender or set BLENDER_BIN")
    return cand


def run_one(blender, brief_path, part, out, in_blend, attempt, log):
    cmd = [blender, "-b"]
    if in_blend:
        cmd.append(in_blend)
    cmd += ["--factory-startup", "--python-exit-code", "1", "--python", os.path.join(HERE, "part_entry.py"),
            "--", "--brief", brief_path, "--part", part["id"], "--out", out, "--skill-root", SKILL_ROOT,
            "--attempt", str(attempt)]
    t = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    with open(log, "a") as f:
        f.write(f"\n===== {part['id']} attempt {attempt} rc={proc.returncode} {time.time() - t:.1f}s\n")
        f.write(proc.stdout[-20000:])
        f.write(proc.stderr[-5000:])
    rp = os.path.join(out, "reports", f"{part['id']}.json")
    if proc.returncode != 0 or not os.path.exists(rp):
        return {"part": part["id"], "status": "ERROR", "errors": [f"blender exit {proc.returncode}"]}
    with open(rp) as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blender")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--input-blend", help="user file to start from (a copy is used; never written)")
    a = ap.parse_args(argv)
    blender = find_blender(a.blender)
    out = os.path.abspath(a.out)
    brief_path = os.path.abspath(a.brief)
    brief = json.load(open(brief_path))
    errs = validate_brief(brief)
    if errs:
        raise SystemExit("invalid brief: " + "; ".join(errs))
    for d in ("reports", "previews", "blend", "renders", "exports", "brief"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    log = os.path.join(out, "run_log.txt")
    current = None
    if a.input_blend:
        current = os.path.join(out, "blend", "input_copy.blend")
        shutil.copy2(a.input_blend, current)
    status = {}
    summary = {"project": brief["project"], "blender": blender, "parts": []}
    for part in topo_order(brief["parts"]):
        pid = part["id"]
        if a.only and pid not in a.only:
            continue
        blocked = [d for d in part["depends_on"] if status.get(d) not in ("PASS", "MANUAL")]
        if blocked:
            status[pid] = "BLOCKED"
            summary["parts"].append({"part": pid, "status": "BLOCKED", "by": blocked})
            continue
        if part.get("mode") == "manual" or part.get("status") == "needs_agent_input":
            st = "MANUAL" if part.get("mode") == "manual" else "NEEDS_INPUT"
            status[pid] = st
            summary["parts"].append({"part": pid, "status": st, "subskill": part["subskill"]})
            if st == "NEEDS_INPUT":
                break
            continue
        rep = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            rep = run_one(blender, brief_path, part, out, current, attempt, log)
            if rep.get("status") != "ERROR":
                break
        st = rep.get("status", "ERROR")
        status[pid] = st
        entry = {"part": pid, "subskill": part["subskill"], "status": st, "attempts": rep.get("attempt", MAX_ATTEMPTS),
                 "fix_rounds": rep.get("fix_rounds", 0),
                 "checks": f"{sum(c['pass'] for c in rep.get('checks', []))}/{len(rep.get('checks', []))}",
                 "previews": [x["path"] for x in rep.get("artefacts", []) if x["kind"] in ("preview", "contact_sheet")]}
        if rep.get("question"):
            entry["question"] = rep["question"]
        if rep.get("errors"):
            entry["errors"] = [e.strip().splitlines()[-1] for e in rep["errors"]]
        summary["parts"].append(entry)
        print(f"{pid:<18} {part['subskill']:<24} {st:<6} checks {entry['checks']}")
        if st == "PASS":
            current = rep.get("blend", current)
        else:
            print(f"  stopped: {entry.get('question') or entry.get('errors')}")
    summary["final_blend"] = current
    summary["pass"] = all(p["status"] in ("PASS", "MANUAL") for p in summary["parts"]) and bool(summary["parts"])
    with open(os.path.join(out, "run_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("RUN", "PASS" if summary["pass"] else "INCOMPLETE", os.path.join(out, "run_summary.json"))
    return 0 if summary["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
