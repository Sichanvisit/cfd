# F0. 진단 체인 정합 고정 상세 계획

## 1. 목적

F0의 목적은 새 `aggregate directional flow` 전환을 시작하기 전에, 현재 XAU 진단 체인에서

- raw runtime row
- effective recomputation row
- refined gate audit 해석
- bounded lifecycle canary 해석

이 서로 왜 다른지, 그리고 그 차이가 **persisted field 누락 때문인지 / 실제 계산 차이 때문인지**를 일관되게 설명 가능한 상태로 만드는 것이다.

즉 F0는 새 판단 로직이 아니라, 앞으로 `structure gate -> aggregate flow -> exact match bonus`로 넘어가기 전에 **진단 체인이 같은 입력을 같은 기준으로 소비하고 있는지 고정하는 진단층**이다.

## 2. 왜 지금 F0가 필요한가

현재까지 구축된 체인은 다음과 같다.

1. `symbol_specific_state_strength_calibration`
2. `xau_readonly_surface`
3. `state_slot_execution_interface_bridge`
4. `state_slot_position_lifecycle_policy`
5. `execution_policy_shadow_audit`
6. `bounded_lifecycle_canary`
7. `xau_refined_gate_timebox_audit`

문제는 현재 XAU live row에서 다음 현상이 반복되었다는 점이다.

- raw runtime row에는 일부 flat field가 비어 있다
- 하지만 effective recomputation을 하면 값이 정상적으로 계산된다
- canary와 audit는 recomputation 기준으로는 설명 가능하지만, raw persisted payload만 보면 이유를 놓치기 쉽다

이 상태를 그대로 두고 `flow_structure_gate_v1`, `aggregate_conviction_v1`, `flow_persistence_v1` 구현으로 넘어가면,

- stale field 때문에 오판처럼 보이는 현상
- 실제 계산 충돌과 단순 persisted 누락이 섞이는 현상
- 나중에 threshold calibration이 잘못된 layer를 원인으로 삼는 현상

이 생길 수 있다.

따라서 F0는 **새 flow gate 구현 전에 현재 진단 체인을 정렬해두는 선행 단계**다.

## 3. F0의 핵심 질문

F0가 답해야 하는 질문은 아래 네 가지다.

1. raw runtime row에서 현재 어떤 핵심 field가 비어 있는가
2. 같은 row를 recompute하면 어떤 값이 실제로 계산되는가
3. refined gate audit가 그 recomputation 결과를 일관되게 설명하는가
4. canary 결론이 stale field가 아니라 effective recomputation 기준으로 내려졌다고 설명 가능한가

## 4. 비교 대상

F0는 XAU current row 기준으로 아래 세 층을 나란히 비교한다.

### 4-1. Raw Runtime Row

`runtime_status.detail.json`에 저장된 현재 persisted row.

여기서는 실제 운영자가 가장 먼저 보게 되는 값들을 본다.

예:

- `symbol_state_strength_best_profile_key_v1`
- `symbol_state_strength_profile_match_v1`
- `symbol_state_strength_flow_support_state_v1`
- `xau_state_slot_core_v1`
- `lifecycle_canary_candidate_state_v1`
- `xau_lifecycle_canary_risk_gate_v1`

### 4-2. Effective Recompute Row

같은 raw row에서 downstream field를 걷어내고,

- symbol calibration
- XAU readonly surface
- bridge
- lifecycle policy
- shadow audit
- bounded canary

순으로 다시 계산한 row.

이 값이 현재 체인 기준의 **실제 계산 결과**다.

### 4-3. Audit Interpretation Row

`xau_refined_gate_timebox_audit`가 raw row를 어떻게 설명하는지 본다.

여기서는 특히 아래 값을 본다.

- `xau_gate_saved_vs_effective_state_v1`
- `xau_gate_failure_stage_v1`
- `xau_gate_effective_candidate_state_v1`
- `xau_gate_effective_risk_gate_v1`
- `xau_gate_effective_flow_support_state_v1`

즉 audit가 raw/effective 차이를 제대로 설명하고 있는지 검증한다.

## 5. F0에서 분리해야 하는 두 종류의 차이

F0는 차이를 모두 같은 문제로 취급하면 안 된다.

