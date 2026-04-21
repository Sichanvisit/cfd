# R0 CA2 안정 유지 실행 로드맵

## 1. 목적

이 로드맵은 `R0. CA2 안정 유지`를 실제 구현 단계로 내리는 문서다.

핵심은 아래 두 summary를 묶어 `READY / HOLD / BLOCKED`를 한 번에 읽게 만드는 것이다.

- `runtime_signal_wiring_audit_summary_v1`
- `directional_continuation_accuracy_summary_v1`

즉 새로운 예측 로직이 아니라, **기존 계측 체계의 생존 상태를 판정하는 운영 레이어**를 만든다.

## 2. 구현 범위

### 포함

- R0 전용 상태 판정기
- 직전 snapshot 대비 delta 계산
- JSON/Markdown artifact 생성
- runtime detail payload surface 추가
- 테스트 추가

### 제외

- continuation/guard/promotion core rule 변경
- session-aware KPI
- annotation contract
- bounded live rollout

## 3. 단계

### R0-A. 입력 summary 계약 고정

목표:

- wiring audit와 accuracy summary에서 R0가 읽어야 할 필드를 고정한다.

입력:

- `symbol_count`
- `execution_diff_surface_count`
- `flow_sync_match_count`
- `ai_entry_trace_count`
- `ai_entry_trace_execution_diff_count`
- `primary_measured_count`
- `primary_correct_rate`
- `resolved_observation_count`

완료 기준:

- R0 판정기가 위 필드만으로 동작 가능

### R0-B. 직전 snapshot 비교 규칙 추가

목표:

- “현재 값이 있다”가 아니라 “계속 누적되고 있다”를 판정한다.

핵심 비교:

- `primary_measured_count_delta`
- `resolved_observation_count_delta`
- `execution_diff_surface_count_delta`
- `flow_sync_match_count_delta`

완료 기준:

- 이전 artifact가 있으면 delta 계산
- 이전 artifact가 없으면 `first_snapshot=true`로 기록

### R0-C. READY / HOLD / BLOCKED 상태 판정기 구현

목표:

- R0 상태를 한 번에 읽을 수 있는 summary를 만든다.

판정 규칙:

- `READY`
  - `symbol_count > 0`
  - `execution_diff_surface_count == symbol_count`
  - `flow_sync_match_count == symbol_count`
  - `primary_measured_count > 0`
  - 누적 값이 역행하지 않음
- `HOLD`
  - 일부 surface 누락
  - 첫 snapshot
  - 누적은 있으나 증가 확인이 불명확
- `BLOCKED`
  - symbol row 비어 있음
  - execution diff surface가 사실상 죽음
  - flow sync가 사실상 죽음
  - accuracy 누적이 0이거나 역행

완료 기준:

- 상태값
- reason list
- delta summary
를 가진 artifact가 생성됨

### R0-D. runtime detail export 연결

목표:

- `runtime_status.detail.json`에서 바로 R0 상태를 읽을 수 있게 한다.

출력 필드:

- `ca2_r0_stability_summary_v1`
- `ca2_r0_stability_artifact_paths`

완료 기준:

- detail payload에 summary와 artifact 경로가 surface됨

### R0-E. 테스트

목표:

- READY / HOLD / BLOCKED가 의도대로 판정되는지 검증한다.

테스트 범위:

- first snapshot
- full ready snapshot
- partial missing -> hold
- regressed counts -> blocked
- runtime detail payload export

## 4. 구현 우선순위

1. R0 상태 판정기
2. artifact 생성기
3. runtime detail export
4. 테스트

## 5. 완료 기준

아래가 만족되면 R0 구현 단계는 완료다.

1. `ca2_r0_stability_latest.json/.md` 생성
2. `runtime_status.detail.json`에 R0 summary surface
3. READY / HOLD / BLOCKED 이유가 명시적으로 기록
4. 직전 snapshot 대비 delta가 기록
5. 관련 테스트 통과

## 6. 이후 연결

R0가 구현되면 그 다음은 아래 순서로 이어진다.

1. `R1` 세션 분해 read-only 분석
2. `R2` 최소 annotation contract
3. `R3` should-have-done label 축

즉 R0는 다음 단계의 바닥을 만드는 작업이다.
