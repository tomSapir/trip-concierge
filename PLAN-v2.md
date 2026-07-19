# Trip Concierge — v2 plan (GUI)

Personal working doc, same spirit as [PLAN.md](PLAN.md) (the v1 roadmap). This captures the **v2**
direction agreed in the 2026-07-02 ideation session. It is a set of committed *directions* with open
questions still to resolve — not yet a build sequence. The next session turns each idea below into
build steps and settles its open questions.

## Scope constraint

**Every v2 improvement is GUI-related** (the Streamlit front-end). Backend/agent/DB-only work is out of
scope for v2. One narrow exception is sanctioned: a *small, additive* backend seam is allowed when it
exists purely to power a GUI feature — specifically the debug reasoning trail (idea 2), which needs the
pipeline to thread a little trace out to the UI. (A non-GUI idea, multi-traveller/group pricing, was
considered and deliberately dropped to hold this line.)

## The four v2 ideas

### 1. Selectable package cards (replace the prose list)

On `recommend`, render the three options as Streamlit **cards** in a row — destination, dates, nights,
hotel, price — each with a **"Book this"** button, instead of the Budget Advisor's streamed-prose
paragraph. Turns recommend → book into a click.

Open questions:
- Keep both paths (cards **and** free-text "book option 2"), or cards-only once options are shown?
- Does a card click **skip the Booking Advisor**, or pass a synthetic "book option 2" through the full
  pipeline so the architecture stays uniform and the evals still cover it? (A button click is
  unambiguous commitment, so it bypasses the commit-vs-musing job the Booking Advisor was built for.)
- Card affordances — Book only, or also "Tell me more" (→ Destination Advisor) and a compare view?

**Resolved (2026-07-02 build-planning):** (a) **keep both paths** — cards are additive; free-text
"book option 2" still flows through the unchanged, eval-covered pipeline. (b) **Deterministic bypass** —
a "Book this" click is unambiguous commitment (the exact thing the Booking Advisor disambiguates in
fuzzy *text*), so it skips that advisor and commits via one thin `book_package(pkg)` finalizer with the
exact package — no LLM call, no "which option?" ambiguity. (c) **Book-only for v2.0** (plus the idea-4
thumbnail); the three cards side-by-side already *are* the compare view, and "Tell me more" adds routing
— defer it to v2.1.

### 2. Debug mode — the reasoning trail

A sidebar toggle **🐞 Debug** that, when on, annotates each concierge turn with what the pipeline did.
We chose the **deep** version (the reasoning trail), not just a final-action badge.

Shows, per turn: the Trip Agent's **original** chosen action, whether an advisor **demoted/vetoed** it
and why (`recommend`→`continue` when no destination is named; `book`→`continue` on musing), which
advisor ran (the route), retrieved guide chunks, and the model used.

Needs the sanctioned small backend seam: today `get_concierge_response` returns only
`(final_action, reply)` and each advisor returns only `(action, reply)`, so the *original* action and
the demotion reasons are discarded. Advisors must return *why* they demoted, and `app/main.py`'s
`get_concierge_response` must thread a small `trace` object out to the UI.

Open questions:
- How to toggle — sidebar switch, URL query param, or a secret so it's **off on the public deploy**?
- Per-message expander vs one global debug panel?
- Exactly which internals to surface (keep it readable, not a firehose)?

**Resolved (2026-07-02 build-planning):** (a) **always-visible sidebar toggle** — the simplest option;
this deliberately leaves the trail visible on the public deploy (transparency-as-feature, reversing the
earlier "off on public" worry — trivially gated later with one `if`). (b) **Per-message expander** — the
trace is inherently per-turn, so a collapsed `st.expander("🐞 trace")` under each assistant message beats
a single global panel (which could only show the latest turn or a firehose). (c) Surface the fixed list —
original→final action + demotion reason, route, retrieved chunks (as **source + one-line snippet**, not
full text), and model.

### 3. Starter screen with clickable example prompts

