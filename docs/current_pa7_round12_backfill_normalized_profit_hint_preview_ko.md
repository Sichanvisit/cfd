# PA7 Round-12 Backfill Normalized Profit Hint Preview

## 목적

`mixed_backfill_value_scale_review`는
rule patch를 더 하기 전에
`backfill source의 current_profit 스케일이 live source와 같은가`
를 먼저 분리해서 봐야 한다.

이번 round는 정규화를 실제 규칙에 적용하지 않고,
`processor preview`에만 반영한다.

즉 지금은:

- raw 분류: `mixed_backfill_value_scale_review`
- normalized preview 분류: `mixed_wait_boundary_review` 또는 `resolved_by_current_policy`

를 같이 보게 하는 단계다.

## 추가 개념

### 1. backfill_profit_scale_ratio_hint

같은 `group_key` 안에서

- backfill source의 `abs(current_profit)` 중앙값
- non-backfill source의 `abs(current_profit)` 중앙값

을 비교한 비율이다.

예:

- backfill median = `186.0`
- non-backfill median = `3.17`
- ratio = `58.675079`

이 값이 크면 raw `current_profit`은 scale이 섞였을 가능성이 높다.

### 2. normalized_backfill_abs_profit_median

preview 전용으로

`backfill_abs_profit_median / backfill_profit_scale_ratio_hint`

를 계산해서,
backfill row를 live source scale로 대충 맞춰보면 어느 정도인지 본다.

이 값은 아직 rule resolver에 쓰지 않는다.

## processor에 반영하는 것

mixed backfill 그룹 row에 아래 preview 필드를 추가한다.

- `backfill_profit_scale_ratio_hint`
- `backfill_abs_profit_median`
- `non_backfill_abs_profit_median`
- `normalized_backfill_abs_profit_median`
- `normalized_preview_state`
- `normalized_preview_review_disposition`
- `normalized_preview_recommendation`

## preview 해석

### `normalized_preview_review_disposition = mixed_wait_boundary_review`

의미:

- raw 값으로 보면 backfill scale 문제가 먼저 보이지만
- scale을 대충 맞춰서 보면
  그 다음 남는 핵심은 `WAIT boundary` 문제라는 뜻

즉 다음 패치는
backfill raw profit 자체가 아니라
`WAIT / PARTIAL_EXIT` 경계 쪽으로 봐야 한다.

### `normalized_preview_review_disposition = resolved_by_current_policy`

의미:

- raw 그룹은 backfill scale 때문에 커 보였지만
- scale noise를 빼면 현재 policy replay만으로도 충분하다는 뜻

## 현재 의도

이 round는 아직 정규화 적용 단계가 아니다.

지금은 오직:

- `raw mismatch`
- `backfill scale issue`
- `normalization 후에도 남는 boundary issue`

를 분리해서 다음 round의 초점을 좁히기 위한 preview 단계다.
