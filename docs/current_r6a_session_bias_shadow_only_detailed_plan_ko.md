# R6-A Session Bias Shadow-Only 상세 계획

## 1. 목적

R6-A의 목적은 세션-aware bias를 실제 execution이나 state25에 적용하지 않고,
`만약 세션 bias를 참고했다면 어떤 변화가 있었을지`를 shadow-only로 기록하는 것이다.

즉 이 단계는 적용 단계가 아니라 관찰 단계다.

- `execution` 변경 없음
- `state25` 변경 없음
- row/detail/artifact에 shadow candidate만 남김

## 2. 왜 필요한가

R1~R5를 통해 아래는 이미 준비됐다.

- 세션별 방향 정확도
- 최소 annotation contract
- should-have-done 후보
- canonical runtime/execution surface
- session-aware annotation accuracy

하지만 아직은 다음 질문에 바로 답하면 위험하다.

- 미국장에서는 continuation bias를 올려야 하나?
- 유럽장에서는 continuation bias를 낮춰야 하나?
- 그 bias가 execution/state25를 실제로 바꾸게 해도 되나?

그래서 R6-A는 먼저 `shadow-only bias`로 남겨서,
실제 적용 전에 바꿨다면 어떤 효과가 있었을지를 확인하는 완충 단계다.

## 3. 범위

### 포함

- row-level shadow field 생성
- summary/artifact 생성
- detail payload export
- `READY / OBSERVE_ONLY / INSUFFICIENT_SAMPLE / NO_SESSION_EDGE` 같은 candidate 상태 surface

### 제외

- execution action 변경
- state25 weight/threshold 변경
- direct session buy/sell rule
- phase별 bias 적용

## 4. row-level field

R6-A v1은 아래 필드를 row에 붙인다.

- `session_bias_candidate_state_v1`
- `session_bias_effect_v1`
- `session_bias_confidence_v1`
- `session_bias_reason_v1`
- `session_bias_session_bucket_v1`
- `session_bias_direction_accuracy_v1`
- `session_bias_measured_count_v1`
- `session_bias_significance_status_v1`
- `would_change_surface_v1`
- `would_change_execution_v1`
- `would_change_state25_v1`

## 5. candidate state 해석

### `INSUFFICIENT_SAMPLE`

- 해당 세션의 `measured_count < 20`
- 아직 bias를 읽을 표본이 부족함

### `NO_SESSION_EDGE`

- 세션 차이 유의미 판정이 없거나 약함
- session gap을 bias 근거로 쓰기 어려움

### `OBSERVE_ONLY`

- 세션 차이는 보이지만 현재 row가 directional surface가 아니거나
- 정확도가 중간대라 bias 방향을 올리거나 내리기 애매함

### `READY`

- row가 directional surface를 가지고 있고
- 세션별 direction accuracy가 충분히 높거나 낮아
- `raise / lower continuation confidence` 그림자를 읽을 수 있음

## 6. effect 해석

- `RAISE_CONTINUATION_CONFIDENCE`
- `LOWER_CONTINUATION_CONFIDENCE`
- `KEEP_NEUTRAL`

이 effect는 shadow-only 의미이며,
실제 execution/state25에 적용되지 않는다.

## 7. 완료 기준

- detail payload에
  - `session_bias_shadow_contract_v1`
  - `session_bias_shadow_summary_v1`
  - `session_bias_shadow_artifact_paths`
  가 보임
- row-level field가 `latest_signal_by_symbol`에 surface됨
- artifact가 생성됨
- execution/state25 직접 변경 허용 플래그는 계속 `false`

## 8. 상태 기준

### READY

- shadow summary와 row field가 정상 생성됨
- execution/state25 change allowed가 모두 `false`

### HOLD

- row field는 생성되지만 표본 부족으로 대부분 `OBSERVE_ONLY / INSUFFICIENT_SAMPLE`

### BLOCKED

- R1/R5 입력이 깨져 session bias shadow를 안정적으로 만들 수 없음

## 9. 다음 연결

R6-A 다음은 곧바로 live bias 적용이 아니다.

다음 판단은 아래 순서로 간다.

1. shadow-only 결과 누적
2. 세션별 should-have-done 누적
3. execution/state25에 실제로 영향을 줄 가치가 있는지 재판단
4. 그 다음에만 `R6-B execution canary`, `R6-C state25 canary` 검토
