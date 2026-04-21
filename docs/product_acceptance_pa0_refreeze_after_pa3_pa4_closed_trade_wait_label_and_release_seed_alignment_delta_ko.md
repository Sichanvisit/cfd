# Product Acceptance PA0 Refreeze After PA3/PA4 Closed Trade Wait Label And Release Seed Alignment Delta

## 기준

- before:
  - runtime closed-history source correction 이후 baseline
- after:
  - wait label / release seed alignment 적용 후 baseline

## 변화

- `must_hold_candidate_count: 1 -> 0`
- `must_release_candidate_count: 10 -> 10`
- `bad_exit_candidate_count: 10 -> 10`

## 해석

- PA3 `must_hold`는 실제로 줄었다
  - short timeout defensive defer를 과한 `bad_wait`로 보던 문제가 정리됐다
- PA4는 숫자 총량은 그대로지만 composition 해석이 더 또렷해졌다
  - 이제 메인은 `meaningful peak + giveback` family
  - 또는 `bad_loss adverse protect` family다