### 5-1. Persisted Field Gap

예:

- raw row에는 `aggregate_conviction`이 비어 있다
- recompute하면 값이 나온다
- audit도 `PERSISTED_FIELDS_MISSING`으로 설명한다

이 경우는 **설명 가능한 차이**다.

### 5-2. Real Calculation Divergence

예:

- same raw input
- effective recomputation row는 `OBSERVE_ONLY`
- audit embedded effective conclusion은 `BOUNDED_READY`

이 경우는 단순 persisted 누락이 아니라 **동일 입력에서 layer별 결론이 뒤집힌 것**이다.

이건 `BLOCKED`로 다뤄야 한다.

## 6. F0 상태 정의

### READY

차이가 있어도 원인을 설명 가능하다.

예:

- raw row는 일부 field 누락
- effective recomputation은 정상 계산
- audit가 그 차이를 `PERSISTED_FIELDS_MISSING` 또는 `PERSISTED_OUTDATED`로 설명
- effective와 audit의 embedded effective conclusion은 일치

### HOLD

일부 chain이 여전히 stale field 또는 partial recomputation에 의존한다.

예:

- raw/effective 차이는 있는데
- audit로 충분히 설명되지 않거나
- effective 쪽 핵심 field 자체가 아직 비어 있어
- 체인이 완전히 닫히지 않음

### BLOCKED

같은 입력에서 layer별 결론이 뒤집힌다.

예:

- effective recomputation row의 canary 결론과
- audit가 담고 있는 effective conclusion이 다름

이 경우는 persisted 누락 문제가 아니라 **체인 정합 문제**다.

## 7. F0에서 고정할 핵심 규칙

1. F0는 진단 전용이다.
2. execution/state25를 직접 바꾸지 않는다.
3. raw row 차이와 effective chain 차이를 분리해서 기록한다.
4. `xau_refined_gate_timebox_audit`는 stale-vs-effective 설명의 주 source로 사용한다.
5. `BLOCKED`는 오직 “같은 effective input인데 layer 결론이 다름”일 때만 쓴다.
6. persisted field 누락은 그 자체로 실패가 아니라, 설명 가능하면 `READY`다.

## 8. Row-Level Surface 제안

### 상태 surface

- `state_flow_f0_chain_alignment_state_v1`
- `state_flow_f0_raw_vs_effective_state_v1`
- `state_flow_f0_effective_vs_audit_state_v1`
- `state_flow_f0_primary_divergence_layer_v1`

### 핵심 비교 surface

- `state_flow_f0_raw_profile_key_v1`
- `state_flow_f0_effective_profile_key_v1`
- `state_flow_f0_raw_slot_core_v1`
- `state_flow_f0_effective_slot_core_v1`
- `state_flow_f0_raw_flow_support_state_v1`
- `state_flow_f0_effective_flow_support_state_v1`
- `state_flow_f0_raw_canary_state_v1`
- `state_flow_f0_effective_canary_state_v1`
- `state_flow_f0_raw_risk_gate_v1`
- `state_flow_f0_effective_risk_gate_v1`

### 설명 surface

- `state_flow_f0_missing_persisted_fields_v1`
- `state_flow_f0_audit_failure_stage_v1`
- `state_flow_f0_reason_summary_v1`

## 9. Summary Surface 제안

- `alignment_state_count_summary`
- `raw_vs_effective_state_count_summary`
- `effective_vs_audit_state_count_summary`
- `primary_divergence_layer_count_summary`
- `alignment_ready_count`
- `alignment_hold_count`
- `alignment_blocked_count`

## 10. 이번 단계에서 하지 않을 것

F0는 아래를 하지 않는다.

- 새 threshold 추가
- XAU pilot gate 완화
- canary eligibility 완화
- flow 구조 판정 변경
- execution/state25 연결 변경

즉 F0는 어디까지나 **현재 체인을 같은 기준으로 설명 가능한지 정리하는 단계**다.

## 11. 완료 기준

- XAU current row에 대해 raw/effective/audit 차이를 한 줄 설명으로 읽을 수 있다
- persisted field 누락과 real divergence가 분리된다
- runtime detail에 F0 contract/summary/artifact가 올라간다
- `READY / HOLD / BLOCKED` 판정이 재현 가능하다
