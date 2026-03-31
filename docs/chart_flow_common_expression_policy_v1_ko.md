# 차트 Flow Common Expression Policy v1

## 목적

이 문서는 `buy / wait / sell` 표현을 공통 baseline으로 묶기 위한
`common_expression_policy_v1`의 최종 필드안을 정의한다.

이 문서는 아직 코드에 전부 반영된 상태를 뜻하지는 않는다.
하지만 Phase 1 시점에서 "무엇을 policy 필드로 본다"를 더 이상 흔들리지 않게 고정하는 문서다.

작성 기준 시점:

- 2026-03-25 KST


## 1. 문서 관계

이 문서는 아래 문서의 다음 단계다.

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase0_freeze_ko.md`
- `docs/chart_flow_common_expression_policy_draft_ko.md`
- `docs/chart_flow_phase2_common_threshold_baseline_spec_ko.md`
- `docs/chart_flow_phase2_common_threshold_implementation_checklist_ko.md`
- `docs/chart_flow_phase3_strength_standard_spec_ko.md`
- `docs/chart_flow_phase3_strength_implementation_checklist_ko.md`
- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`
- `docs/chart_flow_phase4_symbol_override_implementation_checklist_ko.md`
- `docs/chart_flow_phase5_observation_validation_spec_ko.md`
- `docs/chart_flow_phase5_observation_validation_implementation_checklist_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_spec_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_implementation_checklist_ko.md`

역할:

- guide: 전체 설명서
- phase0 freeze: baseline vs override 구분 고정
- draft: 후보값 정리
- phase2 spec: 공통 threshold baseline 상세안
- phase2 checklist: 구현 순서와 범위 제한
- phase3 spec: strength 1..10 버킷과 visual binding 기준
- phase3 checklist: strength 구현 순서와 범위 제한
- phase4 spec: symbol override inventory와 isolation 기준
- phase4 checklist: symbol override 구현 순서와 범위 제한
- phase5 spec: 분포 관측/검증 기준과 산출물 정의
- phase5 checklist: 관측/검증 구현 순서와 범위 제한
- phase6 spec: 운영 순서, gate, calibration 원칙 정의
- phase6 checklist: 실제 rollout 실행 순서와 stop / rollback 기준
- v1: 실제 필드 스펙 확정


## 2. Contract

정식 계약 이름:

- `common_expression_policy_v1`

최상위 구조:

```text
common_expression_policy_v1
├─ contract_version
├─ semantics
├─ readiness
├─ probe
├─ translation
├─ scoring
├─ visual
├─ anchor
└─ override_policy
```


## 3. 최종 필드 목록

### 3-1. `contract_version`

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `contract_version` | `str` | `"common_expression_policy_v1"` | 문서 | 불가 |


### 3-2. `semantics`

역할:

- event family 의미를 잠근다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `semantics.directional_wait_enabled` | `bool` | `true` | painter + 문서 | 불가 |
| `semantics.soft_block_downgrades_ready` | `bool` | `true` | painter + 문서 | 불가 |
| `semantics.structural_wait_recovery_enabled` | `bool` | `true` | painter + 문서 | 불가 |
| `semantics.flat_exit_suppression_enabled` | `bool` | `true` | runner + painter | 불가 |
| `semantics.terminal_exit_requires_position` | `bool` | `true` | runner + painter | 불가 |
| `semantics.event_family_order` | `list[str]` | `["PROBE","WATCH","WAIT","READY","ENTER","EXIT","HOLD"]` | 문서 | 불가 |

해석:

- `WAIT + BUY`와 `WAIT + SELL`은 directional wait다
- soft block은 방향 삭제가 아니라 wait downgrade다
- exit family는 position management 신호다


### 3-3. `readiness`

역할:

- confirm readiness의 공통 baseline을 정의한다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `readiness.confirm_floor_by_state` | `dict[str, float]` | 아래 표 참조 | router | 허용 |
| `readiness.confirm_advantage_by_state` | `dict[str, float]` | 아래 표 참조 | router | 허용 |

#### `confirm_floor_by_state`

| state group | value |
| --- | --- |
| `TREND_PULLBACK_BUY_CONFIRM` | `0.03` |
| `TREND_PULLBACK_SELL_CONFIRM` | `0.03` |
| `FAILED_SELL_RECLAIM_BUY_CONFIRM` | `0.03` |
| `MID_RECLAIM_CONFIRM` | `0.035` |
| `MID_REJECT_CONFIRM` | `0.035` |
| `LOWER_REBOUND_CONFIRM` | `0.20` |
| `UPPER_REJECT_CONFIRM` | `0.20` |
| `LOWER_FAIL_CONFIRM` | `0.24` |
| `UPPER_BREAK_CONFIRM` | `0.24` |
| `DEFAULT` | `0.20` |

