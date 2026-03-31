# Product Acceptance PA1 NAS Middle-Anchor and Upper-Reclaim No-Probe Wait Hide Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

아래 NAS no-probe family를 visible leakage에서 accepted hidden suppression으로 전환한다.

- `NAS100 + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`
- `NAS100 + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe`

관련 상세 문서:

- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 family freeze

- [x] latest PA0 must-hide queue에서 NAS middle-anchor `13` + upper-reclaim `2`가 `15/15`를 채우는지 확인
- [x] live/runtime row에서 no-probe + no importance + directional visible 상태인지 확인

### Step 1. modifier soft-cap policy 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `nas_sell_middle_anchor_wait_hide_without_probe` policy 추가
- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `nas_upper_reclaim_wait_hide_without_probe` policy 추가

### Step 2. build suppression 반영

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) modifier path에서 두 soft-cap apply
- [x] 새 `modifier_primary_reason` surface를 남기기

### Step 3. painter fallback 차단

- [x] [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 에서 두 hidden consumer suppression row를 top-level directional fallback에서 제외

### Step 4. PA0 accepted hidden suppression 추가

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 두 reason 추가
- [x] must-show / must-hide / must-block builder가 이 reason들을 skip하도록 연결

### Step 5. unit tests

- [x] consumer state build hide test 추가
- [x] chart painter hidden fallback skip test 추가
- [x] PA0 hidden suppression skip test 추가

### Step 6. live restart and fresh row verify

- [x] `main.py` restart
- [x] fresh middle-anchor NAS row에서 `nas_sell_middle_anchor_wait_hide_without_probe` 확인
- [x] upper-reclaim direct fresh row는 재발생하지 않았지만 current-build replay에서 `nas_upper_reclaim_wait_hide_without_probe` 확인
- [x] fresh hidden middle-anchor row queue overlap `0` 확인

### Step 7. PA0 refreeze delta

- [x] snapshot 저장
- [x] PA0 latest refreeze
- [x] target NAS family total이 `15 -> 7`로 줄고, upper-reclaim family가 `2 -> 0`으로 빠졌는지 확인
- [x] 다음 replacement backlog를 기록

## 3. 확인 포인트

이 하위축에서 최종적으로 확인해야 할 포인트는 아래다.

- no-probe guard wait row가 wait-check relief로 잘못 올라가지 않는가
- hidden consumer suppression 이후 painter fallback이 directional surface를 다시 그리지 않는가
- PA0에서 queue 이동이 아니라 queue 제외로 처리됐는가

## 4. 다음 단계

이 체크리스트를 닫고 나면 다음 PA1 메인축은 BTC energy-soft-block backlog다.
