"""Recognition, decomposition, routing and brief validation (pure Python, no Blender)."""
from __future__ import annotations

import json
import sys

import pytest

from conftest import ROOT, SKILL

sys.path.insert(0, str(SKILL / "scripts"))
import bm_plan  # noqa: E402

EXAMPLES = {
    "01-product-packshot": "product_shot",
    "02-game-prop-crate": "game_asset",
    "03-small-interior": "interior",
    "04-character-full-run": "character",
    "05-procedural-city-block": "environment",
    "06-product-ad-shot": "product_shot",
}
OVERRIDDEN = {"04-character-full-run", "05-procedural-city-block", "06-product-ad-shot"}
MORE = [
    ("rig my character with IK legs and a foot roll", "rigging"),
    ("write a python script to batch rename objects and export each as FBX", "scripting"),
    ("a procedural city block generator with geometry nodes", "procedural"),
    ("a stylised toon shaded fox with outlines", "stylized"),
    ("cloth falling over a logo then a smoke burst", "vfx_sim"),
]


@pytest.mark.parametrize("name,expected", EXAMPLES.items())
def test_examples_recognised(name, expected):
    req = (ROOT / "examples" / name / "request.txt").read_text().strip()
    params = json.loads((ROOT / "examples" / name / "params.json").read_text())
    if name in OVERRIDDEN:     # the agent pinned the type after reading the request
        assert params["type_override"]["primary"] == expected
    else:
        assert bm_plan.recognise(req)["primary"] == expected


@pytest.mark.parametrize("req,expected", MORE)
def test_other_types_recognised(req, expected):
    assert bm_plan.recognise(req)["primary"] == expected


def test_unknown_request_defaults_to_lookdev():
    r = bm_plan.recognise("make it nicer")
    assert r["primary"] == "lookdev"


@pytest.mark.parametrize("name", EXAMPLES)
def test_example_briefs_are_valid_dags(name):
    req = (ROOT / "examples" / name / "request.txt").read_text().strip()
    params = json.loads((ROOT / "examples" / name / "params.json").read_text())
    rec = bm_plan.recognise(req)
    if params.get("type_override"):
        rec.update(params["type_override"])
    brief = bm_plan.decompose(req, rec, params)
    assert bm_plan.validate_brief(brief) == []
    order = [p["id"] for p in bm_plan.topo_order(brief["parts"])]
    assert order[0].endswith("blockout")
    assert order[-1].endswith(("qa", "export"))
    for p in brief["parts"]:
        assert p["acceptance"], p["id"]
        assert p.get("status") != "needs_agent_input", p["id"]
        assert (SKILL / "subskills" / p["subskill"] / "scripts" / "ops.py").exists(), p["subskill"]


def test_without_params_parts_need_agent_input():
    brief = bm_plan.decompose("a hard surface sci-fi crate prop")
    assert any(p.get("status") == "needs_agent_input" for p in brief["parts"])
    assert bm_plan.validate_brief(brief) == []


def test_no_core_role_falls_back():
    """Every role whose sub-skill is core routes to it (Phase 2: all 22 are core)."""
    import json as _json
    routing = _json.loads((SKILL / "references" / "routing.json").read_text())
    for req in ["rig my character with IK legs", "a procedural city block generator with geometry nodes",
                "a stylised toon shaded fox with outlines", "cloth falling over a logo then a smoke burst",
                "a short animated logo sting edited to mp4", "a hairy creature sculpt"]:
        brief = bm_plan.decompose(req)
        for p in brief["parts"]:
            sub = routing["roles"][p["role"]]["subskill"]
            if routing["subskills"].get(sub) == "core":
                assert p["routed_via"] == "primary", (req, p["role"], p["routed_via"])
                assert (SKILL / "subskills" / sub / "SKILL.md").exists(), sub


def test_later_subskill_routes_to_fallback():
    brief = bm_plan.decompose("a 2D grease pencil animation of a bouncing ball")
    vias = {p["role"]: p["routed_via"] for p in brief["parts"]}
    assert vias.get("gp2d", "").startswith("fallback"), vias


def test_add_roles_appends_in_order():
    brief = bm_plan.decompose("studio packshot of a bottle", {"primary": "product_shot", "modifiers": [], "scores": {}, "ambiguous": False},
                              {"add_roles": ["edit"]})
    roles = [p["role"] for p in brief["parts"]]
    assert "edit" in roles and roles.index("edit") > roles.index("render")


def test_dependencies_respect_freeze_rules():
    brief = bm_plan.decompose("game-ready low-poly crate for Unity, export FBX")
    ids = {p["role"]: p for p in brief["parts"]}
    if "uv" in ids:
        assert ids["model"]["id"] in ids["uv"]["depends_on"]
    assert ids["model"]["id"] in ids["materials"]["depends_on"] or "uv" in ids
    assert ids["qa"]["id"] in ids["export"]["depends_on"]


def test_cycle_detected():
    parts = [{"id": "A", "depends_on": ["B"], "acceptance": [1]}, {"id": "B", "depends_on": ["A"], "acceptance": [1]}]
    with pytest.raises(ValueError):
        bm_plan.topo_order(parts)


def test_template_brief_is_valid():
    brief = json.loads((SKILL / "templates" / "project_brief.json").read_text())
    assert bm_plan.validate_brief(brief) == []