#### `confirm_advantage_by_state`

| state group | value |
| --- | --- |
| `TREND_PULLBACK_BUY_CONFIRM` | `0.003` |
| `TREND_PULLBACK_SELL_CONFIRM` | `0.003` |
| `FAILED_SELL_RECLAIM_BUY_CONFIRM` | `0.003` |
| `MID_RECLAIM_CONFIRM` | `0.01` |
| `MID_REJECT_CONFIRM` | `0.01` |
| `LOWER_REBOUND_CONFIRM` | `0.003` |
| `DEFAULT` | `0.02` |

원칙:

- state별 의미는 baseline에 포함된다
- 심볼 차이는 multiplier/override로만 조정한다


### 3-4. `probe`

역할:

- probe 전환 문턱과 probe 시각화 baseline을 정의한다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `probe.default_floor_mult` | `float` | `0.72` | router | 허용 |
| `probe.default_advantage_mult` | `float` | `0.25` | router | 허용 |
| `probe.default_support_tolerance` | `float` | `0.015` | router | 허용 |
| `probe.upper_min_support_by_side` | `dict[str, float]` | `{"SELL": 0.16, "BUY": 0.18}` | painter -> 추후 공통 policy | 허용 |
| `probe.upper_min_pair_gap_by_side` | `dict[str, float]` | `{"SELL": 0.03, "BUY": 0.04}` | painter -> 추후 공통 policy | 허용 |
| `probe.lower_min_support_by_side` | `dict[str, float]` | `{"BUY": 0.22, "SELL": 0.26}` | painter -> 추후 공통 policy | 허용 |
| `probe.lower_min_pair_gap_by_side` | `dict[str, float]` | `{"BUY": 0.12, "SELL": 0.18}` | painter -> 추후 공통 policy | 허용 |
| `probe.promotion_gate_support_penalty` | `float` | `0.08` | painter | 허용 |
| `probe.promotion_gate_pair_gap_penalty` | `float` | `0.05` | painter | 허용 |
| `probe.blocked_quick_states` | `list[str]` | `["BLOCKED","PROBE_CANDIDATE_BLOCKED"]` | painter | 불가 |

원칙:

- probe는 confirm보다 이른 단계다
- baseline은 공통값으로 두고, scene/context 완화만 override에서 허용한다


### 3-5. `translation`

역할:

- semantic row를 chart event family로 번역하는 공통 규칙을 정의한다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `translation.neutral_block_guards` | `list[str]` | `["outer_band_guard","forecast_guard","middle_sr_anchor_guard","barrier_guard"]` | painter | 불가 |
| `translation.structural_wait_recovery_guards` | `list[str]` | `["middle_sr_anchor_guard","outer_band_guard"]` | painter | 불가 |
| `translation.structural_wait_recovery_reasons` | `list[str]` | `["outer_band_reversal_support_required_observe","middle_sr_anchor_required_observe"]` | painter | 불가 |
| `translation.watch_reason_suffix_by_side` | `dict[str, str]` | `{"BUY":"buy_watch","SELL":"sell_watch"}` | painter | 불가 |
| `translation.conflict_reason_prefixes` | `list[str]` | `["conflict_"]` | painter | 불가 |
| `translation.probe_promotion_gate_neutralization_enabled` | `bool` | `true` | painter | 불가 |
| `translation.edge_pair_directional_wait_fallback_enabled` | `bool` | `true` | painter | 불가 |
| `translation.scene_side_fallback_enabled` | `bool` | `true` | painter | 불가 |

원칙:

- 번역 규칙은 심볼별로 뜻이 달라지면 안 된다
- event family 의미는 override 대상이 아니다


### 3-6. `scoring`

역할:

- 차트 표시 강도용 score 계산식을 정의한다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `scoring.input_paths` | `list[str]` | `["observe_confirm_v2.confidence","probe_candidate_support","probe_pair_gap"]` | painter | 불가 |
| `scoring.reduction` | `str` | `"max"` | painter | 불가 |
| `scoring.probe_ready_bonus` | `float` | `0.05` | painter | 허용 |
| `scoring.probe_ready_bonus_kinds` | `list[str]` | `["BUY_READY","SELL_READY","BUY_PROBE","SELL_PROBE"]` | painter | 불가 |

원칙:

- score는 확률이 아니라 chart intensity용 readiness surrogate다
- Phase 1에서는 단순 max 기준 유지


### 3-7. `visual`

역할:

