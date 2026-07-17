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
    if action == "recommend":
        # No draft — the Budget Advisor rewrites from real rows; vetoes to continue if no destination.
        action, reply = get_budget_advisor_response(messages, reference_date)
        return ConciergeTurn(action, reply)

    if action == "book":
        # Demotes to continue when the traveller is musing rather than committing.
        action, reply = get_booking_advisor_response(messages, draft)
        return ConciergeTurn(action, reply)

    if action == "abandon":
        # Unguarded terminal — no advisor; pass the agent's draft straight through.
        return ConciergeTurn(action, draft)

    # continue (the default): grounds a factual question, scopes an out-of-set one, or keeps the draft.
    action, reply = get_destination_advisor_response(messages, draft)
    return ConciergeTurn(action, reply)
