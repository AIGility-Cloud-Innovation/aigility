---
status: accepted
---

# Require explicit per-Agent memory enablement

AIGility enables Long-term Memory lifecycle hooks only when an Agent explicitly opts in; the presence of `TIMEM_API_KEY` or another provider credential only makes the provider available and never triggers recall or persistence. This adds deliberate configuration but prevents unexpected storage, privacy exposure, and billing for Agents that were not designed to retain user information, and a disabled Agent performs no TiMEM calls.