- 색상과 wait 밝기 보정 규칙을 정의한다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `visual.base_color_by_event_kind` | `dict[str, int]` | 아래 표 참조 | painter | 허용 |
| `visual.compact_history_kinds` | `list[str]` | `["BUY_PROBE","SELL_PROBE","BUY_WATCH","SELL_WATCH","BUY_WAIT","SELL_WAIT","WAIT","HOLD"]` | painter | 불가 |
| `visual.wait_brightness_by_event_kind` | `dict[str, object]` | 아래 표 참조 | painter | 허용 |

#### `base_color_by_event_kind`

| event kind | value |
| --- | --- |
| `BUY_READY` | `65280` |
| `SELL_READY` | `255` |
| `BUY_PROBE` | `0x00E6FF66` |
| `SELL_PROBE` | `2555904` |
| `BUY_WATCH` | `0x00F5FF99` |
| `SELL_WATCH` | `255` |
| `BUY_WAIT` | `0x00C8FF4D` |
| `SELL_WAIT` | `128` |
| `WAIT` | `13421772` |
| `ENTER_BUY` | `65407` |
| `ENTER_SELL` | `16711935` |
| `EXIT_NOW` | `26367` |
| `REVERSE_READY` | `16711808` |
| `HOLD` | `16776960` |

#### `wait_brightness_by_event_kind`

`BUY_WAIT`

- `brighten_threshold = 0.30`
- `brighten_target_color = 0x00FFFFFF`
- `brighten_alpha_base = 0.18`
- `brighten_alpha_scale = 0.90`
- `brighten_alpha_cap = 0.38`
- `dim_threshold = 0.06`
- `dim_target_color = 0x00000000`
- `dim_alpha = 0.18`

`SELL_WAIT`

- `brighten_threshold = 0.34`
- `brighten_target_color = 0x00FFFFFF`
- `brighten_alpha_base = 0.16`
- `brighten_alpha_scale = 0.72`
- `brighten_alpha_cap = 0.34`
- `dim_threshold = 0.06`
- `dim_target_color = 0x00000000`
- `dim_alpha = 0.18`

원칙:

- buy 계열은 차트 support/trend 녹색보다 더 잘 보여야 한다
- wait brightness는 Phase 1에서는 wait 계열까지만 확정


### 3-8. `anchor`

역할:

- event kind/reason별 마커 위치 기준을 정의한다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `anchor.buy_upper_reclaim_mode` | `str` | `"body_low"` | painter | 불가 |
| `anchor.buy_middle_ratio` | `float` | `0.48` | painter | 허용 |
| `anchor.buy_probe_ratio` | `float` | `0.30` | painter | 허용 |
| `anchor.buy_default_ratio` | `float` | `0.36` | painter | 허용 |
| `anchor.sell_mode` | `str` | `"high"` | painter | 불가 |
| `anchor.neutral_mode` | `str` | `"close"` | painter | 불가 |

원칙:

- buy는 무조건 low에 박지 않는다
- sell은 기본적으로 high 기준
- neutral wait는 close 축


### 3-9. `override_policy`

역할:

- 무엇을 override할 수 있고 무엇은 절대 override하면 안 되는지 정의한다

| field | type | default | owner | override |
| --- | --- | --- | --- | --- |
| `override_policy.allowed_groups` | `list[str]` | 아래 표 참조 | 문서 | 해당 없음 |
| `override_policy.forbidden_groups` | `list[str]` | 아래 표 참조 | 문서 | 해당 없음 |

#### `allowed_groups`

- `readiness.confirm_floor_by_state`
- `readiness.confirm_advantage_by_state`
- `probe.default_floor_mult`
- `probe.default_advantage_mult`
- `probe.default_support_tolerance`
- `probe.upper_min_support_by_side`
- `probe.upper_min_pair_gap_by_side`
- `probe.lower_min_support_by_side`
- `probe.lower_min_pair_gap_by_side`
- `anchor.buy_middle_ratio`
- `anchor.buy_probe_ratio`
- `anchor.buy_default_ratio`
- scene-specific context relief

#### `forbidden_groups`

- `semantics.*`
- `translation.*` 중 event meaning을 바꾸는 항목
- `semantics.flat_exit_suppression_enabled`
- `semantics.soft_block_downgrades_ready`
- `semantics.directional_wait_enabled`
- `semantics.event_family_order`

원칙:

- override는 의미가 아니라 문턱과 완화만 조정해야 한다


## 4. Canonical 예시

