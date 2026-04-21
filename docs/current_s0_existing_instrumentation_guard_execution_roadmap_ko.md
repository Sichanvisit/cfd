# S0 기존 계측 안정 유지 실행 로드맵

## 1. 목적

이 로드맵은 `S0. 기존 계측 안정 유지`를 코드로 고정하는 실행 순서를 정리한다.

핵심은 새 해석층을 올리기 전에 아래 기존 summary가 계속 살아 있는지 하나의 guard로 묶는 것이다.

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `ca2_session_split_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `session_bias_shadow_summary_v1`

## 2. 구현 범위

### 포함

- S0 stability guard 서비스
- dependency별 surface / freshness 판정
- JSON/Markdown artifact 생성
- runtime detail export
- 단위 테스트

### 제외

- 기존 summary 계산식 변경
- dominance/state/local structure 계산 추가
- execution/state25 동작 변경

## 3. 단계

### S0-A. dependency 입력 계약 고정

입력 dependency 6개를 명시적으로 고정한다.

- `runtime_signal_wiring_audit_report`
- `ca2_r0_stability_report`
- `ca2_session_split_report`
- `should_have_done_report`
- `canonical_surface_report`
- `session_bias_shadow_report`

완료 기준:

- S0 guard가 이 6개 report만으로 동작 가능

### S0-B. dependency 상태 surface 구현

각 dependency별로 아래를 계산한다.

- `summary_present`
- `summary_generated_at`
- `summary_freshness_state_v1`
- `artifact_paths_present`
- `artifact_files_exist`
- `artifact_freshness_state_v1`
- `dependency_status`
- `dependency_reasons`
- `upstream_summary_status`

완료 기준:

- dependency별 READY/HOLD/BLOCKED 근거가 artifact에 남음

### S0-C. 최종 status 판정

v1 상태 규칙:

- `BLOCKED`
  - dependency summary missing
  - upstream summary status = `BLOCKED`
- `HOLD`
  - summary는 있으나 `generated_at` 누락
  - artifact path / file missing
  - freshness stale
- `READY`
  - dependency 6개가 모두 생존하고 freshness 기준 만족

완료 기준:

- `state_strength_s0_stability_summary_v1.status`가 `READY/HOLD/BLOCKED` 중 하나로 고정됨

### S0-D. artifact 생성

아래 artifact를 생성한다.

- `data/analysis/shadow_auto/state_strength_s0_stability_latest.json`
- `data/analysis/shadow_auto/state_strength_s0_stability_latest.md`

완료 기준:

- runtime detail과 별도로 shadow artifact에서도 S0 상태를 읽을 수 있음

### S0-E. runtime detail export 연결

`runtime_status.detail.json`에 아래를 연결한다.

- `state_strength_s0_stability_summary_v1`
- `state_strength_s0_stability_artifact_paths`

완료 기준:

- live runtime detail에서 S0 상태를 바로 읽을 수 있음

### S0-F. 테스트 고정

최소 테스트:

- 모든 dependency가 fresh하면 `READY`
- artifact missing/stale이면 `HOLD`
- summary missing 또는 upstream blocked면 `BLOCKED`
- runtime detail export에 S0 summary/artifact_paths 포함

## 4. 초기 운영 기준

### freshness 기준

- 초기값: `900초`
- 이 값은 운영 calibration용 초기값이며 고정 진리가 아님

### upstream status 해석

- upstream `HOLD`는 S0 `BLOCKED` 사유가 아니다
- upstream `BLOCKED`는 S0 `BLOCKED`로 올린다

## 5. 완료 기준

아래가 모두 만족되면 `S0` 구현 완료로 본다.

1. S0 guard 서비스가 생성된다
2. shadow artifact가 생성된다
3. runtime detail에 S0 summary가 export된다
4. dependency별 이유가 JSON에 남는다
5. 테스트가 통과한다

## 6. 다음 연결

`S0`가 완료되면 그 다음은 아래 순서로 간다.

1. `S1 state_strength_profile_contract_v1`
2. `S2 local_structure_profile_v1`
3. `S3 state_structure_dominance_profile_v1`

즉 `S0`는 해석 품질 개선 자체가 아니라, 그 이후 단계를 안전하게 올리기 위한 기존 계측 보호막이다.
