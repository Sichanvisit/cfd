# Product Acceptance PA1 BTC Upper-Reject Forecast And Preflight Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Family 고정

- [x] `BTC upper_reject_confirm + forecast_guard + observe_state_wait` family 고정
- [x] `BTC upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe` family 고정
- [x] representative replay로 현재 hidden/leakage 상태 확인

## Step 1. Policy 추가

- [x] `btc_upper_reject_confirm_forecast_wait_as_wait_checks` 추가
- [x] `btc_upper_reject_probe_preflight_wait_as_wait_checks` 추가

## Step 2. Build path 보정

- [x] confirm forecast `blocked_display_reason = forecast_guard` carry 추가
- [x] probe preflight blocked row의 display visibility 복구 추가
- [x] blocked reason carry 보정

## Step 3. Resolve path 확인

- [x] confirm forecast build/resolve 유지 확인
- [x] probe preflight build/resolve 유지 확인

## Step 4. 테스트 고정

- [x] build confirm forecast test 추가
- [x] resolve confirm forecast test 추가
- [x] build probe preflight test 추가
- [x] resolve probe preflight test 추가
- [x] painter 2건 추가
- [x] PA0 skip 2건 추가

## Step 5. Live / PA0 확인

- [x] representative replay 기록
- [x] PA0 snapshot 저장
- [x] PA0 refreeze 재실행
- [x] `main.py` 재시작
- [x] MT5 unavailable 상태 기록

## Step 6. 문서 체인

- [x] detailed reference
- [x] implementation checklist
- [x] implementation memo
- [x] PA0 delta