```yaml
common_expression_policy_v1:
  contract_version: common_expression_policy_v1
  semantics:
    directional_wait_enabled: true
    soft_block_downgrades_ready: true
    structural_wait_recovery_enabled: true
    flat_exit_suppression_enabled: true
    terminal_exit_requires_position: true
    event_family_order: [PROBE, WATCH, WAIT, READY, ENTER, EXIT, HOLD]
  readiness:
    confirm_floor_by_state:
      TREND_PULLBACK_BUY_CONFIRM: 0.03
      TREND_PULLBACK_SELL_CONFIRM: 0.03
      FAILED_SELL_RECLAIM_BUY_CONFIRM: 0.03
      MID_RECLAIM_CONFIRM: 0.035
      MID_REJECT_CONFIRM: 0.035
      LOWER_REBOUND_CONFIRM: 0.20
      UPPER_REJECT_CONFIRM: 0.20
      LOWER_FAIL_CONFIRM: 0.24
      UPPER_BREAK_CONFIRM: 0.24
      DEFAULT: 0.20
    confirm_advantage_by_state:
      TREND_PULLBACK_BUY_CONFIRM: 0.003
      TREND_PULLBACK_SELL_CONFIRM: 0.003
      FAILED_SELL_RECLAIM_BUY_CONFIRM: 0.003
      MID_RECLAIM_CONFIRM: 0.01
      MID_REJECT_CONFIRM: 0.01
      LOWER_REBOUND_CONFIRM: 0.003
      DEFAULT: 0.02
  probe:
    default_floor_mult: 0.72
    default_advantage_mult: 0.25
    default_support_tolerance: 0.015
    upper_min_support_by_side: {SELL: 0.16, BUY: 0.18}
    upper_min_pair_gap_by_side: {SELL: 0.03, BUY: 0.04}
    lower_min_support_by_side: {BUY: 0.22, SELL: 0.26}
    lower_min_pair_gap_by_side: {BUY: 0.12, SELL: 0.18}
    promotion_gate_support_penalty: 0.08
    promotion_gate_pair_gap_penalty: 0.05
    blocked_quick_states: [BLOCKED, PROBE_CANDIDATE_BLOCKED]
  translation:
    neutral_block_guards: [outer_band_guard, forecast_guard, middle_sr_anchor_guard, barrier_guard]
    structural_wait_recovery_guards: [middle_sr_anchor_guard, outer_band_guard]
    structural_wait_recovery_reasons:
      - outer_band_reversal_support_required_observe
      - middle_sr_anchor_required_observe
    watch_reason_suffix_by_side: {BUY: buy_watch, SELL: sell_watch}
    conflict_reason_prefixes: [conflict_]
    probe_promotion_gate_neutralization_enabled: true
    edge_pair_directional_wait_fallback_enabled: true
    scene_side_fallback_enabled: true
  scoring:
    input_paths:
      - observe_confirm_v2.confidence
      - probe_candidate_support
      - probe_pair_gap
    reduction: max
    probe_ready_bonus: 0.05
    probe_ready_bonus_kinds: [BUY_READY, SELL_READY, BUY_PROBE, SELL_PROBE]
  anchor:
    buy_upper_reclaim_mode: body_low
    buy_middle_ratio: 0.48
    buy_probe_ratio: 0.30
    buy_default_ratio: 0.36
    sell_mode: high
    neutral_mode: close
```


## 5. 구현 우선순위

이 v1 스펙을 코드에 반영할 때 우선순위는 아래처럼 간다.

Painter Priority 1 실행 목록:

- `docs/chart_flow_painter_priority1_policy_extraction_list_ko.md`
- `docs/chart_flow_phase1_painter_implementation_checklist_ko.md`

### Priority 1

- `semantics`
- `translation`
- `probe`

### Priority 2

- `readiness`
- `scoring`
- `visual.wait_brightness_by_event_kind`

### Priority 3

- `anchor`
- `visual.base_color_by_event_kind`
- 이후 strength 확장 입력


## 6. 구현 전 체크

코드 반영 전에 아래를 확인한다.

1. 이 필드는 baseline인가 override인가
2. 이 필드의 owner는 router인가 painter인가
3. 이 필드는 의미를 바꾸는가, 문턱만 바꾸는가
4. 이 필드를 symbol별로 다르게 둘 필요가 정말 있는가
5. override가 필요하다면 허용 그룹 안에 들어가는가


## 7. 최종 결론

`policy 필드 최종안`은 결국 아래를 뜻한다.

- 코드 여기저기에 흩어져 있는 기준값을 이름 붙여 묶는다
- 공통 baseline과 symbol override를 분리한다
- router와 painter가 같은 기준선을 바라보게 만든다
- 다음 단계부터는 이 스펙을 기준으로만 코드를 바꾼다
