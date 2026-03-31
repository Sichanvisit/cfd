# Refinement Track Execution Plan

## 1. 목적

이 문서는 현재 정리된 3분류 중:

- `1번`: 이미 구현됨
- `2번`: 구현됐지만 refinement 필요
- `3번`: 아직 진짜 미구현

에서 `2번 refinement 트랙`만 별도로 실행 가능한 계획으로 정리한 문서다.

다만 `3번`이 뒤로 밀리면서 잊히지 않도록 마지막에 backlog로 함께 남긴다.

이 문서의 기본 전제는 다음과 같다.

- 지금까지의 `0~6` 작업은 미세조정을 안전하게 하기 위한 안정화 작업이었다.
- 앞으로의 주작업은 `foundation 재설계`가 아니라 `실행 temperament refinement`다.
- `3번` 확장은 `2번 refinement`가 충분히 안정화된 뒤에만 들어간다.


## 2. 기준 문서

이 계획은 아래 문서군을 현재 기준 source set으로 삼는다.

R에서 P로 이어진 전체 전이 과정은 아래 문서를 함께 본다.

- [r_to_p_transition_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\r_to_p_transition_memo_ko.md)

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_spec_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_implementation_checklist_ko.md`
- `docs/full_system_architecture_explanation_ko.md`
- `docs/system_handoff_overview_ko.md`
- `docs/trust_wait_hold_owner_ko.md`
- `docs/position_response_state_stabilization_roadmap_ko.md`
- `docs/xau_btc_execution_tuning_short_roadmap_ko.md`
- `docs/execution_storage_followup_roadmap_ko.md`
- `docs/semantic_ml_structure_change_plan_ko.md`
- `docs/semantic_ml_v1_execution_plan_ko.md`
- `docs/semantic_ml_v1_promotion_gates_ko.md`
- `docs/storage_semantic_flow_handoff_ko.md`
- `docs/ml_symbol_regime_calibration_proposal_ko.md`
- `docs/refinement_r0_integrity_minimum_spec_ko.md`
- `docs/refinement_r0_integrity_minimum_implementation_checklist_ko.md`
- `docs/refinement_r0_owner_matrix_casebook_ko.md`
- `docs/refinement_r0_non_action_taxonomy_and_key_linkage_ko.md`
- `docs/refinement_r0_detailed_reference_ko.md`
- `docs/refinement_r0_execution_roadmap_ko.md`
- `docs/refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md`
- `docs/refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md`
- `docs/refinement_r0_b6_close_out_handoff_ko.md`
- `docs/decision_log_coverage_gap_detailed_reference_ko.md`
- `docs/decision_log_coverage_gap_execution_roadmap_ko.md`
- `docs/refinement_r1_stagee_micro_calibration_spec_ko.md`
- `docs/refinement_r1_stagee_micro_calibration_implementation_checklist_ko.md`


## 3. 지금 해석 기준

### 3-1. 이미 구현된 축

- chart flow common baseline
- symbol override isolation
- strength `1..10`
- distribution / rollout / sampled baseline compare
- semantic ML v1 scaffold
- semantic live rollout scaffold

### 3-2. refinement가 필요한 축

- `Stage E micro calibration`
- execution temperament
- probe promotion explanation quality
- storage / export / replay join consistency
- semantic target / split / preview 품질
- canary / rollout observability

### 3-3. 아직 진짜 미구현인 축

- `probe lot / confirm add`의 완성형 주문 구조
- `edge-to-edge hold / exit` 완성형 실행 구조
- semantic ML bounded live 확장
- API 운영 안정성 마무리


## 4. Freeze 원칙

refinement 동안 아래 레이어는 재설계하지 않는다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

즉 refinement는 아래 owner를 중심으로 진행한다.

- `ObserveConfirm`
- `EntryService`
- `WaitEngine`
- `ExitProfileRouter`
- `ExitManagePositions`
- `storage/export/replay`
- `semantic target/split/evaluate`


## 5. 현재 검증 스냅샷

2026-03-25 KST 기준 현재 코드 검증 상태는 아래와 같다.

### chart / rollout 계층

- `pytest tests/unit/test_chart_painter.py tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_flow_rollout_status.py tests/unit/test_chart_flow_baseline_compare.py tests/unit/test_observe_confirm_router_v2.py`
- 결과: `104 passed`

### semantic ML 계층

- `pytest tests/unit/test_semantic_v1_contracts.py tests/unit/test_semantic_v1_dataset_builder.py tests/unit/test_semantic_v1_dataset_splits.py tests/unit/test_semantic_v1_promotion_guard.py tests/unit/test_semantic_v1_runtime_adapter.py tests/unit/test_semantic_v1_shadow_compare.py tests/unit/test_check_semantic_canary_rollout.py tests/unit/test_promote_semantic_preview_to_shadow.py`
- 결과: `26 passed`

기존 실패였던 `semantic canary report` recent window 테스트는
기준 시각 주입이 가능하게 보강하면서 해결했다.

즉 현재 refinement 트랙은 다음 해석으로 들어간다.

- chart / rollout 구조는 이미 실사용 가능한 수준
- semantic ML 구조도 대부분 연결됨
- 남은 일은 설계 부재보다 refinement와 acceptance 정리


## 6. Refinement 트랙 전체 구조

```text
R0. 정합성 최소셋
-> R1. Stage E 미세조정
-> R2. 저장 / export / replay 정합성
-> R3. Semantic ML Step 3~7 refinement
-> R4. Acceptance / promotion-ready 정리
```

우선순위는 아래처럼 본다.

- `P0`: R0, R1
- `P1`: R2, R3
- `P2`: R4


## 7. R0. 정합성 최소셋

R0는 범위가 넓기 때문에 전용 문서 2장으로 분리한다.

- spec: [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)
- implementation checklist: [refinement_r0_integrity_minimum_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_implementation_checklist_ko.md)
- detailed reference: [refinement_r0_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_detailed_reference_ko.md)
- execution roadmap: [refinement_r0_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_execution_roadmap_ko.md)
- R0-B actual entry forensic detailed reference: [refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md)
- R0-B actual entry forensic execution roadmap: [refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md)

이 섹션은 요약만 남기고, 세부 범위와 실행 순서는 전용 문서를 기준으로 본다.

### 목표

현재 row와 trace를 읽었을 때:

- 왜 observe인지
- 왜 blocked인지
- 왜 probe가 승격되지 않았는지
- 왜 semantic runtime이 inactive인지

를 즉시 설명할 수 있게 만든다.

### 포함 범위

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_candidate_v1`
- `entry_probe_plan_v1`
- semantic canary / runtime activation reason

