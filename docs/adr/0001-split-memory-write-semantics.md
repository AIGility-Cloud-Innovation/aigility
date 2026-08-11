---
status: accepted
---

# Split completed and submitted memory writes

TiMEM Cloud accepts conversation writes asynchronously, while its high-level SDK `add` method waits for generation to complete. AIGility therefore keeps `Memory.add` as the completed-write convenience API and adds `Memory.submit` plus `Memory.wait` for explicit task control; Chat and ChatFlow use `submit` after a completed assistant response and block only until the cloud accepts the task. After acceptance, they record and expose the `task_id` but do not start unmanaged background polling; completion is observed only through an explicit `wait` or configured task observer. This preserves SDK expectations for direct callers without adding generation latency or event-loop-owned background work to the visible chat response path.
