from __future__ import annotations

from typing import Any


SESSION_DIRECTION_ANNOTATION_CONTRACT_VERSION = "session_direction_annotation_contract_v1"
R2_MINIMUM_ANNOTATION_STATUS = "READY"
R2_SESSION_BIAS_EXPANSION_STATUS = "HOLD"

DIRECTION_ANNOTATION_ENUM_V1 = ("UP", "DOWN", "NEUTRAL")
CONTINUATION_ANNOTATION_ENUM_V1 = ("CONTINUING", "NON_CONTINUING", "UNCLEAR")
CONTINUATION_PHASE_V1_ENUM = ("CONTINUATION", "BOUNDARY", "REVERSAL")
ANNOTATION_CONFIDENCE_ENUM_V1 = ("MANUAL_HIGH", "AUTO_HIGH", "AUTO_MEDIUM", "AUTO_LOW")


def build_session_direction_annotation_contract_v1() -> dict[str, Any]:
    return {
        "contract_version": SESSION_DIRECTION_ANNOTATION_CONTRACT_VERSION,
        "status": R2_MINIMUM_ANNOTATION_STATUS,
        "session_bias_expansion_status": R2_SESSION_BIAS_EXPANSION_STATUS,
        "description": (
            "Minimal read-only annotation contract for direction/continuation/phase. "
            "Session is a context or bias layer only and does not directly decide BUY/SELL."
        ),
        "fields": [
            {
                "field": "direction_annotation",
                "enum": list(DIRECTION_ANNOTATION_ENUM_V1),
                "required": True,
                "notes": "Directional reading only; does not directly trigger execution.",
            },
            {
                "field": "continuation_annotation",
                "enum": list(CONTINUATION_ANNOTATION_ENUM_V1),
                "required": True,
                "notes": "Separates direction from continuation quality.",
            },
            {
                "field": "continuation_phase_v1",
                "enum": list(CONTINUATION_PHASE_V1_ENUM),
                "required": True,
                "notes": "Three-phase v1 contract kept intentionally coarse.",
            },
            {
                "field": "session_bucket_v1",
                "required": True,
                "notes": "Read-only context field from session_bucket_helper_v1.",
            },
            {
                "field": "annotation_confidence_v1",
                "enum": list(ANNOTATION_CONFIDENCE_ENUM_V1),
                "required": True,
                "notes": "Controls should-have-done data quality gating.",
            },
        ],
        "r1_gate": {
            "minimum_status": "READY",
            "requires_session_split_summary": True,
            "allows_asia_sample_gap": True,
            "blocks_session_weighting_expansion": True,
        },
        "execution_rules": {
            "session_direct_buy_sell_allowed": False,
            "state25_bias_expansion_allowed": False,
            "guard_promotion_bias_expansion_allowed": False,
        },
    }
