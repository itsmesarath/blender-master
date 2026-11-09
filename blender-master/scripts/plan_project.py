#!/usr/bin/env python3
"""Request -> project brief (recognise + decompose + route).

Usage:
  python plan_project.py --request "..." [--params params.json] --out project_dir
Writes project_dir/brief/brief.json and prints a summary. Parts that still need agent input
(ops) are marked ``needs_agent_input``; fill them in params.json and re-run.
"""
import argparse
import json
import os
import sys

from bm_plan import decompose, recognise, validate_brief


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True)
    ap.add_argument("--params")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    params = json.load(open(a.params)) if a.params else {}
    recog = recognise(a.request)
    if params.get("type_override"):
        recog.update(params["type_override"])
    brief = decompose(a.request, recog, params)
    errs = validate_brief(brief)
    os.makedirs(os.path.join(a.out, "brief"), exist_ok=True)
    path = os.path.join(a.out, "brief", "brief.json")
    with open(path, "w") as f:
        json.dump(brief, f, indent=2)
    print(f"type: {brief['type']['primary']} + {brief['type']['modifiers']}  scores={brief['type']['scores']}")
    for p in brief["parts"]:
        flag = f"  [{p.get('status')}]" if p.get("status") else ""
        print(f"  {p['id']:<16} -> {p['subskill']:<24} deps={p['depends_on']}{flag}")
    for e in errs:
        print("ERROR:", e)
    print(path)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
