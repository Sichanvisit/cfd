# Product Acceptance PA1 NAS Upper-Reject Probe Promotion Wait Display Contract Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
family를 visible leakage에서 accepted `WAIT + wait_check_repeat` contract로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 freeze

- [x] latest PA0 must-hide queue에서 target family가 main axis인지 확인
- [x] representative row가 `PROBE + scene_probe 있음 + probe_promotion_gate`인지 확인

### Step 1. wait policy 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `nas_upper_reject_probe_promotion_wait_as_wait_checks` 추가

### Step 2. consumer modifier 반영

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 target family wait relief 추가
- [x] `blocked_display_reason = probe_promotion_gate` carry 유지

### Step 3. PA0 wait relief allow-list 추가

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 reason 추가

### Step 4. 회귀 테스트

- [x] consumer state build test 추가
- [x] resolve effective wait relief test 추가
- [x] painter neutral wait rendering test 추가
- [x] PA0 wait relief skip test 추가

### Step 5. live/runtime 확인

- [x] `main.py` restart
- [x] recent 240-row에 old exact rows 5개가 남아 있고 chart contract는 비어 있음을 확인
- [x] post-restart fresh exact recurrence는 아직 `0`임을 확인
- [x] representative current-build replay로 wait contract 확인

### Step 6. PA0 refreeze delta

- [x] pre-refreeze snapshot 보존
- [x] latest baseline refreeze
- [x] target family 변화와 replacement backlog 기록

## 3. 확인 포인트

- target family가 hidden suppression으로 잘못 내려가지 않는가
- painter가 neutral wait checks로 렌더하는가
- fresh recurrence 부재 때문에 old backlog가 남는 상태를 문서에 분리해 두었는가

## 4. 다음 단계

이 축 다음 must-hide main axis는
`NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`다.
