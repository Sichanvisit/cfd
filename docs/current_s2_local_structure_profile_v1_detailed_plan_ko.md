# S2 local_structure_profile_v1 상세 계획

## 1. 목적

`S2`의 목표는 최근 3~9개 캔들에서 드러나는 구조 변화를 공용 상태 필드로 surface하는 것이다.

이 단계는 패턴 이름을 붙이는 단계가 아니다.
대신 다음을 묻는다.

- higher low / lower high 구조가 유지되는가
- breakout 이후 실제로 hold가 유지되는가
- 최근 drive가 continuation 쪽인가, counter 쪽인가

즉 `S2`는 local structure를 **상태 등급**으로 고정하는 read-only 계약이다.

## 2. 왜 S2가 필요한가

S1만으로도 `continuation_integrity / reversal_evidence / friction`을 볼 수 있지만,
그 값이 최근 몇 개 캔들의 구조 변화와 어떻게 맞물리는지까지는 아직 설명하지 못한다.

그래서 S2는 다음 문제를 줄이는 역할을 한다.

- 강세를 보면서도 왜 경계로 소비됐는지 설명 부족
- breakout hold와 false break의 차이를 row-level에서 설명 부족
- continuation with friction과 실제 reversal 시작을 local structure로 구분 부족

## 3. v1 핵심 축

v1 primary axes:

- `few_candle_higher_low_state_v1`
- `few_candle_lower_high_state_v1`
- `breakout_hold_quality_v1`
- `body_drive_state_v1`

secondary axes는 뒤로 미룬다.

- `retest_quality_state_v1`
- `wick_rejection_state_v1`
- `few_candle_continuation_hint_v1`
- `few_candle_reversal_hint_v1`

## 4. v1 상태 등급

### 4-1. swing 구조

`few_candle_higher_low_state_v1`
`few_candle_lower_high_state_v1`

enum:

- `INSUFFICIENT`
- `BROKEN`
- `FRAGILE`
- `HELD`
- `CLEAN_HELD`

### 4-2. breakout hold

`breakout_hold_quality_v1`

enum:

- `INSUFFICIENT`
- `FAILED`
- `WEAK`
- `STABLE`
- `STRONG`

### 4-3. body drive

`body_drive_state_v1`

enum:

- `COUNTER_DRIVE`
- `NEUTRAL`
- `WEAK_DRIVE`
- `STRONG_DRIVE`

### 4-4. local structure bias

`few_candle_structure_bias_v1`

enum:

- `CONTINUATION_FAVOR`
- `MIXED`
- `REVERSAL_FAVOR`
- `INSUFFICIENT`

## 5. v1 계산 재료

이번 버전은 raw candle 전체를 다시 계산하지 않고, 현재 row에 이미 들어와 있는 구조 재료를 재사용한다.

주요 입력:

- `breakout_event_runtime_v1`
- `checkpoint_runtime_hold_quality_score`
- `previous_box_high_retest_count`
- `previous_box_low_retest_count`
- `previous_box_break_state`
- `previous_box_relation`
- `leg_direction`
- `state_strength_side_seed_v1`

즉 v1 local structure는 “완전한 캔들 복원”이 아니라, 이미 있는 breakout/retest/hold proxy를 정리하는 단계다.

## 6. 계산 원칙

### 6-1. higher low / lower high

v1에서는 side seed를 기준으로 구조 건강도를 본다.

- `BULL` seed면 higher low 상태를 더 적극적으로 해석
- `BEAR` seed면 lower high 상태를 더 적극적으로 해석

즉 local structure는 seed를 새로 만들지 않고, seed를 지지/혼합/훼손하는 방향으로 읽는다.

### 6-2. breakout hold quality

아래를 조합해 본다.

- `checkpoint_runtime_hold_quality_score`
- `breakout_state`
- `breakout_retest_status`
- `breakout_failure_risk`
- `previous_box_break_state`

즉 “돌파했는가”보다 “돌파 후 유지되는가”를 중심으로 본다.

### 6-3. body drive state

아래를 조합한다.

- `breakout_strength`
- `breakout_followthrough_score`
- `breakout_failure_risk`
- `breakout_direction`
- `leg_direction`

즉 최근 구조가 실제로 continuation 방향 body drive로 이어지고 있는지, 아니면 counter drive가 생겼는지를 본다.

## 7. 하지 말아야 할 것

- 패턴 이름으로 직접 분류하지 않는다
- side를 local structure만으로 새로 만들지 않는다
- execution/state25를 직접 바꾸지 않는다
- raw candle 복원을 억지로 하다가 v1 범위를 키우지 않는다

## 8. 산출물

문서:

- `current_s2_local_structure_profile_v1_detailed_plan_ko.md`
- `current_s2_local_structure_profile_v1_execution_roadmap_ko.md`

코드:

- `backend/services/local_structure_profile_contract.py`

runtime/detail:

- `local_structure_profile_contract_v1`
- `local_structure_summary_v1`
- `local_structure_artifact_paths`

artifact:

- `data/analysis/shadow_auto/local_structure_summary_latest.json`
- `data/analysis/shadow_auto/local_structure_summary_latest.md`