### 주 대상 파일

- `backend/services/entry_service.py`
- `backend/services/storage_compaction.py`
- `scripts/check_semantic_canary_rollout.py`

### 해야 할 일

1. `observe_reason / blocked_by / action_none_reason`가 서로 다른 owner를 유지하는지 점검한다.
2. `probe_candidate_v1.active=true`인데 `entry_probe_plan_v1.ready_for_entry=false`인 대표 케이스를 수집한다.
3. `probe_not_promoted`, `confirm_suppressed`, `execution_soft_blocked`, `policy_hard_blocked`가 실제로 분리 기록되는지 점검한다.
4. semantic canary report의 recent window 테스트를 안정화한다.

### 완료 기준

- 대표 non-action reason을 설명 가능한 분류표로 만들 수 있다.
- canary report 테스트가 날짜 변화에 흔들리지 않는다.
- runtime row만 봐도 `semantic inactive` 이유가 바로 해석된다.

### 실행 메모

R0는 실제로 아래 4개 작업축으로 나뉜다.

- `R0-1` owner separation audit
- `R0-2` probe promotion miss casebook
- `R0-3` non-action taxonomy and trace contract
- `R0-4` semantic canary stabilization

현재 시점에서 R0를 다시 쓰는 실전 하위 단계는 `R0-B actual entry forensic`으로 본다.
즉 별도 임시 phase를 두기보다,
이미 완료된 R0 기준선을 최근 adverse entry 사례에 다시 연결하는 방식으로 해석한다.


## 8. R1. Stage E 미세조정

R1도 범위가 넓기 때문에 전용 문서 2장으로 분리한다.

