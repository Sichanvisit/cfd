# R1 CA2 세션 분해 실행 로드맵

## 1. 목적

이 로드맵은 `R1. CA2 지표의 세션 분해`를 실제 구현 순서로 정리한다.

## 2. 범위

### 포함

- `session_bucket` 기준으로 continuation accuracy 분해
- `session_bucket` 기준으로 guard/promotion trace 분해
- 세션 차이 유의미 판정
- runtime detail payload surface
- shadow auto artifact 생성

### 제외

- session 기반 execution 변경
- session 기반 state25 weight/threshold 조정
- session을 방향 결정 규칙으로 사용하는 것
- annotation/stage/state25 영향력 확대

## 3. 단계

### R1-A. accuracy by session

구현:

- `directional_continuation_accuracy_tracker_state.json`에서
  `resolved_observations`를 읽는다
- `primary_horizon_bars = 20` 기준으로 필터링한다
- `session_bucket_v1` 기준으로 `correct_rate_by_session`, `measured_count_by_session`를 만든다

완료 기준:

- 4개 세션 버킷에 대해 `measured_count`와 `correct_rate`를 읽을 수 있음

### R1-B. guard / promotion trace by session

구현:

- `entry_decisions.detail.jsonl`에서 guard trace를 읽는다
- `ai_entry_traces`에서 promotion trace를 읽는다
- 첫 버전은 trace 분해부터 하고, hindsight 부족 시 `INSUFFICIENT_HINDSIGHT`로 남긴다

완료 기준:

- `guard_helpful_rate_by_session`
- `promotion_win_rate_by_session`
  필드가 최소한 동일한 키 구조로 surface됨

### R1-C. 세션 차이 유의미 판정

구현:

- 양쪽 세션 모두 `measured_count >= 20`인지 확인
- 세션 간 최대 정확도 차이를 계산
- 아래 기준으로 판정

기준:

- `>= 15%p`: `SIGNIFICANT`
- `10~15%p`: `REFERENCE_ONLY`
- `< 10%p`: `NOT_SIGNIFICANT`
- 표본 조건 실패: `INSUFFICIENT_SAMPLE`

완료 기준:

- `session_difference_significance`가 summary에 포함됨

### R1-D. runtime/detail export

구현:

- `ca2_session_split_summary_v1`
- `ca2_session_split_artifact_paths`
를 `runtime_status.detail.json`에 export

완료 기준:

- detail payload에서 R1 summary와 artifact path를 읽을 수 있음

### R1-E. artifact write

구현:

- `ca2_session_split_audit_latest.json`
- `ca2_session_split_audit_latest.md`
를 생성

완료 기준:

- json / md 둘 다 생성됨

## 4. 상태 기준

### READY

- 세션별 `correct_rate`, `measured_count`가 읽힘
- summary와 artifact가 runtime/detail에 surface됨

### HOLD

- 세션 분해는 되지만 표본 부족
- guard/promotion은 trace-only라 해석 확대 보류

### BLOCKED

- session helper 또는 accuracy state 의존성이 깨짐
- artifact 생성이나 payload export가 실패함

## 5. 테스트

R1 구현은 아래를 잠근다.

- session accuracy 분해
- significance 판정
- trace 기반 guard/promotion 세션 분해
- artifact write
- runtime detail surface

## 6. 다음 연결

R1이 닫히면 바로 execution으로 가지 않는다.

다음 순서는 이렇다.

1. R1 결과를 보고 세션 차이가 실제로 큰지 확인
2. 차이가 유의미하면 R2 annotation contract에서 세션 축을 유지
3. 차이가 작으면 세션 축은 read-only 참고값으로만 유지
4. 실행/state25 영향력 확대는 R5 이후 재판단
