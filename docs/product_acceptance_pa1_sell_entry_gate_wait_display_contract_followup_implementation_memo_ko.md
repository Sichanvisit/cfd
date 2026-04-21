# Product Acceptance PA1 Sell Entry-Gate Wait Display Contract Follow-Up Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 이번 턴에서 한 일

SELL entry-gate blocked residue를 공통 wait contract로 묶었다.

관련 문서:

- [product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_detailed_reference_ko.md)
- [product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_fresh_runtime_followup_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 요약

- NAS/XAU SELL entry-gate mirror reason 2개를 chart wait policy에 추가했다.
- 기존 BTC entry-gate policy까지 포함해서 entry-gate family에 `restore_hidden_display = true`를 올렸다.
- modifier chart wait loop가 hidden baseline에서도 visibility를 restore할 수 있도록 보강했다.
- resolve late suppress guard가 NAS/XAU entry-gate repeat relief를 다시 죽이지 않게 연결했다.
- PA0 accepted wait-check 목록에 NAS/XAU entry-gate reason을 추가했다.

## 4. representative replay

### policy-only replay

- NAS:
  - `upper_break_fail_confirm + clustered_entry_price_zone`
  - build / resolve -> `WAIT + wait_check_repeat + nas_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
- XAU:
  - `upper_reject_mixed_confirm + clustered_entry_price_zone`
  - build / resolve -> `WAIT + wait_check_repeat + xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks`

### first fresh blank row

- row: `2026-04-01T16:42:10`
- family: `XAUUSD + upper_reject_mixed_confirm + pyramid_not_in_drawdown`
- stored:
  - `check_display_ready = false`
  - `check_stage = BLOCKED`
  - `chart_event_kind_hint = ""`
  - `chart_display_mode = ""`
  - `chart_display_reason = ""`

이 row를 current build에 replay하면:

- `check_display_ready = true`
- `check_stage = OBSERVE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks`

즉 첫 restart 뒤 blank row를 보고, hidden baseline restore 보강이 추가로 필요하다는 점을 확인했다.

## 5. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
122 passed
106 passed
49 passed
```

## 6. live / refreeze 메모

- restart log: [cfd_main_restart_20260401_164913.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_164913.out.log)
- err log: [cfd_main_restart_20260401_164913.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_164913.err.log)
- active pid: `15764`

second restart 이후 short watch:

- cutoff: `2026-04-01T16:49:12`
- recent rows: `1655 -> 1725`
- latest row time: `2026-04-01T16:51:59`
- exact `NAS/XAU entry-gate` recurrence: `0`

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T16:52:08`

queue 핵심:

- `must_show = 15`
- `must_hide = 5`
- `must_enter = 12`
- `must_block = 5`

entry-gate residue:

- `NAS100 + upper_break_fail_confirm + clustered/pyramid` `8`
- `XAUUSD + upper_reject_mixed_confirm + clustered/pyramid` `4`

## 7. 현재 해석

이번 축은 `코드 / 테스트 / replay`는 닫혔다.

다만 live 기준으로는 두 단계로 나뉜다.

1. first restart에서는 exact fresh XAU row가 여전히 blank였다.
2. hidden-restore follow-up 이후 second restart에서는 exact recurrence가 short watch에 다시 안 떠서, 새 reason이 live flat payload에 실제 기록됐다는 증빙은 아직 pending이다.

즉 현재 상태는:

- `policy mirror 완료`
- `hidden baseline restore 완료`
- `current-build replay 완료`
- `PA0 old blank backlog 잔존`
- `second fresh exact 증빙 pending`

다음 메인축은 현재 `must_hide / must_block`를 같이 채우는
`XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait`
로 보는 게 가장 자연스럽다.
