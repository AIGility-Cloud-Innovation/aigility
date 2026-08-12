---
status: accepted
---

# Recall long-term memory across sessions by default

AIGility automatic recall searches the same `user_id + agent_id` across Conversation Sessions and does not apply the current `session_id` as a default filter. Current-session continuity remains the responsibility of Conversation State/Checkpoint, while session-scoped memory search is an explicit specialized option; this preserves the cross-session purpose of Long-term Memory instead of turning it into a second chat-history store.
