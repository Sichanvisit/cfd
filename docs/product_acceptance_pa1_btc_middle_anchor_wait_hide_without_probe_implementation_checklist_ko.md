# Product Acceptance PA1 BTC Middle-Anchor Wait Hide Without Probe Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Family 고정

- [x] target family를 `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`로 고정
- [x] representative backlog row 시간 확인

## Step 1. Hidden contract 정리

- [x] generic `structural_wait_hide_without_probe` accepted hidden reason 누락 확인
- [x] BTC sell-side 전용 `btc_sell_middle_anchor_wait_hide_without_probe` soft cap 추가

## Step 2. Build path 연결

- [x] `BUY` no-probe row가 `structural_wait_hide_without_probe`로 유지되는지 확인
- [x] `SELL` no-probe row가 `btc_sell_middle_anchor_wait_hide_without_probe`로 내려가는지 확인

## Step 3. Surface skip 정리

- [x] chart painter hidden suppression set 업데이트
- [x] PA0 accepted hidden suppression set 업데이트

## Step 4. 회귀 테스트

- [x] `tests/unit/test_consumer_check_state.py`
- [x] `tests/unit/test_chart_painter.py`
- [x] `tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

## Step 5. Live 확인

- [x] cfd `main.py` 재시작
- [x] fresh BTC row watch
- [x] exact target live recurrence 없음 기록

## Step 6. Delta 기록

- [x] representative replay 결과 기록
- [x] PA0 refreeze delta 기록
- [x] 상위 memo / roadmap / handoff 링크 추가
