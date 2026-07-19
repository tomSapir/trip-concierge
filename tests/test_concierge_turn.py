"""Guards the backward-compat contract of ConciergeTurn (v2 step 2, sub-step 2a).

The eval harness tuple-unpacks the pipeline's return (`action, _reply = get_concierge_response(...)`),
so ConciergeTurn MUST keep unpacking to exactly (action, reply). Runs standalone, no OpenAI/API key:

    python tests/test_concierge_turn.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # for `app.*`

from app.concierge_turn import ConciergeTurn  # noqa: E402


def test_unpacks_to_action_reply():
    """`action, reply = ConciergeTurn(...)` must still yield exactly the two values."""
    turn = ConciergeTurn("book", "Trip booked!")
    action, reply = turn
    assert action == "book"
    assert reply == "Trip booked!"


def test_extra_fields_default_to_none():
    """packages and trace are optional — absent until the pipeline attaches them."""
    turn = ConciergeTurn("continue", "Which destination are you considering?")
    assert turn.packages is None
    assert turn.trace is None


if __name__ == "__main__":
    test_unpacks_to_action_reply()
    test_extra_fields_default_to_none()
    print("ok — ConciergeTurn unpacks to (action, reply) and its extra fields default to None")
