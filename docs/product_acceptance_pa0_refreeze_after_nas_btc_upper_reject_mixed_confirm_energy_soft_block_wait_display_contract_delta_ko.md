# Product Acceptance PA0 Refreeze After NAS/BTC Upper-Reject Mixed-Confirm Energy-Soft-Block Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 비교 기준

- before baseline: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T15:56:08` 해석 기준
- after baseline: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T16:17:41`

## target family

- `BTCUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `NAS100 + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`

## latest reading

after baseline 기준 target backlog:

- `must_block`: `BTCUSD ...` `8`
- `must_block`: `NAS100 ...` `4`

## 해석

이번 delta는 `즉시 0`으로 닫힌 케이스가 아니다.

이유:

- code / tests / representative build는 이미 wait contract로 닫혔다.
- 하지만 post-restart short watch에서 fresh exact NAS/BTC mixed energy row가 다시 안 떴다.
- 그래서 PA0는 아직 old blank backlog를 recent 120-row window에서 읽고 있다.

즉 현재 해석은 다음과 같다.

- `구현 실패`는 아니다.
- `actual cleanup evidence`는 fresh exact recurrence가 한 번 더 필요하다.

## current queue context

latest 기준 주요 queue는 아래로 재편됐다.

- `must_show`: `upper_break_fail_confirm + pyramid_not_progressed / clustered_entry_price_zone`
- `must_block`: 이번 NAS/BTC mixed energy family `12`
- `must_enter`: `XAU upper_reject_mixed_confirm`, `NAS/BTC upper_break_fail_confirm`

따라서 다음 live follow-up은
이 mixed energy family가 fresh row에서 새 reason으로 찍히는지 확인하는 쪽이 가장 중요하다.
