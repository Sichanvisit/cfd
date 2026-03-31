# Product Acceptance PA1 NAS Upper-Reject Probe Forecast Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`
family를 왜 `WAIT + wait_check_repeat` 계약으로 올려야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_memo_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)

## 2. 문제 family

target family는 아래 조건을 동시에 가진 NAS sell probe row다.

- `symbol = NAS100`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = forecast_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`
- `check_side = SELL`

representative surface:

- `check_stage = PROBE`
- `display_ready = True`
- `display_score = 0.86`
- `display_repeat_count = 2`
- `importance source = 없음`

## 3. 왜 hide가 아니라 wait contract인가

이 family는 confirm no-probe hide 축과 다르게
이미 `scene_probe`가 붙어 있다.

- `probe_scene`가 있다
- stage가 이미 `PROBE`다
- `probe_not_promoted`는 진입 보류이지 구조 무효가 아니다
- forecast guard 아래에서 반복 확인 중인 sell wait로 읽는 게 자연스럽다

즉 이 row는
`숨길 leakage`보다는
`아직 진입은 아니지만 계속 보게 할 neutral wait-check scene`에 가깝다.

## 4. 목표 contract

목표 contract는 아래와 같다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_reject_probe_forecast_wait_as_wait_checks`
- `blocked_display_reason = forecast_guard`
- painter는 directional SELL이 아니라 neutral wait checks로 그린다
- PA0 baseline freeze는 accepted wait-check relief로 본다

## 5. 구현 방향

1. `nas_upper_reject_probe_forecast_wait_as_wait_checks` policy 추가
2. common modifier path에서 probe forecast family를 wait contract로 surface
3. `blocked_display_reason`를 비우지 않고 carry
4. PA0 freeze script wait relief allow-list에 reason 추가
5. unit test, restart, representative replay, refreeze로 추적

## 6. 이번 축에서 하지 않는 것

- `probe_promotion_gate` family 처리
- NAS outer-band hidden backlog 처리
- entry / hold / exit acceptance 처리

## 7. 완료 기준

1. current-build replay에서 target row가 `WAIT + wait_check_repeat`로 보인다
2. painter가 neutral wait checks로 렌더한다
3. fresh exact row가 다시 나오면 PA0 queue overlap이 `0`이 된다
4. 남아 있는 upper-reject must-hide가 정확히 어디인지 분리된다
