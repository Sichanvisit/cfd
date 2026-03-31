# Product Acceptance PA1 NAS Upper-Reject Confirm Forecast Wait No-Probe Hide Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`NAS100 + upper_reject_confirm + forecast_guard + observe_state_wait + no_probe`
family를 visible leakage에서 accepted hidden suppression으로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 freeze

- [x] latest PA0 must-hide queue에서 target family가 남아 있는지 확인
- [x] representative row가 `display_ready=True + no-probe + forecast_guard` surface인지 확인

### Step 1. policy 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `nas_upper_reject_wait_hide_without_probe` 추가

### Step 2. consumer modifier 반영

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서 target family를 hidden suppression으로 내리기
- [x] `modifier_primary_reason` surface 유지

### Step 3. painter fallback 차단

- [x] [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에 hidden suppression reason 추가

### Step 4. PA0 hidden suppression allow-list 추가

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 reason 추가

### Step 5. 회귀 테스트

- [x] consumer state hide test 추가
- [x] painter hidden fallback skip test 추가
- [x] PA0 hidden suppression skip test 추가

### Step 6. live/runtime 확인

- [x] `main.py` restart
- [x] exact fresh row recurrence가 없음을 확인
- [x] representative historical row current-build replay로 hidden suppression 확인

### Step 7. PA0 refreeze delta

- [x] pre-change snapshot 보존
- [x] latest baseline refreeze
- [x] target family가 latest queue에서 `0`으로 내려갔는지 확인
- [x] replacement backlog 기록

## 3. 확인 포인트

- no-probe confirm wait row가 `WAIT relief`로 올라가지 않는가
- hidden suppression 이후 painter fallback이 다시 방향성을 그리지 않는가
- latest PA0 queue에서 confirm no-probe family가 실제로 빠졌는가

## 4. 다음 단계

이 체크리스트를 닫은 뒤에는 같은 upper-reject 축의
`probe + forecast_guard` family를 follow-up으로 이어간다.
