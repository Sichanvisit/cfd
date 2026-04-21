# Product Acceptance PA0 Refreeze After XAU Outer-Band Probe Entry-Gate Wait Display Contract Third Follow-Up

작성일: 2026-04-01 (KST)

## 1. 확인 범위

이번 follow-up은 두 가지를 다시 확인했다.

- exact `XAU outer-band blocked entry-gate` row가 restart 이후 실제로 다시 뜨는지
- recent window turnover 뒤 PA0 `must_show 14 / must_enter 10`이 줄었는지

## 2. fresh runtime 결과

첫 확인:

- cutoff: `2026-04-01T17:42:44`
- total row count: `2585`
- latest row time: `2026-04-01T17:44:39`
- recent row count: `52`
- exact recurrence count: `0`

추가 watch:

- total row count: `2666`
- latest row time: `2026-04-01T17:47:45`
- recent row count: `82`
- exact recurrence count: `0`

즉 XAU row는 계속 쌓였지만, target exact family는 두 번의 follow-up watch에서도 다시 나타나지 않았다.

## 3. PA0 refreeze 결과

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T17:43:01`

queue는 그대로 유지됐다.

- `must_show_missing_count = 15`
- `must_enter_candidate_count = 12`
- `must_hide_leakage_count = 0`
- `must_block_candidate_count = 0`

target family contribution:

- `must_show 14`
- `must_enter 10`

## 4. 현재 판단

지금 상태는 아래로 정리된다.

- 코드 반영 완료
- 회귀 테스트 완료
- representative replay 확인 완료
- short watch 2회에서 exact fresh recurrence 없음
- turnover refreeze 이후에도 target queue 감소 없음

즉 이 축은 아직 `actual cleanup waiting on true recurrence` 상태다.

## 5. 다음 체크포인트

다음은 그대로 하나다.

- exact `XAUUSD + outer_band_reversal_support_required_observe + blocked entry-gate + xau_upper_sell_probe` row가 새 reason으로 한 번 실제 기록되는지 확인

그 직후 다시 PA0를 얼려서:

- `must_show 14 -> 0`
- `must_enter 10 -> 0`

또는 최소한 유의미한 감소가 있는지 보면 된다.
