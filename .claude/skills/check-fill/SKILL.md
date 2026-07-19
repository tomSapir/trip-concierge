---
name: check-fill
description: Verify the user's fill of a handed-over build-step skeleton, clean the scaffolding, run the right verification for what changed, then tick + commit. Use when the user says "filled, check it", "check my fill", "check it", or has just implemented a skeleton with TODO (<step>) comments.
---

# Check a filled skeleton (trip-concierge build rhythm)

The build rhythm in this repo: Claude hands over a skeleton — `TODO (<sub-step>)` comments
containing exact instructions — and the user writes the functional code themselves (that's the
point; they're building this to learn). This skill is the *check* half: verify the fill,
clean up, verify empirically, tick, commit.

## 1. Compare the fill against the skeleton

- `git diff` the working tree. Read every `TODO (<sub-step>)` block and confirm each
  instruction in it was actually applied — including docstring/comment updates the TODO
  asked for (these get missed most often).
- Static consistency: grep for every caller of any function whose signature/return changed;
  confirm they all unpack the new shape. Check both branches of any try/except that was
  widened (a variable assigned only in the `try` is an UnboundLocalError waiting for the
  fallback path).
- Known repo traps: `ConciergeTurn(action, reply, packages=None, trace=None)` — `trace=`
  must be passed as a keyword (positional slot 3 is `packages`).

## 2. Clean up (do directly, never ask)

- Delete the fulfilled `TODO (<sub-step>)` scaffolding comments.
- Fix indentation / continuation-line alignment in the fill.
- Docs, docstrings, and comments are Claude's to fix directly — if the fill missed a
  docstring update or left one stale, write it now. Only *functional code* gaps go back
  to the user.

## 3. Verify empirically — pick by what changed

Always use the venv interpreter: `./.venv/Scripts/python.exe` (bare `python` misses deps).
Any script that imports `app` must `load_dotenv()` (repo-root `.env`) **before** the import.

| What changed | Verification |
|---|---|
| Pipeline code (`app/**`) | Small scratchpad script exercising each changed branch directly (e.g. one commitment turn + one musing turn), print the returned tuples/trace. Then the **full eval**: `./.venv/Scripts/python.exe tests/run_evals.py` — judge by the delta-vs-baseline banner, never a single number (nondeterministic; `book` recall is the known weak spot; baseline 91.2%). |
| UI code (`streamlit_app/**`) | The eval never touches the UI — run the real app: `./.venv/Scripts/python.exe -m streamlit run streamlit_app/streamlit_main.py --server.headless true --server.port 8501` in the background, drive one turn in Chrome (clicking a starter chip is the cheapest real turn), confirm the reply renders and terminal/non-terminal behaviour is right. Gotchas: the layout shifts while the first script run settles — re-screenshot before clicking; CDP screenshots can time out mid-render — just retry. Kill the process on port 8501 when done. |
| API-free code (`app/concierge_turn.py`, `streamlit_app/starters.py`, …) | Its standalone test: `./.venv/Scripts/python.exe tests/test_<name>.py`. |

Report concrete pass/fail with the actual output, not a summary of intent.

## 4. Tick + commit (on pass)

- Tick the sub-step checkbox in the working plan (`docs/plans/step-*.md`); if this closes a
  whole PLAN-v2/PLAN step, mark it `← done` there too (match the existing format).
- If the routing, actions, an advisor's role, or the ConciergeTurn contract changed: update
  README's Mermaid block, CONTEXT.md, RUNNING.md §7, and CLAUDE.md **in the same commit**.
- Stage only the step's files — never unrelated untracked files.
- Commit message format (match history): `feat: <what> (v2 step <2x>)`, `feat(ui): …` for
  Streamlit-only changes, `docs: …` for doc-sync steps. One commit per sub-step.
- Update the memory build-progress note (step done, what's next).
