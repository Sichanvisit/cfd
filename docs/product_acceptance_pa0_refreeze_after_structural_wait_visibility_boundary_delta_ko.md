# Product Acceptance PA0 Refreeze After Structural Wait Visibility Boundary Delta

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 하위축 `structural_wait_hide_without_probe` 적용 이후,
runtime row가 더 쌓인 시점에서 PA0 baseline을 다시 얼리고
직전 baseline과 delta를 비교한 기록이다.

즉 이번 문서는 아래 질문에 답한다.

```text
structural wait visibility boundary 이후
total must-hide leakage가 실제로 줄었는가?
```

## 2. 비교 대상

비교 baseline:

- 이전 snapshot:
  - generated_at = `2026-03-31T15:23:56`
  - [product_acceptance_pa0_baseline_snapshot_20260331_152356.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_152356.json)
  - [product_acceptance_pa0_baseline_snapshot_20260331_152356.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_152356.csv)
  - [product_acceptance_pa0_baseline_snapshot_20260331_152356.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_152356.md)

- 이번 refreeze:
  - generated_at = `2026-03-31T15:54:45`
  - [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
  - [product_acceptance_pa0_baseline_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.csv)
  - [product_acceptance_pa0_baseline_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.md)

runtime row 추적:

- `entry_decisions.csv` latest time: `2026-03-31T15:54:13`
- 이전 snapshot cutoff 이후 추가 row: 총 `692`
- symbol별 추가 row: `BTCUSD 231`, `NAS100 231`, `XAUUSD 230`

즉 이번 비교는 `120 row window` 기준으로
세 심볼 recent window가 사실상 전부 새 row로 교체된 뒤의 refreeze 비교다.

## 3. 요약 결론

직설적으로 요약하면 아래가 맞다.

```text
structural wait visibility boundary 이후
no-probe structural leakage family는 current window에서 사라졌지만,
total must-hide leakage count는 15 -> 15로 그대로였다.

다만 이번에는 그 15개가
BTC no-probe wait leakage가 아니라
BTC probe-scene structural probe_wait family로 전부 교체됐다.
```

즉 `total count`만 보면 줄지 않았고,
`family composition`을 보면 경계는 실제로 바뀌었다.

## 4. baseline delta

### 4-1. global summary

변화 없음:

- `recent_entry_row_count`: `360 -> 360`
- `recent_closed_trade_count`: `79 -> 79`
- `must_show_missing_count`: `15 -> 15`
- `must_hide_leakage_count`: `15 -> 15`
- `must_block_candidate_count`: `12 -> 12`
- `must_hold_candidate_count`: `2 -> 2`
- `must_release_candidate_count`: `10 -> 10`
- `bad_exit_candidate_count`: `10 -> 10`

즉 총량 지표만 보면 이번 refreeze는 그대로다.

### 4-2. tri-symbol display surface delta

1. `BTCUSD`

- `display_ready_ratio`: `0.983333 -> 1.0`
- `display_ready_count`: `118 -> 120`
- `avg_display_score`: `0.8063 -> 0.82`
- `stage_counts`:
  - before: `PROBE 10 / OBSERVE 108 / BLOCKED 2`
  - after: `OBSERVE 120`

해석:

- BTC recent window는 거의 전부 `probe_scene structural observe` surface로 채워졌다.
- `observe_state_wait + no_probe` 비중은 `27 -> 1`로 줄었고,
  `btc_lower_buy_conservative_probe` 비중은 `93 -> 119`로 늘었다.

2. `NAS100`

- `display_ready_ratio`: `0.066667 -> 0.0`
- `display_ready_count`: `8 -> 0`
- `avg_display_score`: `0.05 -> 0.0`
- `stage_counts`:
  - before: `NONE 112 / OBSERVE 8`
  - after: `NONE 120`

해석:

- NAS는 이번 recent window에서 candidate surface가 다시 비워졌다.
- 이번 refreeze의 핵심 변화축은 NAS가 아니라 BTC 쪽이다.

3. `XAUUSD`

- `display_ready_ratio`: `0.341667 -> 0.416667`
- `display_ready_count`: `41 -> 50`
- `avg_display_score`: `0.2802 -> 0.3417`
- `stage_counts`:
  - before: `NONE 78 / OBSERVE 41 / BLOCKED 1`
  - after: `NONE 70 / OBSERVE 50`

해석:

- XAU는 probe-scene structural wait visibility가 더 늘었다.
- blocked seed는 이번 recent window에서 사라졌다.

## 5. must-hide leakage delta

### 5-1. dominant family 비교

이전 snapshot:

- `10 / 15`
- `BTCUSD`
- `observe_reason = conflict_box_upper_bb20_lower_lower_support_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`
- `check_stage = PROBE`

그리고

- `5 / 15`
- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`
- `check_stage = OBSERVE`

이번 refreeze:

- `15 / 15`
- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `check_stage = OBSERVE`

### 5-2. 해석

이번 결과는 아래처럼 읽는 게 맞다.

1. `conflict_wait_hide`와 `structural_wait_hide_without_probe`는 current window에서 먹혔다

- 예전 `conflict + observe_state_wait + no_probe` family `10`개는 사라졌다
- 예전 `middle_anchor + observe_state_wait + no_probe` family `5`개도 사라졌다

2. 하지만 total must-hide는 줄지 않았다

- 그 자리를 `probe_not_promoted + btc_lower_buy_conservative_probe` family `15`개가 채웠다

3. 즉 지금 드러난 문제는 suppression 부족이라기보다 casebook 경계 문제에 가깝다

- no-probe leakage는 current window에서 사실상 정리됐다
- 대신 `probe-scene structural probe_wait`를 PA0가 여전히 must-hide leakage로 잡고 있다
- 같은 family가 must-show queue에도 동시에 들어오기 때문에,
  이건 현재 heuristic이 `acceptable structural visibility`와 `real leakage`를 아직 분리하지 못한다는 신호다

## 6. must-show missing delta

이전 snapshot:

- `12 / 15`
- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `check_stage = OBSERVE`

그리고

- `2 / 15`
- `BTCUSD`
- same family
- `check_stage = BLOCKED`
- `display_ready = False`

그리고

- `1 / 15`
- `XAUUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_second_support_buy_probe`
- `check_stage = BLOCKED`
- `display_ready = False`

이번 refreeze:

- `15 / 15`
- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `check_stage = OBSERVE`
- `display_ready = True`

해석:

- `BTC probe-scene structural probe_wait` family는 now-visible 쪽으로 더 강하게 쏠렸다
- 이전에 섞여 있던 `BLOCKED + hidden` seed는 사라졌다
- `XAU hidden` seed도 이번 recent window에서는 사라졌다

## 7. 지금 시점에서 확실히 말할 수 있는 것

확실히 말할 수 있는 것:

- total `must-hide_leakage_count`는 이번 refreeze에서도 `15`다
- no-probe conflict / no-probe structural leakage family는 current window에서 사라졌다
- current must-hide queue는 이제 `BTC probe-scene structural probe_wait` family가 전부 채운다
- must-show queue도 같은 BTC probe-scene family로 더 응집됐다

아직 확실히 말하면 안 되는 것:

- structural boundary가 실패했다고 단정하는 것
- 지금 queue를 보고 바로 suppression rule을 하나 더 넣는 것

이번 결과는 오히려
`probe-scene structural probe_wait는 보여줘야 하는가, 아니면 leakage인가`
경계를 PA0/PA1 공통 casebook에서 다시 잘라야 한다는 쪽에 가깝다.

## 8. 다음 reopen point

다음 순서는 아래가 자연스럽다.

1. `probe_not_promoted + scene_probe + guard_present + visible` family를
   PA0 must-hide heuristic에서 계속 leakage로 볼지 먼저 결정한다
2. 그 경계가 `acceptable structural visibility relief`라면
   PA0 casebook / ranking rule을 조정한다
3. 그 경계가 실제 leakage라면
   PA1에서 probe-scene structural wait relief 조건을 다시 좁힌다
4. 그 뒤 baseline을 한 번 더 refreeze해서 total must-hide가 실제로 줄었는지 본다

## 9. 한 줄 요약

```text
이번 refreeze에서 total must-hide count는 줄지 않았지만,
그 이유는 no-probe leakage가 계속 남아서가 아니라
BTC probe-scene structural probe_wait family가 must-show와 must-hide 양쪽 queue를 동시에 채우는
새 경계 문제로 바뀌었기 때문이다.
```
