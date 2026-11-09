"""Headless Blender cases for the shared library and every core sub-skill."""
from __future__ import annotations

import pytest

from conftest import ROOT
from run_in_blender import failures, run_case

CASES = sorted(p.relative_to(ROOT / "tests" / "cases") for p in (ROOT / "tests" / "cases").rglob("case_*.py"))


@pytest.mark.parametrize("case", CASES, ids=lambda p: str(p.with_suffix("")))
def test_case(blender, outdir, case):
    res = run_case(blender, case, outdir)
    assert not failures(res), "\n".join(failures(res))
