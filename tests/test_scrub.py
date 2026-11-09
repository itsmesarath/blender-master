"""The reference scan passes on the clean tree and catches seeded problems."""
from __future__ import annotations

import hashlib
import subprocess
import sys

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import scrub_scan  # noqa: E402


def test_clean_tree_passes():
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "scrub_scan.py")], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-2000:]


def _canary_hashes(tmp_path, terms):
    salt = "testsalt"
    lines = [f"salt {salt}", "max_n 4"] + [hashlib.sha256((salt + t).encode()).hexdigest() for t in terms]
    f = tmp_path / "canary.sha256"
    f.write_text("\n".join(lines) + "\n")
    return f


def test_hashed_term_is_caught_without_revealing_it(tmp_path):
    hashes = _canary_hashes(tmp_path, ["zebra lantern quartz"])
    doc = tmp_path / "note.md"
    doc.write_text("A fine line.\nThis mentions Zebra-Lantern\nQUARTZ across a line break.\n")
    findings = scrub_scan.scan(ROOT, hashes, [doc])
    assert any("banned term" in f for f in findings), findings
    assert not any("zebra" in f.lower() for f in findings)


def test_public_patterns_and_urls_are_caught(tmp_path):
    hashes = _canary_hashes(tmp_path, [])
    doc = tmp_path / "x.md"
    # seeds are assembled at run time so this file itself stays clean
    seed_word = "les" + "son 4"
    seed_url = "https://" + "example" + ".com/file"
    doc.write_text(f"See {seed_word} for this.\nGet it at {seed_url}\nOK: https://docs.blender.org/api/\n")
    findings = scrub_scan.scan(ROOT, hashes, [doc])
    assert any("red-flag" in f and ":1:" in f for f in findings), findings
    assert any("example.com" in f for f in findings), findings
    assert not any(":3:" in f for f in findings), findings


def test_binary_media_refused(tmp_path):
    hashes = _canary_hashes(tmp_path, [])
    img = tmp_path / "render.png"
    img.write_bytes(b"\x89PNG\r\n")
    findings = scrub_scan.scan(ROOT, hashes, [img])
    assert any("binary" in f for f in findings), findings


def test_secrets_pattern(tmp_path):
    hashes = _canary_hashes(tmp_path, [])
    doc = tmp_path / "cfg.py"
    doc.write_text('KEY = "sk-' + "a" * 40 + '"\n')
    assert scrub_scan.scan(ROOT, hashes, [doc])
