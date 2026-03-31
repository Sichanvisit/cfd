# Product Acceptance PA1 BTC Lower Probe Promotion Wait Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`BTCUSD + lower_rebound_probe_observe + probe_promotion_gate + probe_not_promoted + btc_lower_buy_conservative_probe`
family를 leakage가 아니라 `WAIT + repeated checks` chart contract로 연결했다.

관련 문서:

- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_probe_promotion_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_probe_promotion_wait_display_contract_delta_ko.md)

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
`btc_lower_probe_promotion_wait_as_wait_checks` policy를 추가했다.

고정 조건:

- `symbol_allow = BTCUSD`
- `side_allow = BUY`
- `observe_reason_allow = lower_rebound_probe_observe`
- `blocked_by_allow = probe_promotion_gate`
- `action_none_allow = probe_not_promoted`
- `probe_scene_allow = btc_lower_buy_conservative_probe`
- `stage_allow = PROBE`
- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = btc_lower_probe_promotion_wait_as_wait_checks`

### 3-2. consumer state blocked reason carry

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`btc_lower_probe_promotion_wait_relief` family match를 추가했고,
이 family일 때 `blocked_display_reason = probe_promotion_gate`가 carry되도록 정리했다.

즉 lower probe scene은 계속 보이되,
왜 기다리는지까지 chart/debug surface에 설명이 남는다.

### 3-3. PA0 accepted wait relief 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`btc_lower_probe_promotion_wait_as_wait_checks`
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
60 passed
70 passed
13 passed
```

고정한 회귀:

- build 단계에서 target family가 `WAIT + wait_check_repeat`로 나오는지
- effective state에서도 contract가 유지되는지
- chart painter가 neutral wait-check marker로 그리는지
- PA0가 더 이상 이 family를 must-hide leakage로 잡지 않는지

## 5. live runtime 확인

`main.py`를 새 코드로 다시 올렸다.

- restart log: [cfd_main_restart_20260331_202858.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_202858.out.log)
- restart err log: [cfd_main_restart_20260331_202858.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_202858.err.log)

post-restart direct fresh row에서는 exact target family recurrence가 바로는 `0건`이었다.

다만 representative row `2026-03-31T20:11:43`을 current build에 replay하면 아래처럼 나온다.

- `check_display_ready = True`
- `check_stage = PROBE`
- `display_score = 0.91`
- `display_repeat_count = 3`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_lower_probe_promotion_wait_as_wait_checks`
- `blocked_display_reason = probe_promotion_gate`

즉 current build 기준 contract 자체는 정상적으로 연결된 상태다.

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_203028.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_203028.json)
- 최신 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

generated_at:

- snapshot = `2026-03-31T20:15:55`
- latest = `2026-03-31T20:30:28`

핵심 delta:

- target `must_hide_leakage = 10 -> 0`

같은 구간에서

- `NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`는 `5 -> 5`
- 새 main must-hide는 `NAS100 + upper_reject_confirm + forecast_guard + observe_state_wait + no_probe = 10`

즉 이번 BTC target family는 queue에서 실제로 빠졌고,
must-hide main axis는 이제 NAS upper-reject family로 넘어간 상태다.

## 7. 같이 본 추가 신호

같은 refreeze에서

- `BTC structural` must-show / must-block은 `5 -> 4`로 한 칸 줄었다
- `XAU middle-anchor energy-soft-block` must-show는 `10` 유지, must-block은 `8` 유지

즉 PA1 기준 남은 문제는 BTC lower probe promotion이 아니라
NAS upper-reject must-hide와 XAU/BTC energy-soft-block backlog 쪽이다.

## 8. 한 줄 요약

```text
이번 PA1 하위축으로 BTC lower_rebound_probe + probe_promotion_gate family는
accepted WAIT + repeated checks 계약으로 정리됐고,
PA0 must-hide queue에서는 10 -> 0으로 빠졌다.
```
