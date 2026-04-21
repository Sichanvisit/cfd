# S3. Runtime Read-Only Surface V1 실행 로드맵

## 1. 목표

S3는 S1/S2에서 계산한 state strength와 local structure를
runtime row 관점에서 바로 읽을 수 있는 read-only surface로 묶는 단계다.

이 단계의 핵심은 `consumer_veto_tier_v1`를 공통 계약으로 surface하는 것이다.

## 2. 구현 순서

### S3-1. contract/service 추가

- `runtime_readonly_surface_contract_v1` 정의
- `consumer_veto_tier_v1` enum 정의
- row builder:
  - `build_runtime_readonly_surface_row_v1(...)`
- attach helper:
  - `attach_runtime_readonly_surface_fields_v1(...)`

### S3-2. veto tier 판정 로직 추가

- `FRICTION_ONLY`
- `BOUNDARY_WARNING`
- `REVERSAL_OVERRIDE`

를 state strength/local structure 조합으로 판정한다.

중요 원칙:

- `friction`만으로 side를 뒤집지 않는다.
- `REVERSAL_OVERRIDE`는 failed hold + counter drive + reversal evidence 조합이 있을 때만 허용한다.

### S3-3. summary artifact 추가

- `runtime_readonly_surface_summary_v1`
- `runtime_readonly_surface_artifact_paths`
- shadow artifact:
  - `runtime_readonly_surface_summary_latest.json`
  - `runtime_readonly_surface_summary_latest.md`

### S3-4. trading_application 연결

pipeline 순서:

1. S1 state strength attach
2. S1 summary write
3. S2 local structure attach
4. S2 summary write
5. S3 runtime read-only surface attach
6. S3 summary write

그리고 `runtime_status.detail.json`에 아래를 export한다.

- `runtime_readonly_surface_contract_v1`
- `runtime_readonly_surface_summary_v1`
- `runtime_readonly_surface_artifact_paths`

### S3-5. 테스트 고정

최소 테스트:

- bull continuation with friction -> `FRICTION_ONLY`
- mixed/boundary case -> `BOUNDARY_WARNING`
- reversal-risk + failed hold -> `REVERSAL_OVERRIDE`
- runtime status export smoke
- artifact write smoke

## 3. 완료 기준

- NAS/XAU/BTC row 모두에서 같은 field 이름으로 읽힌다.
- `consumer_veto_tier_v1`가 상태 차이를 설명한다.
- summary artifact가 생성되고 runtime detail에 연결된다.

## 4. 상태 기준

- `READY`
  - 세 심볼 모두 surface
  - summary/artifact 정상
- `HOLD`
  - 일부 surface 또는 일부 artifact freshness 흔들림
- `BLOCKED`
  - runtime/detail payload 누락
  - S1/S2 profile과 충돌
  - 기존 계측을 깨뜨림
