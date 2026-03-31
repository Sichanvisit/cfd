# Product Acceptance PA1 XAU Upper Reject Probe Energy Soft Block Wait Visibility Relief Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`XAUUSD + upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
family를 숨김 대상으로 두지 않고
`WAIT + repeated checks` chart contract로 연결했다.

관련 기준 문서:

- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 직접 건드린 owner 범위

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

이번 단계에서 하지 않은 범위:

- BTC mirror family 수정
- NAS leakage 수정
- entry / hold / exit acceptance 수정

## 3. 구현 내용

### 3-1. chart wait relief policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`xau_upper_reject_probe_energy_soft_block_as_wait_checks`
policy를 추가했다.

고정 조건:

- `symbol_allow = XAUUSD`
- `side_allow = SELL`
- `observe_reason_allow = upper_reject_probe_observe`
- `blocked_by_allow = energy_soft_block`
- `action_none_allow = execution_soft_blocked`
- `probe_scene_allow = xau_upper_sell_probe`
- `stage_allow = PROBE, BLOCKED`
- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = xau_upper_reject_probe_energy_soft_block_as_wait_checks`

### 3-2. probe-ready blocked 숨김 예외

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
이번 family는 `probe_ready_but_blocked` 숨김 경계에서 빼고,
probe stage를 유지하도록 조정했다.

즉 의미는 그대로다.

- scene은 살아 있음
- entry는 아님
- energy soft block으로 wait

### 3-3. blocked reason carry

visible wait relief가 되었더라도
`blocked_display_reason = energy_soft_block`
가 남도록 정리했다.

그래서 chart/debug surface에서
왜 기다리는지 읽을 수 있다.

### 3-4. PA0 accepted wait relief 정렬

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
새 `chart_display_reason`을 accepted wait relief set에 추가했다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
48 passed
62 passed
5 passed
```

고정된 핵심 확인점:

- XAU energy-soft-block probe family가 visible wait relief로 남는지
- chart painter가 neutral repeated wait marker로 그리는지
- PA0 script가 새 relief reason을 accepted wait relief로 skip하는지

## 5. live runtime 확인

`main.py`를 새 코드로 재시작했다.

- process start: `2026-03-31 17:36:21`
- PID: `26104`

재시작 이후 확인 결과:

- rows since restart: `46`
- per symbol: `NAS100 16 / XAUUSD 15 / BTCUSD 15`

fresh target rows:

- `2026-03-31T17:38:12`
- `2026-03-31T17:38:51`
- `2026-03-31T17:39:01`

이 row들은 top-level CSV chart fields는 비어 있었지만,
nested [consumer_check_state_v1](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv) 안에는 아래 contract가 실제로 찍혔다.

- `check_stage = PROBE`
- `check_display_ready = True`
- `display_score = 0.86`
- `display_repeat_count = 2`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_energy_soft_block_as_wait_checks`

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_173619.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_173619.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

새 baseline generated_at:

- `2026-03-31T17:40:36`

핵심 변화:

- XAU energy-soft-block must-show family: `14 -> 10`
- XAU energy-soft-block must-block family: `7 -> 0`
- must-enter candidate count: `0 -> 6`
- divergence seed count: `1 -> 0`

즉 fresh accepted wait relief row는 실제로 queue에서 빠졌다.
다만 recent 120-row window 안에 재시작 전 old hidden row가 아직 남아 있어서
must-show 총량 `15`는 그대로다.

추가 확인:

- nested target row times `17:38:12 / 17:38:51 / 17:39:01`
- casebook queue overlap: `0`

## 7. current reopen point

이번 하위축이 반영된 뒤
다음 PA1 reopen point는 아래 둘로 좁혀졌다.

1. `BTCUSD + lower_rebound_probe_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
2. `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`

현재 baseline 기준으로는
must-show / must-block 쪽에서 1번,
must-hide 쪽에서 2번이 새 메인 문제다.

## 8. 한 줄 요약

```text
이번 PA1 하위축으로 XAU upper reject probe energy-soft-block family는
live에서 실제 WAIT + repeated checks contract를 찍기 시작했고,
fresh row는 PA0 queue에서 빠졌다.
지금 남아 있는 것은 old hidden row 잔존분과 다음 BTC/NAS family다.
```
