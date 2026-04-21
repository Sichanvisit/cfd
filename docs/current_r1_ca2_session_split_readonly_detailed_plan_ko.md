# R1 CA2 세션 분해 상세 계획

## 1. 목적

이 문서는 `R1. CA2 지표의 세션 분해`를 별도 구현 축으로 정리한다.

지금 단계의 목표는 새 규칙을 실행에 밀어넣는 것이 아니다.
이미 쌓이고 있는 `continuation_accuracy`, `execution_diff`, `guard`, `promotion` 지표를
`session_bucket` 기준으로 나눠서, 정말 세션 차이가 있는지 숫자로 읽을 수 있게 만드는 것이다.

즉 R1은 `read-only 분석 축`이다.

## 2. 왜 지금 R1이 필요한가

현재 시스템은 이미 아래 재료를 계속 쌓고 있다.

- `directional_continuation_accuracy_summary_v1`
- `execution_diff_*`
- `active_action_conflict_guard_*`
- `directional_continuation_promotion_*`
- `session_bucket_v1`

하지만 이 값들은 아직 대부분 전체 합계 중심으로 읽힌다.
그래서 아래 질문에 숫자로 답하기 어렵다.

1. 같은 continuation 구조가 미국장과 아시아장에서 실제로 다르게 맞는가
2. guard/promotion이 세션별로 다른 품질을 보이는가
3. 세션 차이가 직감이 아니라 실제로 유의미한가

R1은 이 질문을 먼저 닫는 단계다.

## 3. R1의 핵심 원칙

### 3-1. 세션은 read-only

R1에서는 세션이 방향이나 실행을 바꾸지 않는다.

- `session_bucket`은 분석/집계용
- execution/state25 영향력 확대 금지
- 세션별 차이가 보여도 이 단계에서는 행동 변경 금지

### 3-2. 기존 CA2 지표를 깨지 않는다

R1은 새 엔진이 아니라 기존 CA2 지표 위에 얇게 올라간 분해 축이다.

- 기존 `primary_correct_rate` 유지
- 기존 `execution_diff_surface_count` 유지
- 기존 guard/promotion trace 유지

### 3-3. 유의미 판단은 보수적으로

세션 차이가 보인다고 바로 bias로 올리지 않는다.

## 4. R1에서 읽을 지표

### 4-1. continuation accuracy by session

- `correct_rate_by_session`
- `measured_count_by_session`

이 지표는 `directional_continuation_accuracy_tracker_state.json`의
`resolved_observations`를 `primary_horizon_bars = 20` 기준으로 세션 버킷에 나눠 읽는다.

### 4-2. guard trace by session

- `guard_helpful_rate_by_session`

첫 버전에서는 hindsight join이 아직 충분하지 않으므로,
trace는 세션별로 분해하되 `guard_helpful_rate`는 `None`일 수 있다.
이 경우 `data_status = INSUFFICIENT_HINDSIGHT`로 정직하게 surface한다.

### 4-3. promotion trace by session

- `promotion_win_rate_by_session`

이 축도 첫 버전은 trace 기반 분해부터 시작한다.
충분한 hindsight join이 생기기 전까지는 `None`과 `INSUFFICIENT_HINDSIGHT`를 유지한다.

## 5. 세션 차이 유의미 판정 기준

R1은 세션 차이를 아래 기준으로 읽는다.

### 5-1. 표본 조건

- 양쪽 세션 모두 `measured_count >= 20`
- 이 조건을 못 채우면 `표본 부족`

### 5-2. 정확도 차이 기준

- 정확도 차이 `>= 15%p`
  - `유의미`
  - 이후 annotation과 bias 해석에서 적극 참고 가능
- 정확도 차이 `10~15%p`
  - `참고 수준`
  - annotation에는 남기되 weighting 확대는 보류
- 정확도 차이 `< 10%p`
  - `유의미하지 않음`
  - 세션 축은 유지하되 핵심 결정 변수로 올리지 않음

## 6. 구현 구조

R1 첫 버전은 아래 경로를 쓴다.

- 정확도 원천:
  - `data/analysis/shadow_auto/directional_continuation_accuracy_tracker_state.json`
- guard trace 원천:
  - `data/trades/entry_decisions.detail.jsonl`
- promotion trace 원천:
  - `runtime_status.detail.json` 내 `ai_entry_traces`

집계기는 아래 artifact를 만든다.

- `data/analysis/shadow_auto/ca2_session_split_audit_latest.json`
- `data/analysis/shadow_auto/ca2_session_split_audit_latest.md`

## 7. 상태 기준

### READY

- `correct_rate_by_session`을 읽을 수 있음
- `measured_count_by_session`을 읽을 수 있음
- 세션 분해 결과가 artifact/detail payload에 정상 surface됨

### HOLD

- 세션 분해는 되지만 `measured_count < 20`인 버킷이 많아 유의미 판정이 어려움
- guard/promotion은 trace 분해까지만 되고 hindsight 품질은 부족

### BLOCKED

- `session_bucket` helper 기준이 불안정
- accuracy state를 읽지 못함
- session split artifact 생성이 실패함

## 8. 산출물

R1이 완료되면 아래가 생긴다.

- `runtime_status.detail.json`
  - `ca2_session_split_summary_v1`
  - `ca2_session_split_artifact_paths`
- `data/analysis/shadow_auto/ca2_session_split_audit_latest.json`
- `data/analysis/shadow_auto/ca2_session_split_audit_latest.md`

## 9. R1이 닫혔다는 뜻

R1이 닫혔다는 것은 세션이 execution에 영향을 주기 시작했다는 뜻이 아니다.

정확한 의미는 이렇다.

- 기존 CA2 지표를 세션별로 읽을 수 있다
- 세션 차이가 실제로 있는지 숫자로 말할 수 있다
- 그 차이가 크지 않으면 세션 축을 과대평가하지 않는다
- 그 차이가 크면 이후 R2~R5에서 annotation/bias 해석으로 안전하게 이어갈 준비가 된다
