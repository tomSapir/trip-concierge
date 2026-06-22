# Trip Concierge — build plan

Personal working doc (gitignored-candidate; keep or delete before any "submission"). This is the
roadmap. It mirrors the architecture of `genai-project` (the SMS recruitment chatbot) beat-for-beat,
re-themed as a travel-planning concierge.

> **Updated 2026-06-22** after a design grilling session. Canonical *terminology* now lives in
> [CONTEXT.md](CONTEXT.md); architecture *decisions* live in [docs/adr/](docs/adr/). This file is the
> build roadmap — where it and CONTEXT.md disagree, CONTEXT.md wins. The `genai` lineage is internal:
> it may be discussed here, but **must never appear in the public README**.

## What we're building

A chat concierge that plans a trip with you. It learns your preferences, answers questions about
destinations (grounded in a destination-guide knowledge base), proposes concrete trip packages
(flight + hotel) pulled from a database within your budget, and finally "books" the one you pick —
or politely closes if you walk away.

Same machine as `genai-project`, different theme:

- **Trip Agent** (main orchestrator) runs the conversation turn by turn and picks one of **four**
  actions: `continue`, `recommend`, `book`, or `abandon`.
- **Destination Advisor** — answers questions about places (climate, best season, attractions, food,
  visas/safety). Backed by a Chroma vector DB of destination-guide PDFs. *(= genai Info Advisor)*
- **Budget Advisor** — on `recommend`, uses **real OpenAI function-calling** (tools API) to query the
  package DB for the three best available packages within budget, then rewrites the reply with concrete
  dates + prices. Veto power: if no destination has been named yet, it demotes the turn back to
  `continue`. *(= genai Scheduling Advisor)*
- **Booking Advisor** — guards `book` only. Confirms the traveller has genuinely committed to a
  specific package ("book option 2") versus merely musing ("option 2 looks tempting…"). Fine-tuned
  (binary `book`/`dont_book`) **purely to demonstrate the SFT workflow**; the live app runs it on the
  base model by default, with the fine-tuned `gpt-4o-mini` swappable via `BOOKING_ADVISOR_MODEL`.
  *(= genai Exit Advisor — but narrower: abandonment is NOT its job; see below.)*

Stack (identical to genai-project): Python 3.11 · LangChain · OpenAI (chat, embeddings, fine-tuning)
· Chroma (vectors) · SQLAlchemy + SQLite (package DB) · Streamlit (UI, deployed to Community Cloud).

## Direct mapping from genai-project

| genai-project | trip-concierge | Mechanism |
|---|---|---|
| Main Agent (continue / schedule / end) | **Trip Agent** (continue / recommend / book / **abandon**) | JSON classifier, few-shot |
| Info Advisor (RAG over JD PDF) | **Destination Advisor** (RAG over destination guides) | Chroma retriever + grounded rewrite |
| Scheduling Advisor (LLM extract date → SQL slots) | **Budget Advisor** (real tool-call → SQL packages) | `bind_tools(get_packages)` + grounded rewrite |
| Exit Advisor (fine-tuned end/dont_end) | **Booking Advisor** (fine-tuned book/dont_book) | SFT'd `gpt-4o-mini`, env-var swap + fallback |
| — (genai folded abandon into `end`) | **Abandon** action | unguarded terminal — fires straight from Trip Agent |
| `data/Python Developer Job Description.pdf` | `data/destinations/*.pdf` | PyPDFLoader → 500/50 chunks |
| `data/tech.db` (Schedule table) | `data/packages.db` (Package table) | auto-seeded SQLite |
| `tests/sms_conversations.json` | `tests/trip_conversations.json` | labeled eval set |
| `EXIT_ADVISOR_MODEL` env var | `BOOKING_ADVISOR_MODEL` env var | optional fine-tune swap |

**Key divergence from genai:** genai's `end` absorbed *both* committing to a slot and abandoning the
conversation. We split those: `book` = commitment only; `abandon` is its own terminal action. So the
Booking Advisor is narrower than the Exit Advisor (commit-vs-musing only), and `abandon` is unguarded.

## The four actions (Trip Agent)

**`continue`** — keep the conversation going: gather preferences (where, when, budget, vibe), answer a
destination question, or **suggest** candidate destinations that fit the vibe. Routed to the
**Destination Advisor**, which grounds factual destination questions in the guide corpus; otherwise the
agent's own draft is kept. Suggestions come only from the destination registry (see ADR 0001) — the
agent never names a city we don't cover.

