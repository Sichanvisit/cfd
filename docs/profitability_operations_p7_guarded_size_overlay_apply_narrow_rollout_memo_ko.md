# Profitability / Operations P7 Guarded Size Overlay Narrow Apply Memo

작성일: 2026-03-30 (KST)

## 1. 목적

이번 메모의 목적은 `dry_run 누적 -> 좁은 apply` 전환 기준을 고정하는 것이다.

핵심 원칙은 단순하다.

- 먼저 `dry_run`이 실제 entry log에 쌓이는지 확인한다.
- 그다음 첫 apply는 `BTCUSD only`로 제한한다.
- XAUUSD / NAS100은 아직 apply로 올리지 않는다.

## 2. 왜 BTCUSD부터인가

현재 P6/P7 해석 기준으로 보면:

- `XAUUSD`: `stressed / hard_reduce`
- `NAS100`: `stressed / hard_reduce`
- `BTCUSD`: `watch / reduce`

즉 XAU/NAS는 압력이 더 강해서 `review pressure`가 남아 있고, 첫 apply 실험은
상대적으로 좁고 보수적인 `BTCUSD`가 더 적절하다.

## 3. Dry-Run 확인 게이트

좁은 apply로 올리기 전에 아래를 먼저 만족해야 한다.

1. dry-run review에서 `p7_schema_present=true`
2. dry-run review에서 `p7_trace_row_count > 0`
3. `BTCUSD`가 `symbol_dry_run_summary`에 나타난다
4. `BTCUSD` top gate reason이 주로 `dry_run_only` 또는 `no_reduction_needed`다
5. `overlay_source_unavailable`, `symbol_not_matched`가 반복되지 않는다

실무적으로는 아래 정도를 최소 기준으로 본다.

- `BTCUSD dry-run rows >= 20`
- `BTCUSD matched_ratio >= 0.70`

## 4. 첫 Apply 설정

첫 apply는 아래처럼 아주 좁게 간다.

- `ENABLE_P7_GUARDED_SIZE_OVERLAY=true`
- `P7_GUARDED_SIZE_OVERLAY_MODE=apply`
- `P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST=BTCUSD`
- `P7_GUARDED_SIZE_OVERLAY_MAX_STEP=0.10`

즉 target `0.57`을 한 번에 점프하는 게 아니라, 현재 lot 기준 `0.10 cap` step만 허용한다.

## 5. Apply 이후 바로 볼 것

첫 apply 이후에는 바로 아래만 본다.

- `BTCUSD`의 `p7_guarded_size_overlay_v1.applied`
- `p7_size_overlay_effective_multiplier`
- `blocked_pressure_alert` delta
- `BTCUSD` symbol health 변화
- `P4/P5/P6/P7` rerun에서 BTC가 악화되는지

## 6. 아직 하지 않는 것

이번 좁은 apply에서 아직 하지 않는 것:

- `XAUUSD` apply
- `NAS100` apply
- XAU timing rule 수정
- legacy identity gap live change
- auto-adaptation

## 7. 현재 상태

현재는 아직 `dry_run 우선` 상태다.

즉 바로 apply로 넘긴 것이 아니라:

1. overlay code surface를 만들었고
2. `.env`를 `dry_run`으로 올렸고
3. 이제 runtime restart 후 새 row가 쌓이면
4. 그 review 결과를 보고 `BTCUSD only apply`로 간다
