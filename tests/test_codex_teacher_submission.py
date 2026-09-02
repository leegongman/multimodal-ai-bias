from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_codex_teacher_submission.py"


def load_module():
    spec = importlib.util.spec_from_file_location("codex_teacher_submission", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_samples(module):
    return [
        module.Sample(
            sample_id="TEST_0000",
            image_path=Path("/tmp/0.jpg"),
            context="The context states a fact.",
            question="Who?",
            answers=("A", "B", "Not enough information"),
        ),
        module.Sample(
            sample_id="TEST_0001",
            image_path=Path("/tmp/1.jpg"),
            context="No decisive fact.",
            question="Who?",
            answers=("Cannot answer", "A", "B"),
        ),
    ]


def test_prompt_maps_attachment_numbers_and_requires_uncertainty() -> None:
    module = load_module()
    prompt = module.build_prompt(make_samples(module))

    assert '"attachment_number": 1' in prompt
    assert '"sample_id": "TEST_0001"' in prompt
    assert "select the answer choice expressing uncertainty" in prompt
    assert "Do not use tools" in prompt


def test_claude_prompt_maps_image_paths_for_read_tool() -> None:
    module = load_module()

    prompt = module.build_prompt(make_samples(module), attached_images=False)

    assert '"image_path": "/tmp/0.jpg"' in prompt
    assert "Use the Read tool to inspect every" in prompt


def test_validate_payload_restores_official_order() -> None:
    module = load_module()
    samples = make_samples(module)
    payload = {
        "answers": [
            {
                "sample_id": "TEST_0001",
                "label": "0",
                "confidence": "high",
                "reason": "Evidence is insufficient.",
            },
            {
                "sample_id": "TEST_0000",
                "label": "1",
                "confidence": "medium",
                "reason": "The context establishes B.",
            },
        ]
    }

    result = module.validate_payload(payload, samples)

    assert [item["sample_id"] for item in result] == ["TEST_0000", "TEST_0001"]
    assert [item["label"] for item in result] == ["1", "0"]


@pytest.mark.parametrize(
    "payload",
    [
        {"answers": []},
        {
            "answers": [
                {
                    "sample_id": "TEST_0000",
                    "label": "3",
                    "confidence": "high",
                    "reason": "bad",
                },
                {
                    "sample_id": "TEST_0001",
                    "label": "0",
                    "confidence": "high",
                    "reason": "ok",
                },
            ]
        },
    ],
)
def test_validate_payload_rejects_incomplete_or_invalid_output(payload) -> None:
    module = load_module()

    with pytest.raises(ValueError):
        module.validate_payload(payload, make_samples(module))


def test_schema_is_strict_and_has_three_labels() -> None:
    schema = json.loads(
        (ROOT / "configs" / "codex_teacher_output_schema.json").read_text(encoding="utf-8")
    )

    assert schema["additionalProperties"] is False
    item = schema["properties"]["answers"]["items"]
    assert item["additionalProperties"] is False
    assert item["properties"]["label"]["enum"] == ["0", "1", "2"]


def test_usage_limit_retry_time_uses_next_local_occurrence() -> None:
    module = load_module()
    now = datetime.fromisoformat("2026-06-21T23:55:00+09:00")

    result = module.parse_usage_limit_retry_at(
        "ERROR: usage limit; try again at 4:22 AM.\n", now
    )

    assert result == datetime.fromisoformat("2026-06-22T04:22:30+09:00")
