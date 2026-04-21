# 세션 인지 방향/지속성 학습 실행 로드맵

## 1. 목적

이 로드맵은 세션/방향/지속성 축을 한 번에 다 구현하는 문서가 아니다.
핵심은 아래 두 가지를 분리하는 것이다.

1. **지금 바로 시작할 최소 annotation 계약**
2. **CA2 세션 분해 근거가 쌓인 뒤에만 확대할 영향력**

즉 이 로드맵은 “빨리 많은 기능을 붙이자”가 아니라,
**annotation 언어를 먼저 만들고, 그 언어가 실제로 가치 있는지 확인한 뒤 영향력을 키우자**는 실행 순서를 고정한다.

## 2. 현재 위치

현재까지 이미 확보된 것:

- `runtime row`
- `execution_diff`
- `continuation_accuracy`
- `flow history`
- `window timebox audit`
- `state25 / forecast / belief / barrier`

즉 지금은 재료를 더 모으는 단계가 아니다.
이미 있는 재료를 세션과 지속성 문맥으로 묶는 언어 체계를 세우는 단계다.

다만 동시에 CA2 검증도 진행 중이므로, 세션-aware 영향력을 execution/state25에 바로 올리면 해석이 섞일 위험이 있다.

따라서 순서는:

1. 최소 annotation 계약
2. CA2 지표의 세션 분해
3. should-have-done 축
4. canonical surface
5. session-aware accuracy
6. 그 뒤 execution/state25 연결

로 가져간다.

## 3. 단계별 로드맵

### R0. CA2 안정 유지

목적:

- 현재의 `execution_diff`, `continuation_accuracy`, `guard/promotion` 지표를 계속 안정적으로 쌓는다.

핵심 작업:

- 기존 CA2 집계를 깨지 않도록 유지
- 세션-aware 축을 추가하더라도 기존 KPI 계산을 방해하지 않게 한다

완료 기준:

- `execution_diff_surface_count`
- `flow_sync_match_count`
- `primary_correct_rate`
가 기존 방식으로 계속 누적됨

상태 기준:

- `READY`: 기존 CA2 지표가 안정적으로 계속 쌓임
- `HOLD`: detail/trace 누락이 간헐적으로 발생
- `BLOCKED`: 기본 CA2 집계가 깨짐

### R0-1. R1 시작 전 session_bucket helper 고정

목적:

- R1 세션 분해 집계가 매번 다른 기준을 쓰지 않도록, session helper의 시간 경계를 먼저 고정한다.

v1 시간 경계:

- `ASIA`
  - `06:00 ~ 15:00 KST`
- `EU`
  - `15:00 ~ 21:00 KST`
- `EU_US_OVERLAP`
  - `21:00 ~ 00:00 KST`
- `US`
  - `00:00 ~ 06:00 KST`

v1 원칙:

- 첫 버전에서는 **고정 4구간**만 사용
- 첫 버전에서는 **서머타임 자동 보정 없음**
- 첫 버전에서는 **전환 구간 bucket 없음**

후속 확장:

- `ASIA_TO_EU_TRANSITION`
- `EU_TO_US_TRANSITION`

같은 전환 버킷은 R5에서 세션별 accuracy를 본 뒤 필요할 때만 추가한다.

완료 기준:

- R1 집계가 항상 같은 4구간 session helper를 사용함

상태 기준:

- `READY`: helper 경계와 enum이 고정됨
- `HOLD`: 경계는 있으나 일부 consumer가 다르게 씀
- `BLOCKED`: session helper 기준이 계속 바뀜

### R1. CA2 지표의 세션 분해

목적:

- 기존 continuation/accuracy/KPI를 세션별로 분해해 “정말 세션 차이가 있는지”를 숫자로 확인한다.

핵심 작업:

- `session_bucket` helper 도입
- `continuation_accuracy`를 세션별로 분해
- `execution_diff`, `guard`, `promotion` KPI를 세션별로 읽을 수 있게 분해

중요 원칙:

- 이 단계에서는 세션이 방향이나 실행을 바꾸지 않는다.
- 오직 **read-only 분석 축**으로만 사용한다.

