# R2 최소 Annotation Contract 실행 로드맵

## 1. 목적

이 로드맵은 `R2 최소 annotation contract`를 실행 가능한 범위로 잠그기 위한 순서를 정의한다.

## 2. 범위

### 포함

- 최소 annotation enum 고정
- contract builder 구현
- runtime/detail export
- R1 결과를 기준으로 R2 진입 가능 여부 명시

### 제외

- annotation 자동 생성
- should-have-done 확장
- canonical surface builder
- execution/state25/forecast 연결

## 3. 단계

### R2-A. 최소 enum 고정

고정 내용:

- `direction_annotation`: `UP / DOWN / NEUTRAL`
- `continuation_annotation`: `CONTINUING / NON_CONTINUING / UNCLEAR`
- `continuation_phase_v1`: `CONTINUATION / BOUNDARY / REVERSAL`
- `annotation_confidence_v1`: `MANUAL_HIGH / AUTO_HIGH / AUTO_MEDIUM / AUTO_LOW`

완료 기준:

- enum이 코드와 문서에서 동일함

### R2-B. contract builder 구현

구현:

- contract version
- field list
- session is bias layer only
- execution/state25 bias expansion blocked

완료 기준:

- consumer가 공용 contract를 읽을 수 있음

### R2-C. runtime/detail export

출력:

- `session_direction_annotation_contract_v1`

완료 기준:

- `runtime_status.detail.json`에서 contract를 읽을 수 있음

### R2-D. R1 gate 문서화

핵심:

- R1 `READY`면 최소 contract 진입 허용
- `ASIA sample gap`은 허용
- session bias expansion은 여전히 `HOLD`

완료 기준:

- R2 시작 가능 범위와 금지 범위가 문서에 명시됨

## 4. 상태 기준

### READY

- 최소 contract가 코드/문서에 고정
- runtime/detail에 export됨

### HOLD

- contract는 있으나 일부 consumer naming이 다름

### BLOCKED

- session bias를 execution/state25에 바로 적용하려는 변경이 섞임

## 5. 다음 연결

R2가 닫히면 다음은 `R3 should-have-done`이다.

그때부터 아래를 이 contract 위에 쌓는다.

- `expected_direction`
- `expected_continuation`
- `expected_phase_v1`
- `expected_surface`
- `annotation_confidence_v1`
