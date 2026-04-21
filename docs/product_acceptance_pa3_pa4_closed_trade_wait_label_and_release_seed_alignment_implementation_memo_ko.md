# Product Acceptance PA3/PA4 Closed Trade Wait Label And Release Seed Alignment Implementation Memo

## 반영 요약

이번 턴에서는 두 층을 같이 손봤다.

1. closed-trade wait label
2. PA0 exit acceptance seed

반영 파일:

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_loss_quality_wait_behavior.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_loss_quality_wait_behavior.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 규칙

### PA3 label rule

`adverse_wait=timeout(...)`라도 아래 조건이면 `bad_wait` 대신 `unnecessary_wait`로 본다.

- timeout seconds 짧음
- exit delay ticks 짧음
- peak_profit_at_exit가 거의 없음
- post_exit_mfe가 거의 없음

### PA4 seed rule

`must_release / bad_exit`에서 giveback은 이제
`meaningful peak`가 있었을 때만 강한 근거로 쓴다.

즉 `peak_profit_at_exit < 0.25`이면
raw giveback을 release failure 근거로 그대로 올리지 않는다.

## 검증

- `pytest -q tests/unit/test_loss_quality_wait_behavior.py` -> `3 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `55 passed`

artifact rewrite:

- `python scripts/cleanup_trade_closed_history.py --apply`
- backup:
  - [trade_closed_history.backup_cleanup_20260401_200513.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.backup_cleanup_20260401_200513.csv)

refreeze:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

## 결과

- `must_hold 1 -> 0`
- `must_release 10 -> 10`
- `bad_exit 10 -> 10`

즉 PA3 hold residue는 닫혔고,
PA4 release/bad-exit는 아직 남아 있지만
이제 `tiny peak defensive loss`와 `actual giveback release issue`를 더 분리한 상태가 됐다.

## 다음 메인축

현재 PA4 메인축은 아래 family로 보는 게 자연스럽다.

- `Exit Context + meaningful peak + giveback > 1.0`
- `Protect Exit / Adverse Stop + hard_guard=adverse + bad_loss`

즉 다음은 `XAU/NAS Exit Context giveback family`와
`BTC/NAS adverse protect bad_loss family`를 나눠서 들어가면 된다.
