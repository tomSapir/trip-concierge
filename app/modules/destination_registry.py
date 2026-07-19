from dataclasses import dataclass
from pathlib import Path

# Anchored to this file, not the cwd — callers differ (run_evals chdirs to the repo
# root, Streamlit Cloud runs from wherever it likes).
_IMG_DIR = Path(__file__).resolve().parents[2] / "data" / "destinations" / "img"


@dataclass(frozen=True)
class Destination:
    name: str
    vibe: list[str]
    image: str  # bare filename inside _IMG_DIR — image_for() owns the directory


DESTINATIONS = [
    Destination("Lisbon", ["coastal", "foodie", "history"], "lisbon.jpg"),
    Destination("Kyoto", ["culture", "history", "scenic"], "kyoto.jpg"),
    Destination("Reykjavik", ["adventure", "nature"], "reykjavik.jpg"),
    Destination("Barcelona", ["city", "beach", "nightlife"], "barcelona.jpg"),
    Destination("Bali", ["beach", "relax", "nature"], "bali.jpg"),
    Destination("Rome", ["history", "culture", "foodie"], "rome.jpg"),
]


def all_destinations():
    """Return the full list of destinations."""
    return DESTINATIONS


def image_for(name):
    """Absolute Path to the destination's bundled image, or None if unknown/missing.

    Graceful fallback is the contract: the UI skips the image and renders on, so an
    out-of-set name or an absent file returns None — this never raises.
    """
    for dest in DESTINATIONS:
        if dest.name.lower() == str(name).lower():
            path = _IMG_DIR / dest.image
            return path if path.is_file() else None
    return None
