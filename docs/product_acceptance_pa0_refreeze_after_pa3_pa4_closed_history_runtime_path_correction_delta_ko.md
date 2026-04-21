# Product Acceptance PA0 Refreeze After PA3/PA4 Closed History Runtime Path Correction Delta

## 비교 기준

- before:
  - latest baseline at `2026-04-01T19:32:10`
  - closed source interpreted from legacy root [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv)
- after:
  - latest baseline at `2026-04-01T19:51:49`
  - closed source = [data/trades/trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)

## 핵심 변화

- `must_hold_candidate_count: 2 -> 1`
- `must_release_candidate_count: 10 -> 10`
- `bad_exit_candidate_count: 10 -> 10`

## 추가 관찰

- runtime closed artifact는 실제로 누적 중이었다
- 문제는 append failure보다 baseline source mismatch에 더 가까웠다
- latest exit queue 해석은 이제 runtime actual close file 기준으로 봐야 한다
