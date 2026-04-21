# Product Acceptance PA0 Refreeze After XAU Lower Probe Guard Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 비교 기준

- before baseline 해석: `2026-04-01T14:06:54`
- after baseline 해석: `2026-04-01T14:21:26`

## target family

`XAUUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + xau_second_support_buy_probe`

## delta

- `must_hide_leakage: 8 -> 12`

## 해석

- representative fresh row replay는 새 contract로 해결됐다.
- 그러나 post-restart exact family fresh row가 아직 다시 기록되지 않았다.
- recent window turnover 과정에서 old blank backlog가 더 들어오면서 queue count는 일시적으로 `8 -> 12`가 됐다.
- 현재 해석은 `구현 완료 + replay 확인 완료 + live recurrence pending`이다.
