# Trip Concierge

A multi-agent travel concierge: a chat assistant that learns a traveller's
preferences, answers destination questions, proposes concrete trip packages
within budget, and finalizes the one the traveller commits to.

## Language

**Concierge**:
The whole assistant as the traveller experiences it — the **Trip Agent** and its
three **Advisors** working together. "The concierge says…" means the app's reply,
regardless of which agent produced it.

**Trip Agent**:
The orchestrator. Each turn it reads the conversation and chooses exactly one
**Action**, then drafts a reply that the matching **Advisor** validates or enriches.

**Action**:
The Trip Agent's per-turn decision. Exactly one of: **Continue**, **Recommend**,
**Book**, or **Abandon**.

**Continue**:
Keep the conversation going — gather more **Preferences**, or answer a
destination question. The non-terminal default.

**Recommend**:
Propose a shortlist of concrete **Packages** — the best available within budget,
each with real departure dates and a total price — for an already-chosen
destination. This is the act of choosing *which package*, not *which destination*.
_Avoid_: reading "recommend" as proposing a place to visit. Proposing a destination
from a vibe is **Suggest**, part of **Continue** — not Recommend.

**Suggest** (a destination):
During **Continue**, the Trip Agent floats candidate destinations that fit the
traveller's vibe and budget ("for a relaxing beach trip, Bali or Barcelona could
fit"). Conversational only — it never queries the package data. Distinct from
**Recommend**, which proposes **Packages** for a destination already settled on.

**Book**:
The traveller has committed to one specific **Package** ("book option 2"). Terminal
and successful — the trip is finalized.
_Avoid_: using "book" for the case where the traveller walks away without choosing
a package. That is **Abandon**, a separate action.

**Abandon**:
The traveller ends the conversation without booking ("never mind, not this year").
Terminal and unsuccessful. Fires directly from the Trip Agent — unguarded, because a
misread is cheap and self-correcting (the traveller simply keeps typing).

**Destination registry**:
The canonical list of destinations the Concierge supports, each with a name and vibe
tags. Single source of truth: the package data, the guide corpus, and the Trip Agent's
**Suggest**ions all derive from it — so every destination the traveller can ask about,
be suggested, or **Book** is the same set.

**Package**:
A bookable bundle — a flight plus a hotel stay for one destination, with a
departure date, a number of nights, and a single total price in USD covering one
traveller (flight + hotel; no per-person/party-size split in v1). The unit the
Budget Advisor proposes and the traveller Books. Fits a budget when its total
price is at or below the budget the traveller stated.

**Preference**:
Something the traveller wants that narrows the search — destination, travel dates,
budget, and vibe (e.g. "relaxing", "foodie", "adventure").

**Destination Advisor**:
Specialist that answers factual questions about places (climate, best season,
attractions, food, visas/safety), grounded in a corpus of destination guides.
Validates/enriches a **Continue**.

**Budget Advisor**:
Specialist that, on a **Recommend**, finds the best available **Packages** within
budget and rewrites the reply with concrete dates and prices. Has veto power: if no
destination has been named yet, it demotes the turn back to **Continue**. Budget is
optional — with no budget stated, it proposes the cheapest available packages.

**Booking Advisor**:
Specialist that guards **Book**. Confirms the traveller has genuinely committed to
a specific **Package** rather than merely musing ("option 2 looks tempting…"). If
not a real commitment, it demotes the turn back to **Continue**.

## Flagged ambiguities

_(none open)_
