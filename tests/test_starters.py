"""Guard the same-set invariant for the v2 starter chips (PLAN-v2.md idea 3).

Every starter chip must be derived from the destination registry, so a chip can never
advertise an out-of-set city. Runs standalone (no pytest needed):

    python tests/test_starters.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))                     # for `app.*`
sys.path.insert(0, str(ROOT / "streamlit_app"))   # for `starters`

from app.modules.destination_registry import all_destinations  # noqa: E402
from starters import starter_prompts  # noqa: E402


def test_starters_only_name_in_set_cities():
    """Exactly one chip per registry destination, each naming only its in-set city."""
    names = {d.name for d in all_destinations()}
    starters = starter_prompts()

    # One chip per destination — no extras, none missing.
    referenced = {s.destination for s in starters}
    assert referenced == names, f"chip destinations {referenced} != registry {names}"

    # A chip's own destination is the only in-set city it may name; no other city leaks in.
    for s in starters:
        named_in_set = {n for n in names if n in s.prompt or n in s.label}
        assert named_in_set == {s.destination}, (
            f"chip {s.destination!r} references unexpected in-set cities: {named_in_set}"
        )


if __name__ == "__main__":
    test_starters_only_name_in_set_cities()
    print("ok — every starter chip names only its in-set registry city")
