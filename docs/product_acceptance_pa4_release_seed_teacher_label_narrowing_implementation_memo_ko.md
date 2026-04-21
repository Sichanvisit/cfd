# Product Acceptance PA4 Release Seed Teacher-Label Narrowing Implementation Memo

## 구현

- owner: [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- helper 추가:
  - `_supports_must_release_bad_loss_seed(...)`
- 변경점:
  - `bad_loss` row라도
  - `meaningful peak/giveback/post-exit-mfe/bad_wait`
  - 증거가 없으면 `must_release` seed에서 제외

## 테스트

- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)
- 결과: `56 passed`

## 결과

- `must_release: 10 -> 8`
- `bad_exit: 10 -> 10`

해석:

- `must_release`는 과대추정이 줄었다
- 남은 PA4 메인은 이제 `late release`보다 `bad_exit protect/adverse` 쪽이 더 크다

## 다음

- fresh closed trade가 더 쌓이면 다시 refreeze
- 다음 PA4 patch는 `bad_exit` top family 기준으로 진행
