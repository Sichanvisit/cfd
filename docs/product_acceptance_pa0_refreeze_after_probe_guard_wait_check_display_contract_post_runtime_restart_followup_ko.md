# Product Acceptance PA0 Refreeze After Probe-Guard Wait Check Display Contract Post-Runtime-Restart Follow-Up

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는
`probe_guard_wait_as_wait_checks`
계약 반영 이후,
실행 중이던 `cfd main.py`를 새 코드로 재시작한 다음
fresh runtime row와 PA0 baseline refreeze를 다시 확인한 기록이다.

즉 이번 문서는 아래 질문에 답한다.

```text
live runtime restart 이후에는
WAIT + repeated checks contract row가 실제로 찍히는가?
그리고 그 row가 PA0 queue에서 빠지는가?
```

## 2. 실행 기록

확인한 주요 시각:

- 기존 `main.py` 프로세스 시작 시각:
  - `2026-03-31T12:34:05`
- 새 contract 코드 수정 시각:
  - [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) `2026-03-31T16:15:14`
  - [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) `2026-03-31T16:15:58`
- 재시작한 새 `main.py` 프로세스 시작 시각:
  - `2026-03-31T16:52:46`

즉 이전까지 fresh row에 hint가 없었던 핵심 이유는
live runtime이 수정 전 프로세스였기 때문이다.

## 3. restart 이후 fresh row 확인

재시작 후 latest runtime / entry row에서는
target family가 아래처럼 실제로 기록됐다.

대표 BTC row:

- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

대표 row 시각:

- `2026-03-31T16:53:38`
- `2026-03-31T16:53:50`
- `2026-03-31T16:53:58`
- `2026-03-31T16:54:07`

recent 120-row window 기준 집계:

- `BTCUSD`: `hint_rows = 4`, `wait_check_rows = 4`
- `NAS100`: `hint_rows = 0`, `wait_check_rows = 0`
- `XAUUSD`: `hint_rows = 0`, `wait_check_rows = 0`

즉 새 contract row가 live runtime에서 실제로 생성되는 것은 확인됐다.

## 4. PA0 refreeze 결과

재시작 후 baseline을 다시 얼렸을 때,
global summary count는 그대로였다.

- `must_show_missing_count = 15`
- `must_hide_leakage_count = 15`
- `must_block_candidate_count = 12`

즉 total count 기준으로는 아직 변화가 없다.

## 5. queue 관점 결론

하지만 이번 follow-up의 핵심은 total count보다
`accepted wait-check row가 queue에 들어갔는가` 여부다.

결론은 아래가 맞다.

```text
새로 생성된 BTC WAIT + repeated checks row는
PA0 queue에 들어가지 않았다.
```

확인 결과:

- `must_show_missing` 안의 `btc_wait_relief` row: `0`
- `must_hide_leakage` 안의 `btc_wait_relief` row: `0`
- `must_block_candidates` 안의 `btc_wait_relief` row: `0`

즉 accepted wait-check relief skip 로직은 실제 fresh row에 대해 정상 작동했다.

## 6. 왜 total count는 그대로인가

이번 refreeze에서 count가 그대로인 이유는
accepted wait-check row가 queue에 남아서가 아니다.

현재 dominant queue는 다른 family가 채우고 있다.

대표 예:

- `must-hide_leakage`
  - `NAS100 conflict_box_upper_bb20_lower_lower_support_confirm + forecast_guard + observe_state_wait + PROBE + visible`
  - `12 / 15`
- 같은 queue 안의 BTC visible middle-anchor family
  - `3 / 15`

즉 이번 단계의 결론은 아래다.

- `WAIT + repeated checks` row는 실제로 생성됐다
- 그 row는 queue에서 실제로 제외됐다
- 하지만 total count는 다른 leakage family가 채워서 그대로다

## 7. 해석

이번 follow-up은 구현 검증 관점에서 중요한 전환점이다.

이제는 더 이상

- "새 contract가 runtime에 안 찍힌다"
- "PA0 skip 로직이 안 먹는다"

를 의심할 필요가 없다.

남은 문제는
`accepted wait-check relief family`
가 아니라
`다른 NAS/BTC leakage family`
를 다음 PA1 follow-up 대상으로 좁히는 일이다.

## 8. 다음 reopen point

다음 순서는 아래가 자연스럽다.

1. `NAS conflict visible` family를 PA1 follow-up 우선순위로 올린다
2. BTC middle-anchor visible 잔여 `3`개가 같은 축인지 별도 축인지 나눈다
3. 그 뒤 PA0 baseline을 다시 얼려 total count가 줄어드는지 본다

## 9. 한 줄 요약

```text
runtime restart 이후
BTC WAIT + repeated checks contract row는 live에서 실제로 생성됐고,
그 row는 PA0 queue에서 정상적으로 제외됐다.
이제 남은 건 total count를 채우는 다른 leakage family를 다음 PA1 대상으로 좁히는 일이다.
```
