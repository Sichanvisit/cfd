# R4 Canonical Surface 실행 로드맵

## 1. 목적

이 로드맵은 `R4 canonical surface`를 최소 구현 범위로 고정한다.

## 2. 범위

### 포함

- canonical surface contract
- row-level canonical surface fields
- runtime/detail summary export
- artifact 생성

### 제외

- chart painter 직접 교체
- execution/state25 직접 영향
- should-have-done과의 자동 정답 판정

## 3. 단계

### R4-A. contract 고정

포함:

- runtime surface enum
- execution surface enum
- alignment enum
- priority rule

완료 기준:

- `canonical_surface_contract_v1`를 읽을 수 있음

### R4-B. row-level canonical mapping

매핑:

- overlay event -> runtime surface
- final action -> execution surface
- runtime surface -> direction/continuation
- selection/countertrend -> phase

완료 기준:

- 각 row에 canonical flat fields가 붙음

### R4-C. summary/artifact

출력:

- runtime surface count
- execution surface count
- alignment count
- phase count
- direction count

완료 기준:

- `canonical_surface_summary_latest.json/.md`

### R4-D. runtime/detail export

출력:

- `canonical_surface_contract_v1`
- `canonical_surface_summary_v1`
- `canonical_surface_artifact_paths`

완료 기준:

- `runtime_status.detail.json`에서 읽을 수 있음

## 4. 상태 기준

### READY

- contract, row fields, summary, artifacts가 모두 있음

### HOLD

- contract는 있으나 일부 row만 canonical fields를 가짐

### BLOCKED

- row와 summary가 서로 다른 canonical mapping을 씀

## 5. 다음 연결

R4 다음은 `R5 session-aware annotation accuracy`다.

그때부터 아래 비교가 가능해진다.

- actual canonical surface
- expected canonical surface
- session별 phase/direction 정확도
