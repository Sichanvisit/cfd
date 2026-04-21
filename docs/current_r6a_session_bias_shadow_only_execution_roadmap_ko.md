# R6-A Session Bias Shadow-Only 실행 로드맵

## 1. 목적

이 로드맵은 `R6-A shadow-only session bias`를 실제 코드와 runtime export에 안전하게 붙이는 순서를 정리한다.

## 2. 범위

### 포함

- shadow contract 정의
- row-level shadow field 부착
- summary/artifact 생성
- runtime/detail export
- 테스트

### 제외

- execution 변경
- state25 변경
- 세션별 direct rule 추가

## 3. 단계

### R6A-1. contract 고정

필수 계약:

- `mode = shadow_only`
- `execution_change_allowed = false`
- `state25_change_allowed = false`

### R6A-2. row field 생성

입력:

- `session_aware_annotation_accuracy_summary_v1`
- canonical row field

출력:

- candidate state
- effect
- confidence
- reason
- change flags

### R6A-3. report 생성

출력:

- `session_bias_shadow_report_latest.json`
- `session_bias_shadow_report_latest.md`

summary 예시:

- `candidate_state_count_summary`
- `effect_count_summary`
- `candidate_count_by_session`

### R6A-4. runtime/detail export

출력:

- `session_bias_shadow_contract_v1`
- `session_bias_shadow_summary_v1`
- `session_bias_shadow_artifact_paths`

### R6A-5. 테스트 잠금

검증:

- contract는 반드시 shadow-only
- execution/state25 변경 허용은 반드시 `false`
- high/low accuracy 세션에서 raise/lower effect가 계산됨
- artifact가 실제로 생성됨

## 4. 판정

### READY

- row/detail/artifact 모두 생성
- change allowed가 `false`

### HOLD

- shadow는 생성되지만 sample 부족으로 대부분 neutral

### BLOCKED

- R1/R5 입력 불안정으로 report 생성 실패

## 5. 다음 단계

R6-A가 완료되면 바로 execution/state25를 바꾸지 않는다.

다음 조건이 쌓일 때만 다음으로 간다.

- 세션별 shadow candidate 누적
- should-have-done 확정 후보 증가
- shadow bias가 실제로 설명력이 있는지 확인

그 전까지는 계속 `shadow-only`를 유지한다.
