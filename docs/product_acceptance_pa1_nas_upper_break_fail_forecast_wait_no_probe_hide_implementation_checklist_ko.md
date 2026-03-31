# Product Acceptance PA1 NAS Upper-Break-Fail Forecast Wait No-Probe Hide Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`
family를 visible leakage에서 accepted hidden suppression으로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 freeze

- [x] latest PA0 must-hide queue에서 target family가 main axis인지 확인
- [x] representative backlog row와 current-build stage 차이를 확인

### Step 1. hide policy 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `nas_upper_break_fail_wait_hide_without_probe` 추가

### Step 2. consumer modifier 반영

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 hidden suppression soft-cap 추가
- [x] `modifier_primary_reason` surface 유지

### Step 3. painter / PA0 연결

- [x] [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에 hidden suppression reason 추가
- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 allow-list 추가

### Step 4. 회귀 테스트

- [x] consumer state hide test 추가
- [x] painter hidden fallback skip test 추가
- [x] PA0 hidden suppression skip test 추가

### Step 5. live/runtime 확인

- [x] `main.py` restart
- [x] recent 240-row에 old exact rows 5개가 남아 있고 chart contract는 비어 있음을 확인
- [x] post-restart fresh exact recurrence는 아직 `0`임을 확인
- [x] current-build replay로 hidden suppression 확인

### Step 6. PA0 refreeze delta

- [x] pre-refreeze snapshot 보존
- [x] latest baseline refreeze
- [x] target family 변화와 replacement backlog 기록

## 3. 확인 포인트

- target family가 wait relief로 잘못 올라가지 않는가
- hidden suppression 이후 painter fallback이 차단되는가
- fresh recurrence 부재 때문에 target queue가 아직 남아 있는 상태를 분리해서 기록했는가

## 4. 다음 단계

이 축 다음 PA1 메인축은
`NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
must-show/must-block backlog다.
