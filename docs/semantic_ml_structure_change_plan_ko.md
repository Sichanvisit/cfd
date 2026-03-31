# Semantic ML 구조 점검 및 변경 계획

## 1. 목적

이 문서는 지금 semantic ML 구조를 어떻게 살피고, 어떤 순서로 바꿀지 정리한 실행 계획이다.

이 문서의 핵심 목적은 세 가지다.

- 지금 어디까지 끝났는지 헷갈리지 않게 정리
- 다음에 무엇을 해야 하는지 순서대로 고정
- `Step`과 `우선순위(P0/P1/P2)`를 분리해서 머릿속이 꼬이지 않게 정리

관련 문서:

- [`semantic_ml_structure_audit_baseline_ko.md`](/C:/Users/bhs33/Desktop/project/cfd/docs/semantic_ml_structure_audit_baseline_ko.md)
- [`semantic_ml_key_strategy_ko.md`](/C:/Users/bhs33/Desktop/project/cfd/docs/semantic_ml_key_strategy_ko.md)
- [`semantic_ml_v1_execution_plan_ko.md`](/C:/Users/bhs33/Desktop/project/cfd/docs/semantic_ml_v1_execution_plan_ko.md)
- [`semantic_ml_v1_promotion_gates_ko.md`](/C:/Users/bhs33/Desktop/project/cfd/docs/semantic_ml_v1_promotion_gates_ko.md)
- [`semantic_v1_audit_20260321_ko.md`](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/semantic_v1_audit_20260321_ko.md)

---

## 2. 이 문서를 읽는 법

여기서 가장 중요한 건 `Step`과 `P`가 다른 축이라는 점이다.

### `Step`

`Step`은 큰 작업 순서다.

- Step 1을 끝내고
- Step 2를 하고
- 그 다음 Step 3으로 간다

즉 `Step`은 실행 순서다.

### `P0 / P1 / P2`

`P`는 각 Step 안에서의 급한 정도다.

- `P0`: 제일 먼저 손대야 하는 것
- `P1`: 그 다음
- `P2`: 나중

즉 `P0 timing target 재설계`는 새로운 Step이 아니라,
`Step 3 안에서 가장 먼저 해야 하는 작업`이라는 뜻이다.

---

## 3. 현재 상태 요약

### 이미 끝난 것

- hot/detail 분리 방향 정리
- `entry_decisions.csv`와 `runtime_status.json` slim/detail 구조 정리
- semantic compact export 경로 구축
- replay / label compact summary 구축
- semantic dataset builder 구축
- preview train / evaluate / shadow / promotion guard 골격 구축
- future bars backfill 경로 구축
- export join bug 수정

### 지금 핵심 문제

- `timing` target 정의가 현재 의도와 반대로 접혔을 가능성이 큼
- `entry_quality` target 정의가 실제 "좋은 진입"과 어긋날 가능성이 큼
- `exit_management`는 숫자가 좋아 보여도 split 건강도가 약함
- legacy source에서는 trace/quality pack 일부가 항상 비어 있음

즉 지금은 rollout을 더 넓히는 단계가 아니라,
`target 계약`과 `split 기준`을 다시 잡는 단계다.

---

## 4. 지금까지 완료한 Step

## Step 1. 구조 감사 기준 고정

상태: 완료

산출물:

- [`semantic_ml_structure_audit_baseline_ko.md`](/C:/Users/bhs33/Desktop/project/cfd/docs/semantic_ml_structure_audit_baseline_ko.md)

무엇을 잠갔는가:

- 구조를 어떤 층으로 볼지
- audit 항목과 합격 기준
- rollout보다 target/split 재설계가 먼저라는 판단

## Step 2. key 전략 정리

상태: 완료

산출물:

- [`semantic_ml_key_strategy_ko.md`](/C:/Users/bhs33/Desktop/project/cfd/docs/semantic_ml_key_strategy_ko.md)

무엇을 잠갔는가:

