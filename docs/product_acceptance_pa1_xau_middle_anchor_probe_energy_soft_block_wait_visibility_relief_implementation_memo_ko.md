# Product Acceptance PA1 XAU Middle Anchor Probe Energy Soft Block Wait Visibility Relief Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`XAUUSD + middle_sr_anchor_required_observe + energy_soft_block + execution_soft_blocked + xau_second_support_buy_probe`
family를 `WAIT + repeated checks` contract로 올리기 위해 policy, consumer state, PA0 skip, 테스트를 묶었다.

관련 문서:

- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 직접 건드린 owner

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. chart wait relief policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`xau_middle_anchor_probe_energy_soft_block_as_wait_checks` policy를 추가했다.

고정 조건:

- `symbol_allow = XAUUSD`
- `side_allow = BUY`
- `observe_reason_allow = middle_sr_anchor_required_observe`
- `blocked_by_allow = energy_soft_block`
- `action_none_allow = execution_soft_blocked`
- `probe_scene_allow = xau_second_support_buy_probe`
- `stage_allow = PROBE, BLOCKED`
- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = xau_middle_anchor_probe_energy_soft_block_as_wait_checks`

### 3-2. consumer state relief 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`xau_middle_anchor_probe_energy_wait_relief` family match를 추가했다.

이 경로는:

- XAU lower-side probe scene이 있고
- blocked 이유가 `energy_soft_block`이며
- second support reclaim importance가 살아 있는 경우

blocked wait scene을 `WAIT + repeated checks` contract로 올릴 준비를 한다.

### 3-3. blocked reason carry

같은 파일에서 relief가 적용될 때
`blocked_display_reason = energy_soft_block`가 유지되도록 정리했다.

그래서 chart/debug surface에서 단순 hidden blocked scene이 아니라
왜 기다림인지 설명 가능한 상태가 된다.

### 3-4. PA0 accepted wait relief 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`xau_middle_anchor_probe_energy_soft_block_as_wait_checks`
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
58 passed
69 passed
12 passed
```

고정한 회귀:

- XAU middle-anchor energy-soft-block family가 current build에서 `WAIT + wait_check_repeat`로 올라가는지
- chart painter가 neutral wait-check marker로 그리는지
- PA0 script가 이 reason을 accepted wait relief로 skip하는지

## 5. live runtime 확인

`main.py`를 새 코드로 다시 올렸다.

- restart log: [cfd_main_restart_20260331_201429.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_201429.out.log)
- restart err log: [cfd_main_restart_20260331_201429.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_201429.err.log)

post-restart fresh row 요약:

- total fresh rows after restart = `6`
- exact XAU target family recurrence = `0`
- exact BTC structural family recurrence = `0`

즉 restart는 정상인데, 이번 exact target family는 fresh window에서 아직 다시 나오지 않았다.

대신 representative row `2026-03-31T20:07:25`를 current build에 replay하면 아래처럼 나온다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `display_score = 0.75`
- `display_repeat_count = 1`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_middle_anchor_probe_energy_soft_block_as_wait_checks`
- `blocked_display_reason = energy_soft_block`

즉 current build 기준 contract 자체는 맞게 연결된 상태다.

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_201555.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_201555.json)
- 최신 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

generated_at:

- snapshot = `2026-03-31T20:09:05`
- latest = `2026-03-31T20:15:55`

baseline summary:

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_block_candidate_count = 12 -> 12`

target family delta:

- `must_show_missing = 11 -> 10`
- `must_block_candidates = 3 -> 7`

이 수치는 구현 효과의 direct proof가 아니라
fresh exact recurrence가 아직 없어서 recent window의 old backlog 조합이 계속 바뀐 결과다.

즉 이번 refreeze는 “구현 실패”가 아니라
“코드는 준비됐지만 exact family가 아직 fresh row로 다시 안 나왔다”로 해석하는 게 맞다.

## 7. 같이 본 추가 신호

계좌 상태 변경 이후 같이 본 결과는 아래와 같다.

- BTC structural exact family도 post-restart fresh recurrence는 아직 `0`
- 현재 fresh BTC는 `outer_band_guard + probe_not_promoted` 또는 `lower_rebound_probe + energy_soft_block` 쪽이 먼저 뜬다
- XAU old `lower_rebound_probe + forecast_guard + probe_not_promoted + xau_second_support_buy_probe` family는 current queue에서 `0`

즉 현재 실제 reopen point는 old XAU forecast family가 아니라
fresh recurrence를 기다리는 XAU middle-anchor energy family와
current must-hide main family다.

## 8. 한 줄 요약

```text
이번 XAU 하위축은 구현과 회귀는 끝났고 representative replay도 성공했다.
다만 post-restart fresh window에서 exact target family가 아직 다시 안 나와,
PA0 queue는 old backlog 조합 기준으로만 움직이고 있는 상태다.
```