완료 기준:

- `correct_rate_by_session`
- `measured_count_by_session`
- `guard_helpful_rate_by_session`
- `promotion_win_rate_by_session`
를 읽을 수 있음

세션 차이 유의미 판정 기준:

- 양쪽 세션 모두 `measured_count >= 20`
  - 이 조건을 못 채우면 `표본 부족`
- 정확도 차이 `>= 15%p`
  - `유의미`
  - 이후 annotation과 bias 해석에서 적극 반영 가능
- 정확도 차이 `10~15%p`
  - `참고 수준`
  - annotation에는 남기되 weighting 확대는 보류
- 정확도 차이 `< 10%p`
  - `유의미하지 않음`
  - 세션 축은 유지하되 핵심 결정 변수로 올리지 않음

적용 원칙:

- 이 유의미 판정은 R1에서 “세션 차이가 진짜 있는가”를 읽는 기준이다.
- 이 기준만으로 곧바로 execution/state25에 session bias를 적용하지는 않는다.
- 실제 영향력 확대는 R5 이후에 다시 판단한다.

상태 기준:

- `READY`: 세션별 표본과 지표가 읽힘
- `HOLD`: 세션 구분은 되지만 표본 부족
- `BLOCKED`: 세션 구분 helper 또는 집계가 불안정

### R2. 최소 annotation contract 정의

목적:

- 구조 인식을 위한 공용 annotation 언어를 최소형으로 고정한다.

계약:

- `direction_annotation`
- `continuation_annotation`
- `continuation_phase_v1`
- `session_bucket`
- `annotation_confidence`

중요 원칙:

- `phase`는 3단계로 시작
  - `CONTINUATION`
  - `BOUNDARY`
  - `REVERSAL`
- `session_bucket`은 bias/context용 필드
- 세션이 직접 `BUY/SELL`을 만들지 않음

완료 기준:

- chart/timebox/runtime 어디서든 같은 필드명으로 annotation을 기록할 수 있음

상태 기준:

- `READY`: 최소 필드와 enum이 고정됨
- `HOLD`: enum은 있으나 정의가 흔들림
- `BLOCKED`: 필드 의미가 자주 바뀜

### R3. timebox audit → should-have-done label 확장

목적:

- 운영자 스크린샷/메모와 자동 hindsight를 같은 학습 축으로 축적할 수 있게 한다.

핵심 작업:

- timebox audit 결과에
  - `expected_direction`
  - `expected_continuation`
  - `expected_phase_v1`
  - `expected_surface`
  - `annotation_confidence`
  - `operator_note`
  를 추가
- 자동 후보와 수동 판정을 같이 다루는 혼합 구조 도입

confidence 정책:

- `MANUAL_HIGH`
- `AUTO_HIGH`
- `AUTO_MEDIUM`
- `AUTO_LOW`

완료 기준:

- 같은 시간대 장면에 대해 “실제 출력”과 “should-have-done”이 같이 저장됨

상태 기준:

- `READY`: 자동/수동 혼합 라벨 저장 가능
- `HOLD`: 라벨 구조는 있으나 confidence 기준 미정
- `BLOCKED`: 수동 메모와 자동 hindsight가 서로 다른 형태로 분리됨

### R4. canonical surface builder

목적:

- chart / runtime / execution / hindsight가 같은 언어를 쓰게 만든다.

예시:

- `BUY_WATCH + CONTINUING + CONTINUATION`
- `SELL_WATCH + CONTINUING + BOUNDARY`
- `SELL_PROBE + NON_CONTINUING + REVERSAL`

중요 원칙:

- 이 단계는 R2, R3 결과를 보고 설계한다.
- 지금 시점에서 전체 surface 종류를 미리 과도하게 고정하지 않는다.

완료 기준:

- chart surface, runtime surface, should-have-done label이 같은 annotation 핵심 필드를 공유함

상태 기준:

- `READY`: 공용 surface가 최소형으로 동작
- `HOLD`: 일부 consumer만 공유
- `BLOCKED`: chart/runtime/execution이 서로 다른 언어를 유지

