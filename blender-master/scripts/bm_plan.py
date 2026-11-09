"""Recognise and decompose a request into a project brief (pure Python, no bpy).

recognise(request)  -> {"primary", "modifiers", "scores", "ambiguous", "question"}
decompose(request, recognition, params) -> brief dict (see references/brief-schema.md)

The agent normally writes ``params`` (facts, per-role ops and extra checks) after reading the
sub-skills. This module supplies the deterministic parts: type scoring, default part list,
dependency graph, routing, and default acceptance checks.
"""
from __future__ import annotations

import copy
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "references")


def _load(name):
    with open(os.path.join(REF, name)) as f:
        return json.load(f)


TAXONOMY = _load("taxonomy.json")
ROUTING = _load("routing.json")


def slug(text: str, n: int = 5) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    stop = {"a", "an", "the", "of", "for", "with", "and", "on", "in", "to", "make", "create", "me", "please", "some"}
    return "-".join([w for w in words if w not in stop][:n]) or "project"


def score(request: str) -> dict:
    text = " " + re.sub(r"\s+", " ", request.lower()) + " "
    out = {}
    for tname, t in TAXONOMY["types"].items():
        s = 0
        for phrase, w in t["signals"].items():
            if re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text):
                s += w
        out[tname] = s
    return out


def recognise(request: str) -> dict:
    sc = score(request)
    ranked = sorted(sc.items(), key=lambda kv: -kv[1])
    primary, top = ranked[0]
    if top == 0:
        primary = "lookdev"
    thr = TAXONOMY["modifier_threshold"]
    mods = [t for t, s in ranked[1:] if s >= thr and t in TAXONOMY["modifier_roles"]]
    ambiguous, question = False, None
    if len(ranked) > 1 and top > 0:
        second, s2 = ranked[1]
        roles_a = set(TAXONOMY["types"][primary]["roles"])
        roles_b = set(TAXONOMY["types"][second]["roles"])
        if top - s2 < TAXONOMY["ambiguity_margin"] and roles_a != roles_b:
            ambiguous = True
            question = (f"Is this mainly a {TAXONOMY['types'][primary]['label']} or a "
                        f"{TAXONOMY['types'][second]['label']}? It changes the part list.")
    return {"primary": primary, "modifiers": mods, "scores": {k: v for k, v in ranked if v},
            "ambiguous": ambiguous, "question": question}


