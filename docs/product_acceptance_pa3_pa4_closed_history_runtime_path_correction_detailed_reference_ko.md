# Product Acceptance PA3/PA4 Closed History Runtime Path Correction Detailed Reference

## 목적

이 문서는 `PA3 wait/hold acceptance`와 `PA4 exit acceptance`가 보던 closed-trade 근거 파일이
runtime 실제 파일과 어긋나 있었던 문제를 고정하기 위한 상세 기준 문서다.

## 실제 문제

runtime `TradeLogger`는 아래 경로를 기준으로 open/closed trade CSV를 기록한다.

- [trading_application_runner.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)
- [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py)
- runtime open path: `data/trades/trade_history.csv`
- runtime closed path: `data/trades/trade_closed_history.csv`

그런데 PA0 baseline freeze script 기본값은 아래 레거시 파일을 보고 있었다.

- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- old default: [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv)

그 결과 PA3/PA4 queue는 runtime 현재 close artifact가 아니라
루트 레거시 closed file 기준으로 계산되고 있었다.

## 증거

2026-04-01 확인 시점 기준:

- runtime actual closed file:
  - [data/trades/trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)
  - row count `8432`
  - latest close sample `2026-04-01`
- legacy root closed file:
  - [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv)
  - row count `139`
  - latest close sample `2026-03-02`

즉 `trade_closed_history.csv`가 멈춘 것이 아니라,
PA0 freeze가 runtime 파일이 아닌 legacy root 파일을 읽고 있었던 것이다.

## 수정 방향

1. baseline freeze default closed-history path를 `data/trades/trade_closed_history.csv`로 교체
2. runtime 파일이 없을 때만 root legacy file로 fallback
3. refreeze 결과에 실제 resolved path가 기록되도록 유지
4. 회귀 테스트로 `runtime path 우선 / legacy fallback`을 잠금

## 기대 효과

- PA3/PA4 queue가 실제 runtime close artifact 기준으로 계산된다
- `fresh closed trade가 안 쌓인다`는 해석과 `wrong source를 읽고 있다`는 문제를 분리할 수 있다
- 이후 exit acceptance 조정은 stale legacy row가 아니라 현재 production artifact 기준으로 진행된다
