# Product Acceptance PA0 Refreeze After XAU Upper Reject Mixed Guard Wait Visibility Relief Delta

작성일: 2026-03-31 (KST)

## 비교 기준

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_171330.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_171330.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

## 새 refreeze 시점

- `generated_at = 2026-03-31T17:14:42`

## 요약

이번 refreeze에서 baseline 총량은 아래처럼 유지됐다.

- `must_show_missing_count = 15`
- `must_hide_leakage_count = 15`
- `must_block_candidate_count = 12`
- `divergence_seed_count = 1`

즉 이번 XAU mixed confirm relief가
즉시 queue 총량 감소로 드러난 것은 아니다.

## 왜 총량이 바로 안 줄었는가

핵심 이유는 recent runtime window에
이번 target family가 아직 다시 나타나지 않았기 때문이다.

재시작 이후 recent check:

- `main.py` running since `2026-03-31 17:09:49`
- rows since restart: `69`
- per symbol: `23 / 23 / 23`
- `XAUUSD + upper_reject_mixed_confirm + barrier_guard + observe_state_wait`: `0`
- `chart_display_reason = xau_upper_reject_mixed_guard_wait_as_wait_checks`: `0`

즉 코드는 live에 올라갔지만
recent window가 아직 이 contract를 찍을 장면을 만나지 않았다.

## 현재 queue composition

### must-show missing

현재 `15`개 중 `14`개는 아래 family다.

- `XAUUSD`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = xau_upper_sell_probe`
- `display_ready = False`

### must-hide leakage

현재 `15`개 전부 아래 family다.

- `NAS100`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = probe_promotion_gate`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`
- `check_stage = PROBE`
- `display_ready = True`

### must-block candidates

현재 `12`개는 아래 구성이 섞여 있다.

- XAU energy soft block hidden `7`
- BTC structural blocked `3`
- NAS outer-band blocked `2`

## 해석

이번 delta는 두 가지를 동시에 보여준다.

1. XAU mixed confirm guard-wait relief 구현 자체는 완료됐다
2. current recent queue는 이미 다음 family로 이동했다

따라서 이번 단계의 결과를
`실패`로 보기보다는
`구현 완료 + 다음 PA1 reopen point 노출`
로 보는 게 맞다.

## 다음 reopen point

다음 PA1 후보는 아래 둘이다.

1. `XAU upper_reject_probe_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
2. `NAS upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`

현 시점 우선순위는 must-show를 크게 채우는 1번이 조금 더 앞이다.

## 한 줄 요약

```text
이번 refreeze는 XAU mixed confirm relief가 아직 recent live window에 안 들어왔음을 확인했고,
대신 다음 PA1 주력 queue가 XAU energy-soft-block hidden과 NAS probe leakage로 넘어갔음을 고정했다.
```