- spec: [refinement_r1_stagee_micro_calibration_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r1_stagee_micro_calibration_spec_ko.md)
- implementation checklist: [refinement_r1_stagee_micro_calibration_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r1_stagee_micro_calibration_implementation_checklist_ko.md)

이 섹션은 요약만 남기고, 세부 범위와 구현 순서는 전용 문서를 기준으로 본다.

### 목표

심볼별 체감 불균형을 줄이고,
`probe -> confirm -> hold -> opposite edge exit` 흐름이 더 자연스럽게 보이게 만든다.

### 주 대상 파일

- `backend/services/wait_engine.py`
- `backend/services/exit_profile_router.py`
- `backend/services/entry_service.py`
- `backend/services/entry_engines.py`
- `backend/trading/chart_symbol_override_policy.py`
- `data/analysis/chart_flow_distribution_latest.json`
- `data/analysis/chart_flow_rollout_status_latest.json`

### 현재 상태

- XAU upper sell probe 2차 조정 반영
- BTC lower hold / duplicate suppression 1차 조정 반영
- NAS clean confirm balance 2차 조정 반영
- BTC middle+lower-edge outer-band context relief 2차 반영
- BTC auto lower reversal buy 실거래 리뷰 기반 recovery policy 우선순위 correction 반영
- latest rollout 기준 `Stage E = advance`, calibration target 없음
- 다음 포인트는 `R2 저장 / export / replay 정합성`으로 넘어가되, BTC/XAU는 새 윈도우 관측만 유지

### 심볼별 핵심 방향

#### XAU

- `upper sell probe`가 너무 늦거나 soft block에 과하게 죽지 않게 조정
- `upper reject -> sell probe -> confirm` 흐름 강화

#### BTC

- lower buy 중복 진입 억제
- lower buy hold patience 강화
- middle noise만으로 너무 빨리 exit되지 않게 조정

#### NAS

- clean confirm / upper sell / neutral wait의 밸런스 확인
- 극단 한쪽 쏠림 완화

### 공통 방향

- `probe`와 `confirm`의 체감 차이를 유지
- directional wait가 neutral wait로 과하게 눌리지 않게 유지
- hold bias가 실제 execution utility에 반영되게 유지

### 완료 기준

- `Stage E` calibration target 수가 감소한다.
- 최근 분포에서 `XAU/BTC/NAS`의 편향이 덜 극단적이다.
- 차트 체감과 runtime reason이 서로 어긋나지 않는다.


## 9. R2. 저장 / export / replay 정합성

### 목표

runtime row, replay intermediate, semantic dataset이 같은 key와 같은 해석 기준으로 묶이게 만든다.

### 주 대상 파일

- `backend/services/storage_compaction.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`
- `ml/semantic_v1/dataset_builder.py`
- `scripts/export_entry_decisions_ml.py`

### 해야 할 일

1. `decision_row_key` uniqueness를 재점검한다.
2. `runtime_snapshot_key`, `trade_link_key`, `replay_row_key`의 join 누락 케이스를 점검한다.
3. 최신 hot/detail 구조가 export / replay intermediate에 그대로 전달되는지 확인한다.
4. detail sidecar는 용량 최적화보다 join 안정성을 먼저 우선한다.

### 완료 기준

- replay / export join 누락 케이스가 재현되지 않는다.
- key 기준 흐름을 문서와 코드로 함께 설명할 수 있다.
- semantic dataset builder가 최신 row 구조를 안정적으로 읽는다.


### R2 전용 문서

- [refinement_r2_storage_export_replay_integrity_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_storage_export_replay_integrity_spec_ko.md)
- [refinement_r2_storage_export_replay_integrity_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_storage_export_replay_integrity_implementation_checklist_ko.md)
- [refinement_r2_key_contract_snapshot_and_join_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_key_contract_snapshot_and_join_casebook_ko.md)
- [refinement_r2_decision_row_key_uniqueness_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_decision_row_key_uniqueness_audit_ko.md)
- [refinement_r2_join_coverage_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_join_coverage_casebook_ko.md)
- [refinement_r2_hot_detail_propagation_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_hot_detail_propagation_audit_ko.md)
- [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)

### 현재 상태

