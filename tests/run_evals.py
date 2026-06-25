"""Standalone runner for the Trip Concierge end-to-end evaluation.

Mirrors tests/test_evals.ipynb so the eval can be re-run without stepping through the
notebook: it replays every labeled turn in trip_conversations.json through
get_concierge_response and prints accuracy, a 4x4 confusion matrix, per-class
precision/recall/F1, and the misclassifications.

    python tests/run_evals.py

Calls the OpenAI API once per labeled turn (~34 calls), so it costs a little and takes a
minute or two.
"""
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import classification_report, confusion_matrix

# Anchor to the repo root from THIS file's location (the script may be run from anywhere),
# chdir there so the app's relative data paths (data/packages.db, data/chroma_db) resolve,
# and put it on sys.path so the `app` package imports.
REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load OPENAI_API_KEY before importing the app — the agents build their ChatOpenAI clients
# at import time and need the key present.
load_dotenv(REPO_ROOT / ".env")

from app.main import get_concierge_response  # noqa: E402 — must follow load_dotenv above

ACTIONS = ["continue", "recommend", "book", "abandon"]
ROLE_OF = {"traveller": "user", "concierge": "assistant"}  # dataset speaker -> message role


def load_cases(data_path):
    """Flatten conversations into one eval case per concierge turn.

    Each case's input is the history BEFORE that turn; its target is the turn's gold label.
    Snapshot before appending so the turn being predicted is never part of its own input.
    """
    data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    reference_date = date.fromisoformat(data["reference_date"])  # fixed "today" for determinism
    cases = []
    for conv in data["conversations"]:
        history = []
        for turn in conv["turns"]:
            if turn["speaker"] == "concierge":
                cases.append({
                    "conversation_id": conv["conversation_id"],
                    "turn_id": turn["turn_id"],
                    "scenario": conv["scenario"],
                    "history": list(history),  # copy — later appends must not mutate this snapshot
                    "gold": turn["label"],
                })
            history.append({"role": ROLE_OF[turn["speaker"]], "content": turn["text"]})
    return cases, reference_date


def predict(cases, reference_date):
    """Run every case through the full pipeline, recording the predicted action in place.

    A failed turn is recorded as an "ERROR: ..." string instead of aborting the whole run.
    """
    for i, case in enumerate(cases, 1):
        try:
            action, _reply = get_concierge_response(case["history"], reference_date)
        except Exception as e:
            action = f"ERROR: {e}"
        case["pred"] = action
        print(f'[{i:>2}/{len(cases)}] gold={case["gold"]:9} pred={action:9} | {case["scenario"][:45]}')


def report(cases):
    """Print accuracy, the confusion matrix, per-class metrics, and the misclassifications."""
    y_true = [c["gold"] for c in cases]
    y_pred = [c["pred"] for c in cases]

    correct = sum(t == p for t, p in zip(y_true, y_pred))
    print(f"\naccuracy: {correct / len(y_true):.1%}  ({correct}/{len(y_true)})")

    # Fixed label order so the grid always reads the same way. An errored prediction isn't one
    # of ACTIONS, so it drops out of the grid (still a miss in the accuracy above).
    cm = confusion_matrix(y_true, y_pred, labels=ACTIONS)
    print("\nconfusion matrix (rows = true, cols = predicted):")
    print(pd.DataFrame(cm, index=ACTIONS, columns=ACTIONS).to_string())

    rep = classification_report(y_true, y_pred, labels=ACTIONS, output_dict=True, zero_division=0)
    print("\nper-class precision / recall / F1:")
    print(pd.DataFrame(rep).T.to_string())

    misses = [
        {"conv": c["conversation_id"], "turn": c["turn_id"], "gold": c["gold"], "pred": c["pred"],
         "last_user": next((m["content"] for m in reversed(c["history"]) if m["role"] == "user"), "")}
        for c in cases if c["pred"] != c["gold"]
    ]
    print(f"\n{len(misses)} misclassification(s):")
    if misses:
        print(pd.DataFrame(misses).to_string(index=False))


def main():
    cases, reference_date = load_cases(REPO_ROOT / "tests" / "trip_conversations.json")
    print(f"{len(cases)} eval cases | {dict(Counter(c['gold'] for c in cases))} "
          f"| reference_date={reference_date}\n")
    predict(cases, reference_date)
    report(cases)


if __name__ == "__main__":
    main()
