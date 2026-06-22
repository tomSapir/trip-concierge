---
status: accepted
---

# Destination suggestion in v1: full prompt list behind a swappable seam

When the traveller gives a vibe but no destination, the Trip Agent suggests cities.
To guarantee it only ever suggests destinations we actually cover, **v1 injects the
entire destination list (name + vibe tags) into the Trip Agent's prompt** instead of
using semantic retrieval. The list comes from a single **destination registry** (also
read by the package seeder and the guide set), and the "candidate destinations for a
vibe" lookup sits behind **one function** so it can later return a retrieval top-k
instead of the full list. With ~6 fixed destinations a prompt list is the cheapest
reliable way to keep suggestions in-set; retrieval would be over-engineering at this
size.

## Considered options

- **Full list in the prompt (chosen)** — simple, deterministic, cannot suggest an
  out-of-set city. Does not scale past a few dozen destinations.
- **Retrieval over a destination index** — scales to any catalog and stays in-set,
  but adds machinery not justified for 6 cities. This is the planned vN path.
- **Trip Agent suggests from general world-knowledge** — rejected: it would suggest
  destinations we have no guides or packages for, forcing embarrassing "I can't
  actually do that" backpedals after the traveller gets excited.

## Consequences

- The destination registry is the single source of truth, so the same-set invariant
  (every destination the traveller can ask about, be suggested, or book is the same
  set) holds by construction.
- Growing the catalog past the point where a prompt list is practical means swapping
  the candidate-destinations function from "return all" to "return retrieval top-k" —
  a localized change. The Trip Agent prompt and the rest of the pipeline are
  unaffected.
