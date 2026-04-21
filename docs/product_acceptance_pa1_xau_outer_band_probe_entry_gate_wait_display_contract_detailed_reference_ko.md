# Product Acceptance PA1 XAU Outer-Band Probe Entry-Gate Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 하위축

이번 축은 `XAUUSD + outer_band_reversal_support_required_observe + clustered_entry_price_zone / pyramid_not_progressed / pyramid_not_in_drawdown + xau_upper_sell_probe` family를 `WAIT + wait_check_repeat` chart contract로 올리는 작업이다.

대상 조건:

- `symbol = XAUUSD`
- `side = SELL`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by in {clustered_entry_price_zone, pyramid_not_progressed, pyramid_not_in_drawdown}`
- `probe_scene_id = xau_upper_sell_probe`
- `action_none_reason = ""`

## 2. 왜 이 축이 필요했는가

직전 PA0 latest 기준 이 family가 사실상 남은 chart residue를 대부분 채우고 있었다.

- `must_show_missing = 14`
- `must_enter_candidates = 10/12` 수준의 대부분

대표 live row:

- `2026-04-01T17:13:09`
- `2026-04-01T17:13:16`
- `2026-04-01T17:13:22`
- `2026-04-01T17:13:29`
- `2026-04-01T17:16:31`
- `2026-04-01T17:16:51`

stored state는 공통적으로 아래와 같았다.

- `action = SELL`
- `consumer_check_display_ready = False`
- `consumer_check_stage = BLOCKED`
- `chart_event_kind_hint = ""`
- `chart_display_mode = ""`
- `chart_display_reason = ""`

즉 실제로는 probe-scene outer-band blocked family인데, live flat payload에는 아직 wait contract가 기록되지 않아 PA0가 계속 blank backlog로 잡고 있었다.

## 3. 이번에 고정한 해석

이 family는 `hidden suppression`이 아니다.

- probe scene이 이미 붙어 있음
- blocked 이유가 entry-gate 계열임
- directional entry로 밀어붙일 상태는 아니지만, chart에서는 `WAIT + repeated checks`로 보여야 함

따라서 해석은:

- `SELL directional signal`
- 가 아니라
- `probe-present entry-gate wait`

reason:

- `xau_outer_band_probe_entry_gate_wait_as_wait_checks`

## 4. owner

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 5. acceptance target

- build replay에서 target family가 `WAIT + wait_check_repeat`로 resolve될 것
- hidden baseline row도 modifier에서 `restore_hidden_display`로 복구할 것
- PA0 accepted wait-check 목록에서 이 reason을 skip할 것
- blocked entry-gate row는 `must_show / must_enter` queue에서 빠질 것
- live exact fresh row가 다시 뜨면 flat payload에도 새 reason이 실제 기록될 것

## 6. 연결 문서

- [product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_fresh_runtime_followup_ko.md)
