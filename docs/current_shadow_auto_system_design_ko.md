# Current Shadow Auto System Design

## 목적

이 문서는 현재 calibration system 위에 올라가는 `shadow auto system`의 설계 원칙을 고정한다.

핵심 목표는 다음과 같다.

- 자동으로 돌려본다
- 그러나 live baseline은 직접 건드리지 않는다
- manual truth와 comparison을 기준으로 shadow를 검증한다
- 검증된 경우에만 bounded review 후보로 올린다

한 줄로 요약하면:

`auto-run first, live-apply later`

---

## 현재 위치

현재 프로젝트는 이미 아래 calibration 자산을 갖고 있다.

- manual truth answer key
- manual vs heuristic comparison
- mismatch family ranking
- bias sandbox / patch draft
- correction loop
- current-rich promotion discipline
- approval log
- post-promotion audit

즉 지금은 owner를 더 만드는 단계보다, owner가 어디서 틀리는지 교정하는 단계가 더 중요하다.

shadow auto system은 이 calibration 층을 버리는 것이 아니라, 그 위에서

- "자동으로 돌리면 실제로 무엇이 달라지는가"
- "달라진 것이 정말 더 좋은가"
- "bounded live candidate로 올릴 만한가"

를 검증하는 비실행(non-live) 실험층이다.

---

## 현재 핵심 진단

현재 preview shadow는 이미 실제로 생성되고 offline으로 활성화됐다.

대표 상태는 다음과 같다.

- preview bundle status: `preview_bundle_ready`
- training bridge rows: `180 / 180 matched`
- runtime activation demo rows: `64`
- available rows: `64`
- `shadow_enter_count = 64`
- `value_diff = 0.0`
- `drawdown_diff = 0.0`
- `manual_alignment_improvement = 0.0`
- SA5 decision: `hold_for_more_shadow_data`
- SA6 decision: `HOLD`

이 수치가 말하는 현재 병목은 분명하다.

> shadow가 "없어서"가 아니라, shadow가 baseline과 충분히 다르게 행동하지 못해서 edge를 만들지 못하고 있다.

즉 지금 문제는 automation completeness가 아니라 discriminative edge 부족이다.

---

## 현재 병목 해석

현 상태는 보통 아래 셋 중 둘 이상이 동시에 걸려 있을 때 나타난다.

1. threshold가 너무 보수적이라 shadow가 baseline을 거의 복제한다
2. target 정의가 너무 애매해서 모델이 무엇을 바꿔야 하는지 모른다
3. dataset이 baseline 행동을 너무 많이 복사해서 차별 신호를 학습하지 못한다

현재 프로젝트는 특히 다음 해석이 유력하다.

- `threshold too conservative`
- `target semantics too weak`

따라서 다음 단계의 목적은 "자동화를 더 붙이는 것"이 아니라:

> baseline과 다른 shadow 행동을 안전하게 만들어내는 것

이다.

---

## 최종 레이어 구조

의도된 운영 스택은 다음과 같다.

```text
[Execution Engine (Live Baseline)]
  - 현재 실제 거래 집행 주체
  - calibration/shadow 결과로 직접 rewrite하지 않음

[Shadow Auto System]
  - patch candidate 적용
  - correction 실험 실행
  - baseline vs shadow 비교
  - non-live / preview / bounded-review 후보층

[Calibration System]
  - manual truth answer key
  - comparison
  - ranking
  - sandbox
  - audit
```

해석:

- live baseline은 현재 수익/리스크의 기준선이다
- shadow는 baseline과 같은 입력을 받지만 실거래는 하지 않는다
- calibration system이 shadow의 승인/보류/기각 기준이 된다

---

## 운영 원칙

### 원칙 1. live authority는 아직 baseline만 가진다

- `baseline`만 실제 live execution authority를 가진다
- `shadow_auto`는 동일 컨텍스트에서 병렬 평가만 한다

### 원칙 2. shadow의 목표는 "더 자동"이 아니라 "더 다름"이다

다음 단계에서 가장 중요한 성공 기준은:

- `baseline_action == shadow_action`를 줄이는 것
- 그 차이가 manual truth 기준으로 무의미하지 않은 것

즉 지금 단계에서는 자동화 퍼센트보다 행동 차이 생성이 더 중요한 지표다.

### 원칙 3. 차이가 생겨도 즉시 live에 올리지 않는다

shadow에서 차이가 생겼더라도 아래가 확인되기 전에는 bounded apply 후보로도 올리지 않는다.

- non-negative value / drawdown behavior
- 의미 있는 manual alignment 변화
- target family에 대한 개선
- freeze-worthy family 오염이 크지 않음
- 사람 승인 기록 존재

### 원칙 4. manual truth는 여전히 answer key다

- manual truth를 곧바로 live training seed로 사용하지 않는다
- manual truth는 shadow를 평가하는 기준으로 남는다

---

## Runtime Modes

명시적으로 두 runtime mode를 둔다.

- `baseline`
- `shadow_auto`

### baseline

- current production logic
- current live execution owner
- current calibration reference

### shadow_auto

- 동일한 runtime 입력을 받는다
- threshold/target/patch 변경안을 적용할 수 있다
- 병렬 action/evaluation trail을 남긴다
- 실 live order는 내지 않는다

---

## 핵심 데이터 흐름

