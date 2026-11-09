# Contributing

Thanks for helping. Please read this before opening a pull request.

## The no-references rule
This project contains **original wording and original code only**.

- Do not paste text, transcripts, code listings, titles or table of contents from books, videos,
  paid or free training material, blogs or other skills. Write guidance in your own words and test
  every setting on Blender 5.2.
- Do not mention where a technique was learned: no titles, authors, presenters, channels,
  publishers, product packs, store or download-site names, demo character or demo project names.
- Avoid wording that points to training material, such as numbered lesson or chapter
  references, phrases that credit a teacher, or the name of a learning product. The scrub scan
  rejects these.
- Numbers (settings) are fine when stated as our own recommended ranges with a reason.
- Public tools may be named where users need them (Blender, an MCP add-on, Rigify), linking only to
  their own home pages. Allowed link domains are listed in `tests/scrub/url_allow.txt`.
- No personal data, private paths, e-mail addresses or tokens.
- No binary media in the repository (`.blend`, renders, video). Examples are text only; renders go
  to the ignored `out/` folder.

## Layout
- `blender-master/SKILL.md`: the coordinator. Keep it under 250 lines; detail goes to
  `references/`.
- `blender-master/subskills/<name>/`:
  - `SKILL.md`: frontmatter `name` equals the folder name, the description is at most 1024
    characters, `license: MIT`, and the file is at most 200 lines;
  - `references/`: at least one guide;
  - `scripts/ops.py`: an `OPS` table, a `FIXES` table and registered checks.
- `blender-master/lib/`: shared helpers that run inside Blender (`bm_*.py`).
- `blender-master/references/`: taxonomy, routing, checks catalogue, brief schema and 5.x API
  notes. `taxonomy.md`, `routing.md` and `checks.md` mirror the JSON files and `bm_plan.py`.
  Update them together.
- `examples/<nn-name>/`: `request.txt`, `params.json` and a walk-through `README.md`. Text only.
- `tests/`: pytest; the headless Blender cases live in `tests/cases/<area>/case_*.py`.

## Adding to a sub-skill
1. Add an op to `scripts/ops.py` and list it in `OPS`. An op must:
   - be idempotent (re-running it replaces its own objects);
   - use real units and base-centred origins;
   - use the prefixes in `references/naming-conventions.md`;
   - return a short string saying what it made.
2. Add or reuse a check with `@bm_checks.register(name)`. It returns
   `(passed, value, expected, detail)`. Where a fix is safe, add a fixer that takes
   `(ctx, args, attempt)` and returns a string starting with `SKIP` when it cannot act.
3. Add a headless case under `tests/cases/`. Use `H.expect(...)` for every claim, and include
   one negative case that the check must catch.
4. Document the op and check in backticks in the sub-skill `SKILL.md` and its reference guide.
   `test_skill_format.py` fails if an op is missing from the docs.
5. If it changes default acceptance or routing, update `bm_plan.py`, `references/checks.md` and
   `references/routing.md`.

## Adding a sub-skill
1. Create the folder with `SKILL.md`, `references/<guide>.md` and `scripts/ops.py`.
2. Register it in `references/routing.json` (status `core` once it has a passing test) and
   route its role in `taxonomy.json`.
3. Link it from the coordinator's route table and the README sub-skill table.

## Running the checks
```
export BLENDER_BIN=/path/to/blender-5.2.x/blender
python -m pytest -m "not slow"       # format, lint, planner and per-sub-skill Blender tests
python -m pytest -m slow             # the example projects end to end
python tools/scrub_scan.py           # reference, private-path, secret and link scan
python blender-master/subskills/scripting-automation/scripts/api_lint.py blender-master tests
python blender-master/subskills/live-control-mcp/scripts/lint_chunks.py
yamllint -c .yamllint.yml .github/workflows   # optional, if you edit CI
```
CI runs the same checks on Blender 5.2.3 (Linux, CPU only). The Blender download is checked
against the official SHA-256 list and cached per version.

## Pull requests
- Keep each PR to one topic, and write the commit subject in the imperative ("Add LOD check").
- Include the test output, plus a preview render path if the change affects visuals. Do not
  attach `.blend` files.
- Say what you could not test (GPU, EEVEE, interactive tools, engine import).
- By contributing you agree your work is released under the MIT licence.
