# Product Acceptance PA1 XAU Upper-Reject Confirm Forecast Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Family 고정

- [x] `XAUUSD + upper_reject_confirm + forecast_guard + observe_state_wait +` family 고정
- [x] representative confirm row replay 확인
- [x] mixed forecast row는 이미 current build에서 WAIT contract인지 재확인

## Step 1. Policy 추가

- [x] `xau_upper_reject_confirm_forecast_wait_as_wait_checks` policy 추가
- [x] 범위를 `forecast_guard + observe_state_wait + no_probe`로만 고정

## Step 2. Build path 보정

- [x] `xau_upper_reject_confirm_forecast_wait_relief` 추가
- [x] `xau_upper_reject_guard_wait_hidden`에서 narrow exemption 추가
- [x] `blocked_display_reason = forecast_guard` carry 추가

## Step 3. Resolve path 보호

- [x] `xau_upper_reject_confirm_forecast_wait_repeat_relief` 추가
- [x] `xau_upper_reject_late_hidden` 예외 추가
- [x] `xau_upper_reject_cadence_suppressed` 예외 추가

## Step 4. 테스트 고정

- [x] build confirm forecast wait test 추가
- [x] resolve confirm forecast wait test 추가
- [x] painter confirm forecast wait test 추가
- [x] PA0 skip confirm forecast wait test 추가
- [x] 기존 barrier hidden test 유지 확인

## Step 5. Live / Refreeze 확인

- [x] PA0 latest snapshot 저장
- [x] cfd `main.py` 재시작
- [x] fresh XAU confirm/mixed forecast watch 시도
- [x] MT5 unavailable 상태 기록
- [x] PA0 refreeze delta 확인

## Step 6. 문서 체인

- [x] detailed reference
- [x] implementation checklist
- [x] implementation memo
- [x] PA0 delta
