# Product Acceptance PA0 Refreeze After XAU Upper Reject Probe Energy Soft Block Wait Visibility Relief Delta

작성일: 2026-03-31 (KST)

## 비교 기준

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_173619.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_173619.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

## 새 refreeze 시점

- `generated_at = 2026-03-31T17:40:36`

## baseline 요약 변화

- `must_show_missing_count`: `15 -> 15`
- `must_hide_leakage_count`: `15 -> 15`
- `must_enter_candidate_count`: `0 -> 6`
- `must_block_candidate_count`: `12 -> 12`
- `divergence_seed_count`: `1 -> 0`

즉 총량만 보면 정체처럼 보이지만,
queue composition은 실제로 바뀌었다.

## XAU target family 변화

이번 구현 전:

- must-show `14/15`
  `XAU upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- must-block `7/12`
  같은 family

이번 구현 후:

- must-show `10/15`
  같은 family 잔존
- must-block `0/12`
  이 family는 제거됨

즉 fresh row는 accepted wait relief로 빠졌고,
recent window에 남아 있는 old hidden row만 아직 must-show에 남아 있다.

## live 확인 근거

재시작 이후 fresh nested target row:

- `2026-03-31T17:38:12`
- `2026-03-31T17:38:51`
- `2026-03-31T17:39:01`

이 row들은 모두:

- `check_stage = PROBE`
- `check_display_ready = True`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_energy_soft_block_as_wait_checks`

그리고 casebook queue overlap은 `0`이었다.

## 새 queue 주력

### must-show missing

현재 주력:

- XAU old hidden energy-soft-block row `10`
- BTC lower rebound energy-soft-block hidden row `5`

### must-hide leakage

현재 주력:

- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`
  `15`

### must-block candidates

현재 주력:

- NAS outer-band blocked `7`
- BTC lower rebound energy-soft-block blocked `5`

## 해석

이번 delta는 아래 두 가지를 동시에 보여준다.

1. XAU energy-soft-block wait relief 구현은 live에서 실제로 먹었다
2. PA0 총량은 old window 잔존분과 새 BTC/NAS family 때문에 바로 줄어들지 않았다

즉 실패가 아니라
`fresh row exclusion 성공 + next family 노출`
로 보는 것이 맞다.

## 다음 reopen point

다음 PA1 후보:

1. `BTC lower_rebound_probe_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
2. `NAS outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`

## 한 줄 요약

```text
이번 refreeze는 XAU energy-soft-block fresh relief row가 실제로 queue에서 빠졌음을 확인했고,
이제 다음 PA1 메인 문제는 BTC mirror family와 NAS outer-band no-probe leakage임을 고정했다.
```
