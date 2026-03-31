# Product Acceptance PA0 Refreeze After Conflict Soft Cap Delta

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 follow-up에서 `conflict_wait_hide` soft cap을 넣은 뒤,
runtime row가 조금 더 쌓인 시점에서 PA0 baseline을 다시 얼리고
직전 baseline과 delta를 비교한 기록이다.

즉 이번 문서는 아래 질문에 답한다.

```text
conflict soft cap 이후에 must-hide leakage가 실제로 줄었는가?
```

## 2. 비교 대상

비교 baseline:

- 이전 snapshot:
  - generated_at = `2026-03-31T15:16:12`
  - [product_acceptance_pa0_baseline_snapshot_20260331_151615.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_151615.json)
  - [product_acceptance_pa0_baseline_snapshot_20260331_151615.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_151615.csv)
  - [product_acceptance_pa0_baseline_snapshot_20260331_151615.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_151615.md)

- 새 refreeze:
  - generated_at = `2026-03-31T15:23:56`
  - [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
  - [product_acceptance_pa0_baseline_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.csv)
  - [product_acceptance_pa0_baseline_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.md)

runtime row 누적:

- `entry_decisions.csv` 최신 시각: `2026-03-31T15:23:15`
- 이전 snapshot cutoff 이후 추가 row: 총 `180`
- symbol별 추가 row: `BTCUSD 60`, `NAS100 60`, `XAUUSD 60`

즉 이번 비교는 `120 row window` 기준으로
각 symbol 최근 절반 window가 새 row로 교체된 뒤의 refreeze 비교다.

## 3. 요약 결론

짧게 요약하면 아래와 같다.

```text
conflict soft cap 이후 must-hide leakage 총량은 15 -> 15로 그대로였지만,
dominant leakage family는 15개 전부 conflict였던 상태에서
10개 conflict + 5개 middle-anchor wait로 바뀌었다.
```

즉 `conflict` family는 실제로 줄었지만,
그만큼 다른 leakage family가 새 window에서 올라오면서
총 queue 길이는 유지됐다.

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

변화:

- `must_enter_candidate_count`: `0 -> 0` 유지
- `divergence_seed_count`: `0 -> 0` 유지

핵심은 총량보다 `구성 변화`였다.

### 4-2. tri-symbol display surface delta

1. `BTCUSD`

- `display_ready_ratio`: `0.95 -> 0.983333` (`+0.033333`)
- `avg_display_score`: `0.7790 -> 0.8063` (`+0.0273`)
- `stage_counts`:
  - before: `PROBE 47 / OBSERVE 67 / BLOCKED 1 / NONE 5`
  - after: `PROBE 10 / OBSERVE 108 / BLOCKED 2`

해석:

- BTC는 conflict/probe family가 일부 눌리면서
  `PROBE`가 줄고 `OBSERVE`로 더 많이 정리됐다.
- 하지만 directional visibility 자체는 여전히 높은 편이라
  leakage family가 완전히 사라지지는 않았다.

2. `NAS100`

- `display_ready_ratio`: `0.0 -> 0.066667` (`+0.066667`)
- `avg_display_score`: `0.0 -> 0.05` (`+0.05`)
- `stage_counts`:
  - before: `NONE 120`
  - after: `NONE 112 / OBSERVE 8`

해석:

- NAS는 current window에서 chart surface가 아예 죽어 있던 상태에서
  일부 observe visibility가 다시 살아났다.

3. `XAUUSD`

- `display_ready_ratio`: `0.15 -> 0.341667` (`+0.191667`)
- `avg_display_score`: `0.1230 -> 0.2802` (`+0.1572`)
- `stage_counts`:
  - before: `NONE 101 / OBSERVE 18 / BLOCKED 1`
  - after: `NONE 78 / OBSERVE 41 / BLOCKED 1`

해석:

- XAU는 visible observe surface가 가장 많이 회복됐다.

## 5. must-hide leakage delta

### 5-1. dominant family 비교

이전 snapshot:

- `15 / 15`
- `BTCUSD`
- `observe_reason = conflict_box_upper_bb20_lower_lower_support_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`

새 refreeze:

- `10 / 15`
- 위 conflict family 그대로 유지

추가로 새로 올라온 family:

- `5 / 15`
- `BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`

### 5-2. 해석

이 결과는 아래처럼 읽는 게 맞다.

1. `conflict_wait_hide`는 conflict family를 일부 실제로 줄였다

- `15 -> 10`
- 절대량 기준 `-5`
- 비중 기준 `100% -> 66.7%`

2. 하지만 total leakage queue는 줄지 않았다

- 같은 최근 120 row window 안에서
  `middle anchor observe wait` family가 새 leakage로 올라왔다

3. 따라서 이번 결과는

- `conflict soft cap이 무효였다`가 아니라
- `conflict 축 하나는 줄었지만, 다음 dominant leakage 축이 드러났다`

로 읽는 게 맞다.

## 6. must-show missing delta

`must_show_missing_count`는 `15 -> 15`로 유지됐다.

family 구성은 거의 아래에 고정되어 있다.

- `BTCUSD middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`

세부 변화:

- `OBSERVE + visible` family: `13 -> 12`
- `BLOCKED + hidden` family: `1 -> 2`
- `XAU second support hidden`: `1 -> 1`

해석:

- must-show queue는 이번 refreeze에서도 여전히
  `BTC structural probe_wait` family가 거의 전부를 차지한다.
- 즉 다음 PA1 follow-up의 우선순위는
  conflict soft cap보다도
  `middle-anchor structural probe_wait visibility relief / soft cap 경계`
  를 더 정밀하게 나누는 쪽으로 이동했다.

## 7. 이번 refreeze에서 확실히 말할 수 있는 것

확실히 말할 수 있는 것:

- conflict family must-hide leakage는 줄었다
- 하지만 total must-hide count는 줄지 않았다
- 새 dominant leakage 후보로 `BTC middle anchor observe wait`가 드러났다
- `XAU`와 `NAS`의 visible surface는 snapshot 대비 회복됐다

아직 확실히 말하면 안 되는 것:

- PA1 chart acceptance가 끝났다고 보기는 이르다
- conflict soft cap 하나로 leakage 문제가 닫혔다고 볼 수는 없다
- must-show family는 아직 structural probe_wait 쪽에서 남아 있다

## 8. 다음 reopen point

다음 순서는 아래가 자연스럽다.

1. `BTC middle_sr_anchor_required_observe + observe_state_wait + no_probe`
   leakage family를 공통 modifier soft cap으로 볼지
   symbol relief 경계로 볼지 먼저 분리한다
2. `BTC/XAU structural probe_wait` must-show family는
   visibility relief와 blocked baseline 경계가 어디서 갈리는지 raw replay로 더 좁힌다
3. 그 뒤 다시 PA0 baseline을 refreeze해서
   total leakage queue가 실제로 줄었는지 본다

## 9. 한 줄 요약

```text
이번 refreeze에서는 conflict soft cap 덕분에 BTC conflict leakage가 15개에서 10개로 줄었지만,
그 빈자리를 BTC middle-anchor wait leakage 5개가 메우면서 total must-hide count는 그대로 15로 유지됐다.
```
