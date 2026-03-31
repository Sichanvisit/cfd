# Chart Flow Phase 1 Painter Implementation Checklist

## 목적

이 문서는 `Painter Priority 1 Policy Extraction`을 실제 코드 작업 순서로 옮긴 구현 체크리스트다.

성격:

- 구현 직전 문서
- 실제 작업 순서와 확인 포인트만 담은 실행용 체크리스트
- 설계 확장 문서가 아니라 범위 통제 문서


## 선행 문서

- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_painter_priority1_policy_extraction_list_ko.md`
- `docs/chart_flow_phase0_freeze_ko.md`


## 이번 단계 목표

이번 Phase 1에서 목표는 아래 하나다.

`chart_painter.py`의 Priority 1 baseline 규칙을 `common_expression_policy_v1`에서 읽게 만들기

이번 단계에서 하지 않는 것:

- router 리팩터링
- scoring 정책 이관
- visual 색상/밝기 전면 이관
- anchor 정책 이관
- symbol override 테이블 분리


## 작업 순서

### Step 1. Painter Policy Getter 만들기

목표:

- painter 안에서 공통 policy를 읽는 단일 진입점을 만든다

작업:

- `chart_painter.py` 안에 policy getter 추가
- 초기에는 문서 기준 default를 그대로 반환해도 됨

완료 조건:

- 이후 함수들이 하드코딩 대신 policy getter를 참조할 수 있다


### Step 2. Translation 필드 이관

대상 함수:

- `_resolve_flow_event_kind(...)`
- `_resolve_blocked_structural_wait(...)`
- `_resolve_flow_observe_side(...)`

먼저 옮길 항목:

- `translation.neutral_block_guards`
- `translation.structural_wait_recovery_guards`
- `translation.structural_wait_recovery_reasons`
- `translation.watch_reason_suffix_by_side`
- `translation.conflict_reason_prefixes`
- `translation.probe_promotion_gate_neutralization_enabled`
- `translation.edge_pair_directional_wait_fallback_enabled`
- `translation.scene_side_fallback_enabled`

완료 조건:

- translation baseline이 함수 본문 하드코딩에서 빠진다


### Step 3. Semantics 필드 이관

대상 함수:

- `_resolve_flow_event_kind(...)`

옮길 항목:

- `semantics.directional_wait_enabled`
- `semantics.soft_block_downgrades_ready`
- `semantics.structural_wait_recovery_enabled`
- `semantics.flat_exit_suppression_enabled`
- `semantics.terminal_exit_requires_position`

완료 조건:

- directional wait / soft block / flat exit 의미 토글이 policy에서 제어된다


### Step 4. Probe Baseline 필드 이관

대상 함수:

- `_resolve_probe_visual_allowed(...)`

옮길 항목:

- `probe.upper_min_support_by_side`
- `probe.upper_min_pair_gap_by_side`
- `probe.lower_min_support_by_side`
- `probe.lower_min_pair_gap_by_side`
- `probe.promotion_gate_support_penalty`
- `probe.promotion_gate_pair_gap_penalty`
- `probe.blocked_quick_states`

완료 조건:

- 공통 probe 문턱값이 하드코딩에서 빠진다


### Step 5. Symbol Override Hook 유지 확인

남겨둘 예외:

- `xau_second_support_buy_probe`
- `xau_upper_sell_probe`
- `btc_lower_buy_conservative_probe`
- `nas_clean_confirm_probe`
- `xau_second_support_probe_relief`

완료 조건:

- baseline 이관 후에도 symbol-specific scene 예외는 기존 동작을 유지한다


### Step 6. 테스트와 회귀 확인

우선 확인 테스트:

- `test_add_decision_flow_overlay_ignores_exit_now_when_flat`
- `test_add_decision_flow_overlay_uses_blocked_middle_edge_pair_buy_wait`
- `test_add_decision_flow_overlay_uses_blocked_lower_buy_wait_for_structural_rebound`
- `test_add_decision_flow_overlay_downgrades_soft_blocked_sell_ready_into_sell_wait`
- probe 관련 주요 테스트들

완료 조건:

- 기존 의미가 깨지지 않고 policy read path만 추가되었다


## 구현 중 금지사항

- symbol override를 이번 단계에 같이 옮기지 않는다
- scoring/visual/anchor를 같이 건드리지 않는다
- router까지 같이 리팩터링하지 않는다
- 의미 변경과 구조 변경을 동시에 하지 않는다


## Done Definition

이번 체크리스트는 아래 조건을 만족하면 완료다.

1. painter가 Priority 1 baseline을 policy getter를 통해 읽는다
2. symbol-specific scene 예외는 그대로 유지된다
3. 기존 테스트가 통과한다
4. 코드 변경 범위가 `chart_painter.py` 중심으로 제한된다


## 다음 단계

이 체크리스트가 끝나면 다음으로 넘어간다.

1. painter scoring 정책 이관
2. painter visual/anchor 정책 이관
3. router 공통 policy 연결
4. event distribution 계측 추가
