# Deploying Trip Concierge (Streamlit Community Cloud)

How to put the app online. The entry point is `streamlit_app/streamlit_main.py`; Community Cloud runs
it straight from the GitHub repo. Commands/paths assume the repo at
`https://github.com/tomSapir/trip-concierge`.

> **Read §0 first.** A Community Cloud app is **public by default** and every turn spends *your*
> OpenAI credits (each turn is multiple `gpt-4.1` calls, plus embeddings on factual turns). The cost
> guardrail is not optional.

---

## 0. The cost guardrail (do this before anything else)

Layered defense — the first line is in your OpenAI account, not the code:

| Layer | What | Where |
|---|---|---|
| **Dedicated key** | A separate OpenAI **project + API key** used *only* by this deploy, so you can revoke it without touching anything else. | OpenAI dashboard → Projects → new project → API key |
| **Hard spend cap** | A **monthly budget / usage limit** on that project. This is the real backstop if the URL leaks. | OpenAI dashboard → Settings → Limits |
| **Per-session cap** | Each visitor's session locks after *N* messages, bounding the cost of any one tab. | app code (already in `streamlit_main.py`) |

The dedicated key + spend cap are the protection that matters — set them before you make the URL public.

---

## 1. Prerequisites

- The `main` branch pushed to GitHub and green (eval passes locally — see [`RUNNING.md`](RUNNING.md) §4).
- A **Streamlit Community Cloud** account, signed in with the GitHub account that owns the repo
  (<https://share.streamlit.io>).
- The restricted OpenAI key from §0.

---

## 2. What Community Cloud needs from the repo (already in place)

| Need | Where | Status |
|---|---|---|
| Dependency list | `requirements.txt` (fully pinned) | ✓ committed |
| Entry point | `streamlit_app/streamlit_main.py` | ✓ already path-fixes the repo root |
| Data stores | `data/packages.db`, `data/chroma_db/` | ✓ **auto-build on first run** (gitignored) — see §5 |
| Source data | `data/destinations/*.pdf`, destination registry | ✓ committed (the stores rebuild from these) |
| Python version | set in **Advanced settings** at deploy time | choose **3.11+** |

Nothing to add to the repo. The package DB and the Chroma vector store are *not* committed; they
rebuild from the committed PDFs + registry the first time a turn needs them.

---

## 3. Deploy steps

1. Go to <https://share.streamlit.io> → **Create app** → **Deploy from an existing repo**.
2. Fill in:
   - **Repository:** `tomSapir/trip-concierge`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app/streamlit_main.py`
3. Open **Advanced settings**:
   - **Python version:** `3.11` (or newer).
   - **Secrets:** paste the TOML below.
4. **Deploy.** The first build installs `requirements.txt` — give it a few minutes (`chromadb` and
   `onnxruntime` are large).

### Secrets (TOML) — Advanced settings → Secrets

```toml
OPENAI_API_KEY = "sk-...restricted-key-from-§0..."
# BOOKING_ADVISOR_MODEL = "ft:gpt-4o-mini-..."   # optional; leave commented to use the base model
```

> Community Cloud also exposes every secret as an **environment variable**, so the app's existing
> `os.getenv("OPENAI_API_KEY")` loading (the agents build their clients at import time) works
> unchanged — no code change needed for the key. You can edit Secrets later from the app's **⋮ →
> Settings → Secrets**; saving reboots the app.

---

## 4. In-app guardrail

Already in `streamlit_main.py`:

- **Per-session message cap** (`MAX_USER_MESSAGES`) — counts user turns in `st.session_state`; once the
  cap is hit, input closes with a notice + reset, bounding the spend of any single visitor. Adjust the
  constant to taste.

---

## 5. Cold start (first request is slow)

On a fresh container the first turn that needs destination facts **builds the Chroma store from the
guide PDFs** — embedding takes a little while, so that first turn shows a long "Thinking…" spinner.
Every later turn reuses the store. Community Cloud **sleeps** idle apps; on wake the container is fresh
and the store rebuilds once more. Community Cloud's memory ceiling is ~1 GB, and the build pulls in
`chromadb`/`onnxruntime`, so if a deploy OOMs during build or first run, see §7.

---

## 6. After it's live

1. Open the app URL and run a happy path: **continue → recommend → book** (and try **abandon**).
2. Confirm the message cap behaves (input closes after the limit).
3. Tick **Streamlit Community Cloud deployment** in [`README.md`](README.md) (To-Do List) and mark
   step 8 done in [`PLAN.md`](PLAN.md) — only once it's actually live.
4. Keep the docs in sync (this file, README, RUNNING, PLAN).

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `OPENAI_API_KEY` not found / 401 | Secret not saved, or saved under the wrong name — check **Settings → Secrets** (exact key name), then reboot. |
| `ModuleNotFoundError: app` | Wrong **Main file path** — it must be `streamlit_app/streamlit_main.py` (the file path-fixes the repo root itself). |
| Build OOM / killed installing deps | Memory ceiling — trim `requirements.txt` to runtime-only deps (drop the notebook/eval stack: `ipykernel`, `jupyter*`, `debugpy`, `matplotlib`, `seaborn`, `scikit-learn`) and redeploy. |
| First turn very slow, then fine | Expected — Chroma store building on cold start (§5). |
| App slept / "Yes, get this app back up" | Idle sleep; first wake rebuilds the store (§5). Nothing to fix. |
| Unexpected spend | Rotate the restricted key in the OpenAI dashboard (revokes the leaked one), confirm the spend cap, re-paste the new key into Secrets. |
