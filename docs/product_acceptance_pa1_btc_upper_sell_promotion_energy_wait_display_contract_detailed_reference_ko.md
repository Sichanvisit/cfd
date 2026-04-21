# Product Acceptance PA1 BTC Upper-Sell Promotion Energy Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 축

이번 PA1 하위축은 아래 3개 BTC upper-sell residue를 `WAIT + wait_check_repeat` 공통 계약으로 올리는 작업이다.

- `BTCUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + btc_upper_sell_probe`
- `BTCUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked`
- `BTCUSD + upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + btc_upper_sell_probe`

상위 흐름:

- [product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_detailed_reference_ko.md)

## 2. 왜 이 축이 남았는가

turn 시작 시점 baseline `2026-04-01T14:21:26` 기준으로 BTC upper-sell residue는 다음처럼 남아 있었다.

- `must_hide`: `probe_promotion_gate` family `3`
- `must_block`: `upper_reject_confirm + energy_soft_block` family `5`
- `must_show/must_block`: `upper_reject_probe + energy_soft_block` family `2 / 2`

즉 forecast/preflight는 이미 앞선 PA1 축에서 대부분 올라갔고, 남은 것은 `promotion`과 `energy`였다.

## 3. 이번 축의 의도

이번 축의 의도는 단순하다.

- `promotion/probe energy`는 숨겨야 할 leakage가 아니라 `아직 진입은 아니지만 봐야 하는 upper-sell wait scene`으로 올린다.
- `confirm energy`는 stage를 `BLOCKED`로 유지하되 chart surface는 `WAIT + wait_check_repeat`로 노출한다.
- `probe energy`와 `probe promotion`은 probe-scene이 있는 만큼 stage를 `PROBE`로 유지하되 chart surface를 wait-check로 통일한다.
- PA0는 이 reason들을 accepted wait row로 간주해서 fresh row부터 queue에서 빼야 한다.

## 4. 구현 owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 5. acceptance 기준

- current-build replay에서 3개 family 모두 `chart_event_kind_hint = WAIT`, `chart_display_mode = wait_check_repeat`를 반환해야 한다.
- `confirm energy`는 `stage = BLOCKED`, `blocked_display_reason = energy_soft_block`를 유지해야 한다.
- `probe energy`와 `probe promotion`은 `stage = PROBE`를 유지해야 한다.
- PA0는 아래 reason을 accepted wait-check row로 skip해야 한다.
  - `btc_upper_reject_probe_promotion_wait_as_wait_checks`
  - `btc_upper_reject_confirm_energy_soft_block_as_wait_checks`
  - `btc_upper_reject_probe_energy_soft_block_as_wait_checks`

## 6. 이번 축 이후 해석

이 축은 `구현/테스트/replay 완료`만으로 닫지 않는다. fresh runtime row가 실제로 새 contract로 기록되어야 PA0 actual cleanup까지 확인할 수 있다.
