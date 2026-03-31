# Product Acceptance PA0 Refreeze After BTC Lower Rebound Probe Energy Soft Block Wait Visibility Relief Delta

작성일: 2026-03-31 (KST)

## 1. 비교 대상

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_175617.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_175617.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

기준 시각:

- snapshot generated_at = `2026-03-31T17:40:36`
- latest generated_at = `2026-03-31T17:57:59`

관련 구현 문서:

- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)

## 2. baseline summary delta

```text
must_show_missing_count: 15 -> 15
must_hide_leakage_count: 15 -> 15
must_enter_candidate_count: 6 -> 5
must_block_candidate_count: 12 -> 12
divergence_seed_count: 0 -> 0
```

즉 total count만 보면 아직 dramatic drop은 없다.

## 3. 하지만 fresh exclusion은 성공했다

restart 이후 nested `consumer_check_state_v1`에
`btc_lower_rebound_probe_energy_soft_block_as_wait_checks`
가 찍힌 fresh BTC row를 확인했다.

대표 시각:

- `2026-03-31T17:57:21`
- `2026-03-31T17:57:30`
- `2026-03-31T17:57:41`
- `2026-03-31T17:57:54`

이 fresh rows의 queue overlap은 아래였다.

```text
fresh target row count = 14
queue overlap count = 0
```

즉 새 wait relief contract는 live/fresh row 기준으로 실제로 먹었다.

## 4. 왜 total must-show / must-block는 그대로인가

latest queue를 보면 BTC family가 아직 아래처럼 남아 있다.

```text
must_show BTC lower rebound energy-soft-block = 15
must_block BTC lower rebound energy-soft-block = 12
```

하지만 이 row들의 시각은 `2026-03-31T17:38:03`부터 `2026-03-31T17:46:49`까지로,
restart 이전 hidden rows가 recent 120-row window에 아직 남아 있는 backlog다.

즉 현재 해석은 아래다.

- fresh row: 이미 새 contract로 살아나서 queue에서 빠짐
- old hidden backlog: 아직 recent window에 남아서 total count 유지

## 5. must-hide 메인축 변화

must-hide는 현재 아래 family가 `15/15`를 채운다.

```text
NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe
```

즉 BTC mirror family를 닫은 뒤, 다음 PA1 메인 leakage 축은 NAS no-probe family로 더 선명해졌다.

## 6. 결론

```text
이번 refreeze의 결론은 “BTC 하위축이 실패했다”가 아니라,
fresh row 기준 구현은 성공했고 total queue가 안 줄어 보이는 이유는 old hidden backlog 때문이라는 것이다.
그래서 다음 PA1 메인 대상은 NAS outer-band no-probe leakage가 맞다.
```
