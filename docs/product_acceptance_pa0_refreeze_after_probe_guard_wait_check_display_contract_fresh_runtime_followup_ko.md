# Product Acceptance PA0 Refreeze After Probe-Guard Wait Check Display Contract Fresh Runtime Follow-Up

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는
`probe_guard_wait_as_wait_checks`
계약 반영 이후,
fresh runtime row가 실제로 추가된 뒤
accepted wait-check relief family가 PA0 queue에서 빠졌는지 재확인한 follow-up 기록이다.

즉 이번 문서는 아래 질문에 답한다.

```text
fresh runtime row가 더 쌓인 뒤,
accepted WAIT + repeated checks family가
must-show / must-hide / must-block queue에서 실제로 빠졌는가?
```

## 2. 확인 시점

이번 follow-up에서 확인한 시각은 아래다.

- `entry_decisions.csv` 파일 수정 시각:
  - `2026-03-31T16:35:11`
- latest row `time`:
  - `2026-03-31T16:35:13`
- 이전 baseline snapshot:
  - `generated_at = 2026-03-31T16:19:38`
  - [product_acceptance_pa0_baseline_snapshot_20260331_161938.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_161938.json)
- refreeze 후 latest baseline:
  - `generated_at = 2026-03-31T16:36:03`
  - [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

즉 baseline 이후 fresh runtime row는 실제로 들어왔다.

## 3. 핵심 결론

직설적으로 요약하면 아래가 맞다.

```text
fresh runtime row는 들어왔지만,
recent 120-row window에는 여전히
chart wait-check hint row가 하나도 없었다.

그래서 accepted WAIT + repeated checks family가
queue에서 빠졌다고는 아직 말할 수 없다.
```

즉 현재 상태는

- `fresh row accumulation = yes`
- `new chart hint propagation into recent rows = no`

로 읽는 것이 맞다.

## 4. hint row 확인

recent 120-row window 기준 결과:

- `BTCUSD`: `hint_rows = 0`, `wait_check_rows = 0`
- `NAS100`: `hint_rows = 0`, `wait_check_rows = 0`
- `XAUUSD`: `hint_rows = 0`, `wait_check_rows = 0`

여기서 `wait_check_rows`는 아래 3필드가 모두 채워진 row를 뜻한다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

즉 PA0 script가 accepted wait-check relief를 skip할 준비는 되어 있지만,
그 조건을 실제로 만족하는 fresh row는 아직 recent window에 없다.

## 5. baseline summary delta

global summary는 그대로였다.

- `recent_entry_row_count`: `360 -> 360`
- `must_show_missing_count`: `15 -> 15`
- `must_hide_leakage_count`: `15 -> 15`
- `must_block_candidate_count`: `12 -> 12`
- `must_hold_candidate_count`: `2 -> 2`
- `must_release_candidate_count`: `10 -> 10`
- `bad_exit_candidate_count`: `10 -> 10`

즉 count 기준으로는 아직 변화가 없다.

## 6. queue composition delta

count는 같았지만,
queue composition은 일부 바뀌었다.

### 6-1. must-hide leakage

대표 변화:

- `BTC visible middle-anchor structural probe family`
  - `9 -> 3`
- `NAS conflict visible family`
  - `6 -> 12`

즉 우리가 보던 BTC visible family는 줄었지만,
그 자리를 NAS conflict visible family가 채웠다.

### 6-2. must-show missing

대표 변화:

- `XAU blocked structural family`
  - `3 -> 2`
- `BTC lower_rebound blocked family`
  - `8 -> 0`

즉 must-show queue는 다른 blocked family 쪽으로 재편됐다.

### 6-3. must-block candidates

대표 변화:

- `XAU blocked structural family`
  - `2 -> 0`
- `BTC lower_rebound preflight-blocked family`
  - `6 -> 12`

즉 must-block queue는 BTC preflight-blocked probe family 쪽으로 더 응집됐다.

## 7. 이번 follow-up에서 확실히 말할 수 있는 것

확실히 말할 수 있는 것:

- fresh runtime row는 baseline 이후 실제로 추가됐다
- 하지만 recent window에는 새 wait-check chart hint row가 아직 없다
- 그래서 accepted wait-check relief의 queue 제외 효과는 아직 artifact에서 확인되지 않는다
- 현재 queue 변화는 accepted wait-check family drop보다
  다른 blocked/conflict family 재편 쪽이 더 크다

아직 확실히 말하면 안 되는 것:

- `WAIT + repeated checks` contract가 runtime에 절대 안 쓰인다고 단정하는 것
- 현재 queue를 보고 wait-check boundary를 다시 되돌리는 것

## 8. 다음 reopen point

다음 순서는 아래가 가장 자연스럽다.

1. fresh runtime row를 조금 더 쌓는다
2. recent window에 `chart_event_kind_hint / chart_display_mode / chart_display_reason`가 실제로 들어오는지 먼저 확인한다
3. 그 뒤 PA0 baseline을 다시 얼린다
4. 그때 accepted wait-check relief family가 queue에서 빠지는지 최종 확인한다

## 9. 한 줄 요약

```text
fresh runtime row는 들어왔지만
recent window에는 아직 새 WAIT + repeated checks chart hint row가 없어서,
accepted wait-check relief family가 queue에서 실제로 빠졌는지는 아직 artifact로 확인되지 않는다.
```
