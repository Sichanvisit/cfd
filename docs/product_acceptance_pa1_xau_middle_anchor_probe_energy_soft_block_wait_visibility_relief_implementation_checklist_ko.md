# Product Acceptance PA1 XAU Middle Anchor Probe Energy Soft Block Wait Visibility Relief Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`XAUUSD + middle_sr_anchor_required_observe + energy_soft_block + execution_soft_blocked + xau_second_support_buy_probe`
family를 hidden blocked scene이 아니라
`WAIT + repeated checks` chart contract로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 family freeze

- [x] latest PA0 queue에서 XAU middle-anchor energy-soft-block family가 must-show / must-block main axis로 떠 있는지 확인
- [x] representative row replay 기준으로 current build가 wait relief contract를 만들 수 있는지 확인

### Step 1. policy axis 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `xau_middle_anchor_probe_energy_soft_block_as_wait_checks` relief 추가
- [x] `symbol / side / observe_reason / blocked_by / action_none_reason / probe_scene` 조건 고정

### Step 2. consumer state 연결

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 `xau_middle_anchor_probe_energy_wait_relief` family match 추가
- [x] relief 시 `blocked_display_reason = energy_soft_block` carry 정리

### Step 3. PA0 accepted wait relief 정리

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait relief reason 추가

### Step 4. unit tests

- [x] consumer state build test 추가
- [x] effective consumer state test 추가
- [x] chart painter neutral wait-check render test 추가
- [x] PA0 skip test 추가

### Step 5. test verify

- [x] `pytest -q tests/unit/test_consumer_check_state.py`
- [x] `pytest -q tests/unit/test_chart_painter.py`
- [x] `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

### Step 6. live restart

- [x] `main.py` restart
- [x] restart 이후 fresh rows 유입 확인
- [x] exact target family recurrence가 아직 `0건`임을 기록

### Step 7. runtime verification

- [x] representative row `2026-03-31T20:07:25` current-build replay 확인
- [x] replay 결과가 `WAIT + wait_check_repeat + xau_middle_anchor_probe_energy_soft_block_as_wait_checks`인지 기록

### Step 8. PA0 refreeze delta

- [x] snapshot 저장
- [x] latest refreeze
- [x] total queue 미감소 원인이 fresh recurrence 부재와 old backlog 잔존임을 해석

## 3. 확인 사인

이번 하위축에서 최종 확인할 사인은 아래와 같다.

- representative row replay는 성공했는가
- PA0 script는 이 reason을 accepted wait relief로 skip하는가
- post-restart fresh exact family 부재가 로그에 남아 있는가

## 4. 다음 단계

이 체크리스트를 닫고 나면 다음은 둘 중 하나다.

1. XAU exact target recurrence를 한 번 더 본다
2. current must-hide main family를 다음 PA1 축으로 진행한다
