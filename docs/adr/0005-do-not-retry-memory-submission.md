---
status: accepted
---

# Do not retry memory submissions without idempotency

Until TiMEM Cloud accepts a client idempotency key, AIGility sends each conversation-generation `Memory.submit` request at most once. A network timeout or disconnect before the HTTP 202 response produces `memory_write=unknown` and is not retried automatically, because the server may already have accepted a task and retrying could create duplicate memories and charges; idempotent searches and task-status polls may still use bounded retries.
