# Semantic Tuning Roadmap v1

## 목적

이 로드맵의 목적은 단순 운영 보정이 아닙니다.

핵심 목표는 두 가지입니다.

1. 현재 semantic foundation이 실제 차트 감각과 맞게 동작하도록 보정
2. 이후 ML/DL forecast가 학습할 수 있을 만큼 좋은 feature quality를 확보

즉 이 로드맵은:

- live behavior tuning
- dataset quality tuning

을 동시에 다룹니다.

---

## 전제

현재 semantic foundation은 이미 존재합니다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

그래서 지금부터는 구조를 새로 만드는 게 아니라:

- acceptance 보정
- 합성 비중 조정
- 과민/과소 반응 수정

을 하는 단계입니다.

---

## 전체 원칙

### 원칙 1. 위에서 아래로 간다

순서는 반드시:

1. `Position / Response / State`
2. `Evidence`
3. `Barrier / Layer Mode / Energy`
4. `Belief`

입니다.

### 원칙 2. consumer로 덮지 않는다

semantic layer가 틀렸는데:

- consumer guard
- entry/exit hard block
- energy hint

로 덮으면 live behavior는 잠깐 가려질 수 있어도 dataset quality는 계속 망가집니다.

### 원칙 3. 한 번에 한 축만 조정한다

같은 스프린트에서

- `Position`
- `Evidence`
- `Barrier`

를 동시에 크게 바꾸면 원인 추적이 불가능합니다.

### 원칙 4. 항상 버전 태그와 shadow 비교를 남긴다

모든 보정은:

- 버전 이름
- 전후 비교
- acceptance 기준

을 같이 남겨야 합니다.

---

# T0. Calibration Scope Freeze

## 안 할 것

- semantic foundation 재설계
- symbol-specific exception 추가
- consumer 재튜닝
- ML/DL 도입
- live action gate 즉시 변경

## 할 것

- semantic layer의 acceptance 보정
- 합성 비중 조정
- 분포 / separation / false wait 문제 교정

## 완료 기준

- 지금 단계는 “구조 재작성”이 아니라 “semantic tuning”이라는 경계가 명확함

---

# T1. Position / Response / State Acceptance Pass

이 단계는 **feature correctness**를 다룹니다.

## T1-1. Position

### 목표

- 위치 해석 자체가 실제 차트 감각과 맞는지 점검

### 점검 포인트

- `primary_label`
- `bias_label`
- `secondary_context_label`
- `position_conflict_score`
- `middle_neutrality`

### 주요 증상

- 상단인데 `LOWER_*` 느낌으로 읽힘
- 하단인데 `UPPER_*` 느낌으로 읽힘
- `UNRESOLVED`가 너무 많거나 너무 적음
- `MIDDLE_*_BIAS`가 실제 감각과 다름

### 수정 대상

- zone 경계
- bias 판정 규칙
- unresolved 허용 범위
- conflict 우선순위

### 완료 기준

- 위치만 봐도 “왜 upper/lower/middle인지” 납득 가능

---

## T1-2. Response

### 목표

- detector -> canonical transition 축이 실제 전이 감각과 맞는지 점검

### 점검 포인트

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

### 주요 증상

- rejection인데 break 쪽으로 읽힘
- continuation인데 reversal 쪽으로 과하게 읽힘
- detector 중복이 canonical strength를 과증폭

### 수정 대상

- raw -> canonical 매핑
- primary / confirmation / amplifier 비중
- 중복 cap 규칙

### 완료 기준

- canonical 6축이 차트 감각과 대칭적으로 맞음

---

## T1-3. State

### 목표

- state gain/damp가 실제 해석 강도 조절에 맞는지 점검

### 점검 포인트

- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`

### 주요 증상

- `RANGE`인데 reversal boost가 약함
- `TREND`인데 pullback/continuation boost가 약함
- conflict/noise가 과하게 눌러서 다 `WAIT`
- liquidity/volatility가 과민하게 들어감

### 수정 대상

- raw -> canonical coefficient mapping
- conflict/noise assist 비중
- position quality 사용 강도

### 완료 기준

- state vector만 보면 “무엇을 강화/감쇠하는지” 설명 가능

---

## T1 전체 완료 기준

- semantic foundation의 feature correctness가 확보됨
- upstream 해석이 consumer 없이도 납득 가능함
- 이 상태로 evidence tuning을 해도 feature 오염이 적음

---

# T2. Evidence Calibration Pass

이 단계는 **setup strength / archetype strength**를 다룹니다.

## 목표

- reversal / continuation strength가 실제보다 과하거나 약하지 않게 조정

## 핵심 필드

- `buy_reversal_evidence`
- `sell_reversal_evidence`
- `buy_continuation_evidence`
- `sell_continuation_evidence`
- `buy_total_evidence`
- `sell_total_evidence`

## 점검 포인트

### reversal
- `lower_hold_up + mid_reclaim_up`
- `upper_reject_down + mid_lose_down`

### continuation
- `upper_break_up`
- `lower_break_down`

### 합성
- side total evidence의 capped merge
- fit 반영 강도
- state gain/damp 반영 강도

## 주요 증상

- setup strength가 너무 약함
- setup strength가 너무 강함
- reversal과 continuation이 동시에 과하게 높음
- side total evidence가 실제보다 과장됨

## 수정 대상

- component weight
- fit coefficient
- state multiplier
- capped merge weight

## 확인 지표

- `buy_total_evidence`
- `sell_total_evidence`
- reversal/continuation dominance
- evidence metadata reason strings

## 완료 기준

- evidence만 봐도 “어느 archetype strength가 현재 dominant인지” 설명 가능

---

# T3. Barrier / Layer Mode / Energy Wait Calibration

이 단계는 **너무 자주 WAIT 되는 문제**를 다룹니다.

## 목표

- semantic conflict는 유지하면서
- barrier 과민 반응을 줄이고
- 진짜 막아야 할 곳만 막도록 조정

## T3-1. Barrier

### 점검 필드

- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

### 주요 증상

- 모든 애매한 구간이 다 `WAIT`
- `middle_chop`가 너무 높음
- `liquidity_barrier`가 실제보다 과함
- `direction_policy_barrier`가 side별로 과민함

### 수정 대상

- component weight
- chop sensitivity
- liquidity penalty coupling
- policy barrier side spread

---

## T3-2. Layer Mode

### 목표

- raw semantic output과 effective semantic output 사이의 영향도를 조정

### 점검 포인트

- `shadow`
- `assist`
- `enforce`

### 주요 증상

- `assist`인데 실질적으로 거의 hard block처럼 동작
- `shadow`인데 로그만 많고 활용도 없음
- `effective outputs`가 raw semantics를 과하게 누름

### 수정 대상

- mode별 effective influence
- override / damp / hint strength

---

## T3-3. Energy Helper

### 목표

- semantic layer를 덮지 않으면서 consumer hint로만 작동하도록 보정

### 주요 증상

- energy helper가 semantic truth처럼 작동함
- barrier보다 energy hint가 더 큰 영향력을 가짐

### 수정 대상

- helper weight
- hint-only semantics
- logging clarity

---

## T3 전체 완료 기준

- `WAIT` 과잉이 줄어듦
- semantic conflict와 barrier overreaction이 분리됨
- consumer 쪽 patch 없이도 live behavior가 개선됨

---

# T4. Belief Temporal Calibration

이 단계는 **시간축 감각 보정**입니다.

## 목표

- persistence가 실제 시장 전개와 비슷하게 유지되도록 조정

## 핵심 필드

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`

