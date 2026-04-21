# State Strength / Local Structure 해석 축 실행 로드맵

## 1. 목적

이 로드맵은 새로운 실전 bias를 즉시 live에 적용하는 계획이 아니다.

목적은 아래 두 가지다.

1. 현재 CA2, R0~R6-A, canonical surface, should-have-done 위에 `state strength + local structure` 해석층을 read-only로 먼저 세운다.
2. 그 해석층이 실제로 가치가 있는지 검증한 뒤에만 shadow bias, execution, state25 쪽으로 영향력을 넓힌다.

즉 순서는 언제나

`언어 고정 -> read-only surface -> audit/accuracy -> shadow-only -> 그 다음 영향력`

이어야 한다.

## 2. 현재 시작점

현재 기준 상태:

- R0: `HOLD`지만 surface와 flow sync는 살아 있음
- R1: `READY`, 그러나 세션 차이는 `NOT_SIGNIFICANT`
- R2: `READY`
- R3: `READY`
- R4: `READY`
- R5: `HOLD`
- R6-A: `READY`, 그러나 `KEEP_NEUTRAL`
- state25: 여전히 `log_only`

즉 지금은 `session bias를 더 세게 쓰자`보다 **state/local structure 해석층을 새로 세우는 편이 더 값이 큰 시점**이다.

## 3. 단계별 로드맵

### S0. 기존 계측 안정 유지

목적:

- 새 해석층을 얹더라도 기존 CA2/R0~R6-A가 깨지지 않게 유지한다.

