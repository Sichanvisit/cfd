# Product Acceptance PA1 XAU Outer-Band Probe Entry-Gate Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 이번 축에서 한 일

`XAUUSD + outer_band_reversal_support_required_observe + blocked entry-gate + xau_upper_sell_probe` family를 `WAIT + wait_check_repeat` chart contract로 연결했다.

관련 문서:

- [product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_fresh_runtime_followup_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_second_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_second_followup_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_third_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_third_followup_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_turnover_resolution_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_turnover_resolution_followup_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 요약

- policy에 `xau_outer_band_probe_entry_gate_wait_as_wait_checks`를 추가했다.
- probe-present entry-gate family도 hidden baseline에서 복구되도록 `restore_hidden_display = true`를 올렸다.
- build path에 `xau_outer_band_probe_entry_gate_wait_relief`와 `blocked_display_reason` carry를 추가했다.
- resolve path에 repeat relief를 추가해서 late display suppress guard가 이 family를 다시 blank로 내리지 않게 했다.
- PA0 accepted wait-check 목록에 새 reason을 추가했고, must-enter builder도 accepted wait-check rows를 skip하도록 보정했다.

## 4. representative replay

stored sample row:

- `2026-04-01T17:16:51`
- `XAUUSD + outer_band_reversal_support_required_observe + clustered_entry_price_zone + xau_upper_sell_probe`

stored state:

- `check_display_ready = False`
- `check_stage = BLOCKED`
- `chart_event_kind_hint = ""`
- `chart_display_mode = ""`
- `chart_display_reason = ""`

current build replay:

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = clustered_entry_price_zone`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_outer_band_probe_entry_gate_wait_as_wait_checks`

즉 build/replay 기준으로는 target family가 새 wait contract로 정확히 올라간다.

## 5. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
126 passed
108 passed
51 passed
```

## 6. live / refreeze

재기동 로그:

- [cfd_main_restart_20260401_173548.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_173548.out.log)
- [cfd_main_restart_20260401_173548.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_173548.err.log)

short watch:

- cutoff: `2026-04-01T17:16:53`
- recent row count: `16`
- latest row time: `2026-04-01T17:38:33`
- exact fresh recurrence: `0`

즉 이번 short watch에서는 exact family가 새 wait reason으로 다시 찍히는 장면까지는 확보하지 못했다.

latest PA0 refreeze:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T17:38:47`

현재 queue는 여전히:

- `must_show = 15`
- `must_enter = 12`
- target family contribution:
  - `must_show 14`
  - `must_enter 10`

즉 이번 축 상태는 `코드/테스트/replay 완료`, `live exact recurrence pending`, `PA0 actual cleanup pending`이다.

## 7. 다음 해석

이 축의 구현 방향 자체는 확정됐다. 다음은 두 단계다.

- exact fresh XAU outer-band blocked row가 한 번 더 나오는지 보고 live flat payload에 새 reason이 실제로 찍히는지 확인
- 그 이후 PA0 refreeze로 blocked entry-gate residue `14 / 10`가 실제로 줄었는지 확인

그 다음에는 blocked variant가 빠진 뒤 남는 `blocked_by = ""` XAU outer-band actual must-enter row를 PA2 쪽에서 다루면 된다.
