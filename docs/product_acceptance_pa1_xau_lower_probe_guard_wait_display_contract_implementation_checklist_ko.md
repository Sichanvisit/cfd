# Product Acceptance PA1 XAU Lower Probe Guard Wait Display Contract Implementation Checklist

작성일: 2026-04-01 (KST)

## 목표

`XAUUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + xau_second_support_buy_probe`
family를 `WAIT + wait_check_repeat` contract로 올린다.

관련 상세 문서:

- [product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_detailed_reference_ko.md)

## 구현 체크리스트

### Step 0. 대표 row 확인

- [x] fresh exact row 존재 확인
- [x] stored state가 `chart_display_reason = ""`라서 must-hide로 남는 점 확인

### Step 1. contract 추가

- [x] `chart_flow_policy.py`에 `xau_lower_probe_guard_wait_as_wait_checks` 추가
- [x] `consumer_check_state.py`에 blocked-display carry 추가
- [x] `product_acceptance_pa0_baseline_freeze.py` accepted wait reason 목록 갱신

### Step 2. 테스트

- [x] build test 추가
- [x] resolve test 추가
- [x] painter rendering test 추가
- [x] PA0 skip test 추가

### Step 3. live / refreeze

- [x] `main.py` restart
- [x] representative replay 확인
- [x] PA0 refreeze 재실행
- [x] post-restart exact recurrence 부재를 기록
