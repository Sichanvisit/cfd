# F0. 진단 체인 정합 고정 실행 로드맵

## F0-1. 공용 계약 정의

목적:

- F0를 진단 전용 contract로 고정한다.

작업:

- `state_flow_f0_chain_alignment_contract_v1`
- 상태 enum
  - `READY / HOLD / BLOCKED / NOT_APPLICABLE`
- 비교 enum
  - `raw_vs_effective`
  - `effective_vs_audit`
  - `primary_divergence_layer`

완료 기준:

- row-level / summary-level field가 문서와 코드에서 동일하다.

## F0-2. Effective recomputation 기준 고정

목적:

- F0가 raw row를 어떤 경로로 다시 계산하는지 명확히 고정한다.

작업:

- downstream field strip
- 아래 순서로 recompute
  1. symbol calibration
  2. XAU readonly surface
  3. execution bridge
  4. lifecycle policy
  5. execution shadow audit
  6. bounded lifecycle canary

완료 기준:

- F0 effective row가 XAU gate audit가 쓰는 recomputation 기준과 동일하다.

## F0-3. Raw vs Effective 차이 분리

목적:

- persisted field missing과 real conclusion drift를 분리한다.

작업:

- critical field set 정의
  - symbol calibration layer
  - XAU readonly surface layer
  - bounded canary layer
  - refined gate audit layer
- raw row missing/diff logic 구현

완료 기준:

- `PERSISTED_FIELDS_MISSING`
- `PERSISTED_OUTDATED`
- `CONCLUSION_DIVERGENCE`
- `CONSISTENT`
  를 재현 가능하게 구분한다.

## F0-4. Effective vs Audit 정합 검증

목적:

- 같은 effective input에 대해 audit embedded conclusion이 뒤집히지 않게 확인한다.

작업:

- audit row 생성
- 아래 값 비교
  - effective canary state
  - effective risk gate
  - effective flow support
  - effective aggregate/persistence

완료 기준:

- audit와 effective chain이 같은 입력에서 같은 결론을 주는지 확인 가능하다.

## F0-5. 상태 판정 고정

목적:

- `READY / HOLD / BLOCKED`를 일관되게 부여한다.

작업:

- `BLOCKED`
  - effective vs audit conflict
- `READY`
  - 차이가 있어도 audit로 설명 가능
- `HOLD`
  - stale/missing이 남아 있지만 설명이 충분히 닫히지 않음

완료 기준:

- 현재 XAU live row에 대해 F0 상태가 재현 가능하다.

## F0-6. Runtime surface 및 artifact 연결

목적:

- F0 결과를 runtime detail과 shadow artifact에 같이 올린다.

작업:

- row-level attach
- summary generation
- artifact write
- runtime export 연결

완료 기준:

- `runtime_status.detail.json`에
  - `state_flow_f0_chain_alignment_contract_v1`
  - `state_flow_f0_chain_alignment_summary_v1`
  - `state_flow_f0_chain_alignment_artifact_paths`
  가 보인다.

## F0-7. 테스트 잠금

목적:

- F0가 future regression에 흔들리지 않게 잠근다.

작업:

- 계약 테스트
- persisted field gap 설명 테스트
- artifact write 테스트
- runtime export 테스트

완료 기준:

- 단위 테스트 통과
- runtime export 테스트 통과

## F0 최종 목표

F0의 최종 목표는 새 flow gate를 만드는 것이 아니다.

목표는:

- 지금 XAU current row가
  - 왜 raw에서는 비어 보이고
  - 왜 effective recompute에서는 계산되고
  - 왜 audit에서는 그런 설명이 붙고
  - 왜 canary는 그 결론을 냈는지

를 **같은 기준으로 설명 가능한 상태로 고정하는 것**이다.