- R2 1차 코드 구현 반영
- export key integrity report 추가
- replay key integrity manifest 추가
- replay detail sidecar의 `decision_row_key` fallback 반영
- semantic dataset join health report 추가
- live sample 기준 `decision_row_key` historical duplicate 3개 그룹 확인
- duplicate root cause는 entered row의 `ticket=0` base key 충돌이었고, future write-path fix 반영
- join coverage casebook 작성 완료
- hot/detail propagation audit 작성 완료
- semantic dataset compatibility memo 작성 완료
- R2 관련 테스트 묶음 재검증 `31 passed`
- 다음 포인트는 `R3. Semantic ML Step 3~7 refinement`

## 10. R3. Semantic ML Step 3~7 refinement

### 목표

semantic ML v1을 `구조는 있음` 상태에서 `품질을 믿고 평가할 수 있음` 상태로 올린다.

### 주 대상 파일

- `ml/semantic_v1/dataset_builder.py`
- `ml/semantic_v1/dataset_splits.py`
- `ml/semantic_v1/evaluate.py`
- `ml/semantic_v1/shadow_compare.py`

### 세부 단계

#### Step 3. timing target refinement

- `timing_now_vs_wait` 정답 정의 재검토
- fallback-heavy row와 clean row 차이 반영

#### Step 4. split health refinement

- time split
- symbol holdout
- regime holdout
- validation / test minority row health

#### Step 5. entry_quality target refinement

- "좋은 진입" 정의를 현재 구조와 맞게 재정리

#### Step 6. legacy feature tier refinement

- all-missing legacy feature 정리
- source tier별 허용 범위 정리

#### Step 7. preview / audit refinement

- preview train / evaluate
- split health
- join health
- leakage / calibration 재확인

### 완료 기준

- timing / entry_quality / exit_management target 정의가 문서와 코드로 고정된다.
- split health가 promotion block 사유 없이 설명 가능하다.
- shadow compare 결과를 기준으로 다음 gate 판단이 가능하다.

### R3 전용 문서

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md)
- [refinement_r3_step3_timing_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_refinement_spec_ko.md)
- [refinement_r3_step3_timing_target_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_refinement_implementation_checklist_ko.md)
- [refinement_r3_step3_timing_target_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_casebook_ko.md)
- [refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md)
- [refinement_r3_step4_split_health_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_refinement_spec_ko.md)
- [refinement_r3_step4_split_health_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_refinement_implementation_checklist_ko.md)
- [refinement_r3_step4_split_health_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_reconfirm_memo_ko.md)
- [refinement_r3_step5_entry_quality_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step5_entry_quality_target_refinement_spec_ko.md)
- [refinement_r3_step5_entry_quality_target_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step5_entry_quality_target_refinement_implementation_checklist_ko.md)
- [refinement_r3_post_step7_split_warning_followup_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_split_warning_followup_memo_ko.md)
- [refinement_r3_post_step7_slice_sparsity_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_refinement_spec_ko.md)
- [refinement_r3_post_step7_slice_sparsity_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_refinement_implementation_checklist_ko.md)

### 현재 상태

- R2 storage / export / replay 정합성 완료
- semantic ML 테스트 baseline `27 passed`
- R3는 전체 spec / checklist를 먼저 고정
- Step 3 timing target 전용 spec / checklist 작성 완료
- Step 3 timing target 1차 rule refinement / casebook 반영 완료
- Step 3 preview / evaluate 재확인 완료
- legacy preview baseline 기준 timing AUC `0.610649 -> 0.633218` (`+0.02257`)
- 다음 active step은 `Step 4 split health refinement`

### Post-Step7 follow-up 상태

- shadow compare / runtime source cleanup은 사실상 정리 완료
- holdout bucket 구조 문제는 follow-up에서 정리 완료
- slice sparsity follow-up까지 재감사 완료
- 최신 preview audit 기준 `promotion_gate.status = pass`, `warning_issues = []`
- follow-up 정리 메모:
  - [refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md)
- 다음 active step:
  - [refinement_r4_acceptance_promotion_ready_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_acceptance_promotion_ready_spec_ko.md)
  - [refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md)


## 11. R4. Acceptance / promotion-ready 정리

### 목표