- canonical key owner는 [`storage_compaction.py`](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- runtime/export/replay가 같은 helper 규칙을 쓴다는 점
- `join_ordinal`은 canonical key가 아니라 dataset join bridge라는 점
- 지금은 row-level unique key v2를 바로 넣지 않는다는 점

---

## 5. 이제부터 진행할 Step

이제부터는 아래 순서로 간다.

## Step 3. timing target 재설계

우선순위: `P0`

### 목적

`timing_now_vs_wait` target이 지금 실제 의미와 같은 방향으로 접히는지 다시 본다.

### 왜 지금 먼저 하는가

현재 audit 기준으로 가장 먼저 깨진 축이 timing이다.

- AUC가 매우 낮음
- 모델 성능 문제라기보다 정답 정의 문제일 가능성이 큼

### 대상 파일

- [`dataset_builder.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_builder.py)

### 작업

1. 지금 `timing` target이 어떤 규칙으로 접히는지 분해
2. `same_side_positive_count`, `adverse_positive_count`, margin 정의가 맞는지 확인
3. "지금 진입이 유리" vs "1~2 bar wait이 유리"를 다시 정의
4. sample row로 사람이 납득 가능한지 검증

### 완료 기준

- timing target을 사람이 설명 가능
- preview가 최소 무작위보다 의미 있게 동작

## Step 4. split 건강도 기준 고정

우선순위: `P0`

### 목적

metrics를 믿을 수 있도록 train/validation/test 기준을 다시 고정한다.

### 왜 timing 다음인가

target이 맞아도 split이 깨지면 숫자가 다 왜곡된다.

### 대상 파일

- [`dataset_splits.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_splits.py)
- [`evaluate.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/evaluate.py)

### 작업

1. validation/test 최소 양/음 클래스 수 기준 고정
2. symbol / regime / setup slice 기준 추가
3. split이 건강하지 않으면 warning이 아니라 실패로 볼지 결정

현재 기준선:

- train minority rows: `64+`
- validation minority rows: `32+`
- test minority rows: `64+`
- test slice 평가는 `50+` rows slice만 본다
- slice minority rows가 `8` 미만이면 건강하지 않은 slice로 본다

### 완료 기준

- split 건강도 기준이 문서와 코드에 같이 반영
- validation/test 단일 클래스 문제를 조기 경고 가능

## Step 5. entry_quality target 재설계

우선순위: `P1`

### 목적

현재 `entry_quality`가 실제 "좋은 진입"을 설명하도록 다시 접는다.

### 대상 파일

- [`dataset_builder.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_builder.py)

### 작업

1. `transition_quality_score` 정의 재검토
2. range / trend를 같은 기준으로 볼지 다시 판단
3. sample row 기준으로 positive / negative 정의 검증

### 완료 기준

- 사람이 봐도 납득 가능한 positive / negative 정의 확보
- direct leakage 없이 preview 재학습 가능

## Step 6. legacy feature tier 자동화

우선순위: `P1`

### 목적

legacy source에서 항상 비는 trace/quality feature를 자동 처리한다.

### 대상 파일

- [`dataset_builder.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_builder.py)
- [`evaluate.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/evaluate.py)

### 작업

1. source generation별 allowed feature tier 나누기
2. all-missing legacy feature 자동 drop
3. manifest에 dropped feature 기록

### 완료 기준

- legacy dataset 학습 시 useless missing warning이 크게 줄어듦

## Step 7. preview 재학습 + audit 재실행

우선순위: `P2`

### 목적

Step 3~6 결과를 반영해서 semantic preview를 다시 돌리고,
join / leakage / split audit를 다시 본다.

### 대상 파일

- [`train_timing.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/train_timing.py)
- [`train_entry_quality.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/train_entry_quality.py)
- [`train_exit_management.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/train_exit_management.py)
- [`evaluate.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/evaluate.py)

### 작업

1. 세 target 재학습
2. join coverage audit 재실행
3. leakage audit 재실행
4. split health audit 재실행
5. promotion gate 기준으로 다시 판정

### 완료 기준

- 그때서야 shadow compare 재개 여부를 판단 가능

---

## 6. 한 장으로 보는 현재 위치

```text
Step 1 완료  -> 구조 감사 기준 고정
Step 2 완료  -> key 전략 정리
Step 3 다음  -> timing target 재설계
Step 4 다음  -> split 건강도 기준 고정
Step 5 다음  -> entry_quality target 재설계
Step 6 다음  -> legacy feature tier 자동화
Step 7 마지막 -> preview 재학습 + audit 재실행
```

즉 지금 위치는 여기다.

```text
[완료] Step 1
[완료] Step 2
[다음] Step 3
```

---

## 7. 지금 하지 말아야 할 것

- rollout mode를 더 넓히는 것
- partial live influence를 확대하는 것
- AUC 숫자 몇 개만 보고 semantic model을 승격하는 것
- raw giant source를 다시 직접 학습에 넣는 것

지금은 `더 붙이기`보다 `정답 정의를 바로잡기`가 먼저다.

---

## 8. 최종 결론

지금 헷갈리지 않게 가장 짧게 정리하면 이렇다.

```text
Step 1 완료
Step 2 완료
이제 Step 3 시작
Step 3의 내용 = P0 timing target 재설계
```

즉 `P0 timing target 재설계`는 Step 바깥의 새 작업이 아니라,
원래 계획 안에서 다음으로 가야 할 `Step 3` 그 자체다.
