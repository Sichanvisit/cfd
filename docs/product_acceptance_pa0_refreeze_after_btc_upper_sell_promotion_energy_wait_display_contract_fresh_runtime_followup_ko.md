# Product Acceptance PA0 Refreeze After BTC Upper-Sell Promotion Energy Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## follow-up 기준

- before refreeze: `2026-04-01T14:48:11`
- after refreeze: `2026-04-01T14:55:23`
- row count: `2688 -> 2836`
- latest row time: `2026-04-01T14:55:09`

## exact fresh recurrence

이번 watch에서는 아래 exact family가 recent window에 다시 찍히지는 않았다.

- `BTCUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + btc_upper_sell_probe`
- `BTCUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked`
- `BTCUSD + upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + btc_upper_sell_probe`

recent 180-row 기준 `chart_display_reason`가 채워진 row도 `0`이었다.

## PA0 delta

- `probe promotion must_hide: 3 -> 3`
- `confirm energy must_block: 10 -> 1`
- `probe energy must_show: 2 -> 2`
- `probe energy must_block: 2 -> 2`

## 해석

이 follow-up은 중요한 의미가 있다.

- exact fresh row가 다시 안 떠도 turnover만으로 `confirm energy` backlog는 `10 -> 1`까지 줄었다.
- 즉 이 family는 current-build replay와 queue turnover 양쪽에서 거의 닫힌 상태다.
- 반면 `probe promotion`과 `probe energy`는 exact recurrence가 아직 없어 old blank row가 그대로 남아 있다.

## 새로 올라온 residue

같은 after baseline에서 BTC upper-sell residue의 중심은 아래처럼 이동했다.

- `must_show`
  - `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone` `4`
  - `BTCUSD + upper_break_fail_confirm + pyramid_not_progressed` `4`
  - `BTCUSD + upper_break_fail_confirm + pyramid_not_in_drawdown` `3`
- `must_block`
  - `BTCUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked` `5`
  - `BTCUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked` `2`

즉 upper-sell main residue는 기존 `upper_reject energy/promotion`에서 `upper_break_fail cluster/energy` 쪽으로 이동하고 있다.

## 연결 문서

- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_delta_ko.md)
