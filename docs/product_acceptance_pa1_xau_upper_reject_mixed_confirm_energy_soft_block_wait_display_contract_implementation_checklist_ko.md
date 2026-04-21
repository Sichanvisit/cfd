# Product Acceptance PA1 XAU Upper-Reject Mixed Confirm Energy Soft-Block Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Family 고정

- [x] target family를 `XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`로 고정
- [x] representative backlog row 시간 확인

## Step 1. Policy contract 추가

- [x] `xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks` policy 추가
- [x] `event_kind_hint = WAIT`
- [x] `display_mode = wait_check_repeat`
- [x] `display_reason = xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

## Step 2. Build / Resolve 보강

- [x] energy-soft-block blocked reason carry 추가
- [x] representative replay에서 build / resolve contract 유지 확인

## Step 3. PA0 accepted queue 정렬

- [x] accepted wait-check reason set 추가
- [x] must-show / must-hide / must-block skip test 추가

## Step 4. 회귀 테스트

- [x] `tests/unit/test_consumer_check_state.py`
- [x] `tests/unit/test_chart_painter.py`
- [x] `tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

## Step 5. Live 확인

- [x] cfd `main.py` 재시작
- [x] fresh XAU row watch
- [x] exact target fresh row 확인

## Step 6. Delta 기록

- [x] representative replay 결과 기록
- [x] PA0 refreeze delta 기록
- [x] 상위 memo / roadmap / handoff 링크 추가
