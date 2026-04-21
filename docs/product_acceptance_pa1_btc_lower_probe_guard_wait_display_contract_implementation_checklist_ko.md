# Product Acceptance PA1 BTC Lower-Probe Guard Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Family 고정

- [x] target family를 `BTCUSD + lower_rebound_probe_observe + {forecast_guard | barrier_guard} + probe_not_promoted + btc_lower_buy_conservative_probe`로 고정
- [x] representative backlog row 시간 확인

## Step 1. Policy contract 추가

- [x] `btc_lower_probe_guard_wait_as_wait_checks` chart wait relief policy 추가
- [x] `event_kind_hint = WAIT`
- [x] `display_mode = wait_check_repeat`
- [x] `display_reason = btc_lower_probe_guard_wait_as_wait_checks`

## Step 2. Build path 연결

- [x] `btc_lower_probe_guard_wait_relief` bool 추가
- [x] `blocked_display_reason = forecast_guard | barrier_guard` carry 추가

## Step 3. Resolve path 보호

- [x] repeated cadence suppression 예외 추가
- [x] representative replay에서 resolve contract 유지 확인

## Step 4. PA0 accepted queue 정렬

- [x] accepted wait-check reason set 추가
- [x] must-show / must-hide / must-block skip test 추가

## Step 5. 회귀 테스트

- [x] `tests/unit/test_consumer_check_state.py`
- [x] `tests/unit/test_chart_painter.py`
- [x] `tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

## Step 6. Live 확인

- [x] cfd `main.py` 재시작
- [x] fresh BTC row watch
- [x] exact target live recurrence 없음 기록

## Step 7. Delta 기록

- [x] representative replay 결과 기록
- [x] PA0 refreeze delta 기록
- [x] 상위 memo / roadmap / handoff 링크 추가
