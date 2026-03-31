# Product Acceptance PA1 NAS Upper-Break-Fail Forecast Wait No-Probe Hide Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`
family를 왜 `accepted hidden suppression`으로 처리해야 하는지 고정하는 상세 reference다.

관련 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_memo_ko.md)

## 2. 문제 family

target family는 아래 조건을 동시에 가진 NAS sell wait row다.

- `symbol = NAS100`
- `observe_reason = upper_break_fail_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- `check_side = SELL`

representative surface:

- `check_stage = PROBE` on historical backlog
- `display_ready = True`
- `display_score = 0.82`
- `display_repeat_count = 2`
- `importance source = 없음`
- `box_state = ABOVE`
- `bb_state = BREAKOUT`

current build로 직접 태우면 이 family는 `OBSERVE` 성격에 가깝다.
즉 historical row는 visible sell leakage처럼 남아 있지만,
현재 코드 해석으로는 감추는 쪽이 더 자연스럽다.

## 3. 왜 hide인가

이 family는 wait-check relief보다 hidden suppression에 가깝다.

- `scene_probe`가 없다
- `probe_not_promoted` repeated checks surface도 아니다
- importance source가 없다
- `forecast_guard + observe_state_wait` 아래 no-probe row다

즉 이 row는
`계속 보여줘야 할 probe scene`이 아니라
`아직 directional surface로 내보낼 만큼 성숙하지 않은 forecast wait`
로 읽는 것이 맞다.

## 4. 목표 contract

목표 contract는 아래와 같다.

- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_upper_break_fail_wait_hide_without_probe`
- painter는 top-level directional fallback을 다시 그리지 않는다
- PA0 freeze는 accepted hidden suppression으로 본다

## 5. 구현 방향

1. `nas_upper_break_fail_wait_hide_without_probe` soft-cap policy 추가
2. common modifier path에서 target family를 hidden suppression으로 내리기
3. painter hidden suppression set에 reason 추가
4. PA0 hidden suppression allow-list에 reason 추가
5. unit test, runtime restart, current-build replay, refreeze로 추적

## 6. 이번 축에서 하지 않는 것

- NAS outer-band must-show/must-block 처리
- `upper_reject_probe_observe + probe_promotion_gate` 처리
- entry / hold / exit acceptance 처리

## 7. 완료 기준

1. current-build replay에서 target family가 hidden suppression으로 내려간다
2. painter가 다시 directional surface를 그리지 않는다
3. fresh exact row가 다시 나오면 PA0 queue overlap이 `0`이 된다
4. 남은 PA1 main backlog가 더 선명해진다
