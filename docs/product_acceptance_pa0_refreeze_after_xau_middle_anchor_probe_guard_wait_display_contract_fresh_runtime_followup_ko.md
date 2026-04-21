# Product Acceptance PA0 Refreeze After XAU Middle-Anchor Probe Guard Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## fresh runtime 상태

- `entry_decisions.csv` latest row time: `2026-04-01T15:32:54`
- recent target family row count: `28`

하지만 recent target family의 latest rows는 모두 old blank row였다.

대표 latest rows:

- `2026-04-01T15:05:19`
- `2026-04-01T15:05:30`
- `2026-04-01T15:05:43`
- `2026-04-01T15:06:17`
- `2026-04-01T15:06:55`
- `2026-04-01T15:07:33`
- `2026-04-01T15:07:49`
- `2026-04-01T15:09:37`

이 rows들의 stored CSV 값은 모두 다음이었다.

- `chart_event_kind_hint = ""`
- `chart_display_mode = ""`
- `chart_display_reason = ""`

## current-build replay

대표 row `2026-04-01T14:59:07`을 current build로 다시 태우면:

- build:
  - `check_side = BUY`
  - `check_stage = OBSERVE`
  - `chart_event_kind_hint = WAIT`
  - `chart_display_mode = wait_check_repeat`
  - `chart_display_reason = probe_guard_wait_as_wait_checks`
- resolve:
  - `blocked_display_reason = middle_sr_anchor_guard`
  - `chart_display_reason = probe_guard_wait_as_wait_checks`

## 해석

이 follow-up은 production bug를 뜻하지 않는다.

- exact family는 current build에서 이미 generic contract로 정상 resolve된다.
- 다만 restart 이후 watch 구간에서 exact same family fresh recurrence가 다시 나오지 않아 live CSV 증빙이 늦어지고 있다.
- 그래서 PA0 queue는 아직 `4 / 4`가 유지된다.

다음 체크포인트는 exact fresh row가 한 번 더 나오면, 그 시점에서 `chart_display_reason = probe_guard_wait_as_wait_checks`가 실제로 live CSV에 찍히는지 확인하고 바로 PA0를 다시 얼리는 것이다.
