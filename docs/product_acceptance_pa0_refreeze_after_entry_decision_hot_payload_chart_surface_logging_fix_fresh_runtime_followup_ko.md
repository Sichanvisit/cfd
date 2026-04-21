# Product Acceptance PA0 Refreeze After Entry-Decision Hot Payload Chart Surface Logging Fix Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## fresh runtime 확인 결과

active [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv) 확인 결과:

- last row time: `2026-04-01T15:55:50`
- total rows: `22`
- recent non-empty `chart_display_reason` rows: `6`

header에도 아래 flat column이 실제로 생겼다.

- `consumer_check_display_score`
- `consumer_check_display_repeat_count`
- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

## direct evidence

fresh XAU row에서 아래 값이 flat CSV surface에 직접 기록됐다.

- `WAIT`
- `wait_check_repeat`
- `xau_upper_reject_confirm_energy_soft_block_as_wait_checks`
- `xau_upper_reject_confirm_forecast_wait_as_wait_checks`

즉 `consumer_check_state_v1 -> hot payload -> CSV header` 흐름은 실제 runtime에서 연결됐다.

## 남은 blank row 해석

같은 active window에서 일부 BTC / NAS row는 여전히 blank였다.

대표 특징:

- nested `consumer_check_state_v1`까지 `chart_event_kind_hint / chart_display_mode / chart_display_reason`가 blank
- `blocked_display_reason`만 남아 있는 row가 존재

이건 이번 logging fix 이후에는 다음처럼 해석하는 것이 맞다.

- flat surface 누락 문제는 해결됨
- 이후 blank row는 hot payload 문제보다 해당 family logic이 아직 wait/display reason을 올리지 못한 경우에 가깝다

## 다음 판단

이제부터 PA1 follow-up에서 필요한 것은
`fresh exact row가 뜨는지`만 보는 것이 아니라,
`fresh row가 떠도 nested chart surface가 blank인지`를 같이 보는 것이다.

그래야 residue를
`logging 축`이 아니라 `modifier / policy 축`으로 바로 좁힐 수 있다.
