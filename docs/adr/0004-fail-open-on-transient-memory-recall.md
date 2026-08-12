---
status: accepted
---

# Fail open on transient memory recall failures

When a Memory-enabled Agent has a complete identity but TiMEM recall fails because of a timeout, rate limit, or server error, AIGility continues the turn without recalled memory and reports `memory_recall=degraded`. A legitimate search abstention reports `ok_empty` instead, so availability is preserved without hiding provider failures as empty results; identity, authentication, entitlement, and validation failures are outside this transient-failure policy.
