"""Destination Advisor — grounds factual destination questions in the guide corpus.

Routed to on `continue`. Answers covered-destination questions grounded in retrieved
guide chunks; scopes out-of-set questions politely; otherwise keeps the Trip Agent's
draft. Mirrors genai's Info Advisor + the honest-scoping deviation.
"""
from langchain_openai import ChatOpenAI
from app.modules.destination_registry import all_destinations
from app.modules.agents.destination_advisor.guide_embedder import get_retriever

llm = ChatOpenAI(model="gpt-4.1", temperature=0)

SYSTEM = """You are the Destination Advisor for a trip-planning concierge. You help only \
with these destinations: {covered}.

You will be given CONTEXT (excerpts from our destination guides), the Trip Agent's DRAFT \
reply, and the traveller's latest message. Decide which case applies and return only the \
final reply text — no labels, no preamble.

1. FACTUAL QUESTION about a covered destination (climate, best season, attractions, food, \
   visas/safety): answer using ONLY facts found in CONTEXT. Never add details that aren't \
   there. If CONTEXT doesn't cover it, say what you can and admit the rest is unknown — \
   don't guess.

2. QUESTION about a place we don't cover (anything not in the list above): don't answer it. \
   Scope politely — name the destinations you cover and note that one isn't among them, \
   e.g. "I cover {covered} — Paris isn't one I can help with."

3. ANYTHING ELSE (not a factual destination question — small talk, stated preferences, a \
   request for suggestions): return the DRAFT exactly as written, unchanged.

Keep the concierge's warm, concise tone."""


def get_destination_advisor_response(messages, draft):
    # The traveller's latest message is the last item in the conversation.
    # `messages` are OpenAI-style dicts: {"role": "user"/"assistant", "content": "..."}.
    question = messages[-1]["content"]

    # 1. Retrieve the most relevant guide chunks, join them into one CONTEXT block.
    docs = get_retriever().invoke(question)
    context = "\n\n".join(doc.page_content for doc in docs)

    # 2. The covered destinations, straight from the registry (single source of truth).
    covered = ", ".join(d.name for d in all_destinations()) # -> "Lisbon, Kyoto, Reykjavik, Barcelona, Bali, Rome"

    # 3. SYSTEM holds the rules; the human turn carries the actual values.
    system = SYSTEM.format(covered=covered)
    human = (
        f"CONTEXT (from our destination guides):\n{context}\n\n"
        f"DRAFT (the Trip Agent's reply):\n{draft}\n\n"
        f"Traveller's latest message:\n{question}"
    )

    # 4. One LLM call. The Destination Advisor never changes the action — it only ever
    #    runs inside `continue` — so it always returns ("continue", reply, meta). meta
    #    hands the raw retrieved Documents to the seam, which trims them for the trace.
    reply = llm.invoke([("system", system), ("human", human)]).content
    return ("continue", reply, {"chunks": docs, "model": llm.model_name})
