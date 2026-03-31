# R4 Bounded Live / Allowlist Expansion Implementation Checklist

## 1. 목적

이 문서는 [refinement_r4_bounded_live_allowlist_expansion_operating_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_bounded_live_allowlist_expansion_operating_spec_ko.md)의 실행 checklist다.

현재 목적은 실제 mode 변경이 아니라,
운영 기준을 바꾸기 전 필요한 판단 단계를 순서대로 고정하는 것이다.

## 2. 입력 기준

- [refinement_r4_final_acceptance_summary_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_final_acceptance_summary_memo_ko.md)
- [refinement_r4_allowlist_expansion_candidate_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_candidate_memo_ko.md)
- [refinement_r4_semantic_canary_acceptance_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_semantic_canary_acceptance_reconfirm_memo_ko.md)
- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json)

## 3. Step 1. Current Action Freeze

목표:

- 현재 추천 action을 `stay_threshold_only`로 다시 고정한다.

완료 기준:

- 왜 지금 바로 partial_live가 아닌지 한 문장으로 설명 가능하다.

## 4. Step 2. NAS100 Candidate Gate

목표:

- NAS100이 첫 확장 후보인지 운영 기준으로 확정한다.

확인 항목:

- runtime latest direction
- probe scene consistency
- allowlist outside fallback 유무
- rollback / kill switch trigger 유무

완료 기준:

- NAS100을 열 수 있는 조건과 아직 못 여는 조건이 동시에 정리된다.

## 5. Step 3. XAUUSD Candidate Gate

목표:

- XAUUSD를 두 번째 후보로 두는 이유를 고정한다.

확인 항목:

- direction consistency
- buy/sell probe dominance
- `probe_against_default_side` 반복 여부

완료 기준:

- XAU가 왜 NAS 뒤인지 설명 가능하다.

## 6. Step 4. No-Go Gate

목표:

- allowlist 확장을 멈추는 조건을 정리한다.

확인 항목:

- chart rollout worsening
- canary deterioration
- preview/shadow health regression
- rollback / kill switch trigger

완료 기준:

- 확장 금지 조건이 모호하지 않다.

## 7. Step 5. Partial Live Preconditions

목표:

- partial_live로 넘어가기 전에 필요한 조건을 따로 묶는다.

완료 기준:

- allowlist expansion과 partial_live가 다른 단계라는 점이 분명해진다.

## 8. Step 6. Next Action Memo

목표:

- 다음 실제 조작 후보를 하나로 좁힌다.

후보:

- `do nothing`
- `prepare NAS100 expansion only`
- `prepare XAUUSD expansion only`
- `hold all expansion`

완료 기준:

- 다음 턴에서 실제 설정 변경을 하더라도 기준이 흔들리지 않는다.

## 9. Step 7. 문서 동기화

업데이트 문서:

- [refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_acceptance_promotion_ready_implementation_checklist_ko.md)
- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)

## 10. Done Definition

- R4가 `acceptance 정리`에서 `다음 운영 행동 기준`으로 이어진다
- allowlist 확장과 partial_live의 경계가 명확하다
- 다음 실제 설정 변경을 해도 rollback 기준과 충돌하지 않는다

## 11. Current Progress

- `NAS100 allowlist expansion within threshold_only` 반영 완료
- current allowlist는 `BTCUSD,NAS100`
- 다음 active candidate는 `XAUUSD`

재확인 메모:

- [refinement_r4_allowlist_expansion_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_reconfirm_memo_ko.md)
- [refinement_r4_nas_post_expansion_xau_candidate_followup_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_nas_post_expansion_xau_candidate_followup_memo_ko.md)
- [refinement_r4_post_30m_runtime_ml_connection_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_post_30m_runtime_ml_connection_memo_ko.md)
