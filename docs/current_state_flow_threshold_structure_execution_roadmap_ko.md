# Aggregate Directional Flow Threshold / Structure Execution Roadmap

## 1. 로드맵 목적

이 로드맵은 `exact pilot match -> aggregate directional flow -> bounded lifecycle canary`를
아무 기준 없이 섞지 않고,

- 왜 이 순서로 가는지
- 어디서 멈춰야 하는지
- 무엇을 먼저 고정하고 무엇을 나중에 열어야 하는지

를 운영 관점에서 정리한 문서다.

핵심 목표는 아래와 같다.

1. decomposition 구조를 깨지 않는다.
2. exact pilot match를 완전히 버리지 않는다.
3. aggregate flow를 "새 예외 제조기"가 아니라 "구조를 잘 소비하는 보조 게이트"로 둔다.
4. XAU에서 먼저 검증하되, 최종 목적은 NAS/BTC까지 먹히는 공용 flow gate를 만든다.

---

## 2. 현재 상태 요약

현재 이미 준비된 층:

- 인식/회고/비교:
  - `runtime_signal_wiring_audit_summary_v1`
  - `should_have_done_summary_v1`
  - `canonical_surface_summary_v1`
  - `dominance_accuracy_summary_v1`
- 해석:
  - `state_strength_profile_v1`
  - `local_structure_profile_v1`
  - `state_structure_dominance_profile_v1`
- decomposition:
  - polarity / intent / stage / texture / location / tempo / ambiguity
- pilot:
  - XAU pilot mapping / readonly / validation
  - NAS/BTC extension surface
- lifecycle:
  - execution bridge
  - lifecycle policy
  - shadow audit
  - bounded canary

즉 foundation은 충분하다.
남은 것은 `flow gate 우선순위와 threshold calibration`이다.

---

## 3. 진행 원칙

### 원칙 1. structure-first

threshold는 structure gate를 통과한 뒤에만 쓴다.

### 원칙 1-1. threshold-is-confidence-classifier

threshold는 본질 판정기가 아니라 확신 수준 분류기다.

### 원칙 2. exact-match-is-not-the-only-door

exact pilot match는 계속 유지하지만 유일한 통과 문으로 두지 않는다.

### 원칙 3. no pure-numeric rollout

숫자만으로 lifecycle canary를 올리지 않는다.

### 원칙 4. decomposition must stay upstream

aggregate flow는 decomposition을 덮어쓰지 못한다.

### 원칙 5. symbol differences are calibration inputs

심볼 차이는 무시하지 않되, 첫 반응을 예외 추가로 하지 않는다.

### 원칙 6. conviction-and-persistence-are-separate

`aggregate_conviction`과 `flow_persistence`는 처음부터 하나의 값으로 접지 않고 분리 surface한다.

### 원칙 6-1. conviction-has-minimum-components

`aggregate_conviction`는 최소 `dominance_support`, `structure_support`, `decomposition_alignment` 세 축을 포함해야 한다.

### 원칙 6-2. persistence-has-recency-decay

`flow_persistence`는 단순 누적이 아니라 최근 N-bar에 더 높은 가중치를 두는 recency/decay 원칙을 가진다.

### 원칙 7. structure-common-thresholds-tunable

구조 gate는 공용 언어로 유지하고, 숫자 band는 심볼별 calibration을 허용한다.

### 원칙 8. hard-before-soft

Structure Gate 안에서는 hard disqualifier가 soft qualifier보다 항상 먼저 판정한다.

### 원칙 9. exact-bonus-has-a-ceiling

exact match bonus는 structure gate를 통과한 장면에만 적용되며, `FLOW_UNCONFIRMED`를 단독으로 `FLOW_CONFIRMED`까지 올릴 수 없다.

### 원칙 10. extension-is-late-not-fresh

`EXTENSION`은 flow 인정 후보일 수는 있어도 기본적으로 `FLOW_CONFIRMED` 상한을 갖지 않는 late continuation 구간으로 본다.

---

## 4. 단계별 로드맵

### F0. 진단 체인 정합 고정

목적:

- raw runtime row, effective recomputation row, canary row가 서로 다른 결론을 주는 구간을 줄인다.

핵심 작업:

- current XAU row 기준
  - symbol calibration
  - XAU readonly surface
  - refined gate audit
  - bounded lifecycle canary
  재계산 경로를 동일 기준으로 점검
- persisted field 누락과 계산 차이를 분리

완료 기준:

- `runtime row`, `effective recompute`, `audit`가 어떤 값이 비어 있고 어떤 값이 계산되었는지 일관되게 설명 가능

상태 기준:

- `READY`: 차이가 있어도 원인을 설명 가능
- `HOLD`: 일부 chain이 여전히 stale field에 의존
- `BLOCKED`: 같은 입력에서 layer별 결론이 뒤집힘

### F1. `flow_structure_gate_v1` 정의

목적:

- "흐름형 장면"의 최소 구조 자격 조건을 정한다.

핵심 작업:

