# R3 Should-Have-Done 실행 로드맵

## 1. 목적

이 로드맵은 `R3 should-have-done`를 최소 구현 범위로 시작하는 순서를 정리한다.

## 2. 단계

### R3-A. contract 고정

고정 필드:

- `expected_direction`
- `expected_continuation`
- `expected_phase_v1`
- `expected_surface`
- `annotation_confidence_v1`
- `candidate_source_v1`
- `operator_note`

완료 기준:

- 공용 contract builder가 있음

### R3-B. 자동 후보 summary

첫 버전 후보:

- `AUTO_SURFACE_EXECUTION_MISMATCH`
- `AUTO_PROMOTION_REVIEW`

완료 기준:

- 최근 후보 rows와 summary count를 생성할 수 있음

### R3-C. runtime/detail export

출력:

- `should_have_done_contract_v1`
- `should_have_done_summary_v1`
- `should_have_done_artifact_paths`

완료 기준:

- detail payload에서 contract와 summary를 읽을 수 있음

### R3-D. artifact write

출력:

- `should_have_done_candidate_summary_latest.json`
- `should_have_done_candidate_summary_latest.md`

완료 기준:

- artifact가 생성됨

## 3. 상태 기준

### READY

- contract 존재
- 자동 후보 summary 생성
- runtime/detail export 성공

### HOLD

- contract는 있으나 자동 후보 없음

### BLOCKED

- contract와 summary가 서로 다른 필드 체계를 씀
- artifact 또는 payload export 실패

## 4. 다음 연결

R3 다음은 `R4 canonical surface`다.

R3가 닫히면 아래를 그 바닥 위에 올린다.

- `expected_surface`와 실제 surface 통합
- chart/runtime/execution/hindsight의 공용 표현 정리
