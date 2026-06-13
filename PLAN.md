# Trip Concierge — build plan

Personal working doc (gitignored-candidate; keep or delete before any "submission"). This is the
roadmap. It mirrors the architecture of `genai-project` (the SMS recruitment chatbot) beat-for-beat,
re-themed as a travel-planning concierge.

## What we're building

A chat concierge that plans a trip with you. It learns your preferences, answers questions about
destinations (grounded in a destination-guide knowledge base), proposes concrete trip packages
(flight + hotel) pulled from a database within your budget, and finally "books" the one you pick —
or politely wraps up if nothing fits.

Same machine as `genai-project`, different theme:

- **Trip Agent** (main orchestrator) runs the conversation turn by turn and picks one of three actions:
  `continue`, `recommend`, or `book`.
- **Destination Advisor** — answers questions about places (climate, best season, attractions, food,
  visas/safety). Backed by a Chroma vector DB of destination-guide PDFs. *(= genai Info Advisor)*
- **Budget Advisor** — when it's time to propose a trip, queries the package DB (function calling) for
  the three best available options within budget and rewrites the reply with concrete dates + prices.
  *(= genai Scheduling Advisor)*
- **Booking Advisor** — second opinion before the concierge finalizes. Catches false positives
  ("that sounds nice" vs. actually committing to option 2). Fine-tuned for this binary call.
  *(= genai Exit Advisor)*

Stack (identical to genai-project): Python 3.11 · LangChain · OpenAI (chat, embeddings, fine-tuning)
· Chroma (vectors) · SQLAlchemy + SQLite (package DB) · Streamlit (UI, deployed to Community Cloud).

## Direct mapping from genai-project

| genai-project | trip-concierge | Mechanism (unchanged) |
|---|---|---|
| Main Agent (continue / schedule / end) | **Trip Agent** (continue / recommend / book) | 3-way JSON classifier, few-shot |
| Info Advisor (RAG over JD PDF) | **Destination Advisor** (RAG over destination guides) | Chroma retriever + grounded rewrite |
| Scheduling Advisor (SQL slots, 3 grounded) | **Budget Advisor** (SQL packages, 3 grounded) | function-calling to SQLite + grounded rewrite |
| Exit Advisor (fine-tuned end/dont_end) | **Booking Advisor** (fine-tuned book/dont_book) | SFT'd `gpt-4o-mini`, env-var swap + fallback |
| `data/Python Developer Job Description.pdf` | `data/destinations/*.pdf` | PyPDFLoader → 500/50 chunks |
| `data/tech.db` (Schedule table) | `data/packages.db` (Package table) | auto-seeded SQLite |
| `tests/sms_conversations.json` | `tests/trip_conversations.json` | labeled eval set |
| `EXIT_ADVISOR_MODEL` env var | `BOOKING_ADVISOR_MODEL` env var | optional fine-tune swap |

## The three actions (Trip Agent)

**`continue`** — keep the conversation going: gather preferences (where, when, budget, vibe) or answer
a destination question. Routed to the **Destination Advisor**, which grounds the reply in the guide
corpus when the user asked something factual; otherwise the agent's own draft is kept.

**`recommend`** — the user has shared enough (at minimum a destination or a clear vibe + a budget) to
propose trips. Routed to the **Budget Advisor**, which function-calls the package DB for the 3 best
options within budget and rewrites the reply listing them with dates and prices. The advisor has veto
power: if it's too early (no destination/budget yet), it demotes back to `continue` (mirrors genai's
Scheduling Advisor veto).

