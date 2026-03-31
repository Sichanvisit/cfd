# R4 Acceptance / Promotion-Ready Implementation Checklist

## 1. 목적

이 문서는 [refinement_r4_acceptance_promotion_ready_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_acceptance_promotion_ready_spec_ko.md)의 실행 checklist다.

이번 단계의 목적은
지금 healthy한 preview/shadow 결과를
운영 승격 기준과 rollback 기준으로 바꾸는 것이다.

## 2. 입력 기준

- preview audit latest: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- runtime status: [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- slice sparsity reconfirm memo: [refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_reconfirm_memo_ko.md)

owner:

- [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)
- [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)
- [promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\scripts\promote_semantic_preview_to_shadow.py)
- [trading_application.py](c:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

## 3. Step 1. Promotion Baseline Snapshot

목표:

- 현재 `preview pass`와 `runtime threshold_only` 상태를 같은 문서에서 동시에 고정한다.

확인 항목:

- preview audit gate 상태
- shadow compare 상태
- current semantic live mode
- symbol allowlist
- recent fallback reason 분포
- kill switch 상태

완료 기준:

- 현재 위치가 `문서상 pass / 운영상 보수 모드`라는 점이 숫자와 함께 정리된다.

## 4. Step 2. Runtime Reason Casebook

목표:

- runtime recent에 나오는 reason을 운영 의사결정 언어로 번역한다.

핵심 reason:

- `baseline_no_action`
- `symbol_not_in_allowlist`
- `trace_quality_state = fallback_heavy`

완료 기준:

- 각 reason이 `정상`, `관측`, `확장 blocker`, `즉시 rollback 사유` 중 어디에 속하는지 분류된다.

현재 산출물:

- [refinement_r4_runtime_reason_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_runtime_reason_casebook_ko.md)

## 5. Step 3. Promotion Action Matrix

목표:

- 아래 4개 행동을 명시적으로 나눈다.

행동:

1. `stay_threshold_only`
2. `expand_allowlist`
3. `enable_partial_live`
4. `rollback / kill_switch`

완료 기준:

- action별 진입 조건과 금지 조건이 표로 정리된다.

현재 산출물:

- [refinement_r4_promotion_action_matrix_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_promotion_action_matrix_ko.md)

## 6. Step 4. Rollback / Kill Switch Contract

목표:

- bounded live나 allowlist 확장을 하더라도 되돌리는 기준이 모호하지 않게 한다.

확인 항목:

- kill switch owner
- rollback trigger
- preview/audit/runtime 중 어떤 신호가 stop 사유인지

완료 기준:

- rollback이 문서상으로만 있는 게 아니라 실제 runtime owner와 연결된다.

현재 산출물:

- [refinement_r4_rollback_kill_switch_contract_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_rollback_kill_switch_contract_ko.md)

## 7. Step 5. Code / Config Surface Audit

목표:

- 문서 기준이 실제 코드 surface와 맞는지 확인한다.

확인 대상:

- `promotion_guard.py`
- `runtime_adapter.py`
- `promote_semantic_preview_to_shadow.py`
- `trading_application.py`

완료 기준:

- 문서에 적은 mode / allowlist / gate / rollback이 코드 surface에서 어디서 읽히는지 설명 가능하다.

## 8. Step 6. Decision Memo

목표:

- 현재 시점의 추천 action을 하나로 고른다.

후보:

- `threshold_only 유지`
- `allowlist 확장`
- `partial_live 준비만 하고 보류`

완료 기준:

- 다음 실제 변경 전에 운영상 추천 action이 문장으로 잠긴다.

## 9. Step 7. 문서 동기화

업데이트 문서:

- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- R4 관련 memo 문서

## 10. Done Definition

- 현재 promotion 상태를 `pass` 하나로 뭉개지 않고 운영 의사결정으로 나눠 설명할 수 있다.
- runtime recent reason이 확장/보류/rollback 판단에 어떻게 쓰이는지 정리된다.
- 다음 턴에서 실제 allowlist나 mode를 바꾸더라도 기준이 흔들리지 않는다.

## 11. Current R4 Artifact Set

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
