from dataclasses import dataclass


@dataclass(frozen=True)
class Destination:
    name: str
    vibe: list[str]


DESTINATIONS = [
    Destination("Lisbon", ["coastal", "foodie", "history"]),
    Destination("Kyoto", ["culture", "history", "scenic"]),
    Destination("Reykjavik", ["adventure", "nature"]),
    Destination("Barcelona", ["city", "beach", "nightlife"]),
    Destination("Bali", ["beach", "relax", "nature"]),
    Destination("Rome", ["history", "culture", "foodie"]),
]


def all_destinations():
    """Return the full list of destinations."""
    return DESTINATIONS
