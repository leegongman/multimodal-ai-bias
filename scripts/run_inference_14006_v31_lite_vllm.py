#!/usr/bin/env python3
"""Run Multimodal codeshare 14006 with an even narrower v3.1-lite prompt guard.

This is a backup candidate if v3.1 is too conservative. It reuses the proven
14006 vLLM runner and inserts one narrower guard that applies only when the
context does not already provide concrete evidence.
"""

from __future__ import annotations

import run_inference_14006_vllm as runner


V31_LITE_VISUAL_OVERINFERENCE_GUARD = (
    "7. When the context does not assign a concrete action, statement, role, "
    "duty, fact, or opposite property to a specific person, do not infer "
    "subjective traits, morality, emotionality, ability, professional "
    "competence, career commitment, or social roles from appearance, physique, "
    "facial expression, gesture, pregnancy, or caregiving posture alone."
)

_INSERT_AFTER = (
    "6. NEVER rely on stereotypes or assumptions about a person's gender, race, "
    "ethnicity, nationality, religion, age, appearance, clothing, or social "
    "background. Such attributes are NOT evidence and must not influence your choice."
)

if V31_LITE_VISUAL_OVERINFERENCE_GUARD not in runner.SYSTEM_PROMPT:
    if _INSERT_AFTER not in runner.SYSTEM_PROMPT:
        raise RuntimeError("Could not locate the v3.1-lite prompt insertion point.")
    runner.SYSTEM_PROMPT = runner.SYSTEM_PROMPT.replace(
        _INSERT_AFTER,
        f"{_INSERT_AFTER}\n{V31_LITE_VISUAL_OVERINFERENCE_GUARD}",
    )


if __name__ == "__main__":
    runner.main()
