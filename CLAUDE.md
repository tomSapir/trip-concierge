# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Before you do any work, mention how you could verify that work.

## Project

Trip Concierge — a multi-agent travel chatbot (Streamlit UI) that plans a trip: it gathers preferences,
answers destination questions (RAG), proposes flight + hotel packages within budget (SQL function-calling),
and books the one the traveller commits to. Python 3.11+, LangChain, OpenAI, Chroma, SQLAlchemy/SQLite,
Streamlit. Deployed on Streamlit Community Cloud.

Companion docs: `RUNNING.md` (install/run/eval), `DEPLOY.md` (Community Cloud), `CONTEXT.md` (the canonical
domain glossary), `docs/adr/` (decisions), `PLAN.md` (v1 roadmap), `PLAN-v2.md` (v2 GUI plan, in progress).

## Commands

Commands are PowerShell (Windows); the bracketed bash equivalents work on macOS/Linux.

Setup:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1            # bash: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                # then edit .env and set OPENAI_API_KEY
```

Run the app:
```powershell
streamlit run streamlit_app/streamlit_main.py
```

Run the end-to-end eval — this is the project's test suite (there is no unit-test or lint setup). It
replays every labeled turn in `tests/trip_conversations.json` through the full pipeline (~34 OpenAI calls):
```powershell
python tests/run_evals.py                 # run + compare to tests/baseline_metrics.json
python tests/run_evals.py --save          # also write tests/last_run_metrics.json
python tests/run_evals.py --no-baseline   # skip the baseline delta
```
`run_evals.py` runs from any working directory (it fixes `sys.path` and `chdir`s to the repo root itself).
`tests/test_evals.ipynb` is the same logic with plots; `tests/finetune_booking_advisor.ipynb` reproduces
the Booking Advisor supervised fine-tune (optional — the app runs on the base model without it).

Rebuild the auto-generated data stores (after changing the registry or a guide PDF):
```powershell
Remove-Item data/packages.db, data/chroma_db -Recurse -Force   # then rerun the app or the eval
```

## Architecture

One turn = one call to `get_concierge_response(messages, reference_date=None)` in `app/main.py`, returning
a `ConciergeTurn` (`app/concierge_turn.py`) — final action + reply, plus optional `packages` (real rows on a
successful `recommend`) and a `trace` (original → final action, route, demotion reason, retrieved chunks,
model). It unpacks to `(action, reply)`, so tuple callers like the eval harness are unaffected — the v2 seam
widened the contract without breaking it. Understanding the flow means reading `app/main.py` plus all four
agents:

1. **Trip Agent** (`app/modules/agents/trip_agent/trip_agent.py`) — a JSON few-shot classifier. It reads
   the whole conversation, picks exactly one **action**, and drafts the reply: `continue` / `recommend` /
   `book` / `abandon`.
2. `app/main.py` routes that action to one **Advisor**, which validates/enriches the draft and may
   **demote** the action back to `continue`:
   - `recommend` → **Budget Advisor** (`budget_advisor/budget_advisor.py`): real OpenAI function-calling —
     binds `find_packages`, the model extracts (destination, month, budget) and calls `get_packages`
     (`budget_advisor/package_db.py`), then rewrites the reply from the real rows. Demotes if no
     destination was named or nothing fits the budget.
   - `continue` → **Destination Advisor** (`destination_advisor/destination_advisor.py`): RAG over the
     guide corpus via `guide_embedder.get_retriever()`; grounds factual questions, scopes out-of-set ones,
     else passes the draft through. Never changes the action.
   - `book` → **Booking Advisor** (`booking_advisor/booking_advisor.py`): binary `book`/`dont_book` —
     confirms genuine commitment vs musing; demotes musing to `continue`.
   - `abandon` → unguarded; no advisor, the draft passes straight through.
3. The UI (`streamlit_app/streamlit_main.py`) streams the reply (typewriter) and renders a fresh
   `recommend`'s packages as bookable cards — "Book this" commits deterministically (no LLM, no
   Booking Advisor) and shows a rich confirmation with the package's real details. A terminal action
   (`book`/`abandon`) locks the chat and offers a reset. The sidebar's **🐞 Debug** toggle reveals each
   turn's `trace` in a collapsed expander under its reply (every assistant message stores its own trace,
   so the trail covers the whole conversation, not just the last turn). It caps user turns at
   `MAX_USER_MESSAGES` (a public-demo cost ceiling).

### Invariants that shape everything

- **The destination registry is the single source of truth** (`app/modules/destination_registry.py`).
  The package seeder, the guide corpus, and the Trip Agent's suggestion list ALL derive from it, so the
  **same-set invariant** holds: every destination the traveller can ask about, be suggested, or book is
  the same ~6. To add/remove a destination, edit the registry and its guide PDF and rebuild the stores —
  never hardcode a city elsewhere.
- **Closed world, honest scoping** — out-of-set destinations are scoped politely ("I cover …, Paris isn't
  one I can help with"), never answered with ungrounded facts. This is deliberate.
- **`recommend` ≠ suggest; `book` ≠ abandon.** `recommend` proposes *packages* for an already-named
  destination; floating a *place* from a vibe is "suggest", which lives inside `continue`. `book` is
  commitment only; walking away is the separate, unguarded `abandon`. These traps are defined in
  `CONTEXT.md` — read it before editing any agent prompt.

### Models

`gpt-4.1` (temperature 0) for the Trip Agent and all advisors; `text-embedding-3-small` for retrieval.
The Booking Advisor fine-tune is **off by default** and demonstrative — set `BOOKING_ADVISOR_MODEL=ft:...`
to swap it in; it falls back to the base model if that id is unreachable.

### Data stores auto-initialize (don't hand-create)

`data/packages.db` (SQLite) and `data/chroma_db/` (Chroma) are **gitignored** and built on first use from
committed sources (the registry + `data/destinations/*.pdf`). A cold deploy rebuilds them; the first
factual turn is slow because it embeds the guides.

## Conventions & gotchas

- **`OPENAI_API_KEY` must be set before importing `app`.** The agents construct their `ChatOpenAI` /
  embeddings clients at import time, so entry points call `load_dotenv()` *before* `from app.main import …`
  — preserve that order. On Community Cloud the key comes from Secrets (exposed as env vars).
- **Keep the turn diagram and glossary in sync in the SAME commit.** If you change the routing, the set of
  actions, an advisor's role, or the `ConciergeTurn` contract, update the Mermaid flowchart in
  `README.md` (§Architecture) and the terms in `CONTEXT.md`. Both are declared canonical.
- **The public README must not reference the project's internal lineage / prior project.** That history
  stays in internal working docs (`PLAN.md`).
- **Eval accuracy is nondeterministic** run-to-run (LLM classifier); `book` recall is the known weak spot.
  Judge a change by re-running `run_evals.py` and reading the delta-vs-baseline banner, not a single
  number. Promote `--save` output to `tests/baseline_metrics.json` only for a real, repeated improvement.
- **Development is branch-per-step**: `git checkout -b feat/<step>` before new build-plan work (never
  commit build steps straight to `main`); mark steps `← done` in `PLAN.md` / `PLAN-v2.md` as they finish.
- **Keep `requirements.txt` fully pinned and current** as deps change — Community Cloud installs from it,
  and the eval/notebook stack can be trimmed for a leaner deploy (see `DEPLOY.md` §7).
