"""Budget Advisor — on `recommend`, finds the best packages within budget and grounds the reply.

Real OpenAI function-calling: binds `find_packages` as a tool, lets the model extract
(destination, month, budget) from the conversation and call it, then writes the reply from
the real rows — concrete dates and prices, never invented. Demotes to `continue` when there's
nothing to recommend. Mirrors genai's Scheduling Advisor.
"""
import json
from datetime import date
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from app.modules.agents.budget_advisor.package_db import get_packages
from app.modules.destination_registry import all_destinations

llm = ChatOpenAI(model="gpt-4.1", temperature=0)
COVERED = ", ".join(d.name for d in all_destinations())  # single source of truth for scoping

# Map our OpenAI-style message dicts to LangChain's tuple roles.
ROLE_MAP = {"user": "human", "assistant": "ai", "system": "system"}


@tool
def find_packages(destination: str, earliest_month: str, max_budget: int | None = None) -> str:
    """Look up the cheapest available trip packages to a destination.

    destination: the city the traveller named.
    earliest_month: 'YYYY-MM' — only show trips departing on or after the 1st of this month.
    max_budget: total USD cap for one traveller, or null for no cap.
    """
    earliest = date.fromisoformat(f"{earliest_month}-01")
    rows = get_packages(destination, max_budget=max_budget, earliest_departure=earliest)
    return json.dumps(rows, default=str)  # default=str serializes the date objects


llm_with_tools = llm.bind_tools([find_packages])

SYSTEM = """You are the Budget Advisor for a trip-planning concierge. Today is {today}.

The traveller wants concrete trip options for a destination they've named. Use the
find_packages tool to look them up — NEVER invent packages, dates, or prices.

Calling the tool:
- destination: the specific place the traveller named.
- earliest_month: the month they want to leave ('YYYY-MM'); if they named none, use {month}.
- max_budget: their total budget in USD if they gave one, else null.
- If the traveller has NOT named a specific destination, do not call the tool at all.

Writing the reply (after the tool returns rows):
- Present the options as a short numbered list. For each: hotel, departure date, nights,
  and total price in USD.
- Warm, concise concierge tone. End by asking which one they'd like to book."""


def get_budget_advisor_response(messages, reference_date=None):
    # reference_date is "today" (overridable so evals replay against a fixed now) — NOT the
    # departure date. The earliest departure is earliest_month, which the model picks per turn.
    today = reference_date or date.today()
    convo = [("system", SYSTEM.format(today=today, month=today.strftime("%Y-%m")))]
    convo += [(ROLE_MAP.get(m["role"], "human"), m["content"]) for m in messages]

    # Round 1: the model extracts the args and calls the tool — or doesn't.
    ai = llm_with_tools.invoke(convo)

    # Veto: no tool call is our signal that no destination was named (the prompt forbids it).
    # The model replied with plain text instead; we discard it for a fixed nudge -> `continue`.
    if not ai.tool_calls:
        return ("continue", "Which destination are you considering? Once we settle on a "
                            "place, I can pull up concrete trip options.")

    call = ai.tool_calls[0]
    rows = json.loads(find_packages.invoke(call["args"]))

    # Nothing fits (out-of-set city, or budget too low) -> honest nudge, demote to `continue`.
    if not rows:
        return ("continue", _no_fit_nudge(call["args"]))

    # Round 2: feed the real rows back so the model writes the list from grounded data.
    convo.append(ai)
    convo.append(ToolMessage(json.dumps(rows, default=str), tool_call_id=call["id"]))
    final = llm_with_tools.invoke(convo)
    return ("recommend", final.content)


def _no_fit_nudge(args):
    """A specific, honest nudge when find_packages came back empty."""
    dest = args["destination"]
    cheapest = get_packages(dest, n=1)  # drop budget/date filters to find the floor price
    if not cheapest:                    # destination we don't cover at all
        return f"I don't have trips to {dest} — I cover {COVERED}."
    floor = cheapest[0]["total_price"]
    budget = args.get("max_budget")
    if budget:
        return (f"Nothing to {dest} under ${budget} — the cheapest is ${floor}. "
                f"Want to raise the budget, or try another destination?")
    return f"I'm not finding {dest} trips for those dates — the soonest available starts at ${floor}."
