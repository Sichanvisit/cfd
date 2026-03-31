# Product Acceptance PA1 BTC Lower Rebound Probe Energy Soft Block Wait Visibility Relief Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`BTCUSD + lower_rebound_probe_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
family를 숨김 blocked scene이 아니라
`WAIT + repeated checks` contract로 연결했다.

관련 기준 문서:

- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 직접 건드린 owner 범위

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

이번 단계에서 일부러 건드리지 않은 범위:

- NAS no-probe leakage 정리
- entry / wait / hold / exit acceptance
- threshold-only broad retune

## 3. 구현 내용

### 3-1. chart wait relief policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`btc_lower_rebound_probe_energy_soft_block_as_wait_checks`
policy를 추가했다.

고정 조건:

- `symbol_allow = BTCUSD`
- `side_allow = BUY`
- `observe_reason_allow = lower_rebound_probe_observe`
- `blocked_by_allow = energy_soft_block`
- `action_none_allow = execution_soft_blocked`
- `probe_scene_allow = btc_lower_buy_conservative_probe`
- `stage_allow = PROBE, BLOCKED`
- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = btc_lower_rebound_probe_energy_soft_block_as_wait_checks`

### 3-2. probe-ready blocked blanket hide 예외

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
BTC target family를 `probe_ready_but_blocked` blanket hide 예외로 분리했다.

즉 의미는 아래다.

- probe는 살아 있다
- entry는 아직 아니다
- energy soft block 때문에 기다린다

그래서 stage를 아예 죽이지 않고 `PROBE` wait scene으로 surface에 남긴다.

### 3-3. blocked reason carry

relief가 적용될 때
`blocked_display_reason = energy_soft_block`
가 남도록 정리했다.

그래서 차트와 debug surface에서
“왜 기다림인지”를 읽을 수 있다.

### 3-4. PA0 accepted wait relief 정리

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`btc_lower_rebound_probe_energy_soft_block_as_wait_checks`
reason을 accepted wait relief set으로 추가했다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
50 passed
63 passed
6 passed
```

고정한 확인 포인트:

- BTC energy-soft-block probe family가 visible wait relief로 뜨는지
- chart painter가 neutral repeated wait marker로 그리는지
- PA0 script가 이 reason을 accepted wait relief로 skip하는지

## 5. live runtime 확인

`main.py`를 새 코드로 다시 시작했다.

- restart log: [cfd_main_restart_20260331_175619.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_175619.out.log)
- restart err log: [cfd_main_restart_20260331_175619.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_175619.err.log)

fresh nested target rows:

- `2026-03-31T17:57:21`
- `2026-03-31T17:57:30`
- `2026-03-31T17:57:41`
- `2026-03-31T17:57:54`

대표 row에서 nested `consumer_check_state_v1` 계약은 실제로 아래처럼 찍혔다.

- `check_stage = PROBE`
- `check_display_ready = True`
- `display_score = 0.91`
- `display_repeat_count = 3`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_lower_rebound_probe_energy_soft_block_as_wait_checks`

주의:

top-level CSV `chart_event_kind_hint / chart_display_mode / chart_display_reason`는 아직 빈 칸일 수 있다.
이번 확인은 nested `consumer_check_state_v1` 기준으로 했다.

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_175617.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_175617.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest baseline generated_at:

- `2026-03-31T17:57:59`

핵심 해석:

- fresh BTC relief rows는 queue overlap이 `0`이었다
- 즉 새 contract는 실제 fresh row에서 먹었다
- total `must_show = 15`, `must_block = 12`가 그대로인 이유는
  restart 이전 old hidden BTC row가 recent 120-row window에 아직 남아 있기 때문이다

current queue composition:

- `must_show 15/15 = BTC lower_rebound_probe_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
- `must_block 12/12 = 같은 BTC family`
- `must_hide 15/15 = NAS outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`

즉 fresh exclusion은 성공했고, backlog 때문에 total count가 아직 남아 있는 상태다.

## 7. current reopen point

이번 하위축이 반영된 뒤 다음 PA1 reopen point는 아래다.

1. `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`
2. old hidden BTC backlog가 recent window에서 자연 교체되는지 재확인

즉 메인 문제축은 이제 must-hide 쪽 NAS no-probe leakage다.

## 8. 한 줄 요약

```text
이번 PA1 하위축으로 BTC lower rebound energy-soft-block family가 fresh row 기준으로는 실제 WAIT + repeated checks contract로 살아났고,
PA0 queue overlap도 0으로 확인됐다. 지금 남아 있는 must-show / must-block은 old hidden backlog와 다음 NAS leakage 축이다.
```
