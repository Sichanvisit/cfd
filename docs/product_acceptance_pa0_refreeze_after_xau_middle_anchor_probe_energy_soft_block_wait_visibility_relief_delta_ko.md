# Product Acceptance PA0 Refreeze After XAU Middle Anchor Probe Energy Soft Block Wait Visibility Relief Delta

작성일: 2026-03-31 (KST)

## 1. 비교 대상

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_201555.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_201555.json)
- 최신 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

기준 시각:

- snapshot generated_at = `2026-03-31T20:09:05`
- latest generated_at = `2026-03-31T20:15:55`

관련 구현 문서:

- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)

## 2. baseline summary delta

```text
must_show_missing_count: 15 -> 15
must_hide_leakage_count: 15 -> 15
must_enter_candidate_count: 0 -> 0
must_block_candidate_count: 12 -> 12
divergence_seed_count: 0 -> 0
```

즉 total count 기준으로는 이번 refreeze에서도 즉시 감소는 보이지 않는다.

## 3. target family delta

대상 family:

```text
XAUUSD + middle_sr_anchor_required_observe
+ energy_soft_block + execution_soft_blocked
+ xau_second_support_buy_probe
```

bucket별 변화:

```text
must_show_missing: 11 -> 10
must_block_candidates: 3 -> 7
must_hide_leakage: 0 -> 0
```

즉 queue 기준으로는 여전히 XAU must-show / must-block main axis 중 하나다.

## 4. 왜 direct 감소가 아닌가

post-restart fresh row는 총 `6`건 들어왔지만
exact XAU target family recurrence는 `0건`이었다.

즉:

- 새 코드로 live는 다시 올라감
- representative replay는 성공함
- 하지만 exact family가 fresh window에 다시 안 나옴
- 그래서 recent queue는 old backlog row 조합 변화에 더 크게 좌우됨

결론적으로 이번 delta는 “fresh exclusion 성공”을 직접 보여주는 delta가 아니라
“구현 완료 후에도 runtime recurrence가 아직 없어서 old backlog가 계속 queue를 채우는 상태”를 보여준다.

## 5. 함께 본 다른 축

같은 비교 구간에서 본 다른 변화:

- `BTC structural` family는 `must_show 4 -> 5`, `must_block 4 -> 5`
- `XAU lower_rebound_probe + forecast_guard + probe_not_promoted + xau_second_support_buy_probe` family는 여전히 `0`
- `must_hide`는 `BTC lower_rebound_probe_observe + probe_promotion_gate + probe_not_promoted + btc_lower_buy_conservative_probe`가 `10`
- 나머지 `5`는 `NAS upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`

즉 현재 다음 PA1 메인 reopen point는 XAU old forecast family가 아니라
current must-hide main family 쪽이다.
