"""Streamlit chat UI for the Trip Concierge — the deploy entry point.

    streamlit run streamlit_app/streamlit_main.py

One turn per user message: the message list goes to get_concierge_response, which returns a
ConciergeTurn — action, reply, plus packages (rendered below the chat as bookable cards) and
trace (for the step-5 debug trail). A terminal action (book / abandon) locks the chat and
offers a reset; a card click books deterministically, no LLM involved.
"""
import sys
import pathlib
import time
from datetime import date

from dotenv import load_dotenv
import streamlit as st

# Put the project root on the path, then load env BEFORE importing the agents — they construct
# ChatOpenAI at import time and need OPENAI_API_KEY set. (On Streamlit Cloud it comes from secrets.)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
load_dotenv()

from app.main import get_concierge_response  # noqa: E402 — must follow load_dotenv() above
from app.modules.destination_registry import image_for  # noqa: E402 — same import-order rule
from starters import starter_prompts  # noqa: E402 — needs the project root on sys.path (above)

TERMINAL = {"book", "abandon"}
GREETING = "Hi! I'm your trip concierge ✈️ Where in the world are you dreaming of going?"
MAX_USER_MESSAGES = 20  # per-session cost ceiling for the public demo

st.set_page_config(page_title="Trip Concierge", page_icon="✈️")
st.title("✈️ Trip Concierge")
st.caption("Tell me your vibe, dates, and budget — I'll find real trip packages and book the one you pick.")

# Always-visible debug switch — deliberately left on the public deploy (the reasoning trail is
# the demo, not a leak). Read once per run; every trace expander below is gated on it.
DEBUG = st.sidebar.toggle(
    "🐞 Debug", value=False,
    help="Show the reasoning trail under each reply: the action the Trip Agent picked, the "
         "advisor that checked it, why it was demoted, and what the guides retrieved.")


def _reset():
    """Start a fresh conversation, seeded with the concierge's greeting."""
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]
    st.session_state.locked = None  # None | "book" | "abandon"
    st.session_state.offer = None   # packages from the latest fresh recommend, shown as cards
    st.session_state.booked = None  # the package committed via a card, for the rich confirmation


