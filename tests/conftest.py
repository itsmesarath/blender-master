"""Shared pytest fixtures: find Blender, give each test an output folder under tests/_output/."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "blender-master"
OUTPUT = ROOT / "tests" / "_output"
sys.path.insert(0, str(Path(__file__).resolve().parent))


def find_blender() -> str | None:
    cand = os.environ.get("BLENDER_BIN") or shutil.which("blender")
    return cand if cand and os.path.exists(cand) else None


@pytest.fixture(scope="session")
def blender() -> str:
    path = find_blender()
    if not path:
        pytest.skip("Blender not found: set BLENDER_BIN or put blender on PATH")
    return path


@pytest.fixture
def outdir(request) -> Path:
    d = OUTPUT / request.node.name.replace("/", "_").replace("[", "_").replace("]", "")
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "blender" in item.fixturenames:
            item.add_marker(pytest.mark.blender)
