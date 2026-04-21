# Product Acceptance PA0 Refreeze After PA4 Release Seed Teacher-Label Narrowing Delta

## delta

- `must_release_candidate_count`: `10 -> 8`
- `bad_exit_candidate_count`: `10 -> 10`

## 핵심 변화

빠진 row는 주로 아래 family다.

- `bad_loss + no_wait + peak_profit_at_exit=0 + giveback=0`
- 대표적으로 `XAU Exit Context topdown-only no-green bad_loss`

남은 `must_release`는 이제 대부분 아래 family로 수렴한다.

- `XAU topdown-only Exit Context + meaningful giveback`
- `NAS/BTC structure Exit Context + meaningful giveback`

즉 이번 delta는 runtime close action보다 `release seed 정렬` 개선 효과다.
