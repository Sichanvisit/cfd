# Product Acceptance PA1 BTC Upper-Sell Promotion Energy Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 이번 턴에서 한 일

이번 턴에서는 BTC upper-sell residue 중 `promotion + energy` 3개 family를 wait-check contract로 올렸다.

관련 문서:

- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_delta_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 요약

- policy에 아래 3개 reason을 추가했다.
  - `btc_upper_reject_probe_promotion_wait_as_wait_checks`
  - `btc_upper_reject_confirm_energy_soft_block_as_wait_checks`
  - `btc_upper_reject_probe_energy_soft_block_as_wait_checks`
- build/resolve에서 `blocked_display_reason` carry를 연결했다.
- `probe energy`는 `PROBE`, `confirm energy`는 `BLOCKED`로 stage 의미를 유지하게 맞췄다.
- PA0 accepted wait-check 목록에 3개 reason을 올렸다.
- resolve 단계의 duplicate carry block 하나를 정리했다.

## 4. representative replay

현재 build로 representative row를 replay하면 저장 당시 blank row여도 새 contract가 정확히 나온다.

### XAU lower probe forecast mirror

- row: `2026-04-01T14:11:28`
- stored: `chart_display_reason = ""`
- build/resolve:
  - `stage = PROBE`
  - `blocked_display_reason = forecast_guard`
  - `chart_display_reason = xau_lower_probe_guard_wait_as_wait_checks`

### BTC upper probe preflight

- row: `2026-04-01T01:49:24`
- stored: `chart_display_reason = ""`
- build/resolve:
  - `stage = BLOCKED`
  - `blocked_display_reason = probe_forecast_not_ready`
  - `chart_display_reason = btc_upper_reject_probe_preflight_wait_as_wait_checks`

### BTC upper confirm energy

- row: `2026-04-01T13:59:51`
- stored: `chart_display_reason = ""`
- build/resolve:
  - `stage = BLOCKED`
  - `blocked_display_reason = energy_soft_block`
  - `chart_display_reason = btc_upper_reject_confirm_energy_soft_block_as_wait_checks`

### BTC upper probe energy

- row: `2026-04-01T14:18:07`
- stored: `chart_display_reason = ""`
- build/resolve:
  - `stage = PROBE`
  - `blocked_display_reason = energy_soft_block`
  - `chart_display_reason = btc_upper_reject_probe_energy_soft_block_as_wait_checks`

### BTC upper probe promotion

- row: `2026-04-01T14:14:28`
- stored: `chart_display_reason = ""`
- build/resolve:
  - `stage = PROBE`
  - `blocked_display_reason = probe_promotion_gate`
  - `chart_display_reason = btc_upper_reject_probe_promotion_wait_as_wait_checks`

## 5. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
108 passed
99 passed
42 passed
```

## 6. live / fresh runtime 메모

- restart log: [cfd_main_restart_20260401_144556.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_144556.out.log)
- err log: [cfd_main_restart_20260401_144556.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_144556.err.log)
- active pid: `19468`

fresh row는 다시 들어오기 시작했다.

- `entry_decisions.csv` row count: `2670 -> 2688`
- latest row time: `2026-04-01T14:47:46`

다만 이번 watch에서는 exact target family fresh recurrence가 아직 다시 안 찍혔다. 그래서 stored CSV 안 `chart_display_reason`는 여전히 blank backlog가 중심이고, current-build replay가 더 강한 확인 근거다.

## 7. 해석

이번 축은 `코드 / 테스트 / replay`는 닫혔다.

actual PA0 cleanup은 fresh exact row가 한 번 더 들어와야 최종 확인 가능하다. 현재 baseline에서는 `confirm energy`와 `probe energy`, `probe promotion` old backlog가 아직 queue에 남아 있다.
