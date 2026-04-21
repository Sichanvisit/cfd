# State25 Context Bridge v1.2 상세 설계

## 1. 목표

`state25_context_bridge_v1`의 목적은
**HTF / previous box / context conflict / late chase 같은 상위 맥락을 state25의 방향 결정 규칙으로 직접 강제하지 않고, 기존 state25의 `weight / threshold / size` 손잡이에 bounded한 미세 조정값으로 번역하는 것**이다.

즉 bridge는:
- 새 decision core가 아니다
- detector 같은 관찰자가 아니다
- notifier 같은 전달자도 아니다

정확히는
**큰 그림 맥락을 state25가 이해할 수 있는 작은 정책 조정값으로 번역하는 bounded policy adapter**다.


## 2. 현재 문제 정의

지금은 아래 흐름이 이미 연결되어 있다.

- runtime row가 `HTF / previous box / context conflict / late chase`를 가진다
- detector가 그 맥락을 읽는다
- notifier가 `맥락:` 한 줄을 보여준다
- `/propose`와 hindsight가 그 맥락을 review language로 이어받는다

하지만 state25 점수 본체는 아직 이 큰 그림을 충분히 자기 손잡이에 번역하지 못한다.

그래서 운영 체감은 종종 이렇게 갈린다.

1. 설명층:
   - `상위 추세 역행`
   - `직전 박스 상단 돌파 유지`
   - `늦은 추격 위험`
2. 점수층:
   - 기존 reversal / short 해석 비중이 그대로 남아 있음
3. 결과:
   - 설명은 불편하다고 말하는데 점수는 예전 습관대로 감

이번 bridge는 바로 이 간극을 줄이는 단계다.


## 3. state25가 현재 가진 실제 손잡이

