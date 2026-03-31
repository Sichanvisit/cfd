# XAU Product Acceptance Initial Adjustment Targets

작성일: 2026-03-30 (KST)

## 1. 이번 첫 패스에서 올릴 것

### 1-1. lower recovery importance

대상:

- `lower_rebound_confirm`
- `lower_rebound_probe_observe`

문맥:

- `box_state=BELOW`
- `bb_state=LOWER_EDGE/BREAKDOWN`

목표:

- `3개 체크`

### 1-2. second support importance

대상:

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `probe_scene_id = xau_second_support_buy_probe`

문맥:

- middle / lower reclaim

목표:

- `2개 체크`

### 1-3. upper reject importance

대상:

- `upper_reject_probe_observe`
- `upper_reject_confirm`
- `upper_reject_mixed_confirm`
- `upper_break_fail_confirm`
- `probe_scene_id = xau_upper_sell_probe`

문맥:

- upper / upper-edge

목표:

- 핵심 confirm은 `3개 체크`
- 나머지 upper reject 전개는 `2개 체크`

## 2. 이번 첫 패스에서 유지할 것

아래 XAU 억제 규칙은 유지한다.

- `xau_upper_reject_guard_wait_hidden`
- `xau_upper_reject_cadence_suppressed`
- `xau_upper_sell_repeat_suppressed`
- `xau_middle_anchor_cadence_suppressed`

이유:

- 지금은 좋은 자리만 살리는 첫 패스다
- 상단 과표시를 다시 열어버리면 XAU는 금방 난잡해질 수 있다

## 3. 첫 패스 owner

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

이번 단계는 `display importance`만 조정하고,
entry/wait/exit owner는 아직 건드리지 않는다.