### R5. session-aware annotation accuracy

목적:

- annotation 자체가 실제로 맞는지 검증한다.

핵심 지표:

- `correct_rate_by_session`
- `phase_accuracy`
- `session_effectiveness`
- `direction_bias_gap_by_session`

중요 원칙:

- 이 단계부터는 continuation accuracy뿐 아니라 annotation accuracy를 본다.
- 세션 차이가 실제로 유의미한지 먼저 증명한다.

완료 기준:

- `US`, `ASIA`, `EU`, `EU_US_OVERLAP`별 annotation 성능을 비교 가능

상태 기준:

- `READY`: 세션별 annotation 정확도 차이가 해석 가능
- `HOLD`: 차이는 있으나 표본 부족
- `BLOCKED`: annotation 자체가 아직 불안정

### R6. execution/state25/forecast 연결

목적:

- 검증된 annotation 차이를 execution/state25/forecast에 반영한다.

중요 원칙:

- 이 단계는 **R1~R5의 근거가 쌓인 뒤에만** 시작한다.
- 세션이 직접 방향을 강제하지 않는다.
- 세션-aware weight/bias는 execution/state25에서 보조 가중으로만 사용한다.

가능한 적용 예:

- session-aware continuation weight 조정
- forecast confidence bias 조정
- state25 review weighting 보정
- guard/promotion sensitivity bias 조정

완료 기준:

- session-aware adjustment가 하드코딩이 아니라 근거 있는 bias layer로 작동함

상태 기준:

- `READY`: 세션별 차이가 충분히 유의미하고 bias layer가 설명 가능함
- `HOLD`: 차이는 보이나 영향력 적용 근거가 아직 약함
- `BLOCKED`: 세션을 직접 BUY/SELL 규칙으로 쓰려는 유혹이 생김

## 4. 하지 말아야 할 것

- 세션을 직접 `BUY/SELL` 규칙으로 하드코딩
- NAS/XAU/BTC별 예외를 annotation contract에 섞기
- phase를 초기에 과도하게 세분화
- operator note를 confidence 없이 전부 같은 학습 데이터로 사용
- annotation intuition만으로 bounded live를 곧바로 바꾸기
- R1~R5 근거 없이 execution/state25에 session bias를 바로 적용

## 5. 단계별 우선순위

가장 가까운 순서:

1. `R1` 세션 분해 read-only 분석
2. `R2` 최소 annotation contract
3. `R3` should-have-done label 축

그다음:

4. `R4` canonical surface
5. `R5` session-aware annotation accuracy

마지막:

6. `R6` execution/state25/forecast 연결

즉 지금 상세하게 다뤄야 할 것은 `R1~R3`이고,
`R4~R6`는 방향만 고정하고 실제 설계는 앞 단계 결과를 보고 조정한다.

## 6. READY / HOLD / BLOCKED 판정 기준

### 6-1. 현재 시점에서 기대하는 상태

- `R1`
  - 목표: `READY`
- `R2`
  - 목표: `READY`
- `R3`
  - 목표: `HOLD -> READY`
- `R4`
  - 현재 기대: `HOLD`
- `R5`
  - 현재 기대: `HOLD`
- `R6`
  - 현재 기대: `BLOCKED`

### 6-2. 의미

- `READY`
  - 지금 바로 진행 가능
- `HOLD`
  - 구조는 필요하지만 앞 단계 결과가 더 필요
- `BLOCKED`
  - 지금 건드리면 검증 체계를 오염시킬 위험이 큼

## 7. 결론

이 로드맵의 핵심은 세션/방향/지속성 축을 “많이 추가”하는 것이 아니라,

1. 최소 annotation 언어를 만들고
2. 기존 CA2/accuracy를 세션별로 읽어보고
3. should-have-done을 confidence 있게 축적한 뒤
4. 그 다음에만 chart/runtime/execution/state25까지 영향력을 확장하는 것

이다.

즉 지금은 **annotation contract를 시작할 시점**이 맞지만,
**session-aware 실행 영향력을 바로 올릴 시점은 아직 아니다.**
