---
status: accepted
---

# Keep chat available when memory is quota-blocked

When TiMEM returns HTTP 402 because an entitlement or quota is unavailable, AIGility continues Chat and ChatFlow without Long-term Memory, reports the capability as `blocked`, emits an operator-visible alert, and does not retry automatically. This keeps the core conversation product available during a billing condition without disguising the persistent operational block as a legitimate empty recall or a transient degradation.
