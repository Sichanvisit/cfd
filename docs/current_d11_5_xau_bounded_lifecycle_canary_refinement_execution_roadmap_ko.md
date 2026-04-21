# D11-5. XAU Bounded Lifecycle Canary Refinement Execution Roadmap

## 목표

- XAU bounded lifecycle canary를 더 좁고 안전한 slice로 세분화한다.

## 실행 순서

### 1. contract 확장

- `bounded_lifecycle_canary_contract_v1`에
  - `xau_lifecycle_canary_risk_gate_enum_v1`
  - `xau_lifecycle_canary_scope_detail_enum_v1`
  - refined `lifecycle_canary_policy_slice_enum_v1`
  를 추가한다.

### 2. row logic 확장

- `build_bounded_lifecycle_canary_row_v1`에서 XAU 전용 gate 함수를 추가한다.
- `pilot match / ambiguity / texture / entry / hold`를 조합해 `PASS/FAIL_*`를 판정한다.
- `HOLD_ONLY`와 `HOLD_REDUCE_ONLY`를 분기한다.

### 3. summary 확장

- `xau_lifecycle_canary_risk_gate_count_summary`
- `xau_lifecycle_canary_scope_detail_count_summary`
  를 summary에 추가한다.

### 4. 테스트 확장

- XAU aligned row가
  - `HOLD_REDUCE_ONLY`
  - `HOLD_ONLY`
  로 갈리는지 본다.
- ambiguity/drift/pilot mismatch가 있으면 `OBSERVE_ONLY`로 떨어지는지 본다.

### 5. runtime export 유지

- 기존 `bounded_lifecycle_canary_summary_v1`
- `bounded_lifecycle_canary_artifact_paths`
  는 유지한다.
- 새 row field가 기존 detail payload와 충돌하지 않게 한다.

## 검증 기준

- 기존 D11-4 테스트를 깨지 않음
- 신규 XAU gate 테스트 통과
- runtime export에 새 field가 정상 반영됨
