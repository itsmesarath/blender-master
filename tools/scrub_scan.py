#!/usr/bin/env python3
"""No-references scan for this repository.

Checks every tracked text file against
  * tests/scrub/banned.sha256  - salted SHA-256 hashes of normalised n-grams (not readable)
  * tests/scrub/patterns.txt   - public red-flag regexes
  * tests/scrub/url_allow.txt  - hosts that may appear in URLs
and refuses binary media (the repo ships text only).

Reports file:line and the rule that fired, never the banned term itself.
Exit code 0 = clean, 1 = findings.
Usage: python tools/scrub_scan.py [ROOT] [--hashes FILE] [--files F1 F2 ...]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

TEXT_EXT = {".md", ".py", ".yaml", ".yml", ".json", ".txt", ".toml", ".cfg", ".ini", ".sh", ".ps1", ".gitignore", ""}
BINARY_EXT = {".blend", ".blend1", ".png", ".jpg", ".jpeg", ".exr", ".hdr", ".tif", ".tiff", ".webp",
              ".mp4", ".mov", ".avi", ".mkv", ".wav", ".mp3", ".fbx", ".glb", ".gltf", ".usd", ".usdc",
              ".usda", ".usdz", ".abc", ".obj", ".epub", ".pdf", ".srt", ".vtt", ".zip"}
# files that legitimately contain the rules themselves
SELF_FILES = {"tests/scrub/banned.sha256", "tests/scrub/patterns.txt", "tests/scrub/url_allow.txt"}
# the scanner's own media-extension list would trip the extension pattern; hashes still apply
PATTERN_EXEMPT = {"tools/scrub_scan.py"}
URL_RE = re.compile(r"https?://([A-Za-z0-9.\-]+)")


def norm_tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^0-9a-z]+", " ", text)
    return text.split()


def load_hashes(path: Path):
    salt, max_n, hashes = "", 4, set()
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("salt "):
            salt = line.split(None, 1)[1].strip()
        elif line.startswith("max_n "):
            max_n = int(line.split()[1])
        else:
            hashes.add(line.strip())
    return salt, max_n, hashes


def load_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")]


def list_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                             cwd=root, capture_output=True, text=True, check=True).stdout
        return [root / p for p in out.splitlines() if p]
    except Exception:
        skip = {".git", "out", "__pycache__", ".pytest_cache"}
        return [p for p in root.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & skip)]


def scan(root: Path, hash_file: Path, files: list[Path] | None = None) -> list[str]:
    salt, max_n, hashes = load_hashes(hash_file)
    patterns = [re.compile(p, re.I) for p in load_lines(root / "tests/scrub/patterns.txt")]
    allow = load_lines(root / "tests/scrub/url_allow.txt")
    findings: list[str] = []
    for path in files if files is not None else list_files(root):
        if not path.exists() or path.is_dir():
            continue
        rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        if rel in SELF_FILES:
            continue
        ext = path.suffix.lower()
        if ext in BINARY_EXT:
            findings.append(f"{rel}: binary/media file not allowed (text-only repo)")
            continue
        if ext not in TEXT_EXT and path.name not in {"LICENSE", "Makefile"}:
            findings.append(f"{rel}: unknown file type, add it to TEXT_EXT or remove it")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{rel}: not UTF-8 text")
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            for pat in patterns if rel not in PATTERN_EXEMPT else ():
                if pat.search(line):
                    findings.append(f"{rel}:{ln}: red-flag pattern /{pat.pattern}/")
            for host in URL_RE.findall(line):
                host = host.lower().rstrip(".")
                if not any(host == a or host.endswith("." + a) for a in allow):
                    findings.append(f"{rel}:{ln}: URL host not on allowlist ({host})")
        # n-grams across the whole file, so a term broken over two lines is still caught
        toks, line_of = [], []
        for ln, line in enumerate(text.splitlines(), 1):
            for t in norm_tokens(line):
                toks.append(t)
                line_of.append(ln)
        hit_lines = set()
        for i in range(len(toks)):
            for n in range(1, max_n + 1):
                if i + n > len(toks):
                    break
                gram = " ".join(toks[i:i + n])
                if hashlib.sha256((salt + gram).encode()).hexdigest() in hashes:
                    hit_lines.add(line_of[i])
        for ln in sorted(hit_lines):
            findings.append(f"{rel}:{ln}: banned term (hashed list)")
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=Path(__file__).resolve().parents[1], type=Path)
    ap.add_argument("--hashes", type=Path)
    ap.add_argument("--files", nargs="*", type=Path)
    a = ap.parse_args(argv)
    root = a.root.resolve()
    hf = a.hashes or root / "tests/scrub/banned.sha256"
    findings = scan(root, hf, [f.resolve() for f in a.files] if a.files else None)
    for f in findings:
        print(f)
    print(f"scrub: {'FAIL' if findings else 'PASS'} ({len(findings)} findings)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
