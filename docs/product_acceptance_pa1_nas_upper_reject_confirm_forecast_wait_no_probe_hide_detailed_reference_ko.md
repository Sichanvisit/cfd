# Product Acceptance PA1 NAS Upper-Reject Confirm Forecast Wait No-Probe Hide Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`NAS100 + upper_reject_confirm + forecast_guard + observe_state_wait + no_probe`
family를 왜 `accepted hidden suppression`으로 처리해야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_memo_ko.md)

## 2. 문제 family

target family는 아래 조건을 동시에 가진 NAS sell wait row다.

- `symbol = NAS100`
- `observe_reason = upper_reject_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- `check_side = SELL`

representative surface:

- `check_stage = PROBE`
- `display_ready = True`
- `display_score = 0.82`
- `display_repeat_count = 2`
- `importance source = 없음`

즉 guard 아래에서 아직 구조 확인만 하는 no-probe wait row인데,
chart에는 이미 방향성 SELL surface처럼 보이고 있었다.

## 3. 왜 wait relief가 아니라 hide인가

이 family는 earlier accepted wait-check relief 축과 성격이 다르다.

- `scene_probe`가 없다
- `probe_not_promoted` repeated checks 계약도 아니다
- importance source가 없다
- 실제 의미는 `아직 보여줄 만큼 성숙하지 않은 forecast wait`에 가깝다

그래서 이 축은
`WAIT으로 살린다`보다 `directional leakage를 감춘다`가 맞다.

## 4. 목표 contract

목표 contract는 아래와 같다.

- `display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_upper_reject_wait_hide_without_probe`
- painter는 이 row를 top-level directional fallback으로 다시 그리지 않는다
- PA0 baseline freeze는 이 row를 accepted hidden suppression으로 본다

## 5. 구현 방향

1. `nas_upper_reject_wait_hide_without_probe` soft-cap policy 추가
2. common modifier path에서 no-probe forecast-wait row를 hidden suppression으로 내리기
3. painter hidden fallback block list에 reason 추가
4. PA0 freeze script hidden suppression allow-list에 reason 추가
5. unit test, restart, representative replay, refreeze delta로 닫기

## 6. 이번 축에서 하지 않는 것

- `upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe` 처리
- `probe_promotion_gate` family 처리
- NAS outer-band hidden backlog 처리
- entry / hold / exit acceptance 처리

## 7. 완료 기준

1. current-build replay에서 target row가 hidden suppression으로 내려간다
2. painter가 directional fallback을 다시 그리지 않는다
3. PA0 latest queue에서 target confirm no-probe family가 사라진다
4. 다음 NAS upper-reject backlog가 무엇인지 더 선명해진다

## 8. 다음 reopen point

이 축 다음 reopen point는 아래 두 family다.

- `NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`
- `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
