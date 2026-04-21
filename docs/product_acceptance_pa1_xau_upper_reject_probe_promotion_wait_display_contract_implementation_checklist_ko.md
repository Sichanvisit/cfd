# Product Acceptance PA1 XAU Upper-Reject Probe Promotion Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## Step 0. Baseline target 고정

- [x] PA0 latest에서 target family가 `must_show 15`, `must_block 5`를 채우는지 확인
- [x] recent raw row가 `xau_upper_reject_cadence_suppressed`로 숨는지 확인

## Step 1. Policy contract 추가

- [x] `chart_wait_reliefs`에 `xau_upper_reject_probe_promotion_wait_as_wait_checks` 추가
- [x] 조건을 `XAUUSD / SELL / upper_reject_probe_observe / probe_promotion_gate / probe_not_promoted / xau_upper_sell_probe / PROBE`로 고정

## Step 2. Build path 반영

- [x] `consumer_check_state.py`에 `xau_upper_reject_probe_promotion_wait_relief` bool 추가
- [x] build 단계에서 `blocked_display_reason = probe_promotion_gate`가 유지되게 반영

## Step 3. Resolve path 반영

- [x] repeated runtime용 `xau_upper_reject_probe_promotion_wait_repeat_relief` 추가
- [x] `xau_upper_reject_cadence_suppressed` 예외에 새 relief를 포함

## Step 4. PA0 accepted reason 반영

- [x] `product_acceptance_pa0_baseline_freeze.py` accepted wait-check reason set에 새 reason 추가

## Step 5. 회귀 잠금

- [x] `test_consumer_check_state.py` build test 추가
- [x] `test_consumer_check_state.py` resolve test 추가
- [x] `test_chart_painter.py` wait overlay test 추가
- [x] `test_product_acceptance_pa0_baseline_freeze.py` queue skip test 추가

## Step 6. 검증 실행

- [x] `pytest -q tests/unit/test_consumer_check_state.py`
- [x] `pytest -q tests/unit/test_chart_painter.py`
- [x] `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

## Step 7. Live 확인

- [x] `cfd main.py` 재시작
- [x] fresh exact row `2026-04-01T01:16:23`에서 새 reason 확인

## Step 8. PA0 refreeze

- [x] snapshot 보존 후 baseline refreeze 실행
- [x] target family delta 기록
