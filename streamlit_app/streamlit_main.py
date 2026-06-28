"""Streamlit chat UI for the Trip Concierge — the deploy entry point.

    streamlit run streamlit_app/streamlit_main.py

One turn per user message: the message list goes to get_concierge_response, which returns
(action, reply). A terminal action (book / abandon) locks the chat and offers a reset.
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


def _get_secret(name):
    """Return a configured secret, or None when there's no secrets file (local/offline dev)."""
    try:
        return st.secrets[name]
    except Exception:
        return None


def _check_password():
    """Gate the public app behind APP_PASSWORD. No-op when the secret isn't set (local dev)."""
    password = _get_secret("APP_PASSWORD")
    if not password or st.session_state.get("authed"):
        return
    entered = st.text_input("Enter password to continue", type="password")
    if not entered:
        st.stop()  # waiting for input — nothing below renders yet
    if entered == password:
        st.session_state.authed = True
        st.rerun()  # re-run so the password box is gone and the chat renders
    st.error("Incorrect password.")
    st.stop()


def _user_msg_count():
    """How many messages in the current session were sent by the traveller."""
    return sum(1 for m in st.session_state.messages if m["role"] == "user")


_check_password()  # gate first; everything below only runs once authed (or when no password is set)

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

elif prompt := st.chat_input("Type your message…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking…"):
                action, reply = get_concierge_response(st.session_state.messages)
            st.write_stream(_typewriter(reply))
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()  # leave the turn un-recorded so the user can retry

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # A terminal action locks the chat; rerun so the input is replaced by the reset button.
    if action in TERMINAL:
        st.session_state.locked = action
        st.rerun()