**`book`** — the user has named/accepted a specific option ("let's do option 2", "book the Lisbon one").
Terminal. Validated by the **Booking Advisor** (fine-tuned): if the user is merely musing ("option 2
looks tempting…") rather than committing, the advisor returns `dont_book` and the turn is demoted to
`continue`. Also the graceful-exit path: if the user bails ("never mind, not this year"), the concierge
closes politely. Mirrors genai's `end`.

## Repository layout (target)

```text
trip-concierge/
├── app/
│   ├── main.py                                  ← get_concierge_response entry point
│   └── modules/
│       └── agents/
│           ├── trip_agent/trip_agent.py
│           ├── destination_advisor/
│           │   ├── destination_advisor.py
│           │   └── guide_embedder.py            ← builds the Chroma store
│           ├── budget_advisor/
│           │   ├── budget_advisor.py
│           │   └── package_db.py                ← SQLite package table + queries
│           └── booking_advisor/booking_advisor.py
├── streamlit_app/streamlit_main.py
├── data/
│   ├── destinations/*.pdf                        ← guide corpus (source for Chroma)
│   ├── packages.db                              ← auto-generated SQLite (gitignored)
│   └── chroma_db/                               ← built on first run (gitignored)
├── tests/
│   ├── trip_conversations.json                  ← labeled eval dataset
│   ├── test_evals.ipynb                         ← accuracy + confusion matrix
│   └── finetune_booking_advisor.ipynb           ← Booking Advisor SFT
├── requirements.txt        (done — copied from genai, same stack)
├── .env.example            (done)
├── .gitignore              (done)
├── README.md               (done — overview)
└── PLAN.md                 (this file)
```

Each agent folder gets an `__init__.py` re-exporting its public function (e.g.
`from .trip_agent import get_trip_agent_response`), matching genai's pattern. Top-level `__init__.py`
files are intentionally omitted (Python 3 namespace packages; genai does the same).

## Data model — package DB (`data/packages.db`)

SQLite via SQLAlchemy, auto-seeded on first use (mirrors `schedule_db.py`). Deterministic
`random.seed(42)` so seeds are reproducible.

```
Package(
  PackageID   PK,
  destination VARCHAR,   -- "Lisbon", "Kyoto", "Reykjavik", "Barcelona", "Bali", "Rome"
  depart_date DATE,      -- 2026 calendar
  nights      INT,       -- 3 / 5 / 7
  flight_price INT,
  hotel_name  VARCHAR,
  hotel_price INT,       -- total for the stay
  total_price INT,       -- flight + hotel
  available   BOOLEAN
)
```

Public API (mirrors `get_slots_by_day`):
`get_packages(destination, max_budget, reference_date, n=3) -> list[dict]` — the n cheapest available
packages to `destination`, departing on/after `reference_date`, with `total_price <= max_budget`.
Seeded across 2026 for ~6 destinations × a few departure dates × {3,5,7} nights, with pseudo-random
availability and prices.

## Knowledge base — destination guides (`data/destinations/`)

One short PDF per destination (climate, best time to visit, top attractions, food, visa/safety basics).
`guide_embedder.py` mirrors `pdf_embedder.py`: PyPDFLoader → RecursiveCharacterTextSplitter(500/50) →
OpenAIEmbeddings(`text-embedding-3-small`) → Chroma at `data/chroma_db/`. Auto-builds on first
retrieval so a cold Streamlit Cloud deploy works (the store is gitignored).

> Open content decision: ship a handful of generated guide PDFs for a fixed destination set, OR let the
> set be swappable. Default for v1: ~6 fixed destinations, generated guides. Easy to extend later.

## Models

- Trip Agent + advisors (base): `gpt-4.1`, `temperature=0` (matches genai).
- Embeddings: `text-embedding-3-small`.
- Booking Advisor fine-tune base: `gpt-4o-mini-2024-07-18`.

## Evaluation

`tests/trip_conversations.json` — labeled trip-planning conversations, each recruiter→ candidate turn
analog (concierge turn) tagged with the correct action: `continue` / `recommend` / `book`.
`tests/test_evals.ipynb` replays every labeled turn through `get_concierge_response` end-to-end and
reports **accuracy**, **confusion matrix**, and per-class **precision / recall / F1** — same harness as
genai's `test_evals.ipynb`.

## Fine-tuning

`tests/finetune_booking_advisor.ipynb` — build train/test JSONL from the labeled set, launch an SFT job
on `gpt-4o-mini-2024-07-18`, evaluate vs. base on a held-out split. Activate by pasting the resulting
`ft:...` id into `.env` as `BOOKING_ADVISOR_MODEL`. `booking_advisor.py` reads it and falls back to the
base LLM if the fine-tuned model is unreachable (mirrors `exit_advisor.py`'s try/except).

## Build sequence

1. **Scaffold + config** — repo, dirs, `.gitignore`, `.env.example`, `requirements.txt`, README, PLAN. ← *done*
2. **Data layer** — `package_db.py` (seed + `get_packages`); generate destination guide PDFs +
   `guide_embedder.py`.
3. **Agents (zero-shot first)** — `trip_agent.py` orchestrator; `destination_advisor.py` (RAG);
   `budget_advisor.py` (two-stage: classify → DB lookup → grounded rewrite); `booking_advisor.py`
   (binary, env-var swap + fallback). Wire `__init__.py` re-exports.
4. **Entry point + UI** — `app/main.py` `get_concierge_response(messages, reference_date=None)`;
   `streamlit_app/streamlit_main.py` (themed chat, typewriter stream, end-state lock + "Plan a New Trip").
5. **Eval** — write `trip_conversations.json`; build `test_evals.ipynb`; record baseline accuracy.
6. **Prompt tuning** — add few-shot examples to Trip Agent / Budget / Destination advisors; re-eval.
7. **Fine-tune** — `finetune_booking_advisor.ipynb`; set `BOOKING_ADVISOR_MODEL`; re-eval.
8. **Deploy** — Streamlit Community Cloud (entry `streamlit_app/streamlit_main.py`, secrets in TOML).
9. **Polish + README sync** — error handling, remove any debug sidebar, keep README in lockstep.

## Open decisions (defaults chosen; flag if you disagree)

- **Mock DB vs. real flight/hotel API.** Default: **mock SQLite** (faithful to genai, self-contained,
  free to deploy, no extra keys). A real Amadeus/Skyscanner integration is a documented *stretch goal*,
  not v1.
- **Destination set.** Default: ~6 fixed, generated guides (Lisbon, Kyoto, Reykjavik, Barcelona, Bali,
  Rome). Swappable later.
- **Terminal action naming.** Using `book` (more evocative than genai's `end`); it also absorbs the
  graceful-exit/abandon case, guarded by the fine-tuned Booking Advisor.
