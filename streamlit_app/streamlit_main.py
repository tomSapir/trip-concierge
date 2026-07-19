"""Streamlit chat UI for the Trip Concierge — the deploy entry point.

    streamlit run streamlit_app/streamlit_main.py

One turn per user message: the message list goes to get_concierge_response, which returns a
ConciergeTurn — action, reply, and optional packages/trace for the later UI steps. A terminal
action (book / abandon) locks the chat and offers a reset.
"""
import sys
import pathlib
import time

from dotenv import load_dotenv
import streamlit as st

# Put the project root on the path, then load env BEFORE importing the agents — they construct
# ChatOpenAI at import time and need OPENAI_API_KEY set. (On Streamlit Cloud it comes from secrets.)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
load_dotenv()

from app.main import get_concierge_response  # noqa: E402 — must follow load_dotenv() above
from starters import starter_prompts  # noqa: E402 — needs the project root on sys.path (above)

TERMINAL = {"book", "abandon"}
GREETING = "Hi! I'm your trip concierge ✈️ Where in the world are you dreaming of going?"
MAX_USER_MESSAGES = 20  # per-session cost ceiling for the public demo

st.set_page_config(page_title="Trip Concierge", page_icon="✈️")
st.title("✈️ Trip Concierge")
st.caption("Tell me your vibe, dates, and budget — I'll find real trip packages and book the one you pick.")


def _reset():
    """Start a fresh conversation, seeded with the concierge's greeting."""
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]
    st.session_state.locked = None  # None | "book" | "abandon"


def _typewriter(text):
    """Yield the reply word-by-word so st.write_stream renders it as it types."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)


def _user_msg_count():
    """How many messages in the current session were sent by the traveller."""
    return sum(1 for m in st.session_state.messages if m["role"] == "user")


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

# Replay the conversation so far.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.locked:
    # Terminal: show the outcome and a reset button instead of the chat input.
    if st.session_state.locked == "book":
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
                    # Hold the whole ConciergeTurn — steps 4/5 will read .packages / .trace off it.
                    turn = get_concierge_response(st.session_state.messages)
                st.write_stream(_typewriter(turn.reply))
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.stop()  # leave the turn un-recorded so the user can retry

        st.session_state.messages.append({"role": "assistant", "content": turn.reply})

        # A terminal action locks the chat; rerun so the input is replaced by the reset button.
        if turn.action in TERMINAL:
            st.session_state.locked = turn.action
            st.rerun()
