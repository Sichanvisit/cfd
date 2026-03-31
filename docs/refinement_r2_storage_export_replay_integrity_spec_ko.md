# R2 Storage / Export / Replay Integrity Spec

## 1. 목적

이 문서는 refinement track의 `R2. 저장 / export / replay 정합성` 전용 spec이다.

R2의 목표는 runtime row, replay intermediate, semantic dataset이
같은 key와 같은 해석 기준으로 묶이게 만드는 것이다.

R0에서 `reason triplet`과 key 역할 분리를 고정했고,
R1에서 `Stage E` 미세조정을 일단 닫았으므로,
R2에서는 이제 그 해석 계약이 storage/export/replay 경로 전체에서
깨지지 않는지 점검하고 보강한다.


## 2. 이 문서의 역할

이 문서는 아래를 고정한다.

- 어떤 key를 source of truth로 볼지
- 어떤 파일이 어떤 join owner인지
- hot/detail 구조가 export/replay로 어떻게 전달되어야 하는지
- semantic dataset builder가 어떤 최신 row 구조를 안정적으로 읽어야 하는지

이 문서는 구현 순서 전체를 다루는 checklist가 아니라,
R2에서 무엇을 맞춰야 하는지와 어떤 축을 건드리면 안 되는지를 고정하는 spec이다.


## 3. 기준 문서

R2는 아래 문서를 기준 source set으로 삼는다.

- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- [refinement_r0_non_action_taxonomy_and_key_linkage_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_non_action_taxonomy_and_key_linkage_ko.md)
- [execution_storage_followup_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\execution_storage_followup_roadmap_ko.md)
- [storage_semantic_flow_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\storage_semantic_flow_handoff_ko.md)
- [semantic_ml_structure_change_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_structure_change_plan_ko.md)


## 4. 범위

### 포함 범위

- `decision_row_key` uniqueness audit
- `runtime_snapshot_key`, `trade_link_key`, `replay_row_key` join coverage audit
- hot/detail -> export/replay propagation contract
- semantic dataset builder latest-row compatibility
- detail sidecar를 용량보다 join 안정성 기준으로 다루는 정책

### 제외 범위

- `Position / Response / State / Evidence / Belief / Barrier` 의미 변경
- `Stage E` 미세조정 추가
- semantic target 정의 변경 자체
- bounded live promotion gate 운영 결정


## 5. 주 대상 파일

- `backend/services/storage_compaction.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`
- `ml/semantic_v1/dataset_builder.py`
- `scripts/export_entry_decisions_ml.py`

필요 시 아래 파일도 같이 본다.

- `backend/services/entry_engines.py`
- `backend/services/entry_try_open_entry.py`
- `backend/app/trading_application_runner.py`


## 6. 현재 계약 스냅샷

R2는 아래 계약이 이미 존재한다는 전제에서 시작한다.

### 6-1. reason triplet

- `observe_reason`
- `blocked_by`
- `action_none_reason`

이 세 필드는 같은 의미가 아니며 서로 다른 owner를 유지해야 한다.
R2는 이 triplet이 export/replay/dataset으로 누락 없이 전달되는지를 본다.

### 6-2. key 역할 분리

- `decision_row_key`
  - reason-bearing row identity
- `runtime_snapshot_key`
  - runtime signal linkage key
- `trade_link_key`
  - execution linkage key
- `replay_row_key`
  - replay/export/dataset join key

R2의 핵심은 이 key들이 runtime, export, replay intermediate, semantic dataset builder에서
같은 뜻으로 유지되는지 확인하는 것이다.

### 6-3. hot/detail 역할 분리

- hot:
  - 빠르게 읽는 compact decision row
- detail:
  - raw payload와 forensic trace를 담는 sidecar

R2에서는 detail sidecar를 가볍게 만드는 것보다
join 안정성과 재현 가능성을 우선한다.


## 7. R2 핵심 질문

R2는 아래 질문에 답할 수 있어야 한다.

1. 같은 runtime row가 export와 replay에서 같은 row로 다시 만나는가
2. `decision_row_key`가 skipped/wait row에서도 충돌 없이 유니크한가
3. hot/detail에 있는 최신 trace가 export/replay intermediate에서 빠지지 않는가
4. semantic dataset builder가 최신 row 구조를 안정적으로 읽는가


## 8. 세부 작업축

### R2-1. Decision Row Key Uniqueness Audit

#### 목표

`decision_row_key`가 sparse wait/non-action row에서도 충돌 없이
row identity 역할을 하게 만든다.

#### 점검 포인트

- 같은 `signal_bar_ts`에서 skipped/wait row가 반복될 때 key가 겹치지 않는지
- `observe_reason`, `probe_state`, `blocked_by`, `action_none_reason` suffix가
  현재 uniqueness를 충분히 만드는지
- export/replay/dataset이 그 key를 그대로 따라가는지

#### 완료 기준

- 최근 hot rows 기준 `decision_row_key` 중복 케이스가 재현되지 않는다.
- key 구성 규칙을 문서와 코드로 함께 설명할 수 있다.


