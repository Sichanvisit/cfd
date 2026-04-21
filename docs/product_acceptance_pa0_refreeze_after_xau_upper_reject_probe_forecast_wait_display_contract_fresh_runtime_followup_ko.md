# Product Acceptance PA0 Refreeze After XAU Upper-Reject Probe Forecast Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 `xau_upper_reject_probe_forecast_wait_as_wait_checks` 구현 이후,
fresh runtime row를 다시 본 뒤 PA0 queue가 실제로 어떻게 바뀌었는지 기록하는 follow-up이다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_delta_ko.md)

## 2. fresh runtime watch

cutoff:

- `2026-04-01T00:04:42`

watch 결과:

- exact target fresh row = `0`
- `xau_upper_reject_probe_forecast_wait_as_wait_checks` fresh row = `0`

대신 fresh XAU는 아래 family로 이동했다.

- `upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
- `upper_reject_confirm + energy_soft_block + execution_soft_blocked`

## 3. PA0 delta

같은 refreeze 기준에서 target family는 아래처럼 바뀌었다.

- `must_show 7 -> 0`
- `must_hide 0 -> 0`
- `must_block 0 -> 0`

## 4. 해석

이번 follow-up은 아래 의미다.

1. exact fresh recurrence는 아직 없었다.
2. 하지만 recent window turnover와 regime shift로 old hidden backlog는 recent queue에서 사라졌다.
3. 따라서 PA0 기준선에서는 이 probe forecast 축도 now-closed로 볼 수 있다.

## 5. 다음 main queue

probe forecast backlog가 빠진 뒤 current must-show main queue는 아래다.

- `XAU outer_band + outer_band_guard + probe_not_promoted`
- `BTC lower_rebound_probe + forecast_guard + probe_not_promoted`
- `NAS outer_band + outer_band_guard + observe_state_wait`
