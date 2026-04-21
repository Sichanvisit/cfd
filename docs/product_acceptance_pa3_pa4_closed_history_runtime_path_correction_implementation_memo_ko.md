# Product Acceptance PA3/PA4 Closed History Runtime Path Correction Implementation Memo

## 요약

PA3/PA4 exit acceptance queue가 멈춘 주된 이유는
`fresh closed trade가 전혀 없다`라기보다,
PA0 baseline freeze 기본 closed-history source가 runtime 실제 파일이 아닌
legacy root [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv) 였기 때문이다.

이번 수정으로 baseline freeze는 이제
[data/trades/trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)
를 우선 사용하고, runtime 파일이 없을 때만 legacy root file로 fallback한다.

## 반영 파일

- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 검증

- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `54 passed`
- `python scripts/product_acceptance_pa0_baseline_freeze.py`

## latest baseline

기준:
- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T19:51:49`
- `closed_history_path = data/trades/trade_closed_history.csv`

summary:
- `must_show_missing = 8`
- `must_hide_leakage = 0`
- `must_enter_candidate = 1`
- `must_block_candidate = 8`
- `must_hold_candidate = 1`
- `must_release_candidate = 10`
- `bad_exit_candidate = 10`

## 해석

- PA3 stale hold queue는 일부 정정됐다
  - old legacy-based `must_hold 2`
  - new runtime-based `must_hold 1`
- `must_release 10 / bad_exit 10`은 runtime closed artifact 기준으로도 여전히 남는다
- chart/entry queue는 separate issue이고, 이번 수정은 exit evidence source correction이다
