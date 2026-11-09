# Verify loop (per part) and final QA

```
ops -> checks -> [fix -> checks] x<=3 -> preview -> look -> PASS | ASK
```

1. **State checks.** Numeric, from `lib/bm_checks.py` (catalogue in [checks.md](checks.md)):
   names, transforms, bounds versus brief sizes, ground contact, overlaps, manifold, normals,
   n-gons and quad ratio, triangle budget, material slots and missing images, cameras, framing,
   exposure, output files.
2. **Fix.** For each failing check with a registered fixer (generic in `bm_checks.FIXES`, or the
   sub-skill's `FIXES`), apply it and re-run the checks. At most 3 rounds. Fixers that cannot act
   say `SKIP` and do not count as a fix. Examples: framing -> dolly an auto-placed camera;
   exposure -> scale light power from the probe render; ground -> drop the group to z; scale ->
   apply scale; normals -> recalculate outward; empty slot -> magenta placeholder (flagged).
3. **Preview.** Low-sample render from the part's preview cameras (`previews/<part>_<cam>.png`),
   optional 4-view contact sheet (front, right, top, three-quarter).
4. **Look.** Open the preview and compare it with the part's goal and references. Numbers catch
   broken geometry; only looking catches "the bottle looks like a jar". If the look fails, add or
   tighten a check, or change the ops, then re-run the part.
5. **Decide.**
   - PASS: versioned save, report written, dependants may start.
   - ASK: still failing after fixes, or no fixer exists. Show the user the preview, the failing
     check, its value and expected value, and offer concrete options. Do not invent a pass.

## Rules

- Never weaken a threshold to get a PASS without writing the reason into the brief.
- A crashing check counts as a failure with the exception text as the detail.
- A part's report is the source of truth; summarise from `reports/*.json`, not from memory.
- Hand-placed cameras are never moved automatically; framing failures on them are ASK.

## Final QA (qa-review)

On the final file: re-run every earlier part's acceptance checks, add generic hygiene checks,
render a contact sheet, list renders, and write `brief/qa_report.md` + `.json`. The QA part
passes only if all rows pass. Then export (if asked) with a re-import round-trip, and deliver
with a list of anything that could not be verified here (GPU look, engine-side import, modal tools).
