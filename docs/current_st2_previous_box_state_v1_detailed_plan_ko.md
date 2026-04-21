# ST2 Previous Box State v1 상세 계획

## 목표

`previous box`를 detector가 매번 임시 추정하지 않게,
upstream 공용 계산기로 `raw + interpreted previous box state v1`를 만든다.

이번 단계의 핵심은:

- `shifted range + swing hybrid`
- `mode / confidence / is_consolidation`
- `previous_box_relation / previous_box_break_state`
- `previous_box_lifecycle` 최소 rule

을 공통 계약으로 고정하는 것이다.


## 왜 ST2가 필요한가

현재 사용자가 차트에서 강하게 느끼는 불만 중 하나는:

- 이미 직전 박스 상단 위에서 유지 중인데
- 시스템은 아직 `upper reject`나 역방향 맥락처럼 읽는 장면

이다.

이 문제는 wick/force 자체보다
`현재가가 직전 박스와 어떤 관계인지`
를 latest state contract가 충분히 못 담기 때문에 생긴다.

따라서 detector를 더 복잡하게 만들기 전에,
`previous box`를 state 차원에서 먼저 계산해 공통 기준으로 올리는 게 맞다.


## 이번 단계 범위

이번 `ST2`에서 구현할 것:

- `backend/services/previous_box_calculator.py`
- `current box = 최근 N봉`
- `previous box = 그 이전 N봉`
- previous box range 계산
- consolidation 여부
- retest count 기반 confidence/mode
- relation / break_state / lifecycle 최소 rule

이번 단계에서 하지 않을 것:

- runtime latest payload 합류
- detector/notifier/propose 연결
- 완전한 구조 박스 탐지기
- 세션/심볼별 box 정의 분기

즉 이번 단계는 `previous box`를 state 계약으로 먼저 굳히는 단계다.


## 구현 원칙

### 1. v1은 mechanical + structural hybrid

이번 버전은 완전한 consolidation detector가 아니라:

- 이전 N봉 range
- 현재 N봉 range
- swing retest count

를 같이 보는 `shifted range + swing hybrid`로 간다.

### 2. previous box는 신뢰도와 함께 읽어야 한다

이번 단계에서 같이 계산:

- `previous_box_mode`
  - `MECHANICAL`
  - `STRUCTURAL`
- `previous_box_confidence`
  - `LOW`
  - `MEDIUM`
  - `HIGH`
- `previous_box_is_consolidation`

즉 downstream은 `박스 값`만 읽는 게 아니라,
이 박스가 얼마나 믿을 만한 박스인지도 함께 읽게 된다.

### 3. lifecycle은 얇은 최소 rule만 둔다

이번 단계에서 lifecycle은 완전판이 아니라 최소 rule만 둔다.

- `CONFIRMED`
- `BROKEN`
- `RETESTED`
- `INVALIDATED`
- `FORMING`

이 정도만 먼저 넣고, 이후 `v2`에서 더 구조적으로 정교화한다.


## 입력

기본 입력:

- `open`
- `high`
- `low`
- `close`
- `time`

선택 입력:

- `current_price`
- `proxy_state`
  - `swing_high_retest_count_20`
  - `swing_low_retest_count_20`
  - `micro_swing_high_retest_count_20`
  - `micro_swing_low_retest_count_20`


## 계산 규칙

### previous box 정의

- `current_window = 최근 20봉`
- `previous_window = 그 이전 20봉`

### consolidation

- `previous_span = previous_high - previous_low`
- `avg_atr = previous_window 근처 ATR 평균`
- `previous_span < avg_atr * 3.0`
  - `true` -> 박스형 구간
  - `false` -> 추세형 구간

### retest count

- previous window 내부에서
  - high pivot 근처 반복 접촉
  - low pivot 근처 반복 접촉

를 tolerance 기반으로 센다.

### confidence / mode

- consolidation true + 양쪽 retest 존재 -> `HIGH / STRUCTURAL`
- consolidation true 또는 retest 합이 충분 -> `MEDIUM / STRUCTURAL`
- 그 외 -> `LOW / MECHANICAL`

### relation

- `ABOVE`
- `BELOW`
- `AT_HIGH`
- `AT_LOW`
- `INSIDE`

### break_state

- `BREAKOUT_HELD`
- `BREAKOUT_FAILED`
- `BREAKDOWN_HELD`
- `RECLAIMED`
- `REJECTED`
- `INSIDE`

### lifecycle 최소 rule

- `INVALIDATED`
  - confidence LOW and consolidation false
- `BROKEN`
  - break_state in
    - `BREAKOUT_HELD`
    - `BREAKOUT_FAILED`
    - `BREAKDOWN_HELD`
    - `RECLAIMED`
- `RETESTED`
  - relation in `AT_HIGH`, `AT_LOW`
  - confidence in `MEDIUM`, `HIGH`
- `CONFIRMED`
  - consolidation true
  - confidence in `MEDIUM`, `HIGH`
- 그 외
  - `FORMING`


## Previous Box State v1 출력 계약

### raw

- `previous_box_high`
- `previous_box_low`
- `previous_box_mid`
- `previous_box_mode`
- `previous_box_confidence`
- `previous_box_lifecycle`
- `previous_box_is_consolidation`
- `distance_from_previous_box_high_pct`
- `distance_from_previous_box_low_pct`
- `previous_box_high_retest_count`
- `previous_box_low_retest_count`

### interpreted

- `previous_box_relation`
- `previous_box_break_state`

### meta

- `previous_box_updated_at`
- `previous_box_age_seconds`
- `previous_box_data_state`
- `previous_box_context_version`
- `previous_box_state_version`
- `previous_box_calculator_version`


## 테스트 원칙

단위 테스트에서 검증할 것:

- insufficient bars fallback
- consolidating previous box -> confirmed structural box
- breakout held
- non-consolidation invalidated
- proxy retest 입력 수용


## 완료 기준

- `previous_box_calculator.py` 존재
- standalone 계산 가능
- `mode / confidence / lifecycle / break_state` 반환
- unit test 통과
- `py_compile` 통과