Before any conversation starts, show a welcome header + a row of clickable **starter chips** that
pre-fill a real opening message (e.g. "Somewhere warm to relax", "An adventure trip", "A food & wine
city", "Kyoto in April, ~$2k"). Click → injects that text as the first user turn; the pipeline is
unchanged (pure front-end). Kills the blank-first-screen cold-start fumble and teaches capability +
covered destinations by example.

Open questions:
- Chips **static-curated** vs **generated from the destination registry** (name + vibe tags, so they
  never advertise an out-of-set city — same-set honesty for free)?
- Starter-only, or also contextual mid-chat quick-replies? (Contextual replies overlap with idea 1's
  card buttons — likely keep this starter-only to avoid stepping on the cards.)

**Resolved (2026-07-02 build-planning):** (a) **registry-derived chips** — seed them from
`all_destinations()` (name + vibe tags) so a chip can *never* advertise an out-of-set city; the same-set
invariant is structural, not curated. Any richer hand-written prompt ("Kyoto in April, ~$2k") stays
allowed but guarded by a one-line test that every chip names only in-set cities. (b) **Starter-only** —
no mid-chat contextual quick-replies (they overlap idea 1's card buttons).

### 4. Destination imagery — make it look like a travel app

Surface a **hero image per destination** at the moments that matter: a banner when a destination is
named/suggested in `continue`; a thumbnail leading each **package card** (idea 1); a full-width shot on
the booking confirmation.

One image per registry destination, **bundled as a static asset** (e.g. `data/destinations/img/<name>.jpg`)
keyed by destination name — 6 destinations, 6 files, no API, works offline on a cold Streamlit deploy
(same closed-world discipline as the rest of the app). Images become one more field per registry entry.

Open questions:
- Bundled static images vs a live image API? (Lean: **bundled** — honest, offline, no key; the cost is
  curating 6 photos. A live API adds a dependency, latency, and can surface a wrong/random image.)
- How far to spread them — everywhere a destination appears, or just cards + confirmation?
- Licensing — bundled photos must be free to redistribute (public-domain / CC0) for the public deploy.

**Resolved (2026-07-02 build-planning):** (a) **bundled** static assets — honest, offline, no key, no
wrong-image risk (the plan's own lean). (b) **Cards + confirmation only** for the first cut — both have an
unambiguous destination from the structured rows; the `continue` hero-banner needs single-city
name-detection in free text and is deferred. (c) **CC0 / public-domain** photos only, recorded in
`data/destinations/img/CREDITS.md`.

## Build sequence

Ordered in the 2026-07-02 build-planning session (open questions above now resolved). Branch per step
(`git checkout -b feat/v2-<step>`, never on main) and mark each `← done` as it fully completes, same
discipline as [PLAN.md](PLAN.md). The **starter screen** goes first — it's independent and touches nothing
in the pipeline. The **result-object seam** (step 2) is the shared foundation for cards, debug, and images,
so it precedes all three.

1. **Starter screen (idea 3)** — *done* — pure front-end, no pipeline change. In `streamlit_main.py`, when
   `_user_msg_count() == 0`, render a welcome header + a row of `st.button` starter chips seeded from
   `all_destinations()` (name + vibe), so a chip can never name an out-of-set city. A click appends the
   chip's text as the first user message and reruns. Optional test: every chip names only in-set cities.
   Built as `streamlit_app/starters.py` (`starter_prompts()` → one `Starter` per registry destination,
   Streamlit-free so it's importable/testable); the UI stages a click via `st.session_state.pending_prompt`
   and reruns, so both a chip and typed text flow through the one unchanged turn-processing block. Invariant
   guarded by `tests/test_starters.py` (`python tests/test_starters.py`, passing). Verified end-to-end in
   the running app: chips render on a fresh session, a click ("Bali") drives a real `continue` turn, and the
   chips retire once a message exists.

2. **Result-object seam (foundation for ideas 1, 2, 4)** — *done* — widen the pipeline's return without
   breaking evals. Sub-step working plan: [`docs/plans/step-2-result-object-seam.md`](docs/plans/step-2-result-object-seam.md).
   Landed as 2a–2h, one commit each on `feat/v2-result-object-seam`: `ConciergeTurn` + per-advisor
   `(action, reply, meta)`, trace assembled in `main.py`, `streamlit_main.py` reading `turn.*`. Eval held
   at the 91.2% baseline (Δ +0.0 after the last pipeline touch); UI verified live (one chip-driven turn).
   - Add `ConciergeTurn(action, reply, packages=None, trace=None)` with `__iter__` yielding
     `(action, reply)`, so `action, reply = get_concierge_response(...)` still works and `run_evals.py:90`
     + `test_evals.ipynb` stay untouched. Only `streamlit_main.py` opts into `.packages` / `.trace`.
   - Advisors return `(action, reply, meta)` (a small dict): Budget Advisor attaches `packages` (its
     `all_rows`) on success and a `reason` on each demote branch; Booking Advisor a `reason` on
     `dont_book`; Destination Advisor its retrieved `chunks` + case. `app/main.py` already holds the
     **original** action (line 18) and sees the advisor's **final** action, so it assembles the `trace`
     (original → final, route, demotion reason, chunks, model) and lifts `packages` onto the
     `ConciergeTurn`. The `abandon` branch builds its trace in `main.py` (no advisor).
   - Switch `streamlit_main.py` to `turn = get_concierge_response(...)` reading `.action` / `.reply`.
   - **Verify:** `python tests/run_evals.py` — accuracy must be unchanged (the seam is behaviour-
     preserving); judge by re-running, not one number (eval is nondeterministic).

3. **Image data layer (idea 4, no render yet)** — *done* — add an `image` field to the `Destination` dataclass;
   drop six CC0 / public-domain files at `data/destinations/img/<name>.jpg` + a `CREDITS.md`; add an
   `image_for(name)` helper with a graceful missing-file fallback. Confirm the images aren't caught by a
   `data/` gitignore (the guide PDFs under `data/destinations/` are tracked, so the dir is fine).

4. **Package cards + rich confirmation (ideas 1 + 4 render)** — all in `streamlit_main.py`.
   - On a turn carrying `turn.packages`, store `st.session_state.offer` and render `st.columns(n)` cards
     **every rerun** (thumbnail via `image_for`, destination, dates, nights, hotel, total). Persisting in
     session_state is mandatory — Streamlit reruns wipe any in-the-moment widget, and the buttons must be
     re-emitted to stay clickable. Retire the offer once the next turn isn't a fresh `recommend`.
   - "Book this" → `book_package(pkg)` finalizer: deterministic, no LLM — lock to `book`, stash the booked
     package, clear the offer. One finalizer = single commit path.
   - Rich confirmation: full-width `image_for(dest)` + real details ("Bali — depart Sep 3, 7 nights,
     $1,420 🎉"), replacing the generic success box, when a package was booked via a card.
   - Free-text "book option 2" still routes through the Booking Advisor (eval-covered) but has no specific
     package object, so it keeps the generic confirmation for now — asymmetry noted; a later step could
     resolve the option index to a row.

5. **Debug trail (idea 2)** — `streamlit_main.py`. Always-visible sidebar `st.toggle("🐞 Debug")`. Store
   each turn's `trace` on its stored message dict (extend `{"role", "content"}` → `+ "trace"`), and when
   the toggle is on render a collapsed `st.expander("🐞 trace")` under each assistant message: original →
   final action (+ demotion reason), route, retrieved chunks (source + one-line snippet), and model.

## Notes for the build session

- These four are the whole of v2's agreed scope; idea-gathering is closed.
- Turn each into build steps and resolve its open questions before coding.
- Ideas 1 and 4 interlock (cards carry the thumbnails) — plan them together.
- The registry stays the single source of truth: starter chips (idea 3) and images (idea 4) both derive
  from it, preserving the same-set invariant for free.
