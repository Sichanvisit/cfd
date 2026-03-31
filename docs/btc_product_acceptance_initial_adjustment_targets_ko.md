# BTC Product Acceptance Initial Adjustment Targets

작성일: 2026-03-30 (KST)

## 1. 이번 첫 패스에서 올릴 것

### 1-1. lower recovery importance

대상:

- `lower_rebound_probe_observe`
- `lower_rebound_confirm`
- `probe_scene_id = btc_lower_buy_conservative_probe`

문맥:

- `box_state=BELOW`
- `bb_state=LOWER_EDGE/BREAKDOWN`

목표:

- `3개 체크`

### 1-2. structural rebound importance

대상:

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `probe_scene_id = btc_lower_buy_conservative_probe`

문맥:

- lower / middle reclaim

목표:

- `2개 체크`

### 1-3. mature continuation non-uplift

대상:

- BTC BUY continuation이 upper context에 이미 올라간 장면

목표:

- 기본 `1개 체크`
- 과표시 금지

## 2. 이번 첫 패스에서 유지할 것

아래 BTC 보호장치는 유지한다.

- `btc_lower_probe_downgrade`
- `btc_lower_probe_late_downgrade`
- `btc_lower_structural_cadence_suppressed`
- `btc_lower_probe_cadence_suppressed`

이유:

- 지금은 좋은 자리만 살리는 첫 패스다
- lower probe 남발이 다시 시작되면 BTC는 해석성이 빠르게 무너진다

## 3. 첫 패스 owner

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

이번 단계는 `display importance`만 조정하고,
entry/wait/exit owner는 아직 건드리지 않는다.
