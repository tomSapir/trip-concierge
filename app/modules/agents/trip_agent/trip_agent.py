"""Trip Agent — the orchestrator. Each turn it reads the conversation, picks EXACTLY ONE
action (continue / recommend / book / abandon), and drafts the reply the traveller sees.
The matching Advisor then validates or enriches that draft (and may demote the action);
`abandon` is unguarded and fires straight from here.

JSON classifier (few-shot): returns {"action": ..., "reply": ...}. Suggestions are
registry-backed — the full destination list (name + vibe tags) is injected so the agent can
only ever suggest in-set cities (ADR 0001); the candidate lookup sits behind
_suggestion_candidates() so a future version can swap the list for a retrieval top-k without
touching the prompt. Mirrors genai's Main Agent.
"""
import json
import re
from datetime import date
from langchain_openai import ChatOpenAI
from app.modules.destination_registry import all_destinations

llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# Map our OpenAI-style message dicts to LangChain's tuple roles (same as the advisors).
ROLE_MAP = {"user": "human", "assistant": "ai", "system": "system"}

ACTIONS = ("continue", "recommend", "book", "abandon")


def _suggestion_candidates():
    """ADR 0001 seam: the in-set destinations the agent may suggest, as 'Name (vibe, vibe)'.
    v1 = the full registry; a future version can swap this for a vibe-filtered top-k."""
    return "\n".join(f"- {d.name} ({', '.join(d.vibe)})" for d in all_destinations())


SYSTEM = """You are the Trip Agent, orchestrator of a trip-planning concierge. Today is {today}.

Each turn: read the conversation, choose EXACTLY ONE action, and write the reply the
traveller will see. Return ONLY JSON, no prose: {{"action": "<action>", "reply": "<text>"}}.

Actions:
- continue: keep going — gather preferences (where/when/budget/vibe), answer a destination
  question, or SUGGEST in-set destinations that fit their vibe. The non-terminal default.
- recommend: the traveller NAMED a specific destination and wants concrete options. A vibe
  alone is NOT enough (that's a suggestion under continue). Budget is optional.
- book: the traveller committed to ONE specific package ("book option 2").
- abandon: the traveller is walking away without booking ("never mind, not this year").

Suggesting destinations (only under continue): suggest ONLY from this list — never name a
place that isn't on it:
{candidates}"""
# TODO (step 6, prompt tuning): add few-shot examples — one per action, plus the edges
# (musing-not-booking -> continue, out-of-set city, vibe-only -> continue/suggest).


def get_trip_agent_response(messages, reference_date=None):
    today = reference_date or date.today()  # "today" override so evals replay against a fixed now
    system = SYSTEM.format(today=today, candidates=_suggestion_candidates())
    convo = [("system", system)] + [(ROLE_MAP.get(m["role"], "human"), m["content"]) for m in messages]

    # raw is the classifier's JSON, sometimes wrapped in a ```json fence — e.g.
    #   '{"action": "recommend", "reply": "Let me pull up Lisbon options."}'
    raw = llm.invoke(convo).content

    # Strip any leading/trailing markdown fence, then parse — unparseable output becomes {}.
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        data = {}

    action = data.get("action")
    reply = data.get("reply")

    # Safe default: a missing/unknown action or empty reply demotes to `continue` with the raw
    # text — a parse miss must NEVER fire a terminal action (book / abandon).
    if action not in ACTIONS or not reply:
        action, reply = "continue", raw

    return (action, reply)
