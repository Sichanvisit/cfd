# Product Acceptance PA1 BTC Lower Rebound Probe Energy Soft Block Wait Visibility Relief Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`BTCUSD + lower_rebound_probe_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
family를 `hidden blocked scene`에서
`WAIT + repeated checks` chart contract로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 family freeze

- [x] latest PA0 queue에서 BTC lower rebound energy-soft-block family가 must-show / must-block를 채우는지 확인
- [x] live/runtime row에서 probe-ready but blocked hidden 상태인지 확인

### Step 1. policy axis 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `btc_lower_rebound_probe_energy_soft_block_as_wait_checks` relief 추가
- [x] `symbol / side / observe_reason / blocked_by / action_none_reason / probe_scene` 조건을 고정

### Step 2. common modifier 매칭 확장

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) relief match path에서 `probe_scene_allow`를 읽도록 확장
- [x] BTC target family boolean helper를 추가

### Step 3. blanket blocked hide 예외

- [x] `probe_ready_but_blocked` blanket hide에서 BTC target family를 예외 처리
- [x] final stage를 `PROBE`로 살릴 수 있게 연결

### Step 4. blocked reason carry

- [x] relief가 적용될 때 `blocked_display_reason = energy_soft_block`가 남도록 정리

### Step 5. PA0 accepted wait relief 추가

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait relief reason으로 추가

### Step 6. unit tests

- [x] consumer state build test 추가
- [x] effective consumer state test 추가
- [x] chart painter neutral wait-check render test 추가
- [x] PA0 skip test 추가

### Step 7. live restart and fresh row verify

- [x] `main.py` restart
- [x] fresh BTC row에서 nested `WAIT + wait_check_repeat` 확인
- [x] fresh row와 PA0 queue overlap이 `0`인지 확인

### Step 8. PA0 refreeze delta

- [x] snapshot 저장
- [x] PA0 latest refreeze
- [x] total count가 그대로인 이유를 old hidden backlog로 해석

## 3. 확인 포인트

이 하위축에서 최종적으로 확인해야 할 포인트는 아래다.

- fresh row는 queue에서 빠졌는가
- 차트는 “BUY로 과장”되지 않고 “WAIT + repeated checks”로 보이는가
- backlog 때문에 total count가 유지된 것과 fresh exclusion 성공을 구분해서 기록했는가

## 4. 다음 단계

이 체크리스트를 닫고 나면 다음 PA1 메인축은 NAS no-probe leakage 정리다.