def _typewriter(text):
    """Yield the reply word-by-word so st.write_stream renders it as it types."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)


def _user_msg_count():
    """How many messages in the current session were sent by the traveller."""
    return sum(1 for m in st.session_state.messages if m["role"] == "user")


def _fmt_date(iso):
    """'2026-09-03' -> 'Sep 3, 2026'. Package rows arrive JSON-serialized, dates as ISO strings."""
    d = date.fromisoformat(str(iso))
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _book_package(pkg):
    """The single deterministic commit path for a card click — no LLM, no Booking Advisor:
    pressing the button on one specific package IS the unambiguous commitment."""
    st.session_state.booked = pkg
    st.session_state.offer = None
    st.session_state.locked = "book"


def _offer_cards():
    """Render the standing offer as package cards, three to a row. Re-emitted EVERY rerun —
    Streamlit wipes widgets each run, so the Book buttons must be redrawn to stay clickable."""
    offer = st.session_state.get("offer") or []
    for start in range(0, len(offer), 3):
        row = offer[start:start + 3]
        for col, pkg in zip(st.columns(len(row)), row):
            with col:
                img = image_for(pkg["destination"])
                if img:
                    st.image(str(img), width="stretch")
                st.markdown(f"**{pkg['destination']}** · {pkg['nights']} nights\n\n"
                            f"🛫 {_fmt_date(pkg['depart_date'])}\n\n"
                            f"🏨 {pkg['hotel_name']}\n\n"
                            f"**${pkg['total_price']}** total")
                st.button("Book this", key=f"book_{pkg['package_id']}", type="primary",
                          width="stretch", on_click=_book_package, args=(pkg,))


def _trace_expander(trace):
    """Render one turn's reasoning trail as a collapsed expander under its assistant message.

    `trace` is the dict app/main.py assembles per route (see its docstring). Always present:
    original_action, final_action, route. Present per outcome: `reason` (why an advisor demoted),
    `model`, and `chunks` (destination_advisor only — already reduced at the seam to
    {"source", "snippet"} dicts, never raw LangChain Documents).

    No-ops when the toggle is off or the message carries no trace (the seeded greeting doesn't).
    """
    if not DEBUG or not trace:
        return
    with st.expander("🐞 trace"):
        original, final = trace["original_action"], trace["final_action"]
        if original == final:
            st.markdown(f"**Action** · `{original}`")
        else:
            # The two differ exactly when an advisor demoted — the headline of the whole trail.
            st.markdown(f"**Action** · `{original}` → `{final}` — demoted")
        if trace.get("reason"):
            st.markdown(f"**Why** · {trace['reason']}")
        # No route means no advisor ran: `abandon` fires straight from the seam.
        st.markdown(f"**Route** · `{trace['route']}`" if trace.get("route")
                    else "**Route** · none — `abandon` is unguarded")
        chunks = trace.get("chunks")
        if chunks:
            st.markdown(f"**Retrieved** · {len(chunks)} guide chunks")
            for chunk in chunks:
                # metadata["source"] is the guide's path; the filename is the readable part.
                source = pathlib.Path(chunk["source"]).name if chunk.get("source") else "guide"
                st.markdown(f"- **{source}** — {chunk['snippet']}…")
        if trace.get("model"):
            st.markdown(f"**Model** · `{trace['model']}`")


def _starter_chips():
    """On a fresh conversation, offer clickable openers seeded from the registry so a chip
    can never name an out-of-set city. A click stages its prompt as the first user turn."""
    st.markdown("**New here? Pick a starting point — or just type below.**")
    starters = starter_prompts()
    for start in range(0, len(starters), 3):  # three chips per row
        row = starters[start:start + 3]
        for col, starter in zip(st.columns(len(row)), row):
            if col.button(starter.label, width="stretch", key=f"starter_{starter.destination}"):
                st.session_state.pending_prompt = starter.prompt
                st.rerun()


if "messages" not in st.session_state:
    _reset()

# Replay the conversation so far. Assistant messages carry the trace of the turn that produced
# them, so flipping the toggle reveals the trail for the WHOLE conversation, not just the last turn.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # .get(), not indexing: user messages and the seeded greeting carry no trace key.
        _trace_expander(msg.get("trace"))

if st.session_state.locked:
    # Terminal: show the outcome and a reset button instead of the chat input.
    if st.session_state.locked == "book":
        booked = st.session_state.get("booked")
        if booked:
            # Card-committed booking: full-width destination shot + the real numbers.
            img = image_for(booked["destination"])
            if img:
                st.image(str(img), width="stretch")
            st.success(f"{booked['destination']} is booked — depart {_fmt_date(booked['depart_date'])}, "
                       f"{booked['nights']} nights at {booked['hotel_name']}, "
                       f"${booked['total_price']} total. Bon voyage! 🎉")
        else:
            # Free-text booking went through the Booking Advisor; there's no specific
            # package object to show, so the confirmation stays generic.
            st.success("Trip booked — bon voyage! 🎉")
    else:
        st.info("Conversation closed — no booking made.")
    if st.button("Plan a New Trip", type="primary"):
        _reset()
        st.rerun()

elif _user_msg_count() >= MAX_USER_MESSAGES:
    # Per-session cost ceiling for the public demo — stop taking input, offer a reset.
    st.warning("Session limit reached for this demo. Start a fresh trip to keep chatting.")
    if st.button("Plan a New Trip", type="primary"):
        _reset()
        st.rerun()

else:
    # A fresh conversation shows clickable starters; skip them while a click is mid-flight.
    if _user_msg_count() == 0 and "pending_prompt" not in st.session_state:
        _starter_chips()

    # The turn's prompt is a staged starter click or freshly typed text. Call chat_input
    # unconditionally so the box stays visible even on a starter-driven turn.
    typed = st.chat_input("Type your message…")
    prompt = st.session_state.pop("pending_prompt", None) or typed
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking…"):
                    turn = get_concierge_response(st.session_state.messages)
                st.write_stream(_typewriter(turn.reply))
                # This turn isn't in session_state yet, so the replay loop above never saw it —
                # render its trace here or the newest turn would be the one you can't inspect.
                _trace_expander(turn.trace)
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.stop()  # leave the turn un-recorded so the user can retry

        # The stored message grows a "trace" key: what the pipeline did, kept for later replays.
        st.session_state.messages.append({"role": "assistant", "content": turn.reply,
                                          "trace": turn.trace})

        # A fresh recommend stages its rows as the standing offer (deduped by id — a compare
        # turn can return the same package twice); any other turn retires a stale offer.
        if turn.action == "recommend" and turn.packages:
            st.session_state.offer = list({p["package_id"]: p for p in turn.packages}.values())
        else:
            st.session_state.offer = None

        # A terminal action locks the chat; rerun so the input is replaced by the reset button.
        if turn.action in TERMINAL:
            st.session_state.locked = turn.action
            st.rerun()

    # The standing offer renders under the conversation every run — including this one, right
    # after a fresh recommend staged it above. Free-text booking stays available alongside.
    if st.session_state.get("offer"):
        _offer_cards()
