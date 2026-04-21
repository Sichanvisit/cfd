# Product Acceptance PA0 Refreeze After PA4 Bad Exit Exit-Now-Best Narrowing Delta

## baseline

- latest: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- generated_at: `2026-04-02T13:38:39`

## delta

- `must_hold: 0 -> 0`
- `must_release: 8 -> 8`
- `bad_exit: 8 -> 0`

## interpretation

- 이번 패치는 `bad_exit` 정의를 teacher-label 기준으로 좁힌 것
- `giveback`이 있었어도 `no_wait + exit_now_best + no post-exit-mfe`면 `bad_exit`가 아니라 `late release` 쪽으로 남김
- 따라서 PA4 잔존 메인은 이제 `bad_exit`가 아니라 `must_release` queue
