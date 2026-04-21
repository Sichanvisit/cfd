# Product Acceptance PA1 BTC Middle-Anchor Wait Hide Without Probe Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 축에서는
`BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`
family를 `accepted hidden suppression`으로 정리했다.

코드 반영:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)

핵심 변화:

- generic hidden reason `structural_wait_hide_without_probe`를 accepted hidden 목록에 추가
- BTC sell-side 전용 reason `btc_sell_middle_anchor_wait_hide_without_probe` 추가

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_consumer_check_state.py` -> `81 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `85 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `28 passed`

## 3. Representative Replay

대표 row:

- `2026-04-01T00:23:14` (`BUY`)
- `2026-04-01T00:25:02` (`SELL`)

current build replay 결과:

- `2026-04-01T00:23:14`
  - `check_display_ready = False`
  - `modifier_primary_reason = structural_wait_hide_without_probe`
- `2026-04-01T00:25:02`
  - `check_display_ready = False`
  - `modifier_primary_reason = btc_sell_middle_anchor_wait_hide_without_probe`

resolve replay에서도 둘 다 hidden contract가 유지됐다.

## 4. Live Restart

재시작 로그:

- [cfd_main_restart_20260401_003520.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_003520.out.log)
- [cfd_main_restart_20260401_003520.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_003520.err.log)

재시작 이후 cfd PID:

- `30052`

cutoff:

- `2026-04-01T00:35:20`

fresh BTC row watch 결과:

- fresh BTC row = `16`
- exact middle-anchor recurrence = `0`

fresh BTC는 이번 watch 구간에서 아래 family로 이동했다.

- `conflict_box_lower_bb20_upper_balanced_observe`
- `conflict_box_lower_bb20_upper_upper_dominant_observe`
- `upper_reject_probe_observe + btc_upper_sell_probe`

즉 이번 축은 `live exact recurrence pending` 상태였다.

## 5. PA0 Delta

delta 기록:

- [product_acceptance_pa0_refreeze_after_btc_middle_anchor_wait_hide_without_probe_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_middle_anchor_wait_hide_without_probe_delta_ko.md)

핵심 해석:

- `must_show 13 -> 0`
- `must_block 12 -> 0`
- `must_hide 5 -> 12`

즉 이 축은 `must-show/must-block cleanup`은 닫혔고,
`must-hide`는 old sell backlog가 recent window에 남아 있어 아직 완전히 닫히지 않았다.

한 줄로 정리하면:

```text
구현 완료 + replay 확인 완료 + must-show/must-block 해소 + must-hide old sell backlog 잔존
```

## 6. 현재 잔여 queue

latest PA0 기준 main residue는 아래로 바뀌었다.

- `must_hide_leakage = 12`: `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`
- `must_show_missing = 14`: `XAUUSD + upper_reject_probe_observe + clustered_entry_price_zone + xau_upper_sell_probe`
- `must_block_candidates = 11`: `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`

즉 다음 체크 포인트는 fresh BTC middle-anchor exact row가 새 hidden reason으로 실제 기록되는지 다시 보는 것이다.

## 7. Fresh Runtime Follow-Up

- [product_acceptance_pa0_refreeze_after_btc_middle_anchor_wait_hide_without_probe_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_middle_anchor_wait_hide_without_probe_fresh_runtime_followup_ko.md)

추가 follow-up 결과:

- exact fresh middle-anchor recurrence는 끝내 `0`
- 그럼에도 recent window turnover로 `must_hide 12 -> 0` 확인

즉 이 축은 queue 기준으로는 닫힌 상태로 봐도 된다.
