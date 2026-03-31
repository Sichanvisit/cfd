# Product Acceptance PA1 BTC Lower-Rebound Forecast-Wait No-Probe Hide Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`
family를 visible probe leakage에서
accepted hidden suppression으로 정리했다.

관련 기준 문서:

- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_rebound_forecast_wait_no_probe_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_rebound_forecast_wait_no_probe_hide_delta_ko.md)

## 2. 직접 건드린 owner 범위

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

이번 단계에서 일부러 건드리지 않은 범위:

- BTC probe-scene wait-check relief family
- XAU energy-soft-block backlog
- NAS probe-scene visible family
- entry / wait / hold / exit acceptance

## 3. 구현 내용

### 3-1. BTC forecast-wait no-probe hide policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`btc_lower_rebound_forecast_wait_hide_without_probe`
policy를 추가했다.

고정 조건:

- `symbol_allow = BTCUSD`
- `side_allow = BUY`
- `observe_reason_allow = lower_rebound_confirm`
- `blocked_by_allow = forecast_guard`
- `action_none_allow = observe_state_wait`
- `importance_source_allow = btc_lower_recovery_start`
- `require_probe_scene_absent = true`

즉 no-probe lower rebound confirm row 중에서도
forecast wait + lower recovery importance source가 붙은 family만 숨긴다.

### 3-2. common modifier suppression 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) modifier path에
새 soft-cap을 연결했다.

이 family가 걸리면:

- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = btc_lower_rebound_forecast_wait_hide_without_probe`

로 surface가 바뀐다.

### 3-3. late-hidden breakdown row에도 동일 suppress reason 태깅

실제 live에서는 `LOWER/BREAKDOWN`뿐 아니라
기존 `BELOW/BREAKDOWN` late-hidden row도 섞여 있었다.

그래서 [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`btc_lower_rebound_forecast_wait_hidden` family tag를 추가해서,
이미 late path에서 숨겨진 동일 family에도
같은 `modifier_primary_reason`이 남도록 보강했다.

이 보강으로:

- common modifier가 직접 숨긴 row
- 기존 lower breakdown suppression이 먼저 숨긴 row

둘 다 같은 hidden suppression contract로 정렬된다.

### 3-4. painter top-level fallback 차단

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에서
`btc_lower_rebound_forecast_wait_hide_without_probe`
reason이 붙은 hidden consumer row는
top-level BUY fallback도 다시 그리지 않게 처리했다.

### 3-5. PA0 accepted hidden suppression 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`btc_lower_rebound_forecast_wait_hide_without_probe`
를 accepted hidden suppression reason으로 추가했다.

그래서 must-show / must-hide / must-block builder가
이 reason이 붙은 hidden row를 queue에서 다시 문제로 세지 않는다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
53 passed
65 passed
8 passed
```

고정한 확인 포인트:

- BTC forecast-wait no-probe row가 build 단계에서 바로 숨는지
- 기존 late-hidden breakdown row도 같은 suppress reason으로 태깅되는지
- painter가 nested hidden row를 top-level fallback으로 다시 그리지 않는지
- PA0 script가 accepted hidden suppression reason을 문제 queue에서 skip하는지

## 5. live runtime 확인

`main.py`를 새 코드로 다시 시작했다.

- restart log: [cfd_main_restart_20260331_185959.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_185959.out.log)
- restart err log: [cfd_main_restart_20260331_185959.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_185959.err.log)
- live process: `PID 14476`
- start time: `2026-03-31T19:00:02`

post-restart fresh BTC rows `37`개를 확인했지만,
exact target family
`lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`
는 재발생하지 않았다.

post-restart fresh BTC rows 구성:

- `16 = lower_rebound_confirm + energy_soft_block + execution_soft_blocked + no_probe`
- `14 = lower_rebound_probe_observe + probe_promotion_gate + probe_not_promoted + btc_lower_buy_conservative_probe`
- `7 = outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe`

즉 live window는 이미 다른 BTC backlog family로 이동한 상태였다.

direct live target row는 없었지만,
previous PA0 queue 대표 row
`2026-03-31T18:11:53`
를 current build로 다시 태웠을 때 계약은 실제로 아래처럼 바뀌었다.

- `check_display_ready = False`
- `check_stage = OBSERVE`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `display_importance_source_reason = btc_lower_recovery_start`
- `modifier_primary_reason = btc_lower_rebound_forecast_wait_hide_without_probe`

즉 코드 자체는 target family를 hidden suppression contract로 내리는 상태가 맞다.

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_190640.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_190640.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest baseline generated_at:

- `2026-03-31T19:06:40`

핵심 해석:

- previous must-hide main family였던
  `BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`
  는 queue에서 `15 -> 0`으로 빠졌다
- total `must_hide = 15`는 그대로였지만,
  그 자리를 NAS family가 채웠다

current queue composition:

- `must_hide 13/15 = NAS middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`
- `must_hide 2/15 = NAS upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe`
- `must_show 11/15 = BTC lower_rebound_confirm + energy_soft_block + execution_soft_blocked + no_probe`
- `must_show 4/15 = BTC outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
- `must_block 8/12 = BTC lower_rebound_confirm + energy_soft_block + execution_soft_blocked + no_probe`
- `must_block 4/12 = BTC outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`

즉 이번 하위축의 결론은 아래다.

```text
BTC forecast-wait no-probe visible leakage 축은 queue 기준으로 닫혔다.
이제 PA1 메인 문제는 NAS must-hide no-probe family와
BTC energy-soft-block must-show / must-block backlog로 이동했다.
```