## 주요 증상

- persistence가 너무 빨리 죽음
- belief가 너무 오래 살아남음
- streak가 실제보다 길게 유지됨
- mode switch가 너무 느리거나 너무 빠름

## 수정 대상

- `alpha_rise`
- `alpha_decay`
- activation threshold
- advantage threshold
- dominance deadband
- persistence window
- mode carry-over rule

## 확인 지표

- belief spread stability
- transition age realism
- mode dominance continuity
- same-bar duplicate suppression 영향

## 완료 기준

- belief가 “한 봉짜리 반응”과 “지속되는 전이”를 제대로 분리함

---

# T5. Shadow Validation / Comparison

각 단계는 무조건 shadow report와 같이 가야 합니다.

## 저장해야 할 것

- 수정 전/후 version
- semantic snapshot
- forecast snapshot
- 주요 gap / barrier / belief 분포
- 실제 outcome 요약

## 권장 비교 항목

- `WAIT` 비율 변화
- `confirm_fake_gap` 변화
- `continue_fail_gap` 변화
- `barrier_state_v1` 분포 변화
- `belief_spread` 분포 변화

## 완료 기준

- “좋아진 것 같은 느낌”이 아니라
- 전/후 비교로 어느 층이 실제 개선을 만들었는지 설명 가능

---

# T6. Versioning Discipline

튜닝은 항상 버전과 같이 가야 합니다.

## 예시

- `position_contract_v3`
- `response_vector_v2_r5`
- `state_vector_v2_s4_tuned`
- `evidence_vector_v1_e6_tuned`
- `belief_state_v1_b5_tuned`
- `barrier_state_v1_br6_tuned`

## 목적

- forecast / outcome / dataset이 어떤 semantic 버전에서 생성됐는지 추적 가능하게 하기

## 완료 기준

- 이후 ML/DL dataset을 만들 때 semantic version mismatch를 추적 가능

---

# T7. Acceptance Gate

튜닝은 무조건 acceptance 기준이 있어야 합니다.

## T7-1. Semantic correctness acceptance

- 위치 해석이 실제 차트 감각과 맞음
- response canonical 축이 전이 감각과 맞음
- state gain/damp가 실제 장 해석과 맞음

## T7-2. Strength acceptance

- evidence가 setup strength를 과/소평가하지 않음

## T7-3. Wait calibration acceptance

- `WAIT`이 필요한 곳에서는 유지
- 불필요한 `WAIT`은 줄어듦

## T7-4. Temporal acceptance

- persistence가 실제 시간 전개와 유사

## 완료 기준

- semantic tuning 결과를 live/runtime/log에서 동시에 설명 가능

---

# 추천 실행 순서

1. `T0` Scope Freeze
2. `T1` Position / Response / State Acceptance
3. `T2` Evidence Calibration
4. `T3` Barrier / Layer Mode / Energy Wait Calibration
5. `T4` Belief Temporal Calibration
6. `T5` Shadow Validation / Comparison
7. `T6` Versioning Discipline
8. `T7` Acceptance Gate

---

# 지금 당장 가장 좋은 시작점

현재 구조 기준으로는 이 순서가 제일 안전합니다.

1. `Position / Response / State`를 다시 acceptance 기준으로 확인
2. `Evidence`의 setup strength를 보정
3. 그 다음에야 `Barrier`의 wait 과민을 건드림
4. 마지막으로 `Belief` 시간축 감각을 다듬음

---

# 최종 정리

이 로드맵의 본질은:

> semantic foundation을 그냥 “동작하는 구조”에서  
> “실제 차트 감각과 맞고, 이후 ML/DL이 학습하기 좋은 구조”로 보정하는 것

입니다.

즉 지금 단계는

- 운영 튜닝
- feature quality 개선
- dataset quality 개선

이 동시에 걸려 있는 매우 중요한 단계로 봐야 합니다.
