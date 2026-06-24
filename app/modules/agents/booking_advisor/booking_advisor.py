"""Booking Advisor — guards `book`. Confirms the traveller genuinely committed to ONE
specific package ("book option 2") versus merely musing ("option 2 looks tempting…").
On a non-commitment it returns `dont_book`, demoting the turn back to `continue`.

Binary classifier (book / dont_book). Runs the base model by default; a fine-tuned
gpt-4o-mini is swapped in via BOOKING_ADVISOR_MODEL when set, falling back to base if
that model is unreachable (e.g. a stale ft: id). Mirrors genai's Exit Advisor — but
narrower: abandonment is NOT its job (that's the unguarded `abandon` action).
"""
import os
from langchain_openai import ChatOpenAI

BASE_MODEL = "gpt-4.1"
# Optional fine-tuned swap; None -> just use the base model.
BOOKING_ADVISOR_MODEL = os.getenv("BOOKING_ADVISOR_MODEL")

base_llm = ChatOpenAI(model=BASE_MODEL, temperature=0)

# Map our OpenAI-style message dicts to LangChain's tuple roles (same as the other advisors).
ROLE_MAP = {"user": "human", "assistant": "ai", "system": "system"}

SYSTEM = """You are the Booking Advisor for a trip-planning concierge.

Decide whether the traveller has genuinely committed to booking ONE specific package,
or is only musing / asking / hesitating.

Reply with EXACTLY one word, lowercase, nothing else: book or dont_book.
- book: a clear commitment to a specific option ("book option 2", "let's do the Lisbon one").
- dont_book: musing, comparing, questions, or hesitation ("option 2 looks tempting…").
"""
# TODO (step 6, prompt tuning): add a few-shot block of book / dont_book examples here.


def _classify(convo):
    """Return 'book' or 'dont_book'. Try the configured model; fall back to base on any error."""
    try:
        # Use the fine-tuned model when BOOKING_ADVISOR_MODEL is set, else the base model.
        llm = ChatOpenAI(model=BOOKING_ADVISOR_MODEL, temperature=0) if BOOKING_ADVISOR_MODEL else base_llm
        raw = llm.invoke(convo).content
    except Exception:
        # Stale / unreachable ft id must never break booking -> fall back to base.
        raw = base_llm.invoke(convo).content
    label = raw.strip().strip(".").lower()
    return "book" if label == "book" else "dont_book"


def get_booking_advisor_response(messages, draft):
    # draft = the Trip Agent's drafted reply for this turn; we keep it on both branches below.
    convo = [("system", SYSTEM)] + [(ROLE_MAP.get(m["role"], "human"), m["content"]) for m in messages]
    label = _classify(convo)

    # Genuine commitment -> keep the terminal `book`; the UI surfaces the confirmation message.
    if label == "book":
        return ("book", draft)

    # Musing / question / hesitation -> demote and keep the agent's draft so the chat continues.
    return ("continue", draft)
