# Product Acceptance PA0 Refreeze After BTC Upper-Break-Fail Entry-Gate Energy Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 비교 기준

- before baseline: `2026-04-01T14:55:23`
- after baseline: `2026-04-01T15:21:43`

before snapshot:

- [product_acceptance_pa0_baseline_snapshot_20260401_151732.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_snapshot_20260401_151732.json)

after latest:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

## target family

- `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone`
- `BTCUSD + upper_break_fail_confirm + pyramid_not_progressed`
- `BTCUSD + upper_break_fail_confirm + pyramid_not_in_drawdown`
- `BTCUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`

## delta

- `clustered_entry must_show: 4 -> 6`
- `pyramid_not_progressed must_show: 4 -> 1`
- `pyramid_not_in_drawdown must_show: 3 -> 0`
- `energy_soft_block must_block: 5 -> 4`

baseline summary도 함께 바뀌었다.

- `must_hide: 15 -> 0`
- `must_block: 12 -> 12`
- `must_show: 15 -> 15`

## 해석

- current-build replay에서는 target family가 모두 `WAIT + wait_check_repeat`로 resolve된다.
- 하지만 after baseline 시점 recent window에는 exact fresh target row가 다시 거의 나오지 않아서 old blank backlog가 일부 남아 있다.
- 그래서 family 전체가 한 번에 `0`으로 닫히진 않았고, `pyramid / drawdown`만 먼저 줄었다.
- `clustered_entry`는 recent window에 old blank row가 더 남으면서 `4 -> 6`으로 다시 커졌다.

즉 이번 delta는 다음 한 줄로 정리한다.

`구현 완료 + replay 확인 완료 + turnover는 부분 진행 + exact fresh recurrence 기반 actual cleanup은 계속 추적 필요`

## 새 top residue

after baseline 기준 top residue는 다음으로 재편됐다.

- `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone` `6`
- `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + xau_second_support_buy_probe` `4`
- `XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait` `4`
- `BTCUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked` `4`
