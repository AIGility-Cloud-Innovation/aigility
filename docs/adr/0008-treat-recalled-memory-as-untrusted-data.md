---
status: accepted
---

# Treat recalled memory as untrusted data

AIGility injects recalled memories into a dedicated context block with their source memory IDs and explicitly treats their contents as untrusted reference data. Instructions embedded in a memory cannot override system, developer, or current-user instructions; this preserves useful historical facts while limiting prompt-injection attacks stored through prior user input or model output.
