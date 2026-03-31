# Product Acceptance PA1 BTC Structural Probe Energy Soft Block Wait Visibility Relief Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`BTCUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
family를 `hidden blocked scene`이 아니라 `WAIT + repeated checks` contract로 올릴 수 있도록 policy, consumer state, PA0 skip, 테스트를 묶었다.

관련 문서:

- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_structural_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_structural_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

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
`btc_structural_probe_energy_soft_block_as_wait_checks` policy를 추가했다.

고정 조건:

- `symbol_allow = BTCUSD`
- `side_allow = BUY`
- `observe_reason_allow = outer_band_reversal_support_required_observe`
- `blocked_by_allow = energy_soft_block`
- `action_none_allow = execution_soft_blocked`
- `probe_scene_allow = btc_lower_buy_conservative_probe`
- `stage_allow = PROBE, BLOCKED`
- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = btc_structural_probe_energy_soft_block_as_wait_checks`

### 3-2. consumer state relief 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`btc_structural_probe_energy_wait_relief` family match를 추가했다.

이 경로는:

- structural probe scene이 붙어 있고
- energy soft block 때문에 entry만 막혀 있고
- scene importance는 `btc_structural_rebound`로 살아 있는 경우

`WAIT + repeated checks` contract로 surface를 올릴 준비를 한다.

### 3-3. blocked reason carry

같은 파일에서 relief가 적용될 때
`blocked_display_reason = energy_soft_block`가 유지되도록 정리했다.

그래서 chart/debug surface에서 단순 hidden blocked scene이 아니라
왜 기다림인지 설명 가능한 상태가 된다.

### 3-4. PA0 accepted wait relief 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`btc_structural_probe_energy_soft_block_as_wait_checks`
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
56 passed
68 passed
11 passed
```

고정한 회귀:

- BTC structural blocked scene이 current build에서 `WAIT + wait_check_repeat`로 올라가는지
- chart painter가 neutral repeated wait marker로 그리는지
- PA0 script가 이 reason을 accepted wait relief로 skip하는지

## 5. live runtime 확인

`main.py`를 새 코드로 다시 올렸다.

- restart log: [cfd_main_restart_20260331_194829.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_194829.out.log)
- restart err log: [cfd_main_restart_20260331_194829.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_194829.err.log)

post-restart runtime row 요약:

- total fresh rows after restart = `115`
- by symbol = `NAS100 39 / XAUUSD 38 / BTCUSD 38`
- exact target family recurrence = `0`

즉 재시작 자체는 정상이고 fresh row도 충분히 쌓였지만,
이번 exact family는 post-restart window에서 아직 다시 나오지 않았다.

대신 representative backlog row를 current build에 replay해서 contract를 확인했다.

- representative row time = `2026-03-31T19:31:03`
- replay result:
  - `check_display_ready = True`
  - `check_stage = BLOCKED`
  - `display_score = 0.82`
  - `display_repeat_count = 2`
  - `chart_event_kind_hint = WAIT`
  - `chart_display_mode = wait_check_repeat`
  - `chart_display_reason = btc_structural_probe_energy_soft_block_as_wait_checks`
  - `blocked_display_reason = energy_soft_block`

즉 current build 기준 contract 자체는 맞게 연결된 상태다.

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_195349.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_195349.json)
- 최신 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

generated_at:

- snapshot = `2026-03-31T19:26:54`
- latest = `2026-03-31T19:53:50`

baseline summary:

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_block_candidate_count = 12 -> 12`

target family delta:

- `must_show_missing = 13 -> 15`
- `must_block_candidates = 12 -> 12`

이건 구현 실패가 아니라,
post-restart fresh window에 exact target family가 `0건`이어서
recent queue를 old hidden backlog가 계속 채운 결과다.

latest must-show / must-block의 대표 time도 여전히 pre-restart old backlog 구간이다.

- sample times: `19:31:03`, `19:39:44`, `19:39:55`, `19:40:04`, `19:40:14`

## 7. 현재 reopen point

이번 하위축은 다음 상태로 닫는다.

- code path 구현 완료
- unit regression 고정 완료
- live restart 완료
- representative backlog row current-build replay 성공
- exact target family post-restart fresh recurrence는 아직 0건

즉 다음 reopen point는 둘 중 하나다.

1. exact BTC structural family가 다시 발생한 뒤 PA0를 한 번 더 refreeze
2. 현재 must-hide main family로 넘어가서 PA1 다음 축 진행

## 8. 한 줄 요약

```text
이번 PA1 하위축은 구현과 회귀는 끝났고 current-build replay도 성공했다.
다만 post-restart fresh window에서 exact BTC structural energy-soft-block family가 아직 다시 나오지 않아,
PA0 queue는 old hidden backlog 기준으로 그대로 남아 있는 상태다.
```
