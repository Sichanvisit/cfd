# Product Acceptance PA4 Bad Exit Exit Context Exit-Now-Best Narrowing Implementation Memo

## implementation

- owner: [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- 추가 helper:
  - `_supports_bad_exit_non_loss_seed(...)`
- normalizer/payload 확장:
  - `decision_reason`
  - `exit_wait_state`
  - `exit_wait_decision`
  - `utility_exit_now`
  - `u_wait_be`
  - `u_wait_tp1`

## rule

- 아래 조건이면 `bad_exit`에서 제외
  - `exit_reason` startswith `Exit Context`
  - `wait_quality_label=no_wait`
  - `decision_reason=exit_now_best`
  - `post_exit_mfe <= 0.5`
- 대신 `must_release`는 그대로 유지

## verification

- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)
- 결과: `59 passed`

## result

- latest baseline 기준
  - `bad_exit: 8 -> 0`
  - `must_release: 8 -> 8`

## next

- PA4 메인은 이제 `must_release 8`
- 구성:
  - `structure_exit_context 6`
  - `xau_topdown_only_exit_context 1`
  - `generic_exit_context 1`