# ----------------------------------------------------------------- default checks per role
def default_acceptance(role: str, facts: dict) -> list[dict]:
    subj = facts.get("subject_prefix", "GEO_")
    size = facts.get("subject_size")
    hero = facts.get("hero_camera", "CAM_hero")
    cams = facts.get("cameras", [hero])
    closed = facts.get("closed_meshes", True)
    a = []
    if role == "blockout":
        a += [{"check": "objects_exist", "args": {"prefix": "PRX_"}, "desc": "proxies exist"},
              {"check": "cameras_exist", "args": {"names": cams}, "desc": "hero cameras exist"},
              {"check": "custom_prop", "args": {"objects": "PRX_", "key": "brief_note"}, "desc": "every proxy carries a brief note"},
              {"check": "names_valid", "desc": "naming convention"}]
        if size:
            a.append({"check": "bounds_size", "args": {"objects": facts.get("subject_proxy", "PRX_"), "target": size, "tol": 0.05},
                      "desc": "subject proxy matches brief size within 5%"})
    elif role == "environment":
        a += [{"check": "objects_exist", "args": {"prefix": "GEO_"}, "desc": "environment geometry exists"},
              {"check": "names_valid", "desc": "naming convention"}]
    elif role == "procedural":
        a += [{"check": "objects_exist", "args": {"prefix": "GEO_"}, "desc": "generated geometry exists"},
              {"check": "gn_evaluates", "args": {"objects": facts.get("procedural_prefix", "GEO_")},
               "desc": "every node-based object evaluates to non-empty geometry"}]
    elif role == "sculpt":
        a += [{"check": "objects_exist", "args": {"prefix": facts.get("sculpt_target", subj)}, "desc": "sculpt target exists"},
              {"check": "sculpt_detail", "args": {"objects": facts.get("sculpt_target", subj),
                                                  "min_verts": facts.get("sculpt_min_verts", 5000)},
               "desc": "high-resolution detail present"}]
    elif role == "retopo":
        low = facts.get("retopo_low", subj)
        a += [{"check": "objects_exist", "args": {"prefix": low}, "desc": "low-poly mesh exists"},
              {"check": "scale_applied", "args": {"objects": low}, "desc": "scale applied"},
              {"check": "quad_ratio", "args": {"objects": low, "min_ratio": facts.get("min_quad_ratio", 0.85)},
               "desc": "mostly quads"}]
        if facts.get("retopo_high"):
            a.append({"check": "surface_distance", "args": {"low": low, "high": facts["retopo_high"],
                                                            "max_mean": facts.get("retopo_max_mean", 0.01)},
                      "desc": "low-poly hugs the high-poly surface"})
        if facts.get("tri_budget"):
            a.append({"check": "tri_budget", "args": {"objects": low, "max_tris": facts["tri_budget"]},
                      "desc": "triangle budget"})
    elif role == "bake":
        a += [{"check": "bake_nonempty", "args": {"pattern": "textures/*.png"}, "desc": "baked maps exist and are not flat"}]
    elif role == "hair":
        a += [{"check": "curve_count", "args": {"prefix": facts.get("hair_prefix", "GEO_"), "min_curves": facts.get("min_curves", 100)},
               "desc": "hair curves generated"}]
    elif role == "rig_face":
        a += [{"check": "shape_keys_valid", "args": {"objects": facts.get("face_mesh", subj)}, "desc": "every shape key moves vertices and stays bounded"},
              {"check": "drivers_resolve", "args": {"objects": facts.get("face_mesh", subj)}, "desc": "all drivers valid"}]
    elif role == "rig_body":
        a += [{"check": "objects_exist", "args": {"prefix": "RIG_", "types": ["ARMATURE"]}, "desc": "armature exists"},
              {"check": "weights_valid", "args": {"objects": facts.get("skin_mesh", subj)}, "desc": "every vertex weighted, max 4 influences, normalised"},
              {"check": "pose_deform_ok", "args": {"objects": facts.get("skin_mesh", subj)}, "desc": "test poses deform without collapse or explosion"}]
    elif role == "animation":
        a += [{"check": "anim_present", "args": {"objects": facts.get("animated", "*"), "min_curves": 1}, "desc": "animation curves exist in range"}]
        if facts.get("loop"):
            a.append({"check": "loop_ok", "args": {"objects": facts.get("animated", "*")}, "desc": "seamless loop"})
    elif role == "simulation":
        a += [{"check": "sim_moved", "args": {"objects": facts.get("sim_objects", "GEO_")}, "desc": "simulated objects move"},
              {"check": "no_explosion", "args": {"objects": facts.get("sim_objects", "GEO_")}, "desc": "simulation stays bounded"}]
    elif role == "edit":
        a += [{"check": "edit_no_gaps", "desc": "every frame of the cut is covered"},
              {"check": "video_ok", "args": {"path": facts.get("video", "video/edit.mp4"), "fps": facts.get("fps", 24),
                                             "audio": facts.get("video_audio")},
               "desc": "video file exists with expected duration, fps and audio"}]
    elif role == "model":
        a += [{"check": "objects_exist", "args": {"prefix": "GEO_"}, "desc": "final geometry exists"},
              {"check": "scale_applied", "args": {"objects": "GEO_"}, "desc": "scale applied, no negative scale"},
              {"check": "names_valid", "desc": "naming convention"}]
        if not facts.get("allow_ngons"):
            a.append({"check": "no_ngons", "args": {"objects": subj}, "desc": "no n-gons on the subject"})
        if facts.get("min_quad_ratio"):
            a.append({"check": "quad_ratio", "args": {"objects": subj, "min_ratio": facts["min_quad_ratio"]},
                      "desc": "quad-dominant topology"})
        if closed:
            a += [{"check": "manifold", "args": {"objects": subj}, "desc": "closed, manifold subject meshes"},
                  {"check": "normals_outward", "args": {"objects": subj}, "desc": "normals face outward"}]
        if size:
            a.append({"check": "bounds_size", "args": {"objects": subj, "target": size, "tol": facts.get("size_tol", 0.05)},
                      "desc": "subject matches brief size"})
        if facts.get("grounded", True):
            a.append({"check": "on_ground", "args": {"objects": subj, "ground_z": facts.get("ground_z", 0.0)},
                      "desc": "subject rests on the ground plane"})
        if facts.get("tri_budget"):
            a.append({"check": "tri_budget", "args": {"objects": subj, "max_tris": facts["tri_budget"]},
                      "desc": "triangle budget"})
    elif role == "uv":
        a += [{"check": "uv_present", "args": {"objects": subj}, "desc": "every subject mesh has a UV map"},
              {"check": "uv_in_bounds", "args": {"objects": subj}, "desc": "UVs inside 0-1"}]
    elif role in ("materials", "npr"):
        a += [{"check": "materials_filled", "args": {"objects": "GEO_"}, "desc": "every slot filled, no missing textures"}]
    elif role in ("lighting", "product"):
        a += [{"check": "lights_exist", "args": {"min_count": 1}, "desc": "at least one light"},
              {"check": "cameras_exist", "args": {"names": cams}, "desc": "deliverable cameras exist"},
              {"check": "camera_frames", "args": {"camera": hero, "objects": facts.get("frame_objects", subj),
                                                  "margin": facts.get("frame_margin", 0.04),
                                                  "min_fill": facts.get("min_fill", 0.15)},
               "desc": "subject fully in frame with margin"},
              {"check": "exposure", "args": dict({"camera": hero}, **facts.get("exposure", {})),
               "desc": "exposure sane: no crushed or clipped frame"}]
    elif role == "render":
        a += [{"check": "render_ok", "args": {"pattern": "renders/*.png", "min_count": len(cams),
                                              "size": facts.get("resolution"),
                                              "need_alpha": bool(facts.get("transparent"))},
               "desc": "deliverable renders exist, right size, not black"}]
    elif role == "qa":
        a += [{"check": "files_exist", "args": {"patterns": ["brief/qa_report.md", "brief/qa_report.json"]},
               "desc": "QA report written"},
              {"check": "qa_all_pass", "desc": "every earlier acceptance check passes on the final file"}]
    elif role == "export":
        a += [{"check": "files_exist", "args": {"patterns": ["exports/*"]}, "desc": "export files written"},
              {"check": "roundtrip_match", "desc": "re-import keeps meshes, materials and size"}]
    elif role == "script":
        a += [{"check": "script_ran", "desc": "script exits 0 headless and is idempotent"}]
    return a


