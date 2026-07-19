"""Concierge turn result — the widened return of `get_concierge_response` (v2 step 2).

Backward-compatible on purpose: it still unpacks to `(action, reply)` via `__iter__`, so the
eval harness (`tests/run_evals.py`), the eval notebook, and the RUNNING.md snippet keep
tuple-unpacking unchanged. Only the Streamlit UI opts into the richer `.packages` / `.trace`
fields (added in later sub-steps). No agent imports here, so this module imports without an
OpenAI key — which is what lets `tests/test_concierge_turn.py` run API-free.

See docs/plans/step-2-result-object-seam.md (sub-step 2a).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ConciergeTurn:
    action: str                    # continue | recommend | book | abandon (the FINAL action)
    reply: str                     # the text shown to the traveller
    packages: list | None = None   # Budget Advisor's real rows on a recommend (ideas 1 + 4)
    trace: dict | None = None      # reasoning trail for debug mode (idea 2)

    def __iter__(self):
        # Exactly these two, in this order — `action, reply = get_concierge_response(...)`
        # unpacks positionally; yielding more (or reordering) breaks every tuple-unpacking caller.
        yield self.action
        yield self.reply
