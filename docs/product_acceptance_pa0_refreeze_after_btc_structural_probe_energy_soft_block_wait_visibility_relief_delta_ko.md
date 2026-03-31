# Product Acceptance PA0 Refreeze After BTC Structural Probe Energy Soft Block Wait Visibility Relief Delta

작성일: 2026-03-31 (KST)

## 1. 비교 대상

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_195349.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_195349.json)
- 최신 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

기준 시각:

- snapshot generated_at = `2026-03-31T19:26:54`
- latest generated_at = `2026-03-31T19:53:50`

관련 구현 문서:

- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)

## 2. baseline summary delta

```text
must_show_missing_count: 15 -> 15
must_hide_leakage_count: 15 -> 15
must_enter_candidate_count: 0 -> 0
must_block_candidate_count: 12 -> 12
divergence_seed_count: 0 -> 0
```

즉 total count만 보면 이번 refreeze에서는 눈에 띄는 감소가 없다.

## 3. target family delta

대상 family:

```text
BTCUSD + outer_band_reversal_support_required_observe
+ energy_soft_block + execution_soft_blocked
+ btc_lower_buy_conservative_probe
```

bucket별 변화:

```text
must_show_missing: 13 -> 15
must_block_candidates: 12 -> 12
must_hide_leakage: 0 -> 0
```

즉 queue 기준으로는 여전히 이 family가 BTC backlog main axis다.

## 4. 왜 줄지 않았는가

이번 live restart 이후 fresh runtime row는 총 `115`건 들어왔다.

```text
NAS100 39 / XAUUSD 38 / BTCUSD 38
```

하지만 post-restart exact target family recurrence는 `0건`이었다.

즉:

- code path는 새 build로 올라가 있음
- fresh rows는 충분히 들어옴
- 그런데 이번 exact family가 새 window에서 다시 발생하지 않음
- 그래서 recent PA0 queue는 pre-restart old hidden backlog row가 계속 채움

대표 sample time:

- `2026-03-31T19:31:03`
- `2026-03-31T19:39:44`
- `2026-03-31T19:39:55`
- `2026-03-31T19:40:04`
- `2026-03-31T19:40:14`

## 5. current-build replay는 성공

representative backlog row `2026-03-31T19:31:03`을 current build에 다시 태우면
아래처럼 relief contract가 정상적으로 나온다.

```text
check_display_ready = True
check_stage = BLOCKED
display_score = 0.82
display_repeat_count = 2
chart_event_kind_hint = WAIT
chart_display_mode = wait_check_repeat
chart_display_reason = btc_structural_probe_energy_soft_block_as_wait_checks
blocked_display_reason = energy_soft_block
```

즉 이번 refreeze의 결론은 “구현 실패”가 아니라
“runtime recurrence 부재 때문에 queue가 아직 old backlog 중심으로 남아 있다”이다.

## 6. must-hide main axis 변화

latest must-hide는 더 이상 NAS no-probe family가 아니라 아래 family가 주도한다.

```text
XAUUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + xau_second_support_buy_probe = 14
BTCUSD + lower_rebound_probe_observe + probe_promotion_gate + probe_not_promoted + btc_lower_buy_conservative_probe = 1
```

즉 다음 PA1 reopen point는 exact BTC structural recurrence 재확인 또는 XAU/BTC probe leakage 정리다.
