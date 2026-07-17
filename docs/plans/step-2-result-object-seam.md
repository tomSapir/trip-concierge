# Step 2 — Result-object seam (working plan)

Working checklist for **v2 build step 2** ([PLAN-v2.md](../../PLAN-v2.md) §Build sequence). This is the
shared foundation for cards (idea 1), the debug trail (idea 2), and images (idea 4). It is the one
sanctioned backend touch in v2's GUI-only scope — a *small, additive* seam that threads packages + a
reasoning trace out to the UI.

Branch: `feat/v2-result-object-seam`. Done in **very small sub-steps**, each independently verifiable and
behaviour-preserving until the UI opts in (2g). Working style: skeletons handed over per sub-step; the
human fills the bodies, then we verify by running.

## The contract change

`get_concierge_response(messages, reference_date=None)` today returns a bare `(action, reply)` tuple, and
each advisor returns `(action, reply)`. Three things are discarded at the seam and are needed by the UI:

- the Budget Advisor's real package rows (`all_rows`) → cards + images
- the **original** Trip Agent action + **why** an advisor demoted → debug trail
- which advisor ran / retrieved chunks / model → debug trail

The fix widens the return to a `ConciergeTurn(action, reply, packages=None, trace=None)` that **still
unpacks** to `(action, reply)` via `__iter__`, so the eval harness (`tests/run_evals.py:90`),
`test_evals.ipynb`, and the RUNNING.md snippet stay untouched. Only `streamlit_main.py` reads the new
fields.

## Sub-steps

- [x] **2a — `ConciergeTurn` type + static test.** New `app/concierge_turn.py` (frozen dataclass, no agent
  imports so it imports without an API key). `__iter__` yields exactly `action, reply`. New
  `tests/test_concierge_turn.py` (standalone, no OpenAI). *Verify:* `python tests/test_concierge_turn.py`.
- [x] **2b — `main.py` returns `ConciergeTurn`, no advisor change.** Unpack each advisor's existing
  `(action, reply)` and wrap: `return ConciergeTurn(action, reply)`. Proves `__iter__` works through the
  real pipeline before touching advisors. *Verify:* `python tests/run_evals.py` — accuracy unchanged.
- [ ] **2c — assemble the trace `main.py` can build alone.** Capture the original action (already at
  `main.py:18`) and the advisor's final action; put `{original_action, final_action, route}` into
  `trace`. No advisor change (route is known from the branch taken; `abandon` builds its trace inline).
  *Verify:* eval unchanged; print one `turn.trace`.
- [ ] **2d — Budget Advisor `meta`.** Return `(action, reply, meta)`: `{"packages": all_rows, "model":
  "gpt-4.1"}` on success; `{"reason": …}` on the veto and no-fit demotes. `main.py` lifts `packages` onto
  the turn and `reason` into the trace. *Verify:* eval unchanged; canned `recommend` turn → `turn.packages`
  non-empty.
- [ ] **2e — Destination Advisor `meta`.** Return `{"chunks": docs, "model": "gpt-4.1"}`. `main.py`
  reduces chunks to `{source, snippet}` in the trace (raw `Document`s never reach session_state).
  *Verify:* eval unchanged.
- [ ] **2f — Booking Advisor `meta`.** Return `{"reason": …, "model": <base or ft>}` on demote,
  `{"model": …}` on `book`. Unify `model` into the trace across all routes. *Verify:* eval unchanged.
- [ ] **2g — `streamlit_main.py` opts in.** Switch `action, reply = …` → `turn = …; turn.action /
  turn.reply`. Still **no** rendering of packages/trace (those are steps 4 and 5). *Verify:* run the app,
  one turn end-to-end.
- [ ] **2h — doc sync + mark done.** README Mermaid diagram + CONTEXT.md (the `(action, reply)` contract is
  *widened, not broken*), RUNNING.md §7 snippet, the CLAUDE.md contract line; mark PLAN-v2 step 2 `← done`.
  *Verify:* docs read consistently.

## Verification notes

- Eval baseline is **91.2% (31/34)**; the classifier is nondeterministic, so judge each pipeline-touching
  sub-step by the delta-vs-baseline banner, **not** a single number. The seam is behaviour-preserving —
  accuracy should hold. `book` recall is the known weak spot.
- Sub-steps 2a is API-free; 2b–2f each cost a full eval run (~34 OpenAI calls). Batch the eval at natural
  points if cost matters, but at minimum run it after 2b (first pipeline touch) and after 2f (last).

## Design decisions (locked)

- `ConciergeTurn` lives in its **own module**, not inside `main.py`, so tests skip the agent-import chain
  (which builds `ChatOpenAI` at import and needs a key).
- Each **advisor reports its own `model`** in `meta` (most honest — captures Booking's base-vs-fine-tune
  distinction for free) rather than a route→model map in `main.py`.
- Chunks are reduced to `{source, snippet}` **at the seam** (`main.py`), keeping the trace lean and
  session_state-serializable.
