---
status: accepted
---

# Limit automatic memory writes to visible completed turns

AIGility automatic memory hooks submit exactly one envelope per successfully completed turn containing only the current user-visible input and final assistant response; they never resend full conversation history, while multi-turn batching requires an explicit policy. They exclude system prompts, hidden reasoning, raw tool payloads, recalled memories, and RAG documents, and they submit nothing for cancelled or failed streams; this prevents duplicate ingestion, local-buffer dependence, internal-data leakage, retrieval feedback loops, and incomplete model output from becoming durable memory, while explicit Memory APIs remain available for caller-controlled structured writes.
