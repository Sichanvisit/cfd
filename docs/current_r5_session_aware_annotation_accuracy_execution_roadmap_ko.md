# R5 Session-Aware Annotation Accuracy 실행 로드맵

## 1. 목적

이 로드맵은 `R5 session-aware annotation accuracy`를 최소 구현 범위로 시작하는 순서를 정리한다.

## 2. 범위

### 포함

- direction accuracy by session
- annotation candidate count by session
- runtime/execution divergence by session
- phase accuracy 보류 상태 명시
- runtime/detail export
- artifact 생성

### 제외

- phase accuracy 확정 라벨 계산
- execution/state25 bias 확대
- session direct execution rule

## 3. 단계

### R5-A. contract 고정

포함 필드:

- `direction_accuracy_by_session`
- `measured_count_by_session`
- `phase_accuracy_by_session`
- `phase_accuracy_data_status`
- `annotation_candidate_count_by_session`
- `runtime_execution_divergence_count_by_session`
- `session_difference_significance`

### R5-B. summary 생성

입력:

- R1 session split
- R3 should-have-done summary
- R4 canonical surface summary

출력:

- 세션별 direction accuracy
- 세션별 candidate count
- 세션별 divergence count
- phase accuracy 보류 상태

### R5-C. runtime/detail export

출력:

- `session_aware_annotation_accuracy_contract_v1`
- `session_aware_annotation_accuracy_summary_v1`
- `session_aware_annotation_accuracy_artifact_paths`

### R5-D. artifact write

출력:

- `session_aware_annotation_accuracy_latest.json`
- `session_aware_annotation_accuracy_latest.md`

## 4. 상태 기준

### READY

- direction accuracy, candidate count, divergence count가 읽힘

### HOLD

- phase accuracy는 아직 insufficient labeled annotations

### BLOCKED

- R1/R3/R4 입력 축이 깨짐

## 5. 다음 연결

R5 다음은 여전히 `R6 execution/state25 연결`이 아니다.

R5 결과를 충분히 보고 나서만 아래를 다시 판단한다.

- session bias를 정말 확대할지
- phase accuracy가 충분히 쌓였는지
- execution/state25에 영향을 주어도 되는지
