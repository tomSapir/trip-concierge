"""Standalone runner for the Trip Concierge end-to-end evaluation.

Mirrors tests/test_evals.ipynb so the eval can be re-run without stepping through the
notebook: it replays every labeled turn in trip_conversations.json through
get_concierge_response and prints accuracy, a 4x4 confusion matrix, per-class
precision/recall/F1, and the misclassifications.

    python tests/run_evals.py                 # run, compare to tests/baseline_metrics.json
    python tests/run_evals.py --save          # also write this run's metrics for history
    python tests/run_evals.py --no-baseline   # skip the baseline comparison

Each run prints a pass/fail marker per turn and a baseline-aware banner: the overall
accuracy delta and per-class recall delta (especially `book`, the known weak spot) make a
tuning or fine-tuning run an instant before/after read.

Calls the OpenAI API once per labeled turn (~34 calls), so it costs a little and takes a
minute or two.
"""
import argparse
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

# Force UTF-8 stdout so the Δ glyph in the banner can't raise UnicodeEncodeError on a legacy
# Windows console (cp1252). Harmless where stdout is already UTF-8 or a redirected pipe.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Load OPENAI_API_KEY before importing the app — the agents build their ChatOpenAI clients
# at import time and need the key present.
load_dotenv(REPO_ROOT / ".env")

from app.main import get_concierge_response  # noqa: E402 — must follow load_dotenv above

ACTIONS = ["continue", "recommend", "book", "abandon"]
ROLE_OF = {"traveller": "user", "concierge": "assistant"}  # dataset speaker -> message role
BASELINE_PATH = REPO_ROOT / "tests" / "baseline_metrics.json"
DEFAULT_SAVE_PATH = REPO_ROOT / "tests" / "last_run_metrics.json"


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
    Each line carries an `ok`/`MISS` marker so misses stand out from the scroll.
    """
    for i, case in enumerate(cases, 1):
        try:
            action, _reply = get_concierge_response(case["history"], reference_date)
        except Exception as e:
            action = f"ERROR: {e}"
        case["pred"] = action
        marker = "ok  " if action == case["gold"] else "MISS"
        print(f'[{i:>2}/{len(cases)}] {marker} gold={case["gold"]:9} pred={action:9} '
              f'| {case["scenario"][:45]}')


def summarize(cases):
    """Reduce predicted cases to the metrics dict saved in baseline_metrics.json.

    Shape: {accuracy, n, by_class: {precision, recall, f1-score, support}} — identical to the
    baseline file, so a run is directly diffable against (and promotable to) the baseline.
    """
    y_true = [c["gold"] for c in cases]
    y_pred = [c["pred"] for c in cases]
    correct = sum(t == p for t, p in zip(y_true, y_pred))
    rep = classification_report(y_true, y_pred, labels=ACTIONS, output_dict=True, zero_division=0)
    return {
        "accuracy": correct / len(y_true),
        "n": len(y_true),
        "by_class": pd.DataFrame(rep).T.to_dict(),
    }


def load_baseline(path):
    """Return the saved baseline metrics dict, or None if it isn't there."""
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _hits(metrics, cls):
    """Recover the (correct, support) integer counts for a class from its recall."""
    support = int(round(metrics["by_class"]["support"][cls]))
    recall = metrics["by_class"]["recall"][cls]
    return round(recall * support), support


def print_banner(metrics, baseline):
    """Loud accuracy + book-recall header, with deltas vs baseline when one is present."""
    acc, n = metrics["accuracy"], metrics["n"]
    correct = round(acc * n)
    book_recall = metrics["by_class"]["recall"]["book"]
    book_hits, book_support = _hits(metrics, "book")
    bar = "=" * 60

    print(f"\n{bar}")
    if baseline:
        d_acc = (acc - baseline["accuracy"]) * 100  # percentage points
        base_book = baseline["by_class"]["recall"]["book"]
        d_book = book_recall - base_book
        print(f"  ACCURACY     {acc:6.1%}  ({correct}/{n})"
              f"     Δ {d_acc:+.1f} pts vs baseline {baseline['accuracy']:.1%}")
        print(f"  book recall  {book_recall:6.2f}  ({book_hits}/{book_support})"
              f"     Δ {d_book:+.2f} vs baseline {base_book:.2f}   <- weak spot")
    else:
        print(f"  ACCURACY     {acc:6.1%}  ({correct}/{n})     (no baseline to compare)")
        print(f"  book recall  {book_recall:6.2f}  ({book_hits}/{book_support})   <- weak spot")
    print(bar)


def print_recall_table(metrics, baseline):
    """Per-class recall next to the baseline and its delta — the tuning scoreboard."""
    rec = metrics["by_class"]["recall"]
    print("\nrecall vs baseline:")
    print(f"  {'class':<10} {'recall':>7} {'baseline':>9} {'Δ':>8}")
    for cls in ACTIONS:
        r = rec[cls]
        if baseline:
            b = baseline["by_class"]["recall"][cls]
            print(f"  {cls:<10} {r:>7.3f} {b:>9.3f} {r - b:>+8.3f}")
        else:
            print(f"  {cls:<10} {r:>7.3f} {'n/a':>9} {'n/a':>8}")


def report(cases, baseline):
    """Print the banner, confusion matrix, per-class metrics, recall delta, and misses."""
    metrics = summarize(cases)
    y_true = [c["gold"] for c in cases]
    y_pred = [c["pred"] for c in cases]

    print_banner(metrics, baseline)

    # Fixed label order so the grid always reads the same way. An errored prediction isn't one
    # of ACTIONS, so it drops out of the grid (still a miss in the accuracy above).
    cm = confusion_matrix(y_true, y_pred, labels=ACTIONS)
    print("\nconfusion matrix (rows = true, cols = predicted):")
    print(pd.DataFrame(cm, index=ACTIONS, columns=ACTIONS).to_string())

    # Drop the scalar `accuracy` row sklearn folds in — it pollutes the per-class columns.
    per_class = pd.DataFrame(metrics["by_class"]).drop(index="accuracy", errors="ignore")
    print("\nper-class precision / recall / F1:")
    print(per_class.round(3).to_string())

    print_recall_table(metrics, baseline)

    misses = [
        {"conv": c["conversation_id"], "turn": c["turn_id"], "gold": c["gold"], "pred": c["pred"],
         "last_user": next((m["content"] for m in reversed(c["history"]) if m["role"] == "user"), "")}
        for c in cases if c["pred"] != c["gold"]
    ]
    print(f"\n{len(misses)} misclassification(s):")
    if misses:
        print(pd.DataFrame(misses).to_string(index=False))

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Run the Trip Concierge eval and report results.")
    parser.add_argument("--no-baseline", action="store_true",
                        help="skip the comparison against tests/baseline_metrics.json")
    parser.add_argument("--save", nargs="?", const=str(DEFAULT_SAVE_PATH), default=None,
                        metavar="PATH",
                        help="write this run's metrics as JSON (default: tests/last_run_metrics.json)")
    args = parser.parse_args()

    cases, reference_date = load_cases(REPO_ROOT / "tests" / "trip_conversations.json")
    print(f"{len(cases)} eval cases | {dict(Counter(c['gold'] for c in cases))} "
          f"| reference_date={reference_date}\n")
    predict(cases, reference_date)

    baseline = None if args.no_baseline else load_baseline(BASELINE_PATH)
    if baseline is None and not args.no_baseline:
        print("\n(no baseline_metrics.json found — skipping delta comparison)")
    metrics = report(cases, baseline)

    if args.save:
        Path(args.save).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(f"\nsaved metrics -> {args.save}")


if __name__ == "__main__":
    main()
