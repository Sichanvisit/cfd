from __future__ import annotations

from typing import Any

from backend.services.session_direction_annotation_contract import (
    ANNOTATION_CONFIDENCE_ENUM_V1,
    CONTINUATION_ANNOTATION_ENUM_V1,
    CONTINUATION_PHASE_V1_ENUM,
    DIRECTION_ANNOTATION_ENUM_V1,
)


SHOULD_HAVE_DONE_CONTRACT_VERSION = "should_have_done_contract_v1"


def build_should_have_done_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": SHOULD_HAVE_DONE_CONTRACT_VERSION,
        "status": "READY",
        "description": (
            "Read-only should-have-done label contract. "
            "Used to accumulate expected direction/continuation/phase/surface annotations "
            "before any execution or state25 influence expansion."
        ),
        "fields": [
            {
                "field": "expected_direction",
                "enum": list(DIRECTION_ANNOTATION_ENUM_V1),
                "required": True,
            },
            {
                "field": "expected_continuation",
                "enum": list(CONTINUATION_ANNOTATION_ENUM_V1),
                "required": True,
            },
            {
                "field": "expected_phase_v1",
                "enum": list(CONTINUATION_PHASE_V1_ENUM),
                "required": True,
            },
            {
                "field": "expected_surface",
                "required": True,
                "notes": "Canonical expected chart/runtime surface such as BUY_WATCH or SELL_WATCH.",
            },
            {
                "field": "annotation_confidence_v1",
                "enum": list(ANNOTATION_CONFIDENCE_ENUM_V1),
                "required": True,
            },
            {
                "field": "candidate_source_v1",
                "required": True,
                "notes": "AUTO or MANUAL candidate source family.",
            },
            {
                "field": "operator_note",
                "required": False,
            },
        ],
        "quality_policy": {
            "manual_high_directly_usable": True,
            "auto_high_directly_usable": True,
            "auto_medium_requires_accumulation": True,
            "auto_low_reference_only": True,
        },
        "execution_rules": {
            "execution_influence_allowed": False,
            "state25_influence_allowed": False,
            "forecast_bias_influence_allowed": False,
        },
    }
