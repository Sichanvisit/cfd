# Product Acceptance PA0 Refreeze After BTC Lower Probe Promotion Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 대상

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_203028.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_203028.json)
- 최신 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

기준 시각:

- snapshot generated_at = `2026-03-31T20:15:55`
- latest generated_at = `2026-03-31T20:30:28`

관련 구현 문서:

- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_memo_ko.md)

## 2. baseline summary delta

```text
must_show_missing_count: 15 -> 15
must_hide_leakage_count: 15 -> 15
must_enter_candidate_count: 0 -> 0
must_block_candidate_count: 12 -> 12
divergence_seed_count: 0 -> 0
```

총량은 그대로지만, composition은 의미 있게 바뀌었다.

## 3. target family delta

대상 family:

```text
BTCUSD + lower_rebound_probe_observe
+ probe_promotion_gate + probe_not_promoted
+ btc_lower_buy_conservative_probe
```

bucket별 변화:

```text
must_hide_leakage: 10 -> 0
must_show_missing: 0 -> 0
must_block_candidates: 0 -> 0
```

즉 이번 target must-hide family는 queue에서 완전히 빠졌다.

## 4. 왜 빠졌는가

representative row `2026-03-31T20:11:43`을 current build로 replay하면 아래처럼 나온다.

```text
check_display_ready = True
check_stage = PROBE
display_score = 0.91
display_repeat_count = 3
chart_event_kind_hint = WAIT
chart_display_mode = wait_check_repeat
chart_display_reason = btc_lower_probe_promotion_wait_as_wait_checks
blocked_display_reason = probe_promotion_gate
```

즉 이 family는 이제 leakage가 아니라
accepted `WAIT + repeated checks` contract로 해석된다.

## 5. current must-hide main axis

target family가 빠진 뒤 latest must-hide는 아래 조합으로 재편됐다.

```text
NAS100 + upper_reject_confirm + forecast_guard + observe_state_wait + no_probe = 10
NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe = 5
```

즉 다음 PA1 main reopen point는 NAS upper-reject family다.

## 6. 같이 본 backlog 변화

같은 비교 구간에서:

- `BTC structural energy-soft-block` must-show / must-block은 `5 -> 4`
- `XAU middle-anchor energy-soft-block` must-show는 `10`, must-block은 `8`

즉 must-hide main 문제는 NAS로 이동했고,
must-show / must-block backlog는 여전히 XAU/BTC energy-soft-block 쪽이 남아 있다.