### R2-2. Join Coverage Audit

#### 목표

`runtime_snapshot_key`, `trade_link_key`, `replay_row_key`가
필요한 경로에서 누락 없이 join되는지 확인한다.

#### 점검 포인트

- runtime row -> entry decision row
- entry decision row -> export parquet
- entry decision row + detail sidecar -> replay intermediate
- replay intermediate -> semantic dataset

#### 완료 기준

- join 누락 대표 케이스가 재현되지 않는다.
- 어떤 경로가 어떤 key를 primary로 쓰는지 표로 설명 가능하다.


### R2-3. Hot / Detail Propagation Contract

#### 목표

최신 hot/detail 구조가 export/replay intermediate에서 같은 의미로 유지되게 만든다.

#### 점검 포인트

- hot에 있는 compact semantic trace가 export에서 그대로 전달되는지
- detail sidecar에 있는 raw/detail trace가 replay intermediate에서 필요한 만큼 복원되는지
- 최신 `semantic_shadow_*`, `semantic_live_*`, `entry_probe_plan_v1`,
  `probe_candidate_v1`, `entry_decision_context_v1`, `entry_decision_result_v1`
  같은 필드가 export/replay에 빠지지 않는지

#### 완료 기준

- 최신 hot/detail 구조가 export/replay에서 누락 없이 이어진다.
- detail sidecar를 줄이더라도 join 안정성이 깨지지 않는다는 근거가 있다.


### R2-4. Semantic Dataset Builder Compatibility

#### 목표

semantic dataset builder가 최신 runtime/export/replay row 구조를
안정적으로 읽게 만든다.

#### 점검 포인트

- latest parquet / replay intermediate에서 필요한 key와 trace를 정상 인식하는지
- 구버전/신버전 row가 섞여 있어도 builder가 안전하게 처리하는지
- dataset row 수가 join 누락 때문에 줄어들지 않는지

#### 완료 기준

- semantic dataset builder가 최신 row 구조를 기준으로 안정적으로 동작한다.
- replay/export 구조 변화가 dataset build 실패나 silent drop으로 이어지지 않는다.


## 9. 우선순위

R2의 우선순위는 아래처럼 둔다.

1. `decision_row_key` uniqueness
2. join coverage
3. hot/detail propagation
4. dataset builder compatibility

이 순서를 지키는 이유는,
join key가 흔들리면 export/replay/dataset을 아무리 손봐도
증상이 재발하기 쉽기 때문이다.


## 10. 금지사항

R2에서는 아래를 하지 않는다.

- key 충돌 문제를 임시 랜덤 suffix로만 덮기
- detail sidecar를 먼저 줄이고 나중에 join을 맞추기
- export/replay 쪽 해석을 runtime과 다르게 두기
- semantic builder에서 missing row를 조용히 drop하고 넘어가기


## 11. 관측 산출물

R2에서 권장하는 산출물은 아래와 같다.

- `decision_row_key` uniqueness audit memo
- key join coverage table
- hot/detail -> export/replay field propagation table
- semantic dataset builder compatibility memo
- export `key_integrity_report`
- replay `key_integrity_manifest`
- semantic dataset `join_health_report`

필요하면 실제 row 샘플은 아래 파일 기준으로 채운다.

- `data/trades/entry_decisions.csv`
- `data/trades/entry_decisions.detail.jsonl`
- `data/datasets/ml_exports/replay/*.parquet`
- `data/datasets/replay_intermediate/*.jsonl`


## 11-1. 현재 구현 상태 (2026-03-26, R2 1차)

현재 R2 1차 구현으로 아래가 이미 반영돼 있다.

- export:
  - `entry_decisions_ml_key_integrity_v1`
  - `key_integrity_report_path`를 summary / manifest에 기록
- replay:
  - `replay_dataset_key_integrity_manifest_v1`
  - `key_integrity_manifest_path`를 summary / manifest에 기록
  - detail sidecar merge에 `decision_row_key` fallback 추가
- semantic dataset:
  - `semantic_v1_dataset_join_health_v1`
  - `join_health_report_path`를 summary / manifest에 기록

현재 구현 스냅샷과 join chain은 아래 문서에 정리한다.

- [refinement_r2_key_contract_snapshot_and_join_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_key_contract_snapshot_and_join_casebook_ko.md)


## 12. 완료 기준

R2는 아래 조건을 만족하면 닫을 수 있다.

- replay / export join 누락 케이스가 재현되지 않는다.
- key 기준 흐름을 문서와 코드로 함께 설명할 수 있다.
- semantic dataset builder가 최신 row 구조를 안정적으로 읽는다.
- hot/detail 구조 변화가 replay/export/dataset에서 silent mismatch를 만들지 않는다.


## 13. 다음 단계와의 연결

R2가 닫히면 다음 단계는 `R3. Semantic ML Step 3~7 refinement`다.

즉 R2의 역할은
semantic target을 새로 정의하는 것이 아니라,
그 target refinement가 믿을 수 있는 row/join 기반 위에서 이뤄지게 만드는 것이다.
