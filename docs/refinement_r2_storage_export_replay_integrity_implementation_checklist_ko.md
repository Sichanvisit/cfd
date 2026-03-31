# R2 Storage / Export / Replay Integrity Implementation Checklist

## 1. 목적

이 문서는 [refinement_r2_storage_export_replay_integrity_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_storage_export_replay_integrity_spec_ko.md)를 실제 구현 순서로 내린 checklist다.

R2의 목적은 runtime row, replay intermediate, semantic dataset이
같은 key와 같은 해석 기준으로 묶이게 만드는 것이다.

즉 이 단계는 새 semantic을 만드는 단계가 아니라,
이미 고정된 reason/key 계약이 storage/export/replay/dataset 전체에서
깨지지 않는지 확인하고 보강하는 단계다.


## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- `decision_row_key` uniqueness 재점검
- `runtime_snapshot_key`, `trade_link_key`, `replay_row_key` join coverage 점검
- hot/detail -> export/replay propagation contract 점검
- semantic dataset builder 최신 row 구조 호환성 점검

### 하지 않을 것

- `Stage E` 추가 미세조정
- semantic target 정의 변경
- promotion gate 정책 변경
- detail sidecar 용량 최적화를 이유로 join 안정성을 희생하는 변경


## 3. 입력 기준

