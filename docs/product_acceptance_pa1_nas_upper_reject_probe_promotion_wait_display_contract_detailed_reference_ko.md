# Product Acceptance PA1 NAS Upper-Reject Probe Promotion Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
family를 왜 `WAIT + wait_check_repeat` 계약으로 올려야 하는지 고정하는 상세 reference다.

관련 문서:

- [product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)

## 2. 문제 family

target family는 아래 조건을 동시에 가진 NAS sell probe row다.

- `symbol = NAS100`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = probe_promotion_gate`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`
- `check_side = SELL`

representative surface:

- `check_stage = PROBE`
- `display_ready = True`
- `display_score = 0.82`
- `display_repeat_count = 2`
- `importance source = 없음`

## 3. 왜 wait contract인가

이 family는 no-probe guard wait가 아니라
이미 probe scene이 붙은 repeated checks family다.

- `scene_probe`가 있다
- `probe_promotion_gate`는 구조 폐기가 아니라 승격 보류다
- `probe_not_promoted`는 계속 확인하라는 뜻에 가깝다
- stage도 이미 `PROBE`다

즉 chart에서 이 row를 숨기기보다
`아직 entry는 아니지만 계속 보는 neutral wait checks`
로 surface 하는 게 더 자연스럽다.

## 4. 목표 contract

목표 contract는 아래와 같다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_reject_probe_promotion_wait_as_wait_checks`
- `blocked_display_reason = probe_promotion_gate`
- painter는 directional SELL 대신 neutral wait checks로 렌더한다
- PA0 freeze는 accepted wait-check relief로 본다

## 5. 구현 방향

1. `nas_upper_reject_probe_promotion_wait_as_wait_checks` policy 추가
2. common modifier path에서 target family를 wait contract로 surface
3. `blocked_display_reason = probe_promotion_gate` carry 유지
4. PA0 freeze wait relief allow-list에 reason 추가
5. unit test, runtime restart, representative replay, refreeze로 추적

## 6. 이번 축에서 하지 않는 것

- `NAS upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe` 처리
- NAS outer-band hidden backlog 처리
- entry / hold / exit acceptance 처리

## 7. 완료 기준

1. current-build replay에서 target row가 `WAIT + wait_check_repeat`로 보인다
2. painter가 neutral wait checks로 렌더한다
3. exact fresh row가 다시 나오면 PA0 queue overlap이 `0`이 된다
4. 남은 NAS must-hide 메인축이 더 분리된다
