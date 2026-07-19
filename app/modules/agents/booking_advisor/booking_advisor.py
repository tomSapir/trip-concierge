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

A commitment counts even when the wording is casual or implicit — what matters is that the
traveller is telling you to go ahead with one specific option, not still weighing them.

Examples — the traveller's latest message, then your answer:
- "Book option 2." -> book
- "Let's do the Lisbon one." -> book
- "Yes, go ahead and book it." -> book
- "I'll take the second package." -> book
- "Sounds great — lock in the Bali trip." -> book
- "Perfect, let's go with option 1." -> book
- "Option 2 looks tempting…" -> dont_book
- "How many nights is option 1?" -> dont_book
- "Which one would you recommend?" -> dont_book
- "Hmm, let me think about it." -> dont_book
- "Maybe the Rome one, but I'm not sure yet." -> dont_book
- "Can you compare option 1 and 2?" -> dont_book
"""


def _classify(convo):
    """Return ('book' or 'dont_book', model_used) — the caller unpacks both.
    Try the configured model; fall back to base on any error."""
    try:
        # Use the fine-tuned model when BOOKING_ADVISOR_MODEL is set, else the base model.
        llm = ChatOpenAI(model=BOOKING_ADVISOR_MODEL, temperature=0) if BOOKING_ADVISOR_MODEL else base_llm
        raw = llm.invoke(convo).content
        model_used = BOOKING_ADVISOR_MODEL or BASE_MODEL
    except Exception:
        # Stale / unreachable ft id must never break booking -> fall back to base.
        raw = base_llm.invoke(convo).content
        model_used = BASE_MODEL

    label = raw.strip().strip(".").lower()
    return ("book" if label == "book" else "dont_book", model_used)


def get_booking_advisor_response(messages, draft):
    # draft = the Trip Agent's drafted reply for this turn; we keep it on both branches below.
    convo = [("system", SYSTEM)] + [(ROLE_MAP.get(m["role"], "human"), m["content"]) for m in messages]
    label, model_used = _classify(convo)

    # Genuine commitment -> keep the terminal `book`; the UI surfaces the confirmation message.
    if label == "book":
        return ("book", draft, {"model": model_used})

    # Musing / question / hesitation -> demote and keep the agent's draft so the chat continues.
    return ("continue", draft,
            {"reason": "classifier said dont_book — musing, not a commitment",
             "model": model_used})
