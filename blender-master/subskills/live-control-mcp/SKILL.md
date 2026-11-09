---
name: live-control-mcp
description: Safe operating loop for driving a running Blender 5.2 through an MCP server - read the scene, send one small scoped code chunk, look at a screenshot, verify with numbers, then continue - with scope locks, approval on every write, localhost-only connections and recovery. Use when the user wants an agent to control their open Blender live, says "control my Blender", or a part's execution mode is live_mcp.
license: MIT
compatibility: Blender 5.2 with any MCP add-on that can run Python and return a viewport screenshot. No server code included. Part of blender-master.
metadata:
  parent: blender-master
  status: core
---

# Live control through MCP

The user watches their own Blender while you build. Every change is small, visible, approved
and checked, so a mistake costs one undo, not the scene.

## Before the first change
1. Confirm the MCP server is connected and listens on **localhost** only.
2. Confirm the host asks before every code-execution call. Never ask the user to turn that off.
3. **Read state**: Blender version, open file name, saved or not, object list with types and
   sizes, current frame, render engine (template `read_state`).
4. If the file has unsaved changes or is the user's original, save a versioned copy first
   (template `versioned_copy`). Work on the copy.

## The loop (one object or system per turn)
```
read -> plan one change -> send chunk -> screenshot -> verify numbers -> next | undo
```
- **One chunk = one scoped change**: a header `# SCOPE: <objects or system>` naming exactly
  what it may touch; at most 60 lines; ends by printing one JSON line with the result.
- **Scope lock**: a chunk only creates, edits or deletes objects named in its scope (or with the
  prefix stated there). Other objects are read-only.
- **Screenshot** after visible changes (the MCP viewport tool, or `lib/bm_shots.look`), then
  **verify** with a check chunk (sizes, counts, overlaps, materials).
- If a chunk fails or the screenshot looks wrong: undo (`bpy.ops.ed.undo()` in the UI session)
  or reload the last versioned copy, then send a smaller chunk.

Chunk templates: [references/chunk-templates.md](references/chunk-templates.md). Lint any chunk
before sending: `python scripts/lint_chunks.py chunk.py` (scope header, size, forbidden calls,
5.x API rules). Templates are linted in CI.

## Safety
- Code runs with the user's permissions: show it, keep approvals on, no shell, no network, no
  file deletion, no add-on installs, no auto-run of scripts in files.
- Do not paste API keys into chunks; asset-generator or paid add-on features need an explicit
  yes per use with the cost stated.
- Do not change preferences, keymaps or startup files.
- Remote access only through a tunnel the user sets up; never bind to 0.0.0.0.

## When to switch modes
Long or heavy jobs (simulation bakes, final renders, batch exports) go headless on a saved copy
instead of blocking the user's UI; come back to live mode to review.

## Scripts
- `scripts/lint_chunks.py`: lints chunk files or the fenced Python blocks in a Markdown file.
