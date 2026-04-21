"""Central Korean registry for learnable/tunable runtime variables."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from backend.services.reason_label_map import (
    RUNTIME_REASON_EXACT_MAP,
    RUNTIME_SCENE_EXACT_MAP,
    RUNTIME_TRANSITION_EXACT_MAP,
)
from backend.services.teacher_pattern_active_candidate_runtime import (
    STATE25_TEACHER_WEIGHT_CATALOG,
)


LEARNING_PARAMETER_REGISTRY_CONTRACT_VERSION = "learning_parameter_registry_v1"


@dataclass(frozen=True, slots=True)
class LearningParameterRegistryRow:
    registry_key: str
    category_key: str
    category_label_ko: str
    parameter_key: str
    label_ko: str
    description_ko: str
    component_key: str
    source_file: str
    source_field: str
    variable_kind: str
    runtime_role_ko: str
    proposal_role_ko: str
    adjustment_mode_ko: str
    notes_ko: str = ""


def _shadow_auto_dir() -> Path:
    return Path("data") / "analysis" / "shadow_auto"


def _row(
    *,
    registry_key: str,
    category_key: str,
    category_label_ko: str,
    parameter_key: str,
    label_ko: str,
    description_ko: str,
    component_key: str,
    source_file: str,
    source_field: str,
    variable_kind: str,
    runtime_role_ko: str,
    proposal_role_ko: str,
    adjustment_mode_ko: str,
    notes_ko: str = "",
) -> LearningParameterRegistryRow:
    return LearningParameterRegistryRow(
        registry_key=registry_key,
        category_key=category_key,
        category_label_ko=category_label_ko,
        parameter_key=parameter_key,
        label_ko=label_ko,
        description_ko=description_ko,
        component_key=component_key,
        source_file=source_file,
        source_field=source_field,
        variable_kind=variable_kind,
        runtime_role_ko=runtime_role_ko,
        proposal_role_ko=proposal_role_ko,
        adjustment_mode_ko=adjustment_mode_ko,
        notes_ko=notes_ko,
    )


def _translation_source_rows() -> list[LearningParameterRegistryRow]:
    return [
        _row(
            registry_key="translation:runtime_reason",
            category_key="translation_source",
            category_label_ko="한국어 번역 기준면",
            parameter_key="runtime_reason_exact_map",
            label_ko="실시간 이유 한글 맵",
            description_ko=f"실시간 진입/대기/청산 reason의 한국어 기준면 ({len(RUNTIME_REASON_EXACT_MAP)}개 exact map).",
            component_key="runtime_translation",
            source_file="backend/services/reason_label_map.py",
            source_field="RUNTIME_REASON_EXACT_MAP",
            variable_kind="translation_map",
            runtime_role_ko="DM/체크/보고서 이유 문구 기준",
            proposal_role_ko="proposal/evidence 한국어 변환 기준",
            adjustment_mode_ko="번역 기준면 유지",
            notes_ko="새 runtime reason이 생기면 여기 exact/token map부터 보강한다.",
        ),
        _row(
            registry_key="translation:runtime_scene",
            category_key="translation_source",
            category_label_ko="한국어 번역 기준면",
            parameter_key="runtime_scene_exact_map",
            label_ko="실시간 scene 한글 맵",
            description_ko=f"scene fine label과 summary label의 한국어 기준면 ({len(RUNTIME_SCENE_EXACT_MAP)}개 exact map).",
            component_key="scene_translation",
            source_file="backend/services/reason_label_map.py",
            source_field="RUNTIME_SCENE_EXACT_MAP",
            variable_kind="translation_map",
            runtime_role_ko="장면(scene) 설명 surface 기준",
            proposal_role_ko="scene disagreement / detector 보고서 번역 기준",
            adjustment_mode_ko="번역 기준면 유지",
            notes_ko="scene-aware alignment, detector evidence, report title이 이 기준을 공유한다.",
        ),
        _row(
            registry_key="translation:runtime_transition",
            category_key="translation_source",
            category_label_ko="한국어 번역 기준면",
            parameter_key="runtime_transition_exact_map",
            label_ko="전이/반전 한글 맵",
            description_ko=f"shock/reversal/false break/continuation 계열 전이 문구의 한국어 기준면 ({len(RUNTIME_TRANSITION_EXACT_MAP)}개 exact map).",
            component_key="transition_translation",
            source_file="backend/services/reason_label_map.py",
            source_field="RUNTIME_TRANSITION_EXACT_MAP",
            variable_kind="translation_map",
            runtime_role_ko="반전/쇼크/전이 설명 surface 기준",
            proposal_role_ko="reverse detector 및 proposal 설명 기준",
            adjustment_mode_ko="번역 기준면 유지",
            notes_ko="shock/reverse/forecast transition 쪽 한글 문구는 여기서 먼저 맞춘다.",
        ),
        _row(
            registry_key="translation:state25_weight_catalog",
            category_key="translation_source",
            category_label_ko="한국어 번역 기준면",
            parameter_key="state25_teacher_weight_catalog",
            label_ko="state25 가중치 한글 카탈로그",
            description_ko=f"state25 teacher 가중치 조정 항목의 한국어 label/description 기준면 ({len(STATE25_TEACHER_WEIGHT_CATALOG)}개 항목).",
            component_key="state25_translation",
            source_file="backend/services/teacher_pattern_active_candidate_runtime.py",
            source_field="STATE25_TEACHER_WEIGHT_CATALOG",
            variable_kind="translation_catalog",
            runtime_role_ko="teacher weight overlay / report line 기준",
            proposal_role_ko="state25_weight_patch_review 한국어 기준",
            adjustment_mode_ko="bounded proposal label 기준",
            notes_ko="가중치 proposal은 raw key 대신 이 카탈로그 label_ko/description_ko를 우선 사용한다.",
        ),
    ]


def _state25_weight_rows() -> list[LearningParameterRegistryRow]:
    rows: list[LearningParameterRegistryRow] = []
    for key, meta in STATE25_TEACHER_WEIGHT_CATALOG.items():
        label_ko = str(meta.get("label_ko", key) or key)
        description_ko = str(meta.get("description_ko", "") or "")
        rows.append(
            _row(
                registry_key=f"state25_weight:{key}",
                category_key="state25_teacher_weight",
                category_label_ko="state25 teacher 가중치",
                parameter_key=key,
                label_ko=label_ko,
                description_ko=description_ko,
                component_key="state25_teacher_weight",
                source_file="backend/services/teacher_pattern_active_candidate_runtime.py",
                source_field=f"STATE25_TEACHER_WEIGHT_CATALOG['{key}']",
                variable_kind="weight",
                runtime_role_ko="state25 해석 비중 조절",
                proposal_role_ko="weight patch review/apply 대상",
                adjustment_mode_ko="bounded log-only weight patch",
                notes_ko="학습 watcher와 수동 proposal이 같은 weight_key를 공유한다.",
            )
        )
    return rows


def _state25_threshold_rows() -> list[LearningParameterRegistryRow]:
    return [
        _row(
            registry_key="state25_threshold:entry_harden_delta_points",
            category_key="state25_threshold_policy",
            category_label_ko="state25 threshold 보정",
            parameter_key="entry_harden_delta_points",
            label_ko="entry threshold harden 포인트",
            description_ko="state25 context bridge가 큰 그림 충돌/늦은 추격 맥락에서 진입 문턱을 얼마나 더 보수적으로 높였는지 나타내는 log-only threshold delta.",
            component_key="state25_context_bridge_threshold",
            source_file="backend/services/state25_context_bridge.py",
            source_field="threshold_adjustment_requested.threshold_delta_points",
            variable_kind="threshold_delta",
            runtime_role_ko="state25 진입 문턱 보수화 trace",
            proposal_role_ko="threshold patch review/apply 후보",
            adjustment_mode_ko="bounded log-only threshold harden",
            notes_ko="v1은 HARDEN only이며, 먼저 review/log-only trace로 관찰한다.",
        ),
    ]


def _forecast_rows() -> list[LearningParameterRegistryRow]:
    source_file = "backend/services/forecast_state25_runtime_bridge.py"
    category_key = "forecast_runtime"
    category_label_ko = "forecast 보조 판단 축"
    shared = {
        "category_key": category_key,
        "category_label_ko": category_label_ko,
        "component_key": "forecast_runtime_summary",
        "source_file": source_file,
        "variable_kind": "derived_signal",
        "adjustment_mode_ko": "보조 판단 / 직접 apply 금지",
    }
    rows = [
        ("confirm_side", "확정 우세 방향", "현재 confirm branch가 더 우세한 방향(BUY/SELL).", "build_forecast_runtime_summary_v1.confirm_side", "진입 confirm/wait relief 보조", "DM/check/report 보조 설명"),
        ("confirm_score", "확정 우세 점수", "현재 confirm branch 우세 강도.", "build_forecast_runtime_summary_v1.confirm_score", "entry confirm bias 보조", "proposal에서 forecast explain evidence"),
        ("false_break_score", "가짜 돌파 경계 점수", "false break 또는 breakout failure 가능성.", "build_forecast_runtime_summary_v1.false_break_score", "wait/fast-cut bias 보조", "detector와 hindsight에서 false break 설명"),
        ("continuation_score", "지속 성공 점수", "현재 continuation branch 성공 가능성.", "build_forecast_runtime_summary_v1.continuation_score", "hold/confirm bias 보조", "지속/소진 proposal evidence"),
        ("continue_favor_score", "보유 선호 점수", "이미 진입했을 때 hold 쪽으로 기울게 하는 보조 점수.", "build_forecast_runtime_summary_v1.continue_favor_score", "trade management 보조", "exit/hold 제안 근거"),
        ("fail_now_score", "즉시 실패 경계 점수", "진입 후 빠른 실패 또는 fast exit 경계 가능성.", "build_forecast_runtime_summary_v1.fail_now_score", "fast cut bias 보조", "exit hindsight evidence"),
        ("wait_confirm_gap", "대기-확정 간극", "wait bias와 confirm bias 사이 간극.", "build_forecast_runtime_summary_v1.wait_confirm_gap", "entry/wait branch 조절", "wait proposal 우선순위 근거"),
        ("hold_exit_gap", "보유-청산 간극", "hold bias와 exit bias 사이 간극.", "build_forecast_runtime_summary_v1.hold_exit_gap", "hold/fast exit 조절", "management detector evidence"),
        ("same_side_flip_gap", "동일방향-반전 간극", "같은 방향 유지와 반전 쪽 긴장 정도.", "build_forecast_runtime_summary_v1.same_side_flip_gap", "reverse-ready 보조", "reverse proposal evidence"),
        ("belief_barrier_tension_gap", "빌리프-베리어 긴장 간극", "belief와 barrier가 얼마나 충돌하는지.", "build_forecast_runtime_summary_v1.belief_barrier_tension_gap", "wait/guard 해석 보조", "설명 surface와 review 우선순위 근거"),
        ("decision_hint", "forecast 결정 힌트", "CONFIRM_BIASED/WAIT_BIASED/HOLD_BIASED/FAST_EXIT_BIASED/BALANCED 요약.", "build_forecast_runtime_summary_v1.decision_hint", "실행 보조 branch 요약", "한국어 설명 surface 후보"),
        ("prefer_entry_now", "지금 진입 선호", "forecast 관점에서 지금 진입 쪽으로 기우는지.", "build_entry_wait_exit_bridge_v1.prefer_entry_now", "entry relief 보조", "proposal에서 confirm bias evidence"),
        ("prefer_wait_now", "지금 대기 선호", "forecast 관점에서 기다리는 게 더 나은지.", "build_entry_wait_exit_bridge_v1.prefer_wait_now", "wait bias 보조", "wait detector/proposal evidence"),
        ("prefer_hold_if_entered", "진입 후 보유 선호", "이미 진입했다면 보유를 더 보는지.", "build_entry_wait_exit_bridge_v1.prefer_hold_if_entered", "management bias 보조", "exit hindsight evidence"),
        ("prefer_fast_cut_if_entered", "진입 후 빠른 청산 선호", "이미 진입했다면 빠른 cut을 더 보는지.", "build_entry_wait_exit_bridge_v1.prefer_fast_cut_if_entered", "risk cut bias 보조", "fast exit proposal evidence"),
    ]
    return [
        _row(
            registry_key=f"forecast:{key}",
            parameter_key=key,
            label_ko=label_ko,
            description_ko=description_ko,
            source_field=source_field,
            runtime_role_ko=runtime_role_ko,
            proposal_role_ko=proposal_role_ko,
            notes_ko="forecast는 메인 방향 결정권이 아니라 confirm/wait/hold/fast-cut 보조축으로 유지한다.",
            **shared,
        )
        for key, label_ko, description_ko, source_field, runtime_role_ko, proposal_role_ko in rows
    ]


def _misread_rows() -> list[LearningParameterRegistryRow]:
    source_file = "backend/services/improvement_log_only_detector.py"
    category_key = "misread_observation"
    category_label_ko = "구조형 오판 관찰 증거"
    shared = {
        "category_key": category_key,
        "category_label_ko": category_label_ko,
        "component_key": "structure_aware_misread_detector",
        "source_file": source_file,
        "variable_kind": "evidence",
        "adjustment_mode_ko": "observe/detect/feedback/propose",
    }
    rows = [
        ("position_dominance", "위치 우세 방향", "현재 상단/하단/중립 우세 방향.", "_resolve_structure_alignment_context.position_dominance", "실시간 구조 정합 설명", "detector evidence 축"),
        ("structure_alignment", "구조 정합 상태", "정합/엇갈림/중립 surface 결과.", "_resolve_structure_alignment_context.structure_alignment", "DM 설명 surface", "misread detector 핵심 evidence"),
        ("context_flag", "문맥 플래그", "range/breakout/reclaim/compression 등 현재 문맥 추정.", "_infer_context_flag_with_confidence.context_flag", "오탐 방지용 문맥 구분", "proposal/review에서 같은 scene family 묶음"),
        ("context_confidence", "문맥 신뢰도", "현재 문맥 플래그의 신뢰도.", "_infer_context_flag_with_confidence.context_confidence", "설명 caution/unknown 분기", "detector 신뢰도/우선순위 근거"),
        ("box_relative_position", "박스 상대 위치", "현재 가격이 최근 박스 범위에서 어디쯤인지.", "_resolve_box_relative_position_context.box_relative_position", "위치 설명 보조", "상하단 방향 오판 evidence"),
        ("box_zone", "박스 영역", "상단/중단/하단 영역 분류.", "_resolve_box_relative_position_context.box_zone", "구조 위치 설명", "복합 불일치 구성요소"),
        ("range_too_narrow", "좁은 박스 예외", "박스 범위가 너무 좁아 위치 해석을 보류해야 하는지.", "_resolve_box_relative_position_context.range_too_narrow", "설명 예외 처리", "box mismatch 과민 억제"),
        ("upper_wick_ratio", "윗꼬리 비율", "윗꼬리 해석 강도.", "_resolve_wick_body_ratio_context.upper_wick_ratio", "캔들 구조 설명", "상단 거부 evidence"),
        ("lower_wick_ratio", "아랫꼬리 비율", "아랫꼬리 해석 강도.", "_resolve_wick_body_ratio_context.lower_wick_ratio", "캔들 구조 설명", "하단 방어 evidence"),
        ("doji_ratio", "도지 비율", "도지/중립 캔들 성격.", "_resolve_wick_body_ratio_context.doji_ratio", "도지 예외 설명", "doji 기반 candle mismatch evidence"),
        ("recent_3bar_direction", "최근 3봉 흐름", "강상승/약상승/혼조/약하락/강하락 분류.", "_resolve_recent_3bar_direction_context.recent_3bar_direction", "단기 흐름 설명", "timing/misread 분해 evidence"),
        ("result_type", "결과 축", "result_correct/result_misread/result_timing/result_unresolved.", "_classify_result_type", "사후 결과 분류", "proposal 우선순위/fast promotion 입력"),
        ("explanation_type", "설명 축", "explanation_clear/explanation_gap/explanation_unknown.", "_classify_explanation_type", "설명 품질 분류", "설명 부족과 결과 오판 분리"),
        ("misread_confidence", "오판 신뢰도", "구조형 오판 가능성의 종합 신뢰도.", "_calculate_misread_confidence", "detector severity 보조", "feedback-aware promotion 점수"),
        ("explainability_snapshot", "설명 스냅샷", "force/alignment/context를 나중에 재현하기 위한 설명 snapshot.", "_build_explainability_snapshot", "당시 설명 재현", "hindsight/proposal 설명 재현"),
        ("cooldown_window_min", "detector cooldown 분", "같은 scope를 다시 surface하기 전 대기 분.", "_cooldown_minutes_for_row", "알림 과밀 억제", "feedback 품질 유지"),
        ("composite_structure_mismatch", "구조 복합 불일치", "box/wick/3bar가 함께 어긋난 복합 mismatch 여부.", "_build_structure_composite_context", "중요 장면만 DM/check에 압축 노출", "proposal 우선순위 강화"),
        ("semantic_baseline_no_action_cluster", "semantic baseline no-action 군집", "semantic rollout에서 baseline_no_action이 특정 observe/blocked 군집으로 반복될 때 같은 이름으로 추적하는 관찰 키.", "semantic_baseline_no_action_cluster_candidate.primary_registry_key_override", "semantic observe cluster 설명", "detector/proposal에서 같은 semantic cluster를 같은 언어로 추적"),
        ("semantic_continuation_gap_cluster", "semantic ?곸뒿 吏???꾨씫 援곗쭛", "?곸뒿 吏??媛?μ꽦???덈뒗??semantic observe/blocked濡?留뚮궓 援곗쭛.", "semantic_baseline_no_action_cluster_candidate.primary_registry_key_override", "?곸뒿 吏???꾨씫 auto-observe", "detector/proposal?먯꽌 怨꾩냽 ?ㅻ씪媛??꾨뒫?깆씠 ?꾨씫???λ㈃ 異붿쟻"),
        ("directional_up_continuation_conflict", "상승 지속 누락 충돌", "semantic observe, wrong-side conflict, market-family observe가 합쳐져 계속 올라가는 형태를 놓친 장면을 같은 키로 추적.", "directional_continuation_learning_candidate.registry_key", "상승 지속 continuation 학습 후보", "detect/propose/bounded live review에서 같은 상승 지속 누락 후보를 추적"),
        ("directional_down_continuation_conflict", "하락 지속 누락 충돌", "semantic observe, wrong-side conflict, market-family observe가 합쳐져 계속 내려가는 형태를 놓친 장면을 같은 키로 추적.", "directional_continuation_learning_candidate.registry_key", "하락 지속 continuation 학습 후보", "detect/propose/bounded live review에서 같은 하락 지속 누락 후보를 추적"),
        ("semantic_gate_review_candidate", "semantic gate review ??", "semantic baseline no-action?? ?? gate? ?? review?? ??? ?? ??? ???? bounded ?? ?.", "semantic_baseline_no_action_gate_review_candidate.primary_registry_key_override", "semantic gate review ??", "proposal/review?? semantic gate backlog? ?? ??? ??"),
        ("semantic_blocked_by", "semantic blocked_by", "semantic baseline no-action? ?? blocked_by gate ??.", "semantic_baseline_no_action_sample_audit.summary.blocked_by_counts", "semantic blocked gate ??", "gate review ?? ??"),
        ("semantic_action_none_reason", "semantic action none reason", "semantic baseline no-action?? action? ?? ?? ?? ??.", "semantic_baseline_no_action_sample_audit.summary.action_none_reason_counts", "semantic no-action ?? ??", "gate review ?? ??"),
        ("semantic_shadow_trace_quality", "semantic shadow trace quality", "semantic shadow trace ?? ??.", "semantic_baseline_no_action_sample_audit.summary.semantic_shadow_trace_quality_counts", "semantic trace ?? ??", "trace availability review ??"),
        ("htf_alignment_state", "HTF 정렬 상태", "현재 판단과 15M/1H/4H/1D 상위 추세의 정합/역행 상태.", "_build_runtime_context_bundle.htf_alignment_state", "상위 추세 경고 evidence", "detector/notifier/propose 공통 HTF context"),
        ("htf_alignment_detail", "HTF 정렬 상세", "전체 상승/하락 정렬인지, 현재만 역행하는지의 상세 분류.", "_build_runtime_context_bundle.htf_alignment_detail", "상위 추세 상세 surface", "context bundle 상세 근거"),
        ("htf_against_severity", "HTF 역행 강도", "상위 추세 역행의 강도 LOW/MEDIUM/HIGH.", "_build_runtime_context_bundle.htf_against_severity", "역행 경고 강도 surface", "review backlog 우선순위 근거"),
        ("previous_box_break_state", "직전 박스 상태", "직전 박스 기준 돌파 유지/실패/되찾기 여부.", "_build_runtime_context_bundle.previous_box_break_state", "직전 박스 구조 evidence", "structure mismatch review 근거"),
        ("previous_box_relation", "직전 박스 관계", "현재가가 직전 박스 상단 위/내부/하단 아래 어디인지.", "_build_runtime_context_bundle.previous_box_relation", "직전 박스 위치 surface", "proposal 구조 문맥 근거"),
        ("previous_box_lifecycle", "직전 박스 lifecycle", "직전 박스가 확정/재테스트/무효화 중 어디 단계인지.", "_build_runtime_context_bundle.previous_box_lifecycle", "직전 박스 생명주기 surface", "box context 해석 강도 근거"),
        ("previous_box_confidence", "직전 박스 신뢰도", "직전 박스 해석의 LOW/MEDIUM/HIGH 신뢰도.", "_build_runtime_context_bundle.previous_box_confidence", "직전 박스 해석 신뢰도", "detector/proposal caution 근거"),
        ("context_conflict_state", "맥락 충돌 상태", "현재 판단과 HTF/직전 박스 맥락이 어떻게 충돌하는지의 primary 상태.", "_build_runtime_context_bundle.context_conflict_state", "맥락 충돌 요약 surface", "detector/proposal 핵심 context evidence"),
        ("context_conflict_intensity", "맥락 충돌 강도", "맥락 충돌의 강도 LOW/MEDIUM/HIGH.", "_build_runtime_context_bundle.context_conflict_intensity", "맥락 충돌 강도 surface", "review 우선순위와 detector severity 근거"),
        ("late_chase_risk_state", "늦은 추격 위험 상태", "추격 진입/추격 숏 위험의 NONE/EARLY_WARNING/HIGH 상태.", "_build_runtime_context_bundle.late_chase_risk_state", "추격 위험 경고 surface", "timing mismatch review 근거"),
        ("late_chase_reason", "늦은 추격 이유", "늦은 추격으로 읽힌 핵심 이유 코드.", "_build_runtime_context_bundle.late_chase_reason", "추격 위험 상세 reason", "hindsight/proposal에서 timing 근거"),
    ]
    return [
        _row(
            registry_key=f"misread:{key}",
            parameter_key=key,
            label_ko=label_ko,
            description_ko=description_ko,
            source_field=source_field,
            runtime_role_ko=runtime_role_ko,
            proposal_role_ko=proposal_role_ko,
            notes_ko="P4-6 detector evidence는 같은 canonical evidence shape를 공유한다.",
            **shared,
        )
        for key, label_ko, description_ko, source_field, runtime_role_ko, proposal_role_ko in rows
    ]


def _detector_policy_rows() -> list[LearningParameterRegistryRow]:
    source_file = "backend/services/improvement_detector_policy.py"
    category_key = "detector_policy"
    category_label_ko = "detector 운영 정책"
    rows = [
        ("scene_aware.daily_surface_limit", "scene-aware 일 surface 한도", "scene-aware detector 하루 surface 상한.", "DETECTOR_DAILY_SURFACE_LIMITS['scene_aware']"),
        ("candle_weight.daily_surface_limit", "candle/weight 일 surface 한도", "candle/weight detector 하루 surface 상한.", "DETECTOR_DAILY_SURFACE_LIMITS['candle_weight']"),
        ("reverse_pattern.daily_surface_limit", "reverse pattern 일 surface 한도", "reverse detector 하루 surface 상한.", "DETECTOR_DAILY_SURFACE_LIMITS['reverse_pattern']"),
        ("scene_aware.min_repeat_sample", "scene-aware 최소 반복 표본", "scene-aware detector가 surface되기 전 필요한 반복 표본.", "DETECTOR_MIN_REPEAT_SAMPLES['scene_aware']"),
        ("candle_weight.min_repeat_sample", "candle/weight 최소 반복 표본", "candle/weight detector의 최소 반복 표본.", "DETECTOR_MIN_REPEAT_SAMPLES['candle_weight']"),
        ("reverse_pattern.min_repeat_sample", "reverse pattern 최소 반복 표본", "reverse detector의 최소 반복 표본.", "DETECTOR_MIN_REPEAT_SAMPLES['reverse_pattern']"),
    ]
    return [
        _row(
            registry_key=f"detector_policy:{key}",
            category_key=category_key,
            category_label_ko=category_label_ko,
            parameter_key=key,
            label_ko=label_ko,
            description_ko=description_ko,
            component_key="improvement_detector_policy",
            source_file=source_file,
            source_field=source_field,
            variable_kind="policy_limit",
            runtime_role_ko="runtime detector 노출 한도",
            proposal_role_ko="review backlog 품질 관리",
            adjustment_mode_ko="정책 값 조정",
            notes_ko="detector는 observe/report 우선이며 자동 apply를 열지 않는다.",
        )
        for key, label_ko, description_ko, source_field in rows
    ]


def _feedback_promotion_rows() -> list[LearningParameterRegistryRow]:
    source_file = "backend/services/trade_feedback_runtime.py"
    category_key = "feedback_promotion_policy"
    category_label_ko = "feedback 승격 정책"
    rows = [
        ("fast_promotion_min_feedback", "빠른 승격 최소 피드백 수", "fast promotion을 고려하기 위한 최소 feedback 수.", "FAST_PROMOTION_MIN_FEEDBACK"),
        ("fast_promotion_min_positive_ratio", "빠른 승격 최소 긍정 비율", "confirmed/positive 비율의 최소 기준.", "FAST_PROMOTION_MIN_POSITIVE_RATIO"),
        ("fast_promotion_min_trade_days", "빠른 승격 최소 거래일 분산", "한 날 몰림이 아니라 최소 여러 거래일에 걸친 반복을 요구.", "FAST_PROMOTION_MIN_TRADE_DAYS"),
        ("fast_promotion_min_misread_confidence", "빠른 승격 최소 오판 신뢰도", "misread confidence가 일정 이상일 때만 빠른 승격 허용.", "FAST_PROMOTION_MIN_MISREAD_CONFIDENCE"),
        ("hindsight_status", "사후 hindsight 상태", "confirmed_misread/false_alarm/partial_misread/unresolved 분류.", "_classify_hindsight_status"),
    ]
    return [
        _row(
            registry_key=f"promotion:{key}",
            category_key=category_key,
            category_label_ko=category_label_ko,
            parameter_key=key,
            label_ko=label_ko,
            description_ko=description_ko,
            component_key="trade_feedback_runtime",
            source_file=source_file,
            source_field=source_field,
            variable_kind="promotion_policy",
            runtime_role_ko="feedback-aware 우선 검토",
            proposal_role_ko="fast promotion / bounded review priority",
            adjustment_mode_ko="review priority 조정 / 자동 apply 금지",
            notes_ko="fast promotion은 proposal 우선 검토까지만 허용한다.",
        )
        for key, label_ko, description_ko, source_field in rows
    ]


def build_learning_parameter_registry() -> dict[str, Any]:
    rows = [
        *_translation_source_rows(),
        *_state25_weight_rows(),
        *_state25_threshold_rows(),
        *_forecast_rows(),
        *_misread_rows(),
        *_detector_policy_rows(),
        *_feedback_promotion_rows(),
    ]
    payload_rows = [asdict(row) for row in rows]
    category_counts: dict[str, int] = {}
    category_labels: dict[str, str] = {}
    for row in payload_rows:
        category_key = str(row["category_key"])
        category_counts[category_key] = category_counts.get(category_key, 0) + 1
        category_labels.setdefault(category_key, str(row["category_label_ko"]))
    return {
        "contract_version": LEARNING_PARAMETER_REGISTRY_CONTRACT_VERSION,
        "row_count": len(payload_rows),
        "categories": [
            {
                "category_key": key,
                "category_label_ko": category_labels[key],
                "row_count": category_counts[key],
            }
            for key in sorted(category_counts)
        ],
        "rows": payload_rows,
    }


def default_learning_parameter_registry_paths() -> tuple[Path, Path]:
    directory = _shadow_auto_dir()
    return (
        directory / "learning_parameter_registry_latest.json",
        directory / "learning_parameter_registry_latest.md",
    )


def render_learning_parameter_registry_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Learning Parameter Registry",
        "",
        f"- contract_version: `{payload.get('contract_version', '-')}`",
        f"- row_count: `{payload.get('row_count', '-')}`",
        "",
        "## Categories",
    ]
    for category in payload.get("categories", []):
        lines.append(
            f"- `{category.get('category_key', '-')}` | {category.get('category_label_ko', '-')}"
            f" | rows={category.get('row_count', '-')}"
        )
    rows = list(payload.get("rows", []) or [])
    categories = sorted({str(row.get("category_key")) for row in rows})
    for category_key in categories:
        category_rows = [row for row in rows if str(row.get("category_key")) == category_key]
        category_label = str(category_rows[0].get("category_label_ko", category_key)) if category_rows else category_key
        lines.extend(["", f"## {category_label} (`{category_key}`)", ""])
        for row in category_rows:
            lines.extend(
                [
                    f"- `{row['registry_key']}` | {row['label_ko']}",
                    f"  parameter_key: `{row['parameter_key']}`",
                    f"  description_ko: {row['description_ko']}",
                    f"  component_key: `{row['component_key']}`",
                    f"  source: `{row['source_file']}::{row['source_field']}`",
                    f"  variable_kind: `{row['variable_kind']}`",
                    f"  runtime_role_ko: {row['runtime_role_ko']}",
                    f"  proposal_role_ko: {row['proposal_role_ko']}",
                    f"  adjustment_mode_ko: {row['adjustment_mode_ko']}",
                ]
            )
            if str(row.get("notes_ko", "") or ""):
                lines.append(f"  notes_ko: {row['notes_ko']}")
    lines.append("")
    return "\n".join(lines)


def write_learning_parameter_registry_snapshot(
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_learning_parameter_registry()
    default_json_path, default_markdown_path = default_learning_parameter_registry_paths()
    resolved_json_path = Path(json_path) if json_path else default_json_path
    resolved_markdown_path = Path(markdown_path) if markdown_path else default_markdown_path
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    resolved_markdown_path.write_text(render_learning_parameter_registry_markdown(payload), encoding="utf-8")
    return {
        "json_path": str(resolved_json_path),
        "markdown_path": str(resolved_markdown_path),
        "row_count": int(payload.get("row_count", 0)),
    }
