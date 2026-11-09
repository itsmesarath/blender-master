#!/usr/bin/env python3
"""Lint live-MCP code chunks before they are sent to a running Blender.

python lint_chunks.py chunk.py [more.py | templates.md ...]
Markdown files: every fenced ```python block is linted as one chunk.
Rules: '# SCOPE:' header on the first line, <= 60 lines, ends with a print(json.dumps(...)),
no forbidden calls, plus the 5.x API rules from scripting-automation/api_lint.py.
Exit 0 = clean, 1 = findings.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "scripting-automation" / "scripts"))
import api_lint  # noqa: E402

MAX_LINES = 60
FORBIDDEN = [
    (r"\bimport\s+(subprocess|socket|requests|urllib|http)\b|\bfrom\s+(subprocess|socket|urllib|http)\b",
     "no shell or network modules in live chunks"),
    (r"\bos\.(system|popen|remove|unlink|rmdir)\b|\bshutil\.(rmtree|move)\b", "no shell calls or file deletion"),
    (r"\bopen\([^)]*[\"'][wa]", "chunks do not write files directly (use Blender save/render with paths)"),
    (r"wm\.read_factory_settings|wm\.read_homefile|preferences\.(keymap|filepaths)|save_userpref",
     "do not reset or change the user's preferences or startup file"),
    (r"bpy\.ops\.wm\.quit_blender", "do not quit the user's Blender"),
    (r"\b0\.0\.0\.0\b", "never bind to all interfaces"),
]
FORBIDDEN_RX = [(re.compile(p), m) for p, m in FORBIDDEN]


def _is_json_print(node) -> bool:
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        return False
    call = node.value
    if not (isinstance(call.func, ast.Name) and call.func.id == "print" and call.args):
        return False
    arg = call.args[0]
    return (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "dumps"
            and isinstance(arg.func.value, ast.Name) and arg.func.value.id == "json")


def lint_chunk(text: str, name: str) -> list[str]:
    out = []
    lines = text.strip("\n").splitlines()
    if not lines or not lines[0].startswith("# SCOPE:"):
        out.append(f"{name}: first line must be a '# SCOPE: ...' header")
    if len(lines) > MAX_LINES:
        out.append(f"{name}: {len(lines)} lines (max {MAX_LINES}); split the chunk")
    try:
        body = ast.parse(text).body
    except SyntaxError as e:
        return out + [f"{name}:{e.lineno}: syntax error: {e.msg}"]
    if not body or not _is_json_print(body[-1]):
        out.append(f"{name}: last statement must print(json.dumps(...)) a result")
    for i, ln in enumerate(lines, 1):
        if ln.lstrip().startswith("#"):
            continue
        for rx, msg in FORBIDDEN_RX:
            if rx.search(ln):
                out.append(f"{name}:{i}: {msg}")
    out += api_lint.lint_text(text, name)
    return out


def chunks_in(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        for i, m in enumerate(re.finditer(r"```python\n(.*?)```", text, re.S), 1):
            yield f"{path.name}#block{i}", m.group(1)
    else:
        yield path.name, text


def main(argv) -> int:
    findings, count = [], 0
    for p in argv or [str(HERE.parent / "references" / "chunk-templates.md")]:
        for name, chunk in chunks_in(Path(p)):
            count += 1
            findings += lint_chunk(chunk, name)
    for f in findings:
        print(f)
    print(f"lint-chunks: {'FAIL' if findings else 'PASS'} ({count} chunks, {len(findings)} findings)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
