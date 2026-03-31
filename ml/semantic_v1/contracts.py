from __future__ import annotations

from dataclasses import dataclass

from ml.semantic_v1.feature_packs import (
    SEMANTIC_FEATURE_CONTRACT_VERSION,
    SEMANTIC_INPUT_PACKS,
    SUPPORT_PACKS,
    feature_pack_rows,
)


SEMANTIC_TARGET_CONTRACT_VERSION = "semantic_target_contract_v1"
RULE_MODEL_OWNER_TABLE_VERSION = "rule_owner_vs_model_owner_table_v1"


@dataclass(frozen=True)
class TargetFamily:
    key: str
    label: str
    description: str


MODEL_TARGET_FAMILIES: tuple[TargetFamily, ...] = (
    TargetFamily(
        key="timing_now_vs_wait",
        label="timing now vs wait",
        description="지금 진입할지 잠시 더 기다릴지를 판단하는 target family",
    ),
    TargetFamily(
        key="entry_quality",
        label="entry quality",
        description="현재 semantic setup의 진입 품질을 점수화하는 target family",
    ),
    TargetFamily(
        key="exit_management",
        label="exit management",
        description="보유, 청산, giveback 관리 품질을 판단하는 target family",
    ),
)

RULE_OWNER_FIELDS: tuple[str, ...] = (
    "side",
    "entry_setup_id",
    "management_profile_id",
    "invalidation_id",
    "hard_guard",
    "kill_switch",
)

MODEL_OWNER_FIELDS: tuple[str, ...] = (
    "timing_now_vs_wait",
    "entry_quality",
    "exit_management",
    "meta_calibration",
    "bounded_threshold_adjustment",
    "bounded_wait_adjustment",
    "bounded_penalty_adjustment",
)

rule_owner_vs_model_owner_table: tuple[dict[str, str], ...] = (
    {
        "domain": "rule_owner",
        "field": "side",
        "description": "매수 or 매도 방향 결정은 계속 규칙 엔진이 owner로 가진다.",
    },
    {
        "domain": "rule_owner",
        "field": "entry_setup_id",
        "description": "셋업 identity는 semantic 규칙 엔진이 고정한다.",
    },
    {
        "domain": "rule_owner",
        "field": "management_profile_id",
        "description": "관리 프로필 선택은 모델이 직접 바꾸지 않는다.",
    },
    {
        "domain": "rule_owner",
        "field": "invalidation_id",
        "description": "무효화 기준은 규칙 엔진이 owner로 유지한다.",
    },
    {
        "domain": "rule_owner",
        "field": "hard_guard",
        "description": "하드 가드와 킬 스위치는 규칙 엔진 and 운영 안전장치가 owner다.",
    },
    {
        "domain": "rule_owner",
        "field": "kill_switch",
        "description": "긴급 비활성화는 언제나 모델 밖에서 수행한다.",
    },
    {
        "domain": "model_owner",
        "field": "timing_now_vs_wait",
        "description": "새 ML이 먼저 맡을 핵심 target family다.",
    },
    {
        "domain": "model_owner",
        "field": "entry_quality",
        "description": "semantic setup의 품질 보정은 모델이 맡는다.",
    },
    {
        "domain": "model_owner",
        "field": "exit_management",
        "description": "보유 or 청산 품질과 giveback 관리 보정은 모델이 맡는다.",
    },
    {
        "domain": "model_owner",
        "field": "meta_calibration",
        "description": "심볼 and regime and session 보정은 bounded 방식으로 허용한다.",
    },
    {
        "domain": "model_owner",
        "field": "bounded_threshold_adjustment",
        "description": "entry threshold는 제한된 범위에서만 조정한다.",
    },
    {
        "domain": "model_owner",
        "field": "bounded_wait_adjustment",
        "description": "wait 강도는 제한된 범위에서만 조정한다.",
    },
    {
        "domain": "model_owner",
        "field": "bounded_penalty_adjustment",
        "description": "penalty 보정은 제한된 범위에서만 조정한다.",
    },
)

_feature_pack_rows = feature_pack_rows()

semantic_feature_contract_v1: dict[str, object] = {
    "version": SEMANTIC_FEATURE_CONTRACT_VERSION,
    "semantic_input_packs": _feature_pack_rows[: len(SEMANTIC_INPUT_PACKS)],
    "support_packs": _feature_pack_rows[len(SEMANTIC_INPUT_PACKS) : len(SEMANTIC_INPUT_PACKS) + len(SUPPORT_PACKS)],
    "all_packs": _feature_pack_rows,
}

semantic_target_contract_v1: dict[str, object] = {
    "version": SEMANTIC_TARGET_CONTRACT_VERSION,
    "target_families": [
        {
            "key": target.key,
            "label": target.label,
            "description": target.description,
        }
        for target in MODEL_TARGET_FAMILIES
    ],
}

SEMANTIC_FEATURE_CONTRACT = semantic_feature_contract_v1
SEMANTIC_TARGET_CONTRACT = semantic_target_contract_v1