- 마스터 계획: [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- R2 spec: [refinement_r2_storage_export_replay_integrity_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_storage_export_replay_integrity_spec_ko.md)
- R2 key/join snapshot: [refinement_r2_key_contract_snapshot_and_join_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_key_contract_snapshot_and_join_casebook_ko.md)
- key/taxonomy 기준: [refinement_r0_non_action_taxonomy_and_key_linkage_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_non_action_taxonomy_and_key_linkage_ko.md)
- storage follow-up: [execution_storage_followup_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\execution_storage_followup_roadmap_ko.md)
- semantic handoff: [storage_semantic_flow_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\storage_semantic_flow_handoff_ko.md)

주 대상 파일:

- `backend/services/storage_compaction.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`
- `ml/semantic_v1/dataset_builder.py`
- `scripts/export_entry_decisions_ml.py`

확인용 파일:

- `backend/services/entry_engines.py`
- `backend/services/entry_try_open_entry.py`
- `data/trades/entry_decisions.csv`
- `data/trades/entry_decisions.detail.jsonl`


## 3-1. 현재 구현 상태 (2026-03-26, R2 1차)

현재까지 실제 반영된 항목은 아래다.

- Step 2 일부:
  - export key integrity report 추가
- Step 3 일부:
  - replay key integrity manifest 추가
  - replay detail sidecar의 `decision_row_key` fallback 추가
- Step 5:
  - semantic dataset join health report 추가
  - latest-row compatibility memo 작성 완료
- 관련 테스트:
  - `test_export_entry_decisions_ml.py`
  - `test_replay_dataset_builder.py`
  - `test_semantic_v1_dataset_builder.py`
  - `test_storage_compaction.py`
- 재검증:
  - `pytest tests/unit/test_storage_compaction.py tests/unit/test_export_entry_decisions_ml.py tests/unit/test_replay_dataset_builder.py tests/unit/test_semantic_v1_dataset_builder.py`
  - `31 passed`

즉 R2는 “코드 1차 구현과 audit 문서화가 함께 닫힘” 상태다.

현재까지 작성된 audit 문서:

- [refinement_r2_key_contract_snapshot_and_join_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_key_contract_snapshot_and_join_casebook_ko.md)
- [refinement_r2_decision_row_key_uniqueness_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_decision_row_key_uniqueness_audit_ko.md)
- [refinement_r2_join_coverage_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_join_coverage_casebook_ko.md)
- [refinement_r2_hot_detail_propagation_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_hot_detail_propagation_audit_ko.md)
- [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)


## 4. 구현 순서

### Step 1. Key Contract Snapshot 고정

목표:

- 현재 `decision_row_key`, `runtime_snapshot_key`, `trade_link_key`, `replay_row_key`의
  역할과 생성 위치를 코드 기준으로 다시 확정한다.

확인 포인트:

- 어떤 함수가 key를 생성하는지
- 어떤 key가 reason-bearing key인지
- export / replay / dataset이 어떤 key를 primary join으로 보는지

완료 기준:

- key 역할 표 초안이 있다.
- key 생성 owner를 코드 기준으로 바로 설명할 수 있다.


### Step 2. Decision Row Key Uniqueness Audit

목표:

- skipped/wait/non-action row에서 `decision_row_key` 충돌이 없는지 점검한다.

최소 확인 항목:

- 같은 `signal_bar_ts` 반복 rows
- `observe_reason`, `probe_state`, `blocked_by`, `action_none_reason` suffix 작동 여부
- `decision_row_key == replay_row_key` 가정이 깨지는 대표 케이스 존재 여부

완료 기준:

- 최근 샘플 기준 중복 케이스가 재현되지 않는다.
- 중복이 있으면 어떤 suffix가 부족한지 바로 설명 가능하다.


### Step 3. Join Coverage Casebook 작성

목표:

- `runtime_snapshot_key`, `trade_link_key`, `replay_row_key` join 누락 케이스를 표준 케이스북으로 정리한다.

최소 분류:

- runtime row -> decision row 누락
- decision row -> export row 누락
- decision row + detail sidecar -> replay intermediate 누락
- replay intermediate -> semantic dataset 누락

완료 기준:

- 최소 1건 이상의 대표 샘플로 각 join 경로를 설명할 수 있다.
- 누락이 없다면 “누락 없음”을 어떤 샘플과 테스트로 판단했는지 남긴다.


### Step 4. Hot / Detail Propagation Audit

목표:

- 최신 hot/detail 구조가 export/replay intermediate로 그대로 전달되는지 확인한다.

최소 확인 필드:

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `entry_probe_plan_v1`
- `probe_candidate_v1`
- `entry_decision_context_v1`
- `entry_decision_result_v1`
- `semantic_shadow_*`
- `semantic_live_*`

완료 기준:

- hot/detail -> export/replay propagation table이 있다.
- 어떤 필드가 hot-only, detail-only, export-required, replay-required인지 구분 가능하다.


### Step 5. Semantic Dataset Builder Compatibility Audit

목표:

- semantic dataset builder가 최신 export/replay row 구조를 안정적으로 읽는지 확인한다.

최소 확인 항목:

- builder가 최신 key를 정상 인식하는지
- 구버전 row와 최신 row가 섞일 때 안전하게 처리되는지
- join 누락 때문에 dataset row 수가 silent drop 되지 않는지

완료 기준:

- dataset builder compatibility memo가 있다.
- latest row 구조 기준 실패 또는 drop이 있으면 원인을 바로 설명할 수 있다.


### Step 6. 테스트 묶음 확인

권장 최소 테스트:

- `pytest tests/unit/test_storage_compaction.py`
- `pytest tests/unit/test_export_entry_decisions_ml.py`
- `pytest tests/unit/test_replay_dataset_builder.py`
- `pytest tests/unit/test_semantic_v1_dataset_builder.py`

상황별 추가:

- `pytest tests/unit/test_entry_engines.py`
- `pytest tests/unit/test_check_semantic_canary_rollout.py`

완료 기준:

- R2 관련 key/join/export/replay/dataset 테스트가 통과한다.
- 실패가 있으면 어느 join 축의 문제인지 바로 분리 가능하다.


### Step 7. 문서 동기화

목표:

- R2 spec과 checklist, 마스터 refinement 문서가 현재 구현 상태와 맞게 유지되게 한다.

완료 기준:

- R2 문서만 읽어도 현재 상태와 다음 착수점이 보인다.


## 5. Done Definition

아래가 모두 만족되면 R2 구현 착수 단계를 닫을 수 있다.

- `decision_row_key` uniqueness audit가 끝난다.
- join coverage casebook이 정리된다.
- hot/detail -> export/replay propagation contract가 표로 설명된다.
- semantic dataset builder latest-row compatibility가 확인된다.
- 관련 테스트 묶음이 현재 구조를 깨지 않는다는 근거가 있다.


## 6. 다음 단계

R2가 닫히면 다음은 `R3. Semantic ML Step 3~7 refinement`다.

즉 순서는 아래처럼 본다.

```text
R0 정합성 최소셋 -> R1 Stage E 미세조정
-> R2 저장 / export / replay 정합성 -> R3 Semantic ML Step 3~7 refinement
-> R4 Acceptance / promotion-ready
```
