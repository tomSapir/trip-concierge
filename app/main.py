"""Concierge entry point — one turn in, one ConciergeTurn out.

The Trip Agent picks the action and drafts a reply; the matching Advisor then validates or
enriches that draft and may DEMOTE the action (e.g. Budget Advisor vetoing a destination-less
`recommend` back to `continue`). `abandon` is unguarded — it fires straight from here with the
agent's draft. Each advisor still returns (action, reply); this seam wraps it in a
ConciergeTurn, which unpacks back to (action, reply) for existing callers (v2 step 2b).
"""
from app.concierge_turn import ConciergeTurn
from app.modules.agents import (
    get_trip_agent_response,
    get_destination_advisor_response,
    get_budget_advisor_response,
    get_booking_advisor_response,
)


def get_concierge_response(messages, reference_date=None):
    # The Trip Agent classifies the turn and drafts a reply.
    action, draft = get_trip_agent_response(messages, reference_date)

    # Route on the action; each advisor returns its own (action, reply) and may demote.
    # `action` is the Trip Agent's original pick, `final_action` the advisor's verdict —
    # they differ exactly when the advisor demoted, which is what the trace makes visible.
    if action == "recommend":
        # No draft — the Budget Advisor rewrites from real rows; vetoes to continue if no destination.
        final_action, reply, meta = get_budget_advisor_response(messages, reference_date)
        trace = {"original_action": action,
                 "final_action": final_action,
                 "route": "budget_advisor"}
        # Lift only the keys this outcome produced: demotes carry "reason", success
        # carries "model" + "packages" (absent -> .get gives the dataclass default None).
        if "reason" in meta:
            trace["reason"] = meta["reason"]
        if "model" in meta:
            trace["model"] = meta["model"]
        return ConciergeTurn(final_action, reply, packages=meta.get("packages"), trace=trace)

    if action == "book":
        # Demotes to continue when the traveller is musing rather than committing.
        final_action, reply = get_booking_advisor_response(messages, draft)
        return ConciergeTurn(final_action, reply, trace={
            "original_action": action,
            "final_action": final_action,
            "route": "booking_advisor",
        })

    if action == "abandon":
        # Unguarded terminal — no advisor ran, so original == final and route is None.
        return ConciergeTurn(action, draft, trace={
            "original_action": action,
            "final_action": action,
            "route": None,
        })

    # continue (the default): grounds a factual question, scopes an out-of-set one, or keeps the draft.
    final_action, reply, meta = get_destination_advisor_response(messages, draft)
    trace = {"original_action": action,
             "final_action": final_action,
             "route": "destination_advisor",
             "model": meta["model"]}
    # Reduce retrieved chunks at the seam: raw LangChain Documents must not reach
    # session_state — the trace keeps only what the debug trail displays.
    trace["chunks"] = [{"source": d.metadata.get("source"),
                        "snippet": d.page_content[:200]}
                       for d in meta["chunks"]]
    return ConciergeTurn(final_action, reply, trace=trace)
