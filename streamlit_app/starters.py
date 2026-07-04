"""Starter chips for the fresh-conversation screen (v2 idea 3).

One opener per registry destination. Because every chip is derived from
`all_destinations()` — its label and injected prompt only ever interpolate a real
registry name — a chip is structurally incapable of naming an out-of-set city, so the
same-set invariant holds for free (no curation, no drift). See PLAN-v2.md idea 3.

Kept Streamlit-free on purpose: the UI imports `starter_prompts()` to render the chips,
and tests import it to assert the invariant, without pulling in Streamlit's page setup.
"""
from dataclasses import dataclass

from app.modules.destination_registry import all_destinations


@dataclass(frozen=True)
class Starter:
    label: str        # text shown on the chip button
    prompt: str       # first user message a click injects into the conversation
    destination: str  # the registry name this chip was derived from


def starter_prompts():
    """Build one starter chip per registry destination (label = name + top two vibes)."""
    return [
        Starter(
            label=f"{d.name} · {', '.join(d.vibe[:2])}",
            prompt=f"I'd like to plan a trip to {d.name}.",
            destination=d.name,
        )
        for d in all_destinations()
    ]
