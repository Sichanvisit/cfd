# PA7 Round 3: Runner Trim Boundary Patch

## 목적

`PA7 review processor` 최신 기준 top actionable group은 아래였다.

- `BTCUSD | follow_through_surface | FIRST_PULLBACK_CHECK | runner_secured_continuation | PARTIAL_THEN_HOLD -> hindsight PARTIAL_EXIT`
- `NAS100 | continuation_hold_surface | RUNNER_CHECK | runner_secured_continuation | PARTIAL_THEN_HOLD -> hindsight PARTIAL_EXIT`

즉 current policy replay도 여전히 `PARTIAL_THEN_HOLD`를 유지하고 있었고,
현재 `runner` 쪽에서 가장 먼저 손대야 할 경계는

- `runner 유지/일부 확보`
vs
- `바로 trim`

의 초기 구간이었다.

## 관찰된 패턴

문제 row는 공통으로 아래 특성을 가졌다.

- `management_row_family = runner_secured_continuation`
- `unrealized_pnl_state = OPEN_PROFIT`
- `partial_exit_ev`는 높음 (`~0.54+`)
- `hold_quality`는 낮음 (`~0.32~0.39`)
- `reversal_odds > continuation_odds`
- `full_exit`까지는 아님
- 기존 resolver는 이 구간을 `score_leader::partial_then_hold`로 남기는 경우가 있음

반면 healthy `PARTIAL_THEN_HOLD` row는:

- continuation 우세
- hold quality 더 높음
- `partial_then_hold`가 확실히 더 앞섬

## Round 3 규칙

`path_checkpoint_action_resolver.py`

`PARTIAL_THEN_HOLD` branch 전에 아래 narrow rule을 추가한다.

- `row_family == runner_secured_continuation`
- `pnl_state == OPEN_PROFIT`
- `partial_score >= 0.52`
- `hold_score <= 0.40`
- `reversal >= continuation + 0.04`
- `partial_then_hold_score <= partial_score + 0.08`

그러면:

- `PARTIAL_EXIT`
- reason: `runner_secured_early_trim_bias`

로 보정한다.

## 의도

이 패치는 `runner_secured_continuation` 전체를 trim 쪽으로 보내는 것이 아니다.

오직:

- 이미 수익 중이지만
- hold 품질은 낮고
- reversal이 continuation보다 앞서고
- partial exit이 거의 동률 이상으로 강한

“초기 trim이 더 맞는 runner 구간”만 잡는다.

## 기대 효과

- `BTC/NAS runner_secured_continuation` top mismatch 축소
- `PARTIAL_THEN_HOLD` 과잉을 줄이고
- 다음 PA7 review가 `early loss trim` 또는 `HOLD->WAIT` 계열로 자연스럽게 이동

## 검증

- resolver unit test
- runtime-proxy dataset unit test
- PA7 processor rebuild
- checkpoint eval / review packet 재확인
