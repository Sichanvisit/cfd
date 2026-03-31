# Product Acceptance PA1 NAS Upper-Reject Probe Forecast Wait Display Contract Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`
family를 visible leakage에서 accepted `WAIT + wait_check_repeat` contract로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 freeze

- [x] confirm no-probe 축을 닫은 뒤 probe forecast family가 다음 upper-reject backlog인지 확인
- [x] representative row가 `PROBE + display_ready=True + scene_probe 있음`인지 확인

### Step 1. wait policy 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `nas_upper_reject_probe_forecast_wait_as_wait_checks` 추가

### Step 2. consumer modifier 반영

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서 target family를 wait contract로 surface
- [x] `blocked_display_reason` carry 유지

### Step 3. PA0 wait relief allow-list 추가

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 reason 추가

### Step 4. 회귀 테스트

- [x] consumer state wait relief test 추가
- [x] resolve effective wait relief test 추가
- [x] painter neutral wait rendering test 추가
- [x] PA0 wait relief skip test 추가

### Step 5. live/runtime 확인

- [x] `main.py` restart
- [x] exact fresh recurrence가 아직 `0`임을 확인
- [x] representative historical row current-build replay로 wait contract 확인

### Step 6. PA0 refreeze follow-up

- [x] latest baseline refreeze
- [x] target family가 latest queue에서 얼마나 남는지 기록
- [x] fresh recurrence 부재 때문에 old backlog가 남아 있다는 해석까지 기록

## 3. 확인 포인트

- target family가 hidden suppression으로 잘못 내려가지 않는가
- `blocked_display_reason = forecast_guard`가 유지되는가
- fresh exact row가 다시 생기면 PA0 queue에서 빠질 준비가 된 상태인가

## 4. 다음 단계

이 축 다음 main backlog는
`probe_promotion_gate` upper-reject family다.