refinement 결과를 `좋아진 것 같다`가 아니라
`다음 단계로 승격해도 된다 / 아직 안 된다`로 말할 수 있게 만든다.

### 주 대상 파일

- `data/analysis/chart_flow_distribution_latest.json`
- `data/analysis/chart_flow_rollout_status_latest.json`
- `ml/semantic_v1/shadow_compare.py`
- `scripts/check_semantic_canary_rollout.py`

### 해야 할 일

1. `Stage E` acceptance 조건 정리
2. semantic canary acceptance 조건 정리
3. shadow compare acceptance 조건 정리
4. bounded live로 넘어가기 전 stop / hold / advance 규칙 재확인

### 완료 기준

- refinement 종료 시점을 숫자로 설명할 수 있다.
- 다음 단계인 `promotion gate 확장`으로 넘어갈 근거가 생긴다.

### R4 전용 문서

- [refinement_r4_acceptance_promotion_ready_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_acceptance_promotion_ready_spec_ko.md)
- [refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md)
- [refinement_r4_promotion_ready_baseline_snapshot_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_promotion_ready_baseline_snapshot_ko.md)
- [refinement_r4_runtime_reason_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_runtime_reason_casebook_ko.md)
- [refinement_r4_promotion_action_matrix_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_promotion_action_matrix_ko.md)
- [refinement_r4_rollback_kill_switch_contract_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_rollback_kill_switch_contract_ko.md)
- [refinement_r4_allowlist_expansion_candidate_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_candidate_memo_ko.md)
- [refinement_r4_semantic_canary_acceptance_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_semantic_canary_acceptance_spec_ko.md)
- [refinement_r4_semantic_canary_acceptance_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_semantic_canary_acceptance_implementation_checklist_ko.md)
- [refinement_r4_semantic_canary_acceptance_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_semantic_canary_acceptance_reconfirm_memo_ko.md)
- [refinement_r4_final_acceptance_summary_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_final_acceptance_summary_memo_ko.md)
- [refinement_r4_bounded_live_allowlist_expansion_operating_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_bounded_live_allowlist_expansion_operating_spec_ko.md)
- [refinement_r4_bounded_live_allowlist_expansion_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_bounded_live_allowlist_expansion_implementation_checklist_ko.md)
- [refinement_r4_allowlist_expansion_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_reconfirm_memo_ko.md)
- [refinement_r4_nas_post_expansion_xau_candidate_followup_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_nas_post_expansion_xau_candidate_followup_memo_ko.md)
- [refinement_r4_post_30m_runtime_ml_connection_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_post_30m_runtime_ml_connection_memo_ko.md)


## 12. 이번 refinement에서 하지 않을 것

아래는 `2번 refinement` 문서 범위 밖이다.

- `Position / Response / State / Evidence / Belief / Barrier` 재설계
- semantic foundation의 의미 변경
- event family 의미 변경
- ML이 `side`, `setup_id`, `management_profile_id`, `invalidation_id` owner를 가져가게 만드는 일
- bounded live를 바로 확대 적용하는 일


## 13. 3번 backlog

아래는 `2번 refinement`가 충분히 안정화된 뒤에 착수할 `3번`이다.

### B1. Probe lot / confirm add 완성형 분리

- `probe`는 작은 lot
- `confirm`은 add 또는 normal size
- same-thesis 추적 주문 구조 완성

### B2. Edge-to-edge hold / exit 완성형

- symbol-aware hold patience
- premature exit risk
- opposite edge completion 확률을 실제 execution policy에 완성형으로 반영

### B3. Semantic ML bounded live 확장

- `threshold_only` -> `partial_live` -> expansion
- allowlist / stage gate / rollback 기준 강화

### B4. API 운영 안정성 마무리

- `/trades/summary`
- `/trades/closed_recent`
- 운영 헬스와 semantic/rollout 계측의 병렬 안정성 확보


## 14. 최종 한 줄 요약

이 문서의 핵심은 아래 한 줄이다.

```text
foundation은 건드리지 않고,
trace / execution temperament / storage join / semantic target 품질을 먼저 다듬은 뒤,
그 다음에만 probe lot 분리, edge-to-edge 실행 완성, bounded live 확장으로 넘어간다.
```
