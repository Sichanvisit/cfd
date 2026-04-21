# Product Acceptance PA0 Refreeze After BTC Upper-Sell Promotion Energy Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 비교 기준

- before baseline 해석: `2026-04-01T14:21:26`
- after baseline 해석: `2026-04-01T14:48:11`

## target family

- `BTCUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + btc_upper_sell_probe`
- `BTCUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked`
- `BTCUSD + upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + btc_upper_sell_probe`

## delta

- `probe promotion must_hide: 3 -> 3`
- `confirm energy must_block: 5 -> 10`
- `probe energy must_show: 2 -> 2`
- `probe energy must_block: 2 -> 2`

같이 본 residue:

- `probe preflight must_block: 3 -> 0`

## 해석

- preflight residue는 turnover로 빠졌다.
- promotion / energy 3축은 current-build replay에서는 새 wait-check contract로 정확히 resolve된다.
- 그런데 after baseline 시점 recent window에는 exact fresh row가 다시 기록되지 않아 old blank backlog가 그대로 queue를 채우고 있다.
- 특히 `confirm energy`는 recent window 안에 같은 family blank row가 더 쌓이면서 `5 -> 10`으로 보였다.

즉 이번 delta 해석은 다음 한 줄로 정리된다.

`구현 완료 + replay 확인 완료 + actual queue cleanup은 fresh exact recurrence pending`

## 새로 커진 must-show residue

after baseline에서는 upper energy/promotion 외에 아래 family가 새 must-show 메인으로 올라왔다.

- `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone` `4`
- `BTCUSD + upper_break_fail_confirm + pyramid_not_progressed` `5`
- `BTCUSD + upper_break_fail_confirm + pyramid_not_in_drawdown` `3`
