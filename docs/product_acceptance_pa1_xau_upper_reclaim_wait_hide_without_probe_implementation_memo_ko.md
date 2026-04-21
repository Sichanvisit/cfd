# Product Acceptance PA1 XAU Upper-Reclaim Wait Hide Without Probe Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 이번 축에서 한 일

`XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait` family를 NAS mirror hidden suppression으로 연결했다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 요약

- policy에 `xau_upper_reclaim_wait_hide_without_probe`를 추가했다.
- build modifier에서 XAU upper reclaim family가 probe scene 없이 forecast guard에 막힌 경우 visibility를 끄게 연결했다.
- painter hidden suppression 목록과 PA0 accepted hidden suppression 목록에 같은 reason을 추가했다.
- XAU mirror hidden suppression 테스트 3개를 추가했다.

## 4. representative replay

stored exact sample row:

- `2026-04-01T16:36:38`
- `XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait`

current build replay 결과:

- `check_display_ready = False`
- `check_stage = OBSERVE`
- `check_side = BUY`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = xau_upper_reclaim_wait_hide_without_probe`
- `modifier_stage_adjustment = visibility_suppressed`

즉 이 family는 wait contract가 아니라 hidden suppression으로 처리되는 것이 맞음을 replay로 확인했다.

## 5. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
123 passed
107 passed
50 passed
```

## 6. live / refreeze

재기동 로그:

- [cfd_main_restart_20260401_171408.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_171408.out.log)
- [cfd_main_restart_20260401_171408.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_171408.err.log)

short watch:

- cutoff: `2026-04-01T17:14:06`
- recent row count: `30`
- latest row time: `2026-04-01T17:16:31`
- exact fresh recurrence: `0`

direct fresh proof는 아직 없었지만, PA0 refreeze latest는 `2026-04-01T17:16:41` 기준으로:

- `must_hide_leakage_count = 0`
- `must_block_candidate_count = 0`

으로 내려갔다. 직전 `XAU upper_reclaim` residue `5 / 5`는 recent window turnover로 queue에서 빠진 상태다.

## 7. 다음 residue

현재 latest PA0는 chart acceptance의 남은 main residue가 XAU outer-band entry-gate 쪽으로 이동한 상태다.

- `must_show_missing = 14`
- `must_enter_candidates` 다수가 `XAU outer_band_reversal_support_required_observe + clustered_entry_price_zone / pyramid_not_in_drawdown + xau_upper_sell_probe`

즉 다음 축은 XAU upper reclaim이 아니라 XAU outer-band entry-gate / must-enter 정리로 이어지는 것이 자연스럽다.
