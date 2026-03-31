# Product Acceptance PA0 Refreeze After Probe-Guard Wait Check Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 하위축
`probe_guard_wait_as_wait_checks`
구현 이후,
PA0 baseline을 다시 얼리고
직전 snapshot과 delta를 비교한 기록이다.

즉 이번 문서는 아래 질문에 답한다.

```text
WAIT + repeated checks chart contract를 붙인 뒤,
PA0 must-show / must-hide / must-block queue가 실제로 줄었는가?
```

## 2. 비교 대상

비교 baseline:

- 이전 snapshot:
  - generated_at = `2026-03-31T15:54:45`
  - [product_acceptance_pa0_baseline_snapshot_20260331_155445.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_155445.json)
  - [product_acceptance_pa0_baseline_snapshot_20260331_155445.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_155445.csv)
  - [product_acceptance_pa0_baseline_snapshot_20260331_155445.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_155445.md)

- 이번 refreeze:
  - generated_at = `2026-03-31T16:19:38`
  - [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
  - [product_acceptance_pa0_baseline_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.csv)
  - [product_acceptance_pa0_baseline_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.md)

## 3. 요약 결론

직설적으로 요약하면 아래가 맞다.

```text
코드 계약과 테스트는 이미 WAIT + repeated checks 방향으로 닫혔지만,
이번 refreeze baseline 숫자는 아직 그대로였다.

이유는 recent entry row에 새 chart hint contract가 아직 기록되지 않았기 때문이다.
```

즉 이번 결과는
`구현 실패`
가 아니라
`artifact 반영 대기`
로 읽는 것이 맞다.

## 4. baseline delta

### 4-1. global summary

이번 refreeze의 global summary는 아래처럼 그대로였다.

- `recent_entry_row_count`: `360 -> 360`
- `recent_closed_trade_count`: `79 -> 79`
- `must_show_missing_count`: `15 -> 15`
- `must_hide_leakage_count`: `15 -> 15`
- `must_block_candidate_count`: `12 -> 12`
- `must_hold_candidate_count`: `2 -> 2`
- `must_release_candidate_count`: `10 -> 10`
- `bad_exit_candidate_count`: `10 -> 10`

즉 숫자만 보면 아직 움직임이 없다.

### 4-2. tri-symbol quick read

이번 latest baseline quick read:

- `BTCUSD`: `display_ready_count = 98`, `display_ready_ratio = 0.816667`, `avg_display_score = 0.6697`
- `NAS100`: `display_ready_count = 12`, `display_ready_ratio = 0.1`, `avg_display_score = 0.0785`
- `XAUUSD`: `display_ready_count = 68`, `display_ready_ratio = 0.566667`, `avg_display_score = 0.4647`

즉 recent window 자체는 이미 새 row로 바뀌고 있지만,
problem seed queue는 아직 새 chart contract 기준으로 재분류되지 않았다.

## 5. 왜 숫자가 안 움직였는가

핵심 이유는 단순하다.

PA0 script는
`entry_decisions.csv -> consumer_check_state_v1`
에 저장된 nested payload를 읽어
accepted wait-check relief를 skip한다.

그런데 recent 120-row window 확인 결과는 아래와 같았다.

- `BTCUSD`: hint row `0`
- `NAS100`: hint row `0`
- `XAUUSD`: hint row `0`

즉 recent stored row에는 아래 새 contract field가 아직 없다.

- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

그래서 script 쪽 skip logic은 이미 들어가 있지만,
그 logic이 읽을 수 있는 fresh row가 아직 없는 상태다.

## 6. 무엇은 이미 확인됐는가

artifact가 아직 안 따라왔을 뿐,
코드 contract 자체는 아래로 확인됐다.

### 6-1. consumer surface

synthetic replay / unit test 기준:

- `check_stage = OBSERVE`
- `check_display_ready = True`
- `display_repeat_count = 2`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

### 6-2. chart surface

unit test 기준:

- final history event kind = `WAIT`
- side = `""`
- repeat_count = `2`
- neutral marker pair가 repeat index를 포함해 반복 생성된다

### 6-3. PA0 heuristic alignment

unit test 기준:

- accepted wait-check relief row는
  `must-show missing`
  `must-hide leakage`
  `must-block`
  queue에서 빠진다

즉 문제는 로직이 아니라
live row accumulation timing이다.

## 7. 테스트

실행한 테스트:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
45 passed
60 passed
3 passed
```

## 8. 지금 시점에서 확실히 말할 수 있는 것

확실히 말할 수 있는 것:

- code-level contract는 `WAIT + repeated checks`로 연결됐다
- painter surface도 그 계약을 실제로 그린다
- PA0 heuristic alignment도 들어갔다
- 이번 refreeze baseline 숫자가 그대로인 이유는 recent stored row가 old contract이기 때문이다

아직 확실히 말하면 안 되는 것:

- 이번 하위축이 실패했다고 단정하는 것
- fresh runtime row 없이 must-hide queue 해석을 다시 뒤집는 것

## 9. 다음 reopen point

다음 순서는 아래가 자연스럽다.

1. 새 contract가 들어간 fresh runtime row를 조금 더 쌓는다
2. PA0 baseline을 다시 얼린다
3. `probe_guard_wait_as_wait_checks` family가 queue에서 실제로 빠졌는지 본다
4. 그래도 남는 must-show / must-hide / must-block family만 다시 PA1 follow-up 대상으로 좁힌다

## 10. 한 줄 요약

```text
이번 refreeze에서 baseline 숫자는 그대로였지만,
그 이유는 WAIT + repeated checks 구현이 안 먹어서가 아니라
recent entry row가 아직 새 chart hint contract를 기록하지 않았기 때문이다.
```
