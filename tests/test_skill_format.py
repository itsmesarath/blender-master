"""Agent Skills format: frontmatter, names, size limits, links, and sub-skill layout."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from conftest import ROOT, SKILL

SKILL_FILES = sorted(SKILL.rglob("SKILL.md"))
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ROUTING = json.loads((SKILL / "references" / "routing.json").read_text())
CORE = sorted(k for k, v in ROUTING["subskills"].items() if v == "core")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path}: no frontmatter"
    block = text[4:text.index("\n---\n", 4)]
    out, parent = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith("  ") and parent:
            k, _, v = line.strip().partition(":")
            out[parent][k.strip()] = v.strip().strip('"')
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if v == "":
            out[k], parent = {}, k
        else:
            out[k], parent = v.strip('"'), None
    return out


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_frontmatter(path):
    fm = frontmatter(path)
    assert fm.get("name") == path.parent.name, "name must equal the folder name"
    assert NAME_RE.match(fm["name"]) and len(fm["name"]) <= 64
    desc = fm.get("description", "")
    assert 40 <= len(desc) <= 1024, f"description length {len(desc)}"
    assert fm.get("license") == "MIT"
    assert "compatibility" in fm and len(fm["compatibility"]) <= 500


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_size_limits(path):
    lines = path.read_text(encoding="utf-8").count("\n")
    limit = 250 if path.parent == SKILL else 200
    assert lines <= limit, f"{path.name} has {lines} lines (keep detail in references/)"


def _md_files():
    return sorted(p for p in ROOT.rglob("*.md") if "_output" not in p.parts and "out" not in p.parts
                  and ".git" not in p.parts)


@pytest.mark.parametrize("path", _md_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if re.match(r"[a-z]+://", target) or target.startswith("#") or target.startswith("mailto:"):
            continue
        dest = (path.parent / target.split("#")[0]).resolve()
        assert dest.exists(), f"{path.relative_to(ROOT)}: broken link {target}"


@pytest.mark.parametrize("name", CORE)
def test_core_subskill_layout(name):
    d = SKILL / "subskills" / name
    assert (d / "SKILL.md").exists()
    refs = list((d / "references").glob("*.md"))
    assert refs, f"{name}: references/ is empty"
    scripts = list((d / "scripts").glob("*.py"))
    assert scripts, f"{name}: scripts/ is empty"


@pytest.mark.parametrize("name", [n for n in CORE if (SKILL / "subskills" / n / "scripts" / "ops.py").exists()])
def test_ops_are_documented(name):
    d = SKILL / "subskills" / name
    src = (d / "scripts" / "ops.py").read_text()
    m = re.search(r"^OPS\s*=\s*\{(.*?)\}", src, re.S | re.M)
    assert m, f"{name}: ops.py has no OPS table"
    ops = re.findall(r'"(\w+)"\s*:', m.group(1))
    doc = (d / "SKILL.md").read_text()
    missing = [o for o in ops if f"`{o}`" not in doc]
    assert not missing, f"{name}: SKILL.md does not mention ops {missing}"


def test_coordinator_links_every_core_subskill():
    text = (SKILL / "SKILL.md").read_text()
    for name in CORE:
        assert f"subskills/{name}/SKILL.md" in text, name


def test_taxonomy_has_15_types_and_routes_every_role():
    tax = json.loads((SKILL / "references" / "taxonomy.json").read_text())
    assert len(tax["types"]) == 15
    roles = {r for t in tax["types"].values() for r in t["roles"]}
    roles |= {r for rs in tax["modifier_roles"].values() for r in rs}
    assert roles <= set(ROUTING["roles"]), roles - set(ROUTING["roles"])
    assert roles <= set(tax["role_dependencies"]), roles - set(tax["role_dependencies"])


def test_licence_and_no_binaries():
    assert "MIT License" in (ROOT / "LICENSE").read_text()
    banned = {".blend", ".png", ".jpg", ".exr", ".mp4"}
    import subprocess
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    assert not [f for f in files if Path(f).suffix.lower() in banned]


@pytest.mark.parametrize("name", [n for n in CORE if (SKILL / "subskills" / n / "scripts" / "ops.py").exists()])
def test_core_subskill_has_blender_case(name):
    cases = "\n".join(p.read_text() for p in (ROOT / "tests" / "cases").rglob("case_*.py"))
    assert f'"{name}"' in cases, f"{name}: no Blender test case loads it"