- directional flow 후보의 최소 gate 정의
  - side alignment
  - rejection split
  - stage
  - ambiguity
  - tempo
  - hold quality
- exact match 없이도 directional flow로 인정 가능한 최소 구조를 문서화

초기 후보:

Hard disqualifier:

- polarity mismatch면 즉시 `INELIGIBLE`
- `rejection_type == REVERSAL_REJECTION`
- `consumer_veto_tier == REVERSAL_OVERRIDE`
- `ambiguity == HIGH`

Soft qualifier:

- `stage in {INITIATION, ACCEPTANCE}`
- `tempo in {PERSISTING, REPEATING}` 또는 raw count가 충분
- `breakout_hold_quality >= STABLE`
- `higher_low / lower_high` 구조 유지

완료 기준:

- "이 장면은 숫자를 보기 전에 directional flow 후보인가 아닌가"를 구조만으로 분리 가능

추가 산출물:

- `flow_structure_gate_v1 = ELIGIBLE / WEAK / INELIGIBLE`
- `flow_structure_fail_reason_v1`

### F2. `aggregate_conviction_v1` / `flow_persistence_v1` 분리 고정

목적:

- directional flow를 하나의 숫자가 아니라, 강도와 지속성으로 나눠 읽는다.

핵심 작업:

- `aggregate_conviction_v1`
  - `dominance_support`
  - `structure_support`
  - `decomposition_alignment`
  - ambiguity / veto penalty
  를 종합하는 방향 정렬 점수로 정의
- `flow_persistence_v1`
  - breakout hold bars
  - higher-low / lower-high persistence
  - repeat / streak / reclaim hold
  - recency/decay weighting
  를 종합하는 지속성 점수로 정의
- 둘 다 row-level surface와 summary 분포로 남김

완료 기준:

- `conviction`과 `persistence`를 따로 봤을 때 어떤 row가 "강하지만 짧은지", "중간이지만 오래가는지" 설명 가능

### F3. retained window calibration set 고정

목적:

- threshold calibration에 쓸 기준 장면 집합을 고정한다.

핵심 작업:

- XAU
  - up recovery pilot windows
  - down rejection pilot windows
- NAS
  - strong continuation under-veto windows
  - later breakdown / mixed windows
- BTC
  - mixed recovery
  - reclaim/drift

을 `confirmed / building / mixed / not-flow` 기준으로 1차 정리

완료 기준:

- calibration 기준 장면이 "좋은 장면 / 애매한 장면 / 흐린 장면"으로 묶여 있음

### F4. threshold provisional band 정의

목적:

- 숫자를 절대 진리가 아닌 provisional band로 정의한다.

핵심 작업:

- `aggregate_conviction`
- `flow_persistence`

분포를 retained window 위에서 비교

초기 band 예시:

- `FLOW_CONFIRMED`
  - structure gate `ELIGIBLE`
  - conviction / persistence both high
- `FLOW_BUILDING`
  - structure gate `ELIGIBLE` or `WEAK`
  - conviction / persistence 중 하나가 먼저 높고 다른 하나가 따라오는 구간
- `FLOW_UNCONFIRMED`
  - structure gate 약하거나 conviction / persistence 중 하나 부족
- `FLOW_OPPOSED`
  - structure fail 또는 polarity mismatch

중요 원칙:

- 하나의 숫자보다 band와 structure gate 조합으로 본다
- XAU/NAS/BTC 분포 차이를 같이 기록
- threshold는 hard pass/fail이 아니라 confidence band다
- `FLOW_CONFIRMED`는 두 값이 둘 다 높아야 한다
- `EXTENSION`은 기본적으로 `FLOW_CONFIRMED` 상한을 갖지 않는다

완료 기준:

- threshold가 감이 아니라 retained evidence 기반 provisional band로 정리됨

### F5. exact pilot match 역할 재배치

목적:

- exact pilot match를 hard gate에서 bonus gate 쪽으로 재배치할지 결정한다.

선택지:

1. exact pilot match 유지 + aggregate flow는 참고만
2. structure gate + threshold 통과 시 exact pilot 없이도 flow confirmed 허용
3. exact pilot match가 있을 때만 더 낮은 threshold 허용

현재 권장 방향:

- `structure gate + threshold`가 먼저
- `exact pilot match`는 우대 가중치 또는 빠른 통과권

완료 기준:

- exact match의 역할이 문서와 코드에서 일관됨

추가 원칙:

- exact match는 structure gate를 대체할 수 없음
- exact match는 `FLOW_BUILDING -> FLOW_CONFIRMED` 승격 또는 bonus 가중치로만 사용
- exact match는 `FLOW_UNCONFIRMED -> FLOW_CONFIRMED` 직행을 만들 수 없음

### F6. shadow-only 비교 실험

목적:

- 기존 exact-match-only gate와 flow-enabled gate를 같은 장면에서 비교한다.

핵심 작업:

- 같은 retained row에 대해
  - old verdict
  - new verdict
  - should-have-done alignment
  - over-veto / under-veto 변화
를 비교

중점 지표:

- continuation under-promotion 감소 여부
- false flow confirmation 증가 여부
- symbol별 편향 발생 여부

