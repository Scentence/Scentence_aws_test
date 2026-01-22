"""Prompt placeholders for potential LLM-guided layering flows.

Until conversational flows are required, this module simply documents
where natural-language instructions would be stored.
"""

from __future__ import annotations

DEFAULT_EXPLANATION_TEMPLATE = (
    "Combine {base} with {candidate} to emphasize {highlights}."
    " Harmony: {harmony:.2f}, Bridge: {bridge:.2f}, Target: {target:.2f}."
)

USER_PREFERENCE_PROMPT = (
    "You are a fragrance assistant. Analyze the user input and return JSON. "
    "JSON keys: keywords (list of lowercase intent words), intensity (0 to 1). "
    "If unsure, return empty keywords and intensity 0.5. "
    "User input: {user_input}"
)
