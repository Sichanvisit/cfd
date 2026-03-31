# Product Acceptance PA0 Refreeze After NAS Middle-Anchor and Upper-Reclaim No-Probe Wait Hide Delta

작성일: 2026-03-31 (KST)

## 1. 비교 대상

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_192035.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_192035.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

기준 시각:

- snapshot generated_at = `2026-03-31T19:06:40`
- latest generated_at = `2026-03-31T19:26:54`

관련 구현 문서:

- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_memo_ko.md)

## 2. baseline summary delta

```text
must_show_missing_count: 15 -> 15
must_hide_leakage_count: 15 -> 15
must_enter_candidate_count: 12 -> 0
must_block_candidate_count: 12 -> 12
divergence_seed_count: 0 -> 0
```

즉 total count만 보면 must-show / must-hide / must-block는 여전히 꽉 차 있다.

## 3. target NAS family는 실제로 줄었다

이전 must-hide main family:

```text
13 = NAS100 + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe
2  = NAS100 + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe
```

latest must-hide queue:

```text
7 = NAS100 + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe
0 = NAS100 + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe
```

즉 이번 하위축의 결과는

- middle-anchor sell no-probe `13 -> 7`
- upper-reclaim buy no-probe `2 -> 0`

이다.

## 4. fresh hidden row는 queue overlap 0이었다

restart 이후 fresh middle-anchor hidden rows는 아래 조건으로 누적됐다.

- `modifier_primary_reason = nas_sell_middle_anchor_wait_hide_without_probe`
- `check_display_ready = False`

집계:

```text
fresh_hidden_count = 60
queue_overlap_count = 0
```

즉 accepted hidden suppression과 PA0 skip logic은 live/fresh row 기준으로 실제로 먹었다.

## 5. 왜 total must-hide는 그대로인가

latest must-hide queue는 새 family가 올라와서 다시 15를 채운다.

```text
8 = NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe
7 = NAS100 + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe
```

즉 이번 NAS no-probe 축이 줄어든 자리를
NAS probe-scene family가 일부 채운 것이다.

이건 “NAS fix 실패”가 아니라
“기존 main family를 줄이니 다음 visible family가 더 선명하게 드러난 상태”로 보는 게 맞다.

## 6. must-show / must-block current composition

latest must-show:

- `13/15 = BTC outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
- `1/15 = NAS outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
- `1/15 = NAS middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + nas_clean_confirm_probe`

latest must-block:

- `12/12 = BTC outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`

즉 현재 남은 메인 backlog는
NAS probe-scene visible family와
BTC energy-soft-block backlog 쪽으로 이동했다.

## 7. 결론

```text
이번 refreeze의 결론은 “NAS must-hide no-probe main axis가 실제로 줄었다”는 것이다.
upper-reclaim은 2 -> 0으로 빠졌고,
middle-anchor는 13 -> 7까지 내려왔다.
지금 다음 메인축은 NAS probe-scene family와 BTC energy-soft-block backlog다.
```
