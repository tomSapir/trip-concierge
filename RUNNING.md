# Running Trip Concierge

Everything you need to install, run, evaluate, and (optionally) fine-tune the app. Commands are
PowerShell (Windows); the bracketed bash equivalents work on macOS/Linux.

---

## 1. Prerequisites

| Component | Requirement | Notes |
|---|---|---|
| Python | **3.11+** | `python --version` |
| pip | bundled with Python | |
| OpenAI API key | required | used for chat, embeddings, and fine-tuning |
| Git | to clone | |

The app calls the OpenAI API on every turn, so a funded key is required — there is no offline mode.

---

## 2. One-time setup

```powershell
git clone https://github.com/tomSapir/trip-concierge.git
cd trip-concierge

# Virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1            # bash: source .venv/bin/activate

# Dependencies (pinned)
pip install -r requirements.txt

# Environment file
copy .env.example .env                # bash: cp .env.example .env
```

Then open `.env` and set your key:

```ini
OPENAI_API_KEY=sk-...                 # required
# BOOKING_ADVISOR_MODEL=ft:gpt-4o-mini-...   # optional; leave unset to use the base model
```

### What auto-initializes (don't create these by hand)

| Store | Path | Built when | Tracked in git? |
|---|---|---|---|
| Package DB (SQLite) | `data/packages.db` | first call that needs packages | no (`.gitignore`) |
| Vector store (Chroma) | `data/chroma_db/` | first destination retrieval | no (`.gitignore`) |

Both are seeded/embedded from committed sources: the destination registry
(`app/modules/destination_registry.py`) and the guide PDFs (`data/destinations/*.pdf`). The first
run that touches them is slower because it embeds the guides; later runs reuse the stores. To rebuild
from scratch, delete `data/packages.db` and `data/chroma_db/` and run again.

---

## 3. Run the app (Streamlit UI)

```powershell
streamlit run streamlit_app/streamlit_main.py
```

Opens a chat in the browser. Describe a trip, ask about a destination, get package options, and book
one — or walk away. Both terminal actions (book / abandon) lock the chat and show a "Plan a New Trip"
reset button.

---

## 4. Run the evaluation

The eval replays every labeled turn in `tests/trip_conversations.json` through the full
`get_concierge_response` pipeline and reports accuracy, a 4×4 confusion matrix, per-class
precision/recall/F1, and the misclassifications.

> Each labeled turn is one OpenAI call (~34 calls total), so a full run costs a little and takes a
> minute or two. It uses a fixed `reference_date` from the dataset so results are deterministic.

### Option A — standalone script (re-runnable, no notebook)

```powershell
python tests/run_evals.py
```

Run it from anywhere — the script anchors to the repo root itself (so `data/` paths resolve) and
loads `.env` before importing the app.

### Option B — notebook (same logic, step-through + plots)

```powershell
jupyter notebook tests/test_evals.ipynb
```

Baseline to compare against (saved in `tests/baseline_metrics.json`): **91.2% accuracy (31/34)**.
The known weak spot is **`book` recall (0.40)** — genuine commitments demoted to `continue`. `book`
precision is 1.0 (no false bookings).

---

## 5. (Optional) Fine-tune the Booking Advisor

Only needed to reproduce the supervised fine-tune; the app runs fine on the base model without it.

```powershell
jupyter notebook tests/finetune_booking_advisor.ipynb
```

The notebook builds a small `book`/`dont_book` JSONL, launches an SFT job on
`gpt-4o-mini-2024-07-18`, and evaluates it vs. the base model. To activate the result in the app,
paste the returned `ft:...` id into `.env` as `BOOKING_ADVISOR_MODEL` and restart. `booking_advisor.py`
falls back to the base LLM if that model is unreachable.

---

## 6. Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | yes | chat, embeddings, fine-tuning |
| `BOOKING_ADVISOR_MODEL` | no | fine-tuned Booking Advisor id; unset → base model |

For Streamlit Community Cloud deployment, set the same keys as secrets (TOML) instead of a `.env`
file.

---

## 7. Component map (what runs what)

```text
streamlit_app/streamlit_main.py     UI → calls get_concierge_response per turn
app/main.py                         get_concierge_response(messages, reference_date=None)
                                      → (action, reply); routes to one advisor, which may demote
app/modules/destination_registry.py canonical destination list (single source of truth)
app/modules/agents/
  trip_agent/trip_agent.py          classifies the turn: continue / recommend / book / abandon
  destination_advisor/
    destination_advisor.py          RAG over the guide corpus; scopes out-of-set questions
    guide_embedder.py               builds data/chroma_db/ from data/destinations/*.pdf
  budget_advisor/
    budget_advisor.py               function-calls get_packages, rewrites with dates/prices
    package_db.py                   seeds + queries data/packages.db
  booking_advisor/booking_advisor.py  confirms genuine commitment before booking
tests/
  trip_conversations.json          labeled eval set (14 conversations / 34 turns)
  run_evals.py                      standalone eval runner  (section 4A)
  test_evals.ipynb                 eval notebook            (section 4B)
  finetune_booking_advisor.ipynb   SFT workflow             (section 5)
  baseline_metrics.json            saved baseline to compare against
```

Calling the pipeline directly from Python:

```python
from app.main import get_concierge_response

action, reply = get_concierge_response(
    [{"role": "user", "content": "I want a relaxed beach trip in September"}]
)
# action ∈ {"continue", "recommend", "book", "abandon"}
```

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `OPENAI_API_KEY` not found / auth errors | `.env` missing or key unset; the agents build their clients at import time, so the key must be present before import |
| `ModuleNotFoundError: app` | run from the repo root, or use `tests/run_evals.py` which fixes `sys.path`/cwd itself |
| First run is slow / "embedding" pause | expected — the Chroma store is being built; subsequent runs reuse it |
| Stale or corrupt data store | delete `data/packages.db` and/or `data/chroma_db/` and re-run to rebuild |
| Wrong Python in venv | re-create: remove `.venv`, then `python -m venv .venv` with Python 3.11+ |
```
