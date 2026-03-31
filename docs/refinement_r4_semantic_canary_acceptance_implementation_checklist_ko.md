# R4 Semantic Canary Acceptance Implementation Checklist

## 1. 목적

이 문서는 [refinement_r4_semantic_canary_acceptance_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_semantic_canary_acceptance_spec_ko.md)의 실행 checklist다.

이번 단계의 목적은 canary를 다시 만드는 것이 아니라,
R4 운영 판단 안에서 canary를 어떻게 읽을지
`숫자 -> 해석 -> action`
순서로 고정하는 것이다.

## 2. 입력 기준

- canary latest json: [semantic_canary_rollout_BTCUSD_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_canary\semantic_canary_rollout_BTCUSD_latest.json)
- canary latest markdown: [semantic_canary_rollout_BTCUSD_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_canary\semantic_canary_rollout_BTCUSD_latest.md)
- preview audit latest: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- runtime status: [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- runtime reason casebook: [refinement_r4_runtime_reason_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_runtime_reason_casebook_ko.md)
- rollback contract: [refinement_r4_rollback_kill_switch_contract_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_rollback_kill_switch_contract_ko.md)

## 3. Step 1. Canary Baseline Snapshot

목표:

- 최신 canary 수치를 R4 운영 판단 기준으로 다시 고정한다.

확인 항목:

- report freshness
- `recent_rows`
- `threshold_applied_rows`
- `fallback_rows`
- `fallback_ratio`
- `threshold_applied_ratio`
- `recommendation.value`

완료 기준:

- 지금 canary가 어떤 숫자를 말하는지 한 장에서 설명 가능하다.

## 4. Step 2. Fallback Reason Taxonomy

목표:

- fallback reason을 운영 의미로 분류한다.

분류 대상:

- `baseline_no_action`
- `symbol_not_in_allowlist`
- `semantic_unavailable`
- `compatibility_mode_blocked`

완료 기준:

- 각 reason이 `정상 관측`, `확장 후보`, `hold`, `stop 후보` 중 어디에 속하는지 정리된다.

## 5. Step 3. Preview / Shadow Cross-Check

목표:

- canary 해석이 preview audit / shadow compare와 충돌하지 않는지 확인한다.

확인 항목:

- `promotion_gate.status`
- `warning_issues`
- `shadow_compare.status`
- canary fallback reason과 preview/shadow health의 관계

완료 기준:

- canary와 preview/shadow가 서로 다른 owner라는 점이 분명해진다.

## 6. Step 4. Pass / Hold / Stop Decision

목표:

- 현재 canary를 R4 운영 기준으로 한 단어로 분류한다.

후보:

- `pass`
- `hold`
- `stop`

완료 기준:

- 현재 시점의 canary 상태가 문장 하나로 좁혀진다.

## 7. Step 5. Action Mapping

목표:

- canary 상태를 실제 운영 action에 연결한다.

후보:

- `stay_threshold_only`
- `expand_allowlist candidate only`
- `prepare_partial_live`
- `rollback / investigate runtime source`

완료 기준:

- canary 해석이 promotion action matrix와 자연스럽게 이어진다.

## 8. Step 6. 문서 동기화

업데이트 문서:

- [refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md)
- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- 필요 시 R4 관련 memo 문서

## 9. Done Definition

- semantic canary를 R4 운영 언어로 `pass / hold / stop` 해석할 수 있다
- 최신 canary 수치가 preview/shadow와 함께 모순 없이 설명된다
- 현재 추천 action이 `stay_threshold_only`인지, 그보다 더 나아갈 수 있는지 분명해진다
