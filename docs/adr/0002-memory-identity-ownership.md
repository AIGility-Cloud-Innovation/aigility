---
status: accepted
---

# Keep memory identity ownership outside the memory layer

AIGility requires the business invocation to provide `user_id`, Agent configuration to provide a stable `agent_id`, and the conversation runtime to provide `session_id`; the Long-term Memory layer validates and forwards these values but never supplies defaults or derives one identity from another. A Memory-enabled Agent with an incomplete identity raises `MemoryIdentityError` before model execution instead of silently skipping memory. This gives up convenient fallback identities and permissive degradation to prevent memories from different users, agents, or conversations being silently merged, while the TiMEM API key remains a provider account and billing credential rather than a business memory identity.