**`recommend`** — propose concrete packages. **Requires a named destination** (a vibe alone is *not*
enough — vibe is handled conversationally as a suggestion during `continue`). Budget is optional. Routed
to the **Budget Advisor**, which function-calls `get_packages` for the 3 best options and rewrites the
reply listing them with dates and prices. Veto: no named destination yet → demote to `continue`.

**`book`** — the traveller has committed to one specific package ("let's do option 2", "book the Lisbon
one"). Terminal and successful. Validated by the **Booking Advisor**: if the traveller is merely musing
("option 2 looks tempting…") rather than committing, the advisor returns `dont_book` and the turn is
demoted to `continue`.

**`abandon`** — the traveller walks away without booking ("never mind, not this year"). Terminal and
unsuccessful. **Unguarded** — fires directly from the Trip Agent, because a misread is cheap and
self-correcting (the traveller just keeps typing and the next turn flips back to `continue`).

## Closed world & honest scoping

The concierge supports a fixed set of ~6 destinations and nothing else. **Same-set invariant:** every
destination the traveller can ask about, be suggested, or book is the *same* set — enforced by the
**destination registry** as the single source of truth (the package seeder, the guide corpus, and the
Trip Agent's suggestion list all derive from it).

At the edges of that closed world, the concierge is **honest** (a deliberate deviation from genai's
soft-fail, which just kept the agent's draft):

- **Out-of-set question** ("What's Paris like?") → scope politely: "I cover Lisbon, Kyoto, Reykjavik,
  Barcelona, Bali, Rome — Paris isn't one I can help with." Never free-associate ungrounded facts.
- **Out-of-set booking** ("Book me Paris") → Budget Advisor gets `[]`, demotes to `continue`, same
  honest scoping.
- **In-set, nothing fits budget** ("Lisbon under $300") → demote to `continue` with a specific nudge:
  "Nothing to Lisbon under $300 — the cheapest is $740. Raise the budget, or try another destination?"

## Destination suggestion (ADR 0001)

When the traveller gives a vibe but no destination, the Trip Agent suggests cities. v1 injects the full
destination list (name + vibe tags, from the registry) into the Trip Agent's prompt so it can only ever
suggest in-set cities. The "candidate destinations for a vibe" lookup sits behind one function so a
future version can swap the full list for a retrieval top-k without touching the prompt or pipeline.
See [docs/adr/0001](docs/adr/0001-destination-suggestion-v1-prompt-list.md).

## Data model — package DB (`data/packages.db`)

SQLite via SQLAlchemy, auto-seeded on first use (mirrors `schedule_db.py`). Deterministic
`random.seed(42)` so seeds are reproducible.

```
Package(
  PackageID    PK,
  destination  VARCHAR,   -- from the destination registry
  depart_date  DATE,      -- seeded across 2026 AND 2027
  nights       INT,       -- 3 / 5 / 7
  flight_price INT,
  hotel_name   VARCHAR,
  hotel_price  INT,       -- total for the stay
  total_price  INT,       -- flight + hotel; total USD for ONE traveller
  available    BOOLEAN
)
```

Public API (mirrors `get_slots_by_day`):
`get_packages(destination, max_budget=None, earliest_departure=None, n=3) -> list[dict]` — the n cheapest
available packages to `destination`, departing on/after `earliest_departure`, with
`total_price <= max_budget` when a budget is given.

- **Budget optional.** No budget stated → no price cap; return the cheapest available.
- **"Within budget"** = `total_price <= max_budget`.
- **Soft date anchor.** `earliest_departure` = the start of the month the traveller mentioned
  ("Bali in September" → 2026-09-01), else the conversation's reference date (today in the demo). Trips
  before it are never shown. Departures span **2026 and 2027** so there are always future options.

## Destination registry

The canonical list of supported destinations, each with a name and vibe tags (e.g. Bali = beach/relax,
Reykjavik = adventure). Single source of truth: the package seeder, the guide corpus, and the Trip
Agent's suggestion list all read from it, so the same-set invariant holds by construction. Default set:
Lisbon, Kyoto, Reykjavik, Barcelona, Bali, Rome.

## Knowledge base — destination guides (`data/destinations/`)

One short PDF per destination (climate, best time to visit, top attractions, food, visa/safety basics).
`guide_embedder.py` mirrors `pdf_embedder.py`: PyPDFLoader → RecursiveCharacterTextSplitter(500/50) →
OpenAIEmbeddings(`text-embedding-3-small`) → Chroma at `data/chroma_db/`. Auto-builds on first retrieval
so a cold Streamlit Cloud deploy works (the store is gitignored). Out-of-set questions are scoped, not
answered ungrounded (see Closed world & honest scoping).

## Models

- Trip Agent + advisors (base): `gpt-4.1`, `temperature=0`.
- Embeddings: `text-embedding-3-small`.
- Booking Advisor fine-tune base: `gpt-4o-mini-2024-07-18` — built/evaluated in the notebook, **off by
  default** in the live app, swapped in only when `BOOKING_ADVISOR_MODEL` is set (fallback to base if
  unreachable).

## Evaluation

`tests/trip_conversations.json` — ~12–15 hand-built trip-planning conversations; each *concierge* turn
labeled with its correct action: `continue` / `recommend` / `book` / `abandon`. `tests/test_evals.ipynb`
replays every labeled turn through `get_concierge_response` end-to-end and reports **accuracy**, a **4×4
confusion matrix**, and per-class **precision / recall / F1** (`continue` will dominate; per-class metrics
keep that from masking weak terminal-action performance).

The set is purpose-built to cover every action **and** every edge decided this session:
happy path (`continue`→`recommend`→`book`), `abandon`, **musing-then-booking** (stays `continue`),
**out-of-set city**, **nothing-in-budget**. (Separate from the Booking Advisor's binary fine-tune set.)

## Fine-tuning

`tests/finetune_booking_advisor.ipynb` — build a small, focused, hand-crafted train/test JSONL (~35/9)
of near-booking turns labeled `book` (genuine commitment) vs `dont_book` (musing / question /
hesitation), launch an SFT job on `gpt-4o-mini-2024-07-18`, evaluate vs. base on a held-out split.
Purpose is to **demonstrate the SFT workflow**, not cost/quality. Activate by pasting the resulting
`ft:...` id into `.env` as `BOOKING_ADVISOR_MODEL`; `booking_advisor.py` reads it and falls back to the
base LLM if unreachable (mirrors `exit_advisor.py`'s try/except).

## UI (Streamlit)

Themed chat with typewriter streaming. **Both** terminal actions lock the chat and surface a
"Plan a New Trip" button to reset:
- `book` → a confirmation message ("You're booked! Bali — depart Sep 3, 7 nights, $1,420 🎉").
- `abandon` → a warm goodbye ("No worries — come back whenever you're ready to plan.").

## Build sequence

1. **Scaffold + config** ← *done*
2. **Data layer** — destination registry; `package_db.py` (seed 2026–2027 + `get_packages`); generate
   destination guide PDFs + `guide_embedder.py`.
3. **Agents** — `trip_agent.py` (4-action orchestrator, registry-backed suggestions);
   `destination_advisor.py` (RAG + out-of-set scoping); `budget_advisor.py` (veto → tool-call → grounded
   rewrite, soft date anchor); `booking_advisor.py` (binary, env-var swap + fallback). Wire `__init__.py`.
4. **Entry point + UI** — `app/main.py` `get_concierge_response(messages, reference_date=None)`;
   `streamlit_app/streamlit_main.py` (chat, typewriter, dual terminal lock + "Plan a New Trip").
5. **Eval** — write `trip_conversations.json` (4 actions + 3 edges); build `test_evals.ipynb`; baseline.
6. **Prompt tuning** — few-shot examples; re-eval.
7. **Fine-tune** — `finetune_booking_advisor.ipynb`; set `BOOKING_ADVISOR_MODEL`; re-eval.
8. **Deploy** — Streamlit Community Cloud (entry `streamlit_app/streamlit_main.py`, secrets in TOML).
9. **Polish + README sync** — error handling, README in lockstep (NO genai mention).

## Resolved this session (2026-06-22 grilling)

1. **4 actions, not 3.** `book` = commitment only; `abandon` is a separate, unguarded terminal action.
2. **`recommend` requires a named destination.** Vibe is conversational *suggestion* during `continue`,
   never a DB query key. Budget optional.
3. **Closed world, honest scoping** at all three edges (deviation from genai soft-fail).
4. **Destination registry** = single source of truth; enforces the same-set invariant. Suggestions via
   full prompt list in v1, behind a seam for future retrieval (ADR 0001).
5. **Packages**: total USD for one traveller; seeded 2026–2027; future-only; soft date anchor on the
   traveller's requested month.
6. **Budget Advisor uses real OpenAI function-calling** (veto → tool-call → grounded reply).
7. **Booking Advisor** = pure commit-vs-musing; fine-tune to *demonstrate SFT*; base model by default.
8. **Eval**: 4×4, ~12–15 conversations purpose-built to cover all actions + edges.
9. **UI**: both terminals lock + "Plan a New Trip"; message differs (confirmation vs goodbye).
