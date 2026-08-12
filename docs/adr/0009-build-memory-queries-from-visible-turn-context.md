---
status: accepted
---

# Build memory queries from visible turn context

AIGility automatic recall uses the current user-visible input as its default query. An explicitly configured Query Builder may use a bounded window of recent Conversation State to resolve incomplete references into a standalone query, but it cannot consume system prompts, hidden execution traces, recalled memories, or RAG content; this improves follow-up recall without leaking internal instructions or creating retrieval feedback loops.
