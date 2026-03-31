# Product Acceptance PA1 BTC Lower Probe Promotion Wait Display Contract Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`BTCUSD + lower_rebound_probe_observe + probe_promotion_gate + probe_not_promoted + btc_lower_buy_conservative_probe`
family를 `accepted wait display contract`로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 family freeze

- [x] latest PA0 queue에서 BTC lower probe promotion family가 must-hide main axis인지 확인
- [x] representative row replay 기준으로 이 family가 이미 `display_ready=True / PROBE`인지 확인

### Step 1. policy axis 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `btc_lower_probe_promotion_wait_as_wait_checks` relief 추가
- [x] `symbol / side / observe_reason / blocked_by / action_none_reason / probe_scene / stage` 조건 고정

### Step 2. consumer state 연결

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 `btc_lower_probe_promotion_wait_relief` family match 추가
- [x] `blocked_display_reason = probe_promotion_gate` carry 정리

### Step 3. PA0 accepted wait relief 정리

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait relief reason 추가

### Step 4. unit tests

- [x] consumer state build test 추가
- [x] effective consumer state test 추가
- [x] chart painter neutral wait render test 추가
- [x] PA0 skip test 추가

### Step 5. test verify

- [x] `pytest -q tests/unit/test_consumer_check_state.py`
- [x] `pytest -q tests/unit/test_chart_painter.py`
- [x] `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

### Step 6. live restart

- [x] `main.py` restart
- [x] fresh runtime row 유입 확인
- [x] exact target family post-restart recurrence가 바로는 `0건`임을 기록

### Step 7. runtime verification

- [x] representative row `2026-03-31T20:11:43` current-build replay 확인
- [x] replay가 `WAIT + wait_check_repeat`와 `probe_promotion_gate` blocked reason을 만드는지 기록

### Step 8. PA0 refreeze delta

- [x] snapshot 저장
- [x] latest refreeze
- [x] target must-hide leakage가 `10 -> 0`으로 빠졌는지 기록

## 3. 확인 사인

이번 하위축의 확인 사인은 아래와 같다.

- representative row replay가 성공했는가
- PA0 script가 해당 reason을 accepted wait relief로 skip하는가
- latest refreeze에서 target must-hide leakage가 실제로 사라졌는가

## 4. 다음 단계

이 체크리스트를 닫고 나면 다음은 current must-hide main family인 NAS upper-reject 축이다.