핵심 작업:

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `ca2_session_split_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `session_bias_shadow_summary_v1`

가 계속 정상 surface되는지 확인한다.

완료 기준:

- 기존 artifact와 runtime detail 필드가 계속 갱신된다.

상태 기준:

- `READY`: 기존 surface/summary가 유지됨
- `HOLD`: 일부 artifact freshness나 detail surface가 흔들림
- `BLOCKED`: 새 해석층 때문에 기존 계측이 깨짐

### S1. state strength contract 정의

목적:

- "강하다/약하다/경계가 세다/실행 마찰이 세다"를 같은 언어로 읽는 최소 계약을 만든다.

핵심 작업:

- `state_strength_profile_contract_v1` 정의
- 원인 계층 고정:
  - `trend_pressure`
  - `continuation_integrity`
  - `reversal_evidence`
  - `friction`
  - `exhaustion_risk`
  - `ambiguity`
- 도출 계층 고정:
  - `wait_bias_strength`
  - `dominance_gap`
  - `dominant_side`
  - `dominant_mode`
  - `caution_level`

중요 원칙:

- `wait_bias_strength`는 원인 필드가 아니라 도출 필드로 취급한다.
- 개념 모델은 6축을 유지하지만, v1 계산 우선순위는 4축으로 좁힌다.
- v1에서 `dominance_gap`은 `continuation_integrity - reversal_evidence`로 고정한다.
- 이 단계에서는 점수 의미와 우세 해석만 정의한다.
- execution/state25에 직접 영향은 없다.

완료 기준:

- 원인층과 도출층이 분리된 상태로 enum/score 범위/우세 해석 규칙이 고정된다.
- v1 우선 구현 축이 문서에 명시된다.

상태 기준:

- `READY`: 공용 계약이 고정됨
- `HOLD`: 축 이름은 있으나 의미 정의가 흔들림
- `BLOCKED`: 강세/경계/실행마찰이 서로 다른 언어로 표현됨

### S2. local structure contract 정의

목적:

- 최근 3~9개 캔들을 중심으로 continuation/reversal 구조를 읽는 최소 계약을 만든다.

핵심 작업:

- `local_structure_profile_contract_v1` 정의
- 1차 핵심 축 고정:
  - `few_candle_higher_low_state`
  - `few_candle_lower_high_state`
  - `breakout_hold_quality`
  - `body_drive_state`
- 2차 보조 축은 뒤로 미룸:
  - `retest_quality_state`
  - `wick_rejection_state`
  - `few_candle_continuation_hint`
  - `few_candle_reversal_hint`

중요 원칙:

- 세션은 이 단계의 주인공이 아니다.
- 패턴 이름보다 구조 상태 변화를 본다.
- 심볼 이름이 아니라 공용 구조만 본다.
- 첫 버전은 3축 우선, 나머지는 뒤로 미룬다.
- local structure는 seed direction을 직접 생성하기보다 지지/혼합/훼손하는 방향으로 사용한다.

완료 기준:

- timebox audit에서 같은 구조를 같은 필드로 읽을 수 있고, 첫 버전은 1차 핵심 축만으로도 설명력이 생긴다.

상태 기준:

- `READY`: 구조 축과 상태명이 고정됨
- `HOLD`: 구조 축은 있으나 timebox 적용 규칙이 모호함
- `BLOCKED`: 스크린샷 장면을 같은 언어로 재현할 수 없음

### S3. runtime read-only surface 추가

목적:

- state strength와 local structure를 실제 runtime row에 read-only로 surface한다.

핵심 작업:

- `state_strength_profile_v1` runtime builder 추가
- `local_structure_profile_v1` runtime builder 추가
- `consumer_veto_tier_v1` read-only surface 추가
- `runtime_status.detail.json`에 row-level surface 추가
- summary artifact 생성

예상 surface:

- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `consumer_veto_tier_v1`
- `state_strength_summary_v1`
- `local_structure_summary_v1`

완료 기준:

- NAS/XAU/BTC row에서 공통 필드로 읽히고, `reversal evidence`와 `continuation with friction`이 구분되어 보인다.

상태 기준:

- `READY`: 세 심볼 모두 동일 계약으로 surface됨
- `HOLD`: 일부 심볼만 surface됨
- `BLOCKED`: runtime payload 과부하나 surface 누락이 발생함

### S4. dominance resolver shadow-only

목적:

- state strength + local structure + session bias를 합쳐 최종 우세 해석을 read-only로 계산한다.

핵심 작업:

- `state_structure_dominance_profile_v1` 생성
- 최소 출력:
  - `dominant_side_v1`
  - `dominant_mode_v1`
  - `caution_level_v1`
  - `dominance_gap_v1`
  - `dominance_reason_summary_v1`
  - `local_continuation_discount_v1`
  - `would_override_caution_v1`

중요 원칙:

- session은 bias layer로만 사용
- `consumer veto`는 아래 tier로 분리한다.
  - `FRICTION_ONLY`
  - `BOUNDARY_WARNING`
  - `REVERSAL_OVERRIDE`
- `execution_change_allowed = false`
- `state25_change_allowed = false`
- `ambiguity`는 side 반전보다 `BOUNDARY`와 `caution_level` 조정에 우선 사용한다.
- threshold는 고정값이 아니라 초기 calibration 값으로 둔다.
- `friction`은 `dominant_side`를 바꾸지 못하고 `dominant_mode`와 `caution_level`만 조정한다.
- `REVERSAL_OVERRIDE`는 continuation 약화 + reversal 증거 + structure break 조합이 있을 때만 허용한다.

완료 기준:

- 현재처럼 `BUY_WATCH인데 WAIT/SELL로 소비되는` 장면에서 dominance 설명이 가능해지고, `WAIT`가 마찰인지 전환 위험인지 구분된다.
- `dominance_gap`이 중심 비교 필드로 작동한다.

상태 기준:

- `READY`: dominance profile이 row/summary에 안정적으로 남는다
- `HOLD`: 일부 장면만 설명 가능
- `BLOCKED`: dominance가 기존 canonical surface와 충돌만 늘림

### S5. should-have-done / canonical surface와 결합한 검증

목적:

- 새 dominance 해석이 실제 review 가치가 있는지 검증한다.

핵심 작업:

- R3 candidate와 dominance profile join
- R4 canonical surface와 dominance profile join
- `dominance_vs_should_have_done_summary_v1`
- `dominance_vs_runtime_execution_gap_summary_v1`
- 후보별 calibration 필드 추가:
  - `expected_dominant_side_v1`
  - `expected_dominant_mode_v1`
  - `expected_caution_level_v1`
  - `dominance_error_type_v1`
  - `overweighted_caution_fields_v1`
  - `undervalued_continuation_evidence_v1`
  - `side_seed_source_v1`

핵심 질문:

- dominance가 should-have-done과 더 자주 맞는가
- dominance가 runtime/execution divergence를 줄일 가능성이 있는가
- dominance가 caution 과소비를 설명하는가

완료 기준:

- NAS/XAU/BTC 대표 장면에서 새 dominance 해석이 기존 surface보다 설명력이 높다는 근거가 생긴다.

상태 기준:

- `READY`: should-have-done과 유의미한 정렬이 보임
- `HOLD`: 설명력은 있으나 표본 부족
- `BLOCKED`: 기존 canonical surface보다 더 나은 설명을 못 함

### S6. dominance accuracy / shadow bias

목적:

- 새 해석층을 accuracy와 shadow-only bias로 검증한다.

핵심 작업:

- `dominance_accuracy_summary_v1`
- `dominance_candidate_shadow_report_v1`
- 세션별/구조별/심볼별 summary
- 검증 순서 고정:
  - `dominance_gap vs 20-bar direction`
  - `discount 적용/미적용 비교`
  - `guard/promotion 정합`
- 핵심 지표 우선:
  - `over_veto_rate`
  - `under_veto_rate`
  - `friction_separation_quality`
  - `boundary_dwell_quality`

중요 원칙:

- 이 단계에서도 실제 execution/state25 변경 금지
- 먼저 `would_change_*`만 남긴다
- discount는 `friction`과 `wait_bias_strength`에만 적용하고, `reversal_evidence`를 무효화하지 않는다.

완료 기준:

- `dominance`가 단순 설명을 넘어 review/accuracy 축에서 유의미한 신호를 만든다.

상태 기준:

- `READY`: shadow-only로도 의미 있는 차이가 보임
- `HOLD`: 데이터는 쌓이나 우세 차이가 약함
- `BLOCKED`: shadow 결과가 계속 neutral/no-edge에 머묾

### S7. execution/state25 연결 판단

목적:

- 여기서 처음으로 실제 영향력 확대 여부를 판단한다.

전제 조건:

- S0~S6 안정
- should-have-done과 dominance 정렬이 누적됨
- dominance accuracy가 기존 canonical 설명보다 가치 있음
- bias가 세션 하드코딩이 아니라 구조/상태 기반으로 설명 가능

중요 원칙:

- 여기서도 바로 전면 live 적용 금지
- `execution canary -> state25 canary` 순서

현재 상태:

- **BLOCKED**

이유:

- 지금은 아직 dominance layer 자체가 없다.
- R5도 phase 라벨 부족으로 HOLD다.
- session bias도 전부 neutral observe 상태다.

## 4. 우선순위

지금 당장 할 일 우선순위는 아래가 맞다.

1. `S1 state strength contract`
2. `S2 local structure contract`
3. `S3 runtime read-only surface`
4. `S4 dominance resolver shadow-only`
5. `S5 should-have-done / canonical join`
6. `S6 dominance accuracy`
7. `S7 execution/state25 판단`

즉 지금은 execution/state25가 아니라 **언어와 read-only profile**이 우선이다.

## 5. v1 구현 절차 고정

S1~S6 구현은 아래 순서를 따른다.

1. `side_seed`를 먼저 정한다.
2. 원인 계층을 계산한다.
3. local structure를 상태 등급으로 surface한다.
4. `dominance_gap`을 계산한다.
5. `dominant_mode`를 정한다.
6. `veto_tier`와 `caution_level`을 정한다.
7. 제한적인 discount를 마지막에만 적용하고 final dominance surface를 출력한다.

## 6. 구현 판단 기준

아래 질문에 "예"가 되면 다음 단계로 넘어간다.

### S1 -> S2

- 강세/경계/실행마찰을 한 장면에서 동시에 표현할 수 있는가

### S2 -> S3

- 최근 몇 개 캔들로 continuation/reversal 힌트를 공용 필드로 표현할 수 있는가

### S3 -> S4

- runtime row에 state/local structure를 안정적으로 surface할 수 있는가

### S4 -> S5

- dominance profile이 "왜 BUY_WATCH인데 WAIT가 됐는가"를 설명할 수 있는가

### S5 -> S6

- should-have-done과 canonical divergence를 dominance가 더 잘 설명하는가

### S6 -> S7

- shadow-only 결과만으로도 방향 우세 조정 가치가 있는가

## 6. 한 줄 결론

지금부터의 구현은 세션 bias를 더 세게 거는 작업이 아니라,
**강한 state와 최근 캔들 구조를 분해해 어느 해석이 우세한지 설명하는 read-only 해석층을 먼저 만드는 작업**이어야 한다.
