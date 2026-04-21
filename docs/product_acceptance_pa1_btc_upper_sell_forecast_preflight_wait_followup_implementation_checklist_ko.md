# Product Acceptance PA1 BTC Upper-Sell Forecast Preflight Wait Follow-Up Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Family 고정

- [x] `upper_break_fail_confirm + forecast_guard + observe_state_wait` family 고정
- [x] `upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe` family 고정
- [x] `upper_reject_confirm + preflight_action_blocked + preflight_blocked` family 고정

## Step 1. Policy 추가

- [x] `btc_upper_break_fail_confirm_forecast_wait_as_wait_checks` 추가
- [x] `btc_upper_reject_probe_forecast_wait_as_wait_checks` 추가
- [x] `btc_upper_reject_confirm_preflight_wait_as_wait_checks` 추가

## Step 2. Build path 보정

- [x] break-fail forecast carry 추가
- [x] probe forecast carry 추가
- [x] confirm preflight blocked visibility restore 추가

## Step 3. 테스트 고정

- [x] build 테스트 3건 추가
- [x] resolve 테스트 3건 추가
- [x] painter 테스트 3건 추가
- [x] PA0 skip 테스트 3건 추가

## Step 4. Refreeze / Runtime

- [x] representative replay 기록
- [x] PA0 snapshot 저장
- [x] PA0 refreeze 재실행
- [x] live MT5 unavailable 상태 재기록

## Step 5. 문서 체인

- [x] detailed reference
- [x] implementation checklist
- [x] implementation memo
- [x] PA0 delta
