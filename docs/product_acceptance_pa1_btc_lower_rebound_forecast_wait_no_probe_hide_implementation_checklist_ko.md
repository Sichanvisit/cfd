# Product Acceptance PA1 BTC Lower-Rebound Forecast-Wait No-Probe Hide Implementation Checklist

작성일: 2026-03-31 (KST)

## 1. 목표

`BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`
family를 visible leakage에서
accepted hidden suppression으로 전환한다.

관련 상세 문서:

- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md)

## 2. 구현 체크리스트

### Step 0. 대상 family freeze

- [x] latest PA0 must-hide queue에서 BTC forecast-wait no-probe family가 `15/15`를 채우는지 확인
- [x] live/runtime row와 recent csv row에서 `PROBE + display_ready=True + btc_lower_recovery_start + no_probe` 상태인지 확인

### Step 1. modifier soft-cap policy 추가

- [x] [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `btc_lower_rebound_forecast_wait_hide_without_probe` policy 추가
- [x] 조건을 `BTCUSD + BUY + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe + btc_lower_recovery_start`로 고정

### Step 2. build suppression 반영

- [x] [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) modifier path에서 새 soft-cap apply
- [x] `modifier_primary_reason = btc_lower_rebound_forecast_wait_hide_without_probe` surface를 남기기

### Step 3. painter fallback 차단

- [x] [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 에서 hidden consumer suppression row는 top-level BUY fallback도 그리지 않게 처리

### Step 4. PA0 accepted hidden suppression 추가

- [x] [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted hidden suppression reason set 추가
- [x] must-show / must-hide / must-block builder가 이 reason을 skip하도록 연결

### Step 5. unit tests

- [x] consumer state build hide test 추가
- [x] chart painter hidden fallback skip test 추가
- [x] PA0 hidden suppression skip test 추가

### Step 6. live restart and fresh row verify

- [x] `main.py` restart
- [ ] post-restart window에서는 exact target family fresh row가 재발생하지 않아 direct live row 증빙은 보류
- [x] post-restart BTC fresh rows가 이미 다른 family(`energy_soft_block`, `probe_promotion_gate`)로 이동했는지 확인
- [x] representative historical queue row current-build replay에서 `modifier_primary_reason = btc_lower_rebound_forecast_wait_hide_without_probe` 확인

### Step 7. PA0 refreeze delta

- [x] snapshot 저장
- [x] PA0 latest refreeze
- [x] target BTC family가 queue에서 `15 -> 0`으로 빠졌는지 확인
- [x] total must-hide가 그대로면 replacement family를 기록

## 3. 확인 포인트

이 하위축에서 최종적으로 확인해야 할 포인트는 아래다.

- 중요도 source가 있다고 해서 no-probe forecast wait row가 directional probe로 과상승하지 않는가
- hidden consumer suppression 이후 painter fallback이 BUY probe/observe를 다시 그리지 않는가
- PA0에서 queue 이동이 아니라 queue 제외로 처리됐는가

## 4. 다음 단계

이 체크리스트를 닫고 나면 다음 PA1 메인축은 refreeze 결과 기준으로 다시 잡는다.