1. baseline engine이 평소처럼 동작한다
2. calibration layer가 shadow candidate를 선정한다
3. shadow_auto가 같은 decision context 위에서 병렬 실행된다
4. baseline/shadow 결과가 side-by-side로 저장된다
5. evaluation layer가 행동 차이와 품질을 계산한다
6. decision engine이
   - `APPLY_CANDIDATE`
   - `HOLD`
   - `FREEZE`
   - `REJECT`
   중 하나를 낸다
7. 그 뒤에만 bounded review가 가능하다

---

## 현재 단계에서 진짜 필요한 산출물

### 1. Shadow vs Baseline

현재 이미 존재한다.

- `data/analysis/shadow_auto/shadow_vs_baseline_latest.csv`
- `data/analysis/shadow_auto/shadow_vs_baseline_latest.json`
- `data/analysis/shadow_auto/shadow_vs_baseline_latest.md`

이 층은 "같은 상황에서 baseline과 shadow가 무엇을 했는가"를 저장한다.

### 2. Shadow Evaluation

현재 이미 존재한다.

- `data/analysis/shadow_auto/shadow_evaluation_latest.csv`
- `data/analysis/shadow_auto/shadow_evaluation_latest.json`
- `data/analysis/shadow_auto/shadow_evaluation_latest.md`

이 층은 "shadow가 더 나았는가"를 평가한다.

### 3. Shadow Decision

현재 이미 존재한다.

- `data/analysis/shadow_auto/shadow_auto_decision_latest.csv`
- `data/analysis/shadow_auto/shadow_auto_decision_latest.json`
- `data/analysis/shadow_auto/shadow_auto_decision_latest.md`

이 층은 "bounded review 후보인지 아닌지"를 판정한다.

### 4. 지금 추가로 중요해진 산출물

다음 단계에서 더 중요해지는 것은 아래 세 가지다.

- `shadow_divergence_audit`
  - baseline과 shadow가 얼마나 다르게 행동했는지
- `shadow_threshold_sweep`
  - 어느 threshold 구간에서 의미 있는 divergence가 생기는지
- `shadow_dataset_bias_audit`
  - dataset이 baseline 복제를 얼마나 유도하는지

즉 이제는 "모델이 있나 없나"보다 "차이를 만들 수 있나"를 보는 표면이 필요하다.

---

## 다음 단계의 설계 초점

### 1. Threshold Tuning

현재 shadow가 너무 baseline에 붙어 있으면, threshold를 낮추거나 완화해 divergence를 만들어야 한다.

예:

- confidence gate 완화
- apply 조건 완화
- family별 다른 threshold 사용

### 2. Target Mapping Redesign

지금 target이 너무 애매하면 shadow는 baseline을 모사하는 쪽으로 수렴하기 쉽다.

다음 단계에서는 manual truth family를 더 직접적으로 shadow target으로 매핑하는 게 필요하다.

예:

- `enter_now`
- `wait_more`
- `exit_protect`

이런 식의 coarse but decisive target semantics가 필요하다.

### 3. Dataset Rebalance

지금 dataset에 baseline 행동 비중이 너무 크면 shadow는 baseline 복제기를 만들기 쉽다.

다음 단계에서는:

- manual truth anchored rows 비중 강화
- freeze-only family와 correction family 분리
- baseline-copy dominant rows downweight

가 필요하다.

### 4. First Divergence Experiment

다음 구현 블록의 목적은 "더 정교한 automation"이 아니라

> shadow가 baseline과 실제로 다르게 행동하는 첫 실험

을 만드는 것이다.

성공 기준은:

- `baseline_action != shadow_action`
- divergence가 특정 family에서 관찰됨
- value/drawdown이 즉시 악화되지 않음

---

## 다음 단계 성공 기준

이 설계가 다음 단계에서 유효하다고 보려면 최소한 아래가 필요하다.

### 레벨 1. 차이 생성

- action divergence rate > 0
- 특정 family에서 shadow가 baseline과 다른 결정을 냄

### 레벨 2. bounded quality

- `value_diff >= 0`
- `drawdown_diff`가 통제 가능
- `manual_alignment_improvement >= 0` 또는 target family 개선

### 레벨 3. 첫 비-HOLD 결과

- SA5에서 첫 `accept_preview_candidate` 또는 `reject_preview_candidate`
- SA6에서 첫 `APPLY_CANDIDATE` 또는 명시적 `REJECT`

즉 다음 성공 기준은 "자동화 퍼센트 증가"가 아니라:

> 차이 생성 -> bounded 품질 확인 -> 첫 비-HOLD 의사결정

이다.

---

## 지금 하지 말아야 할 것

아래는 지금 단계에서 금지하거나 보류해야 한다.

- preview shadow 결과를 바로 live rule에 반영
- manual truth를 바로 training/live seed로 혼합
- entry/exit teacher 확장으로 focus 분산
- divergence가 없는 상태에서 automation 퍼센트만 더 올리기

---

## 짧은 결론

shadow auto system은 이제 존재한다.

현재의 진짜 병목은:

- shadow가 없어서가 아니라
- shadow가 baseline과 충분히 다르게 행동하지 못해서
- edge가 없는 상태라는 점이다

따라서 다음 설계 초점은:

- 더 많은 자동화
- 더 많은 기능

이 아니라

- threshold tuning
- target redesign
- dataset rebalance
- first divergence experiment

이다.
