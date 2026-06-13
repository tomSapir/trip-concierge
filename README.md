<!-- PROJECT LOGO -->
<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" alt="Logo" width="120" height="120">
</p>

<h1 align="center">Trip Concierge</h1>

<p align="center">
  A multi-agent chatbot that plans a trip with you — learns your preferences, answers questions about
  destinations, proposes concrete flight + hotel packages within your budget, and books the one you pick.
</p>

---

> **Status: scaffolding.** Repo structure, dependencies, and the build plan are in place. The agents,
> data layer, UI, eval, and fine-tuning are being built out per [`PLAN.md`](PLAN.md). Checklist below
> tracks progress.

---

## Table of Contents

- [About The Project](#about-the-project)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [To-Do List](#to-do-list)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

---

## About The Project

> A multi-agent travel concierge built around a **Trip Agent** that decides one of three actions every
> turn — **Continue**, **Recommend**, or **Book** — and three specialist **Advisors** that validate or
> enrich each decision.

<div style="background: #272822; color: #f8f8f2; padding: 10px; border-radius: 8px;">
  <b>Technologies:</b> Python, LangChain, OpenAI (Chat, Embeddings, Fine-Tuning), Chroma, SQLAlchemy, Streamlit
</div>

This project deliberately reuses the architecture of a recruitment-chatbot project, re-themed as a
travel concierge — a Main Agent + specialist Advisors, RAG over a document corpus, function calling to a
SQL database, an end-to-end evaluation, and a fine-tuned sub-agent.

---

## Architecture

Every turn flows through this pipeline:

1. **Trip Agent** reads the conversation history and proposes an action (`continue` / `recommend` /
   `book`) plus a draft reply.
2. The decision is routed to the matching **Advisor** for validation or enrichment:
   - **Destination Advisor** — answers questions about places (climate, best season, attractions, food,
     visas) using semantic retrieval over a Chroma knowledge base of destination guides.
   - **Budget Advisor** — queries the package database (function calling) for the three best available
     flight + hotel packages within budget and rewrites the reply with concrete dates and prices.
   - **Booking Advisor** — confirms that the user has actually committed to a specific option before the
     concierge finalizes. Fine-tuned for this binary classification task.
3. If an Advisor disagrees with the Trip Agent (e.g. the Budget Advisor says *too early to recommend*),
   the action is demoted back to `continue`.

See [`PLAN.md`](PLAN.md) for the full design, the mapping to the source project, and the build sequence.

---

## Getting Started

### Prerequisites

- Python >= 3.11
- pip
- An OpenAI API key

### Installation

```powershell
git clone https://github.com/tomSapir/trip-concierge.git
cd trip-concierge

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copy the env template and fill in your OpenAI API key:

```powershell
copy .env.example .env
```

Open `.env` and set `OPENAI_API_KEY`. If you have a fine-tuned Booking Advisor model, also set
`BOOKING_ADVISOR_MODEL=ft:gpt-4o-mini-...` — otherwise leave it commented out and the Booking Advisor
will use the base LLM.

> Data stores auto-initialize: the Chroma vector store (`data/chroma_db/`) and the package SQLite DB
> (`data/packages.db`) are both created on first use.

---

## Usage

```powershell
streamlit run streamlit_app/streamlit_main.py
```

_(Available once the UI is implemented — see the checklist.)_

---

## Project Structure

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
│   ├── destinations/*.pdf                        ← guide corpus
│   ├── packages.db                              ← auto-generated SQLite
│   └── chroma_db/                               ← built on first run
├── tests/
│   ├── trip_conversations.json                  ← labeled eval dataset
│   ├── test_evals.ipynb                         ← evaluation notebook
│   └── finetune_booking_advisor.ipynb           ← Booking Advisor fine-tuning
├── requirements.txt
├── .env.example
├── PLAN.md
└── README.md
```

---

## To-Do List

- [x] Repo scaffold, dependencies, build plan
- [ ] Package DB (`package_db.py`) — seed + `get_packages`
- [ ] Destination guide corpus + Chroma embedder (`guide_embedder.py`)
- [ ] Trip Agent + three advisors wired end-to-end
- [ ] Streamlit chat UI
- [ ] Labeled eval dataset + accuracy / confusion matrix
- [ ] Few-shot prompt tuning
- [ ] Supervised fine-tuning of the Booking Advisor
- [ ] Streamlit Community Cloud deployment

---

## Contact

**Tom Sapir** — [tom.sapir@akribis-sys.com](mailto:tom.sapir@akribis-sys.com)

---

## Acknowledgments

- [LangChain](https://www.langchain.com/)
- [OpenAI](https://platform.openai.com/)
- [Chroma](https://www.trychroma.com/)
- [Streamlit](https://streamlit.io/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
