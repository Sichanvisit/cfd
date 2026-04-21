# Product Acceptance PA0 Refreeze After Sell Entry-Gate Wait Display Contract Follow-Up Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## 1. first fresh follow-up

policy mirror만 올린 뒤 first restart에서 exact fresh row가 실제로 들어왔다.

대표 row:

- `2026-04-01T16:42:10`
- `XAUUSD + upper_reject_mixed_confirm + pyramid_not_in_drawdown`

stored result:

- `consumer_check_display_ready = False`
- `consumer_check_stage = BLOCKED`
- `chart_event_kind_hint = ""`
- `chart_display_mode = ""`
- `chart_display_reason = ""`

이 시점의 해석은:

- chart wait reason 추가만으로는 충분하지 않았고
- hidden baseline을 modifier가 다시 살리는 보강이 더 필요했다

## 2. hidden-restore follow-up

그래서 follow-up으로 다음을 추가했다.

- entry-gate wait policy에 `restore_hidden_display = true`
- restore stage를 `OBSERVE`로 고정
- `modifier_primary_reason = chart_wait_visibility_restore` 경로 추가

## 3. second restart watch

second restart:

- out log: [cfd_main_restart_20260401_164913.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_164913.out.log)
- err log: [cfd_main_restart_20260401_164913.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_164913.err.log)

watch 결과:

- cutoff: `2026-04-01T16:49:12`
- row count: `1655 -> 1725`
- latest row time: `2026-04-01T16:51:59`
- exact `NAS/XAU entry-gate` recurrence: `0`

즉 second restart 뒤에는 target family가 short watch 안에 다시 안 떠서, 새 reason이 live CSV에 실제 찍혔는지까지는 아직 확인하지 못했다.

## 4. current-build replay 재확인

first blank fresh row `2026-04-01T16:42:10`을 current build에 다시 태우면 결과는 정상이다.

- `check_display_ready = true`
- `check_stage = OBSERVE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks`

즉 현재 결론은:

- live blank 증상은 재현되어 원인이 식별됐고
- 코드 follow-up은 반영됐으며
- exact second fresh recurrence만 다시 기다리면 된다

## 5. 현재 pending

pending은 딱 하나다.

- exact fresh `NAS/XAU sell entry-gate` row가 다시 뜰 때
- live flat payload에 새 wait reason이 실제 기록되는지 확인

그 전까지 PA0 current residue는 old blank backlog로 해석하는 것이 맞다.
