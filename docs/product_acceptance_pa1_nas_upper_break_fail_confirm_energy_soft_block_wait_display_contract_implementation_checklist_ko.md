# Product Acceptance PA1 NAS Upper-Break-Fail Confirm Energy Soft-Block Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. 타겟 고정

- [x] PA0 latest에서 target family가 `must_block 12`를 채우는지 확인
- [x] recent raw row가 `display_ready=True / check_stage=BLOCKED / chart contract blank` 상태인지 확인

## Step 1. Policy contract 추가

- [x] `chart_wait_reliefs`에 `nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks` 추가
- [x] 조건을 `NAS100 / SELL / upper_break_fail_confirm / energy_soft_block / execution_soft_blocked / no probe / BLOCKED`로 고정

## Step 2. Consumer carry 보강

- [x] `blocked_display_reason = energy_soft_block`가 build path에서 유지되도록 보강

## Step 3. PA0 accepted reason 반영

- [x] `product_acceptance_pa0_baseline_freeze.py` accepted wait-check reason set에 새 reason 추가

## Step 4. 회귀 잠금

- [x] `test_consumer_check_state.py` build test 추가
- [x] `test_consumer_check_state.py` resolve test 추가
- [x] `test_chart_painter.py` wait overlay test 추가
- [x] `test_product_acceptance_pa0_baseline_freeze.py` queue skip test 추가

## Step 5. 검증

- [x] `pytest -q tests/unit/test_consumer_check_state.py`
- [x] `pytest -q tests/unit/test_chart_painter.py`
- [x] `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

## Step 6. Live 확인

- [x] `cfd main.py` 재시작
- [ ] fresh exact `energy_soft_block` row에서 새 reason 직접 확인

## Step 7. PA0 refreeze

- [x] snapshot 보존 후 baseline refreeze 실행
- [x] live recurrence pending 상태에서 delta 해석 기록
