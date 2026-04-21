# Product Acceptance PA4 Bad Exit Exit Context Exit-Now-Best Narrowing Detailed Reference

## target

- `bad_exit`에 남아 있던 `Exit Context + no_wait + decision_reason=exit_now_best + post_exit_mfe=0` family
- 대표 ticket
  - `99802294` `XAUUSD`
  - `99774778` `NAS100`
  - `98726456` `NAS100`
  - `96732774` `NAS100`
  - `98768270` `BTCUSD`

## interpretation

- 이 family는 `giveback`은 있었지만 `실제로 더 기다린 흔적`은 거의 없음
- `decision_reason=exit_now_best`
- `wait_quality_label=no_wait`
- `post_exit_mfe=0`
- 따라서 teacher-label 기준으론 `bad_exit`보다 `must_release` 쪽 해석이 더 맞음

## owner

- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)

## intended effect

- `bad_exit`에서만 제거
- `must_release`는 유지
- 즉 `release timing issue`와 `actually bad cut`을 분리
