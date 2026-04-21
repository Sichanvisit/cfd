# Product Acceptance PA1 XAU Upper-Reject Mixed Forecast Wait Visibility Relief Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Family 고정

- [x] `XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait +` family 고정
- [x] representative hidden row replay 확인

## Step 1. Policy 확장

- [x] `xau_upper_reject_mixed_guard_wait_as_wait_checks`의 `blocked_by_allow` 확장
- [x] 기존 reason 재사용 방침 고정

## Step 2. Build path 확장

- [x] `xau_upper_reject_mixed_guard_wait_relief`가 `forecast_guard`도 받도록 수정
- [x] `blocked_display_reason` carry 추가

## Step 3. Resolve path 보호

- [x] `xau_upper_reject_late_hidden` 예외 확장
- [x] cadence suppression repeat relief 추가

## Step 4. 회귀 테스트

- [x] build forecast mixed test 추가
- [x] resolve forecast mixed test 추가
- [x] painter forecast mixed test 추가
- [x] PA0 skip forecast mixed test 추가

## Step 5. Live / PA0 확인

- [x] cfd `main.py` 재시작
- [x] fresh XAU watch
- [x] PA0 refreeze delta 확인

## Step 6. 문서 체인

- [x] detailed reference
- [x] implementation checklist
- [x] implementation memo
- [x] PA0 delta