완료 기준:

- flow gate가 실제로 "좋은 장면을 더 잘 통과시키는지" 보임

### F7. XAU bounded canary 재판정

목적:

- XAU에서만 아주 좁게 flow-enabled gate를 bounded canary에 적용 가능할지 본다.

핵심 작업:

- exact pilot이 아니어도
  - structure gate `ELIGIBLE`
  - flow confirmed 또는 strong building
  - ambiguity low
  - lifecycle policy alignment good
이면
  `BOUNDED_READY` 후보가 되는지 확인

제한:

- scope는 계속 좁게 유지
- entry aggressive 전환 금지
- hold/reduce 위주 slice 우선

완료 기준:

- XAU에 한해 flow gate가 bounded canary readiness를 개선하는지 확인

### F8. NAS/BTC 공용화 판정

목적:

- XAU에서 잡은 gate가 NAS/BTC에도 공용 언어로 먹히는지 본다.

핵심 작업:

- NAS strong continuation
- BTC mixed recovery / drift

에 같은 구조 gate + threshold band를 적용

질문:

- NAS는 exact pilot이 없어도 strong flow로 빨리 통과해야 하는가?
- BTC는 mixed 상태가 많으므로 더 높은 persistence를 요구해야 하는가?
- symbol-specific threshold profile을 허용할지, common band + symbol penalty로 갈지?

완료 기준:

- 공용 band와 symbol-specific adjustment 중 어느 쪽이 더 자연스러운지 판단 가능

추가 확인 항목:

- 심볼별 조정이 conviction/persistence band 수준에 머무는지
- hard disqualifier나 rejection split까지 심볼별 예외가 침범하지 않는지

### F9. lifecycle 연결 판단

목적:

- flow gate를 실제 lifecycle policy와 어떻게 연결할지 결정한다.

핵심 작업:

- `FLOW_CONFIRMED`
- `FLOW_BUILDING`
- `FLOW_UNCONFIRMED`

상태가

- entry
- hold
- add
- reduce
- exit

bias에 어떤 영향을 줄지 설계

중요:

- 이 단계 전까지는 계속 read-only / shadow 중심
- decomposition과 dominance 보호 규칙을 깨지 않음

완료 기준:

- flow gate가 실제 execution behavior를 바꿔도 되는지 판단 가능한 수준까지 shadow 근거가 쌓임

---

## 5. 우리가 현재 기울어 있는 선택

현재 기준으로 가장 자연스러운 선택은 아래다.

1. `flow_structure_gate_v1`를 먼저 본다
2. 그 뒤 `aggregate_conviction_v1`와 `flow_persistence_v1` band를 본다
3. exact pilot match는 bonus 또는 priority boost로 둔다
4. 구조는 공용으로 유지하고 threshold는 심볼별 calibration을 허용한다

즉:

> exact-match-only
> 또는
> pure-threshold-only

둘 다 피하고,

> structure-first + threshold-second + exact-match-as-bonus

로 가는 것이다.

---

## 6. 현재 가장 중요한 운영 주의점

### 주의점 1. 숫자를 너무 빨리 얼리지 않기

처음 본 XAU 장면 하나에 맞춰 threshold를 박으면 과적합 위험이 크다.

### 주의점 2. decomposition을 무력화하지 않기

aggregate flow가 강하다고 해서

- `REVERSAL_REJECTION`
- `HIGH ambiguity`
- `REVERSAL_OVERRIDE`

같은 보호 규칙을 덮으면 안 된다.

### 주의점 2-1. threshold가 structure보다 위로 올라가지 않게 하기

숫자 threshold가 structure gate보다 먼저 판정을 가져가면,
다시 tuning 지옥으로 돌아간다.

### 주의점 3. exact pilot match를 갑자기 완전히 버리지 않기

pilot match는 여전히 검증된 사례 보너스이기 때문에,
곧바로 제거하는 것은 위험하다.

### 주의점 4. symbol 차이를 threshold 숫자 하나로 억지 통일하지 않기

NAS/BTC/XAU는 분포가 다르므로,
공용 밴드가 있더라도 symbol-specific calibration 메모는 남겨야 한다.

### 주의점 5. conviction과 persistence를 너무 빨리 하나로 접지 않기

처음부터 하나의 합성값으로 접으면,
"강하지만 짧은 장면"과 "중간이지만 오래가는 장면"을 구분하기 어려워진다.

---

## 7. 한 줄 요약

지금 다음 단계의 핵심은
`숫자를 몇으로 할까`가 아니라

> exact match, structure, aggregate flow를 어떤 순서로 소비해야
> decomposition 구조를 살리면서도 너무 딱딱하지 않은 gate를 만들 수 있는가

를 정하는 것이다.

현재 우리가 가장 유망하다고 보는 방향은 아래다.

> XAU에서 먼저
> structure-first + threshold-second + exact-match-as-bonus
> 구조를 shadow와 bounded canary에 시험하고,
> 그다음 NAS/BTC로 공용화 판정을 넓힌다.
