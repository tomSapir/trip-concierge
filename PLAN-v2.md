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

## Notes for the build session

- These four are the whole of v2's agreed scope; idea-gathering is closed.
- Turn each into build steps and resolve its open questions before coding.
- Ideas 1 and 4 interlock (cards carry the thumbnails) — plan them together.
- The registry stays the single source of truth: starter chips (idea 3) and images (idea 4) both derive
  from it, preserving the same-set invariant for free.
