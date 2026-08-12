# AIGility Domain Context

AIGility provides agent application building blocks. This context fixes the language used where conversation runtime, knowledge retrieval, and cross-session memory meet.

## Agent Context

**Conversation State**:
The messages and checkpointed runtime state of one active conversation.
_Avoid_: Memory, long-term memory

**Knowledge**:
An uploaded or indexed document corpus retrieved through RAG.
_Avoid_: Memory, user memory

## Long-term Memory

**Long-term Memory**:
Cross-session information about a memory subject and memory agent, persisted and retrieved through a memory provider. It excludes Conversation State, Knowledge, and rule learning.
_Avoid_: Chat history, RAG memory

**Memory Subject**:
The business end user whose memories are isolated by `user_id`. The business invocation supplies this identity; the Long-term Memory layer only validates it.
_Avoid_: Account, tenant, API-key owner

**Memory Agent**:
The stable AI role whose memories are isolated with a Memory Subject. Agent configuration supplies this identity, and a provider adapter may map it to `character_id`, `expert_id`, or `agent_id`.
_Avoid_: Character, expert outside provider adapters

**Conversation Session**:
The stable conversation identity supplied as `session_id` when generating memories. The conversation runtime owns it; the Long-term Memory layer must not default, synthesize, or derive it from a Memory Subject.
_Avoid_: User session, generated user hash

**Memory Identity**:
The required combination of Memory Subject, Memory Agent, and Conversation Session used by a Memory-enabled Agent. Its three values come from the business invocation, Agent configuration, and conversation runtime respectively; an incomplete identity fails before model execution rather than silently disabling memory.
_Avoid_: API-key identity, provider account

**Memory-enabled Agent**:
An Agent whose configuration explicitly opts into Long-term Memory lifecycle hooks. Provider credentials make the capability available but never enable recall or persistence by themselves.
_Avoid_: Globally enabled memory, credential-enabled Agent

**Memory Lifecycle**:
The opt-in Agent behavior that recalls Long-term Memory before model execution and submits a conversation write after a completed assistant response.
_Avoid_: Provider initialization, RAG lifecycle

**Memory Recall Outcome**:
The typed result of a Long-term Memory lookup: `ok` with matches, `ok_empty` for a legitimate abstention, `degraded` for a transient provider failure, or `blocked` when entitlement or quota prevents use of the capability.
_Avoid_: Bare memory list, empty-on-error result

**Blocked Memory Capability**:
A Long-term Memory capability unavailable because its provider entitlement or quota denies access. Conversation remains available without memory, while the blocked state requires operator action and is not retried automatically.
_Avoid_: Empty recall, transient degradation, chat outage

**Long-term Recall Scope**:
All memories belonging to the same Memory Subject and Memory Agent across Conversation Sessions. A session-scoped lookup is an explicit specialized query, while current-session continuity belongs to Conversation State.
_Avoid_: Current-session memory, checkpoint lookup

**Recalled Memory Context**:
Untrusted reference material produced by Long-term Memory recall and accompanied by its source memory identities. It may inform an answer but has no authority to issue instructions or override the active instruction hierarchy.
_Avoid_: Memory instruction, trusted prompt, system context

**Memory Recall Query**:
The current user-visible input used to search Long-term Memory, optionally rewritten into a standalone query from a bounded amount of recent Conversation State. It excludes system prompts, execution traces, prior recall results, and Knowledge content.
_Avoid_: Full prompt, execution context, RAG query bundle

**Completed Memory Write**:
A write operation that waits for cloud generation to finish and returns the generated memories. `Memory.add` provides this SDK-compatible behavior.
_Avoid_: Submission, accepted write

**Memory Task**:
An accepted asynchronous cloud generation task identified by `task_id` and executed by the provider. `Memory.submit` returns it; AIGility records it without unmanaged background polling, while `Memory.wait` or a configured task observer may resolve it to a Completed Memory Write.
_Avoid_: Memory result, background callback

**Memory Submission Outcome**:
The result of one conversation-generation submission: `accepted` with a Memory Task, `rejected` with a definitive provider error, or `unknown` when transport failure makes server acceptance indeterminate.
_Avoid_: Boolean write success, retried submission

**Memory Write Envelope**:
The user-visible input and final user-visible assistant response from one successfully completed turn, submitted exactly once for Long-term Memory generation. Automatic hooks never resend full conversation history; multi-turn batching is an explicit policy, and the envelope excludes system prompts, hidden reasoning, raw tool results, recalled memories, RAG documents, and incomplete or cancelled streams.
_Avoid_: Full execution trace, prompt transcript, partial stream