# ----------------------------------------------------------------- decomposition
def roles_for(recog: dict) -> list[str]:
    roles = list(TAXONOMY["types"][recog["primary"]]["roles"])
    for m in recog["modifiers"]:
        for r in TAXONOMY["modifier_roles"].get(m, []):
            if r not in roles:
                roles.append(r)
    order = list(TAXONOMY["role_dependencies"].keys())
    return sorted(roles, key=order.index)


def route(role: str) -> dict:
    r = ROUTING["roles"][role]
    sub = r["subskill"]
    status = ROUTING["subskills"].get(sub, "core")
    if status == "core":
        return {"subskill": sub, "routed_via": "primary"}
    fb = r.get("fallback", "manual")
    return {"subskill": fb, "routed_via": f"fallback ({sub} is {status})", "intended": sub}


def decompose(request: str, recog: dict | None = None, params: dict | None = None) -> dict:
    recog = recog or recognise(request)
    params = copy.deepcopy(params or {})
    facts = params.get("facts", {})
    role_params = params.get("roles", {})
    skip = set(params.get("skip_roles", []))
    roles = roles_for(recog)
    order = list(TAXONOMY["role_dependencies"].keys())
    for extra in params.get("add_roles", []):          # e.g. an edit pass on a product shot
        if extra not in roles:
            if extra not in order:
                raise ValueError(f"unknown role {extra!r}")
            roles.append(extra)
    roles = sorted((r for r in roles if r not in skip), key=order.index)
    # a role routed to manual with no params is listed as a manual step, not executed headless
    ids = {}
    parts = []
    for i, role in enumerate(roles, 1):
        ids[role] = f"P{i:02d}-{role}"
    for role in roles:
        rt = route(role)
        deps = [ids[d] for d in TAXONOMY["role_dependencies"][role] if d in ids]
        rp = role_params.get(role, {})
        acc = rp.get("acceptance_override") or default_acceptance(role, facts)
        acc = acc + rp.get("acceptance_extra", [])
        part = {"id": ids[role], "role": role, "subskill": rp.get("subskill", rt["subskill"]),
                "routed_via": rt["routed_via"], "depends_on": deps, "goal": rp.get("goal", ""),
                "mode": "manual" if rt["subskill"] == "manual" else params.get("execution_mode", "headless"),
                "ops": rp.get("ops", []), "acceptance": acc}
        if "intended" in rt:
            part["intended_subskill"] = rt["intended"]
        if "preview" in rp:
            part["preview"] = rp["preview"]
        if part["mode"] != "manual" and not part["ops"] and role not in ("qa",):
            part["status"] = "needs_agent_input"
        parts.append(part)
    assumptions = list(params.get("assumptions", []))
    for p in parts:
        if p["routed_via"].startswith("fallback"):
            assumptions.append(f"{p['id']}: {p['routed_via']}; handled by {p['subskill']}")
    if recog.get("ambiguous"):
        assumptions.append(f"type ambiguous; assumed {recog['primary']} ({recog['question']})")
    return {
        "schema": "blender-master/brief@1",
        "project": params.get("project", slug(request)),
        "request": request,
        "type": {"primary": recog["primary"], "modifiers": recog["modifiers"], "scores": recog["scores"]},
        "deliverables": params.get("deliverables", [{"kind": "still", "res": facts.get("resolution", [1920, 1080]),
                                                     "cameras": facts.get("cameras", ["CAM_hero"])}]),
        "units": params.get("units", "metric_m"),
        "style": params.get("style", {"look": "realistic"}),
        "budget": params.get("budget", {}),
        "facts": facts,
        "assumptions": assumptions,
        "questions": [recog["question"]] if recog.get("ambiguous") else [],
        "execution_mode": params.get("execution_mode", "headless"),
        "parts": parts,
    }


def topo_order(parts: list[dict]) -> list[dict]:
    done, out, pending = set(), [], list(parts)
    while pending:
        ready = [p for p in pending if all(d in done for d in p["depends_on"])]
        if not ready:
            raise ValueError("dependency cycle in parts: " + ", ".join(p["id"] for p in pending))
        for p in ready:
            out.append(p)
            done.add(p["id"])
            pending.remove(p)
    return out


def validate_brief(brief: dict) -> list[str]:
    errs = []
    ids = {p["id"] for p in brief.get("parts", [])}
    for k in ("schema", "project", "request", "type", "parts"):
        if k not in brief:
            errs.append(f"missing key {k}")
    for p in brief.get("parts", []):
        for d in p.get("depends_on", []):
            if d not in ids:
                errs.append(f"{p['id']}: unknown dependency {d}")
        if not p.get("acceptance"):
            errs.append(f"{p['id']}: no acceptance checks")
    try:
        topo_order(brief.get("parts", []))
    except ValueError as e:
        errs.append(str(e))
    return errs