관련 파일:
- [teacher_pattern_active_candidate_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\teacher_pattern_active_candidate_runtime.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [teacher_pattern_execution_policy_log_only_binding.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\teacher_pattern_execution_policy_log_only_binding.py)

### 3-1. Weight

목적:
- 무엇을 더 믿고 덜 믿을지 조정

대표 계약 필드:
- `state25_teacher_weight_overrides`

대표 weight key:
- `directional_bias_weight`
- `participation_weight`
- `reversal_risk_weight`
- `range_reversal_weight`
- `same_color_run_weight`
- `prediction_weight`

### 3-2. Threshold

목적:
- 진입 문턱을 높이거나 낮춤

현재 대표 필드:
- `state25_threshold_log_only_max_adjustment_abs`

중요한 현재 제약:
- 기존 state25 threshold log-only 계약은 사실상 `actual_threshold - max_adjustment_abs` 구조에 가깝다
- 즉 threshold 완화 쪽 표현에는 자연스럽지만,
- `역추세일수록 더 까다롭게` 같은 **보수적 threshold 상향**을 직접 표현하기에는 불편하다

그래서 bridge에서는 아래 계약을 별도 설계 대상으로 둔다.

- `state25_threshold_log_only_delta_points`
- `threshold_delta_direction`
- `threshold_delta_reason_keys`

### 3-3. Size

목적:
- 맞더라도 얼마나 세게 들어갈지 조정

대표 필드:
- `state25_size_log_only_min_multiplier`
- `state25_size_log_only_max_multiplier`

size는 가장 마지막에 붙인다.


## 4. 핵심 원칙

### 원칙 1. 방향 강제 금지

bridge는 아래를 하지 않는다.

- `HTF 상승이면 SELL 금지`
- `직전 박스 위면 무조건 BUY`
- `late_chase = HIGH면 자동 차단`

bridge는 오직
- weight
- threshold
- size

를 작은 범위로 조정하는 번역기다.

### 원칙 2. interpreted 80 / raw 20

bridge는 기본적으로 **interpreted context 중심**으로 작동한다.

예:
- `AGAINST_HTF`
- `BREAKOUT_HELD`
- `AGAINST_PREV_BOX_AND_HTF`
- `LATE_CHASE_RISK`

raw 값은 주로:
- 조정 강도
- freshness 검증
- cap/감쇠

에만 쓴다.

공식:
- `interpreted = 보정 방향`
- `raw = 보정 강도`

### 원칙 3. knob 역할 분리

- `weight` = 해석 비중 조정
- `threshold` = 진입 문턱 조정
- `size` = 리스크 강도 조정

서로의 책임을 넘지 않는다.

### 원칙 4. share는 confidence booster만

share는:
- 반복성 태그
- confidence 보강
- proposal priority 보강

용도까지만 쓴다.

share는 direction authority가 아니다.

### 원칙 5. freshness 없으면 약화 또는 무효

stale한 HTF / previous box는 그대로 반영하지 않는다.

### 원칙 6. v1 실제 활성 범위는 더 좁게

v1에서 실제로 강하게 켜는 것은 제한한다.

- threshold는 `HARDEN` only
- late chase는 threshold / size 우선
- outcome counterfactual은 나중
- RELAX는 schema 자리만 남기고 실제 live는 보류


## 5. 전체 구조

```text
[state-first context row]
  └─ HTF / previous box / conflict / late chase / freshness

        ↓

[state25_context_bridge.py]
  ├─ context intake
  ├─ freshness / gating
  ├─ interpreted normalization
  ├─ knob translators
  │    ├─ weight translator
  │    ├─ threshold translator
  │    └─ size translator
  ├─ cap / decay / stacking limit
  └─ trace builder

        ↓

[state25_candidate_context_bridge_v1]
  ├─ weight_adjustments
  ├─ threshold_adjustments
  ├─ size_adjustments
  ├─ effective_adjustments
  └─ trace / rationale / freshness

        ↓

[entry_try_open_entry.py / trading_application.py]
  ├─ log_only trace
  ├─ runtime export
  └─ later review / apply / bounded rollout
```

bridge 내부는 반드시 아래 4구간으로 나눈다.

1. `intake`
2. `gating`
3. `translator`
4. `cap_and_trace`


## 6. 입력 스키마

bridge는 기본적으로 ST4 이후의 runtime enriched row를 읽는다.

### 6-1. 기본 입력
- `symbol`
- `entry_stage`
- `consumer_check_side`
- `signal_timeframe`

### 6-2. interpreted context 입력
- `htf_alignment_state`
- `htf_alignment_detail`
- `htf_against_severity`
- `previous_box_break_state`
- `previous_box_relation`
- `previous_box_confidence`
- `previous_box_lifecycle`
- `context_conflict_state`
- `context_conflict_flags`
- `context_conflict_intensity`
- `context_conflict_score`
- `late_chase_risk_state`
- `late_chase_reason`
- `late_chase_confidence`
- `late_chase_trigger_count`
- `cluster_share_symbol_band`
- `share_context_label_ko`

### 6-3. raw / freshness 입력
- `trend_15m_strength_score`
- `trend_1h_strength_score`
- `trend_4h_strength_score`
- `trend_1d_strength_score`
- `distance_from_previous_box_high_pct`
- `distance_from_previous_box_low_pct`
- `trend_1h_age_seconds`
- `trend_4h_age_seconds`
- `trend_1d_age_seconds`
- `previous_box_age_seconds`

### 6-4. version / meta 입력
- `context_state_version`
- `htf_context_version`
- `previous_box_context_version`
- `conflict_context_version`

### 6-5. overlap guard 입력
가능하면 아래 bridge/신호도 함께 읽는다.

- `forecast_state25_runtime_bridge_v1`
- `belief_state25_runtime_bridge_v1`
- `barrier_state25_runtime_bridge_v1`
- `countertrend_continuation_signal_v1`


## 7. gating / freshness 규칙

### 7-1. freshness state

주요 context는 freshness를 3단계로 나눈다.

- `FRESH`
- `AGING`
- `STALE`

### 7-2. 반영 규칙

- `FRESH` = 100% 반영
- `AGING` = 50% 반영
- `STALE` = 조정 0, trace만 기록

### 7-3. component activation

bridge는 coarse skip보다 **component별 activation ratio**를 먼저 계산한다.

예:

```json
{
  "component_activation": {
    "htf": 1.0,
    "previous_box": 0.5,
    "late_chase": 1.0,
    "share": 0.2
  },
  "component_activation_reasons": {
    "previous_box": ["LOW_CONFIDENCE", "AGING"],
    "share": ["BOOSTER_ONLY"]
  }
}
```

이를 통해:
- HTF는 신선하면 강하게 반영
- previous_box는 confidence가 낮거나 aging이면 절반 반영
- share는 단독 authority가 아니라 약한 보조만 반영

### 7-4. skip / 약화 예시

- `previous_box_confidence = LOW` → previous_box activation 약화
- `previous_box_is_consolidation = false` → previous_box activation 약화 또는 skip
- `context_conflict_state = NONE` and `late_chase_risk_state = NONE` → threshold/size skip 가능


## 8. translator 설계

## 8-1. Weight translator

목적:
- 무엇을 더 믿고 덜 믿을지 조정

### 8-1-1. v1 핵심 원칙

**한 context 이벤트당 핵심 weight 2개까지만 조정한다.**

이유:
- hindsight에서 효과 분리 가능
- 과보정 방지
- rollback 단순화

### 8-1-2. v1 대표 매핑

#### `AGAINST_HTF`
- `reversal_risk_weight`: 하향
- `directional_bias_weight`: 상향

#### `BREAKOUT_HELD`
- `range_reversal_weight`: 하향
- `directional_bias_weight`: 상향

#### `RECLAIMED`
- `reversal_risk_weight`: 하향
- `participation_weight`: 상향

### 8-1-3. bias side 추정

bridge는 내부적으로 `context_bias_side`를 추정할 수 있다.

추가 필드:
- `context_bias_side`
- `context_bias_side_confidence`
- `context_bias_side_source_keys`

예:

```json
{
  "context_bias_side": "BUY",
  "context_bias_side_confidence": 0.72,
  "context_bias_side_source_keys": ["AGAINST_HTF", "BREAKOUT_HELD"]
}
```

### 8-1-4. late chase와 weight의 관계

`LATE_CHASE_RISK`는 v1에서 **weight의 주 입력으로 적극 사용하지 않는다.**

이유:
- late chase는 해석 bias 문제이기도 하지만,
- 더 본질적으로는 timing / risk 문제에 가깝다

그래서 v1에서는:
- `AGAINST_HTF`, `BREAKOUT_HELD`, `RECLAIMED` → weight 우선
- `LATE_CHASE_RISK` → threshold / size 우선

으로 역할을 나눈다.

late chase 기반 weight 조정은 필요해도 아주 약한 log-only candidate로만 남긴다.

### 8-1-5. 출력

- `weight_adjustments_requested`
- `weight_adjustments_effective`
- `weight_adjustments_suppressed`


## 8-2. Threshold translator

목적:
- 진입 문턱을 더 엄격하게 또는 완화되게 조정

### 8-2-1. 핵심 전제

threshold는 기존 abs-only 계약 위에 억지로 올리지 않는다.

bridge는 아래 3종 세트를 남긴다.

- `state25_threshold_log_only_delta_points`
- `threshold_delta_direction`
- `threshold_delta_reason_keys`

### 8-2-2. threshold signed contract

- `HARDEN` = 더 까다롭게
- `RELAX` = 덜 까다롭게

단, **v1 실제 활성 모드는 `HARDEN` only**로 둔다.

즉:
- schema에는 `RELAX` 자리를 남겨두되
- v1 운영에선 `HARDEN` 또는 `0`만 사용한다

### 8-2-3. 대표 초기 매핑

#### `AGAINST_HTF`
- `LOW` → 소폭 `HARDEN`
- `MEDIUM` → 중간 `HARDEN`
- `HIGH` → 강한 `HARDEN`

#### `AGAINST_PREV_BOX_AND_HTF`
- 강한 `HARDEN`

#### `LATE_CHASE_RISK = HIGH`
- 중간 이상 `HARDEN`

### 8-2-4. entry_stage multiplier / stage cap

threshold는 `entry_stage`에 따라 배율을 둘 수 있다.

- `aggressive` → 0.7x
- `balanced` → 1.0x
- `conservative` → 1.2x

그리고 stage별 최대 harden cap도 함께 둔다.

- `aggressive_threshold_cap`
- `balanced_threshold_cap`
- `conservative_threshold_cap`

예:
- aggressive max harden = 작은 값
- balanced max harden = 중간 값
- conservative max harden = 조금 더 큰 값

v1에서는 기본 자리만 열고, 실제 적용은 log-only trace로 먼저 검증한다.

### 8-2-5. 출력

- `threshold_adjustment_requested`
- `threshold_adjustment_effective`
- `threshold_adjustment_suppressed`


## 8-3. Size translator

목적:
- 맞더라도 얼마나 세게 들어갈지 줄이는 리스크 조정

### 8-3-1. 대표 입력
- `late_chase_risk_state`
- `context_conflict_intensity`
- `previous_box_confidence`

### 8-3-2. 대표 매핑

#### `late_chase_risk = HIGH`
- size 축소

#### `context_conflict_intensity = HIGH`
- size 축소

#### `previous_box_confidence = HIGH` and current side conflict
- size 축소

share는 단독 size authority가 아니다.

### 8-3-3. size floor 보호

추가 필드:
- `size_floor_protected`
- `size_floor_reason`
- `size_adjustment_state`

`size_adjustment_state` 예:
- `UNCHANGED`
- `REDUCED`
- `SUPPRESSED_BY_FLOOR`

예:

```json
{
  "size_multiplier_delta": -0.22,
  "candidate_size_min_multiplier": 0.80,
  "size_floor_protected": true,
  "size_floor_reason": "GLOBAL_MIN_GUARD",
  "size_adjustment_state": "SUPPRESSED_BY_FLOOR"
}
```

### 8-3-4. 출력

- `size_adjustment_requested`
- `size_adjustment_effective`
- `size_adjustment_suppressed`


## 9. overlap / double counting guard

### 9-1. 목적

forecast / belief / barrier / continuation 계열이 이미 같은 방향 불편함을 반영하고 있으면
bridge가 같은 의미를 다시 세게 반영하지 않도록 막는다.

### 9-2. 출력

- `double_counting_guard_active`
- `overlap_sources`
- `overlap_class`
- `stacking_limited`

`overlap_class` 예:
- `SAME_DIRECTION_DUPLICATE`
- `RISK_DUPLICATE`
- `WAIT_BIAS_DUPLICATE`
- `CONTINUATION_DUPLICATE`


## 10. cap / decay / stacking limit

### 10-1. knob별 max cap

초기에는 아주 작게 시작한다.

예:
- weight delta 절대값 최대 `0.20`
- threshold delta 절대값 최대 작은 범위
- size 감소 최대 `0.25`

### 10-2. decay

같은 context가 오래 지속돼도 100% 그대로 누적하지 않는다.

### 10-3. stacking limit

- 동일 계열 context는 최대 2개까지만 강하게 반영
- share는 never authority, only booster
- threshold와 size가 동시에 최대치까지 가는 것 금지


## 11. trace / 출력 스키마

bridge는 최소 아래 구조를 남긴다.

### 11-1. 기본 trace

- `context_inputs`
- `freshness`
- `component_activation`
- `component_activation_reasons`
- `weight_adjustments_requested`
- `weight_adjustments_effective`
- `threshold_adjustment_requested`
- `threshold_adjustment_effective`
- `size_adjustment_requested`
- `size_adjustment_effective`
- `caps_applied`
- `trace_lines_ko`
- `trace_reason_codes`

### 11-2. suppressed trace

조정이 요청됐지만 실제로 눌리거나 0이 된 경우도 구조적으로 남긴다.

- `weight_adjustments_suppressed`
- `threshold_adjustment_suppressed`
- `size_adjustment_suppressed`

### 11-3. decision counterfactual

v1에서는 먼저 **판단이 달라졌는가**만 안전하게 본다.

- `without_bridge_decision`
- `with_bridge_decision`
- `bridge_changed_decision`

예:

```json
{
  "decision_counterfactual": {
    "without_bridge_decision": "ENTER",
    "with_bridge_decision": "SKIP",
    "bridge_changed_decision": true
  }
}
```

### 11-4. outcome counterfactual

`outcome` counterfactual은 hindsight가 충분히 쌓인 뒤에만 켠다.

- `bridge_changed_outcome`
- `bridge_contribution`

즉 v1에서는 schema 자리만 열고,
실제 운영 평가는 decision counterfactual 위주로 시작한다.

### 11-5. explicit linkage keys

- `bridge_decision_id`
- `hindsight_link_key`
- `proposal_link_key`

### 11-6. override scope

weight 조정 trace에는 bounded rollout 범위를 읽기 쉽게 남긴다.

- `override_scope`
- `override_scope_detail`

예:

```json
{
  "override_scope": "SYMBOL_CONTEXT_ONLY",
  "override_scope_detail": {
    "symbol": "NAS100",
    "entry_stage": "balanced",
    "context_conflict_state": "AGAINST_PREV_BOX_AND_HTF"
  }
}
```


## 12. failure / guard modes

### 12-1. failure modes

- `STALE_CONTEXT_SUPPRESSED`
- `LOW_CONFIDENCE_CONTEXT`
- `SIGNED_THRESHOLD_UNAVAILABLE`

### 12-2. guard modes

- `DOUBLE_COUNTING_SUPPRESSED`
- `CAP_HIT`
- `SIZE_FLOOR_PROTECTED`


## 13. rollout 원칙

### 13-1. 우선순위

1. `weight`
2. `threshold`
3. `size`

### 13-2. 이유

- `weight`는 해석 bias 조정이라 가장 안전
- `threshold`는 행동 자체를 바꾸므로 계약 정리가 먼저 필요
- `size`는 실제 돈 크기를 건드리므로 가장 마지막

### 13-3. 첫 bounded live

첫 실제 bounded live는 **weight-only**가 맞다.

### 13-4. rollback trigger

rollout 문서에는 항상 아래 3종이 같이 있어야 한다.

1. 시작 조건
2. 관찰 지표
3. rollback 조건

예시 rollback trigger:
- reversal precision 급락
- continuation false positive 증가
- late chase 개선 없음
- skip 증가만 있고 PnL 개선 없음


## 14. v1에서 의도적으로 하지 않는 것

- HTF로 side 강제 뒤집기
- previous box로 자동 진입 차단
- share를 direction authority로 승격
- threshold / size / weight를 한 번에 전면 live 적용
- trend_quality의 정교한 실계산
- context를 decision core score식에 직접 하드코딩
- `RELAX`의 실제 live 활성화
- late chase의 공격적 weight 보정


## 15. 한 줄 결론

`state25_context_bridge_v1`은
**state-first context를 기존 state25의 `weight / threshold / size` 손잡이에 작고 bounded한 조정값으로 번역하는 adapter**다.

즉 새 엔진이 아니라,
기존 엔진이 큰 그림을 덜 놓치게 만드는 보정 계층이다.
