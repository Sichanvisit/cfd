# PA7 Round-8 Moderate Protective Backfill WAIT Patch

## 목적

`PA7 review queue`의 최상단에 남아 있던 `NAS/XAU continuation_hold_surface + RUNNER_CHECK + open_loss_protective + FULL_EXIT -> WAIT` 잔여 그룹을 아주 좁은 예외로 줄인다.

이번 패치는 `strong full-exit`를 건드리지 않고, `moderate protective backfill loss`만 `WAIT`로 재분류하는 것을 목표로 한다.

## 관찰

남은 잔여 row는 공통적으로 아래 특징을 보였다.

- `source in {open_trade_backfill, closed_trade_hold_backfill, closed_trade_runner_backfill}`
- `surface_name = continuation_hold_surface`
- `checkpoint_type = RUNNER_CHECK`
- `checkpoint_rule_family_hint = open_loss_protective`
- `current_profit < 0`
- `giveback_ratio >= 0.95`
- `runtime_hold_quality_score ~= 0.30`
- `runtime_partial_exit_ev ~= 0.44`
- `runtime_full_exit_risk ~= 0.56`
- `reversal - continuation ~= 0.06`
- `top gap ~= 0.12`

문제는 이 row들이 기존 `backfill_open_loss_protective_wait_retest` 조건 자체는 거의 만족해도,
더 앞쪽의 `full_exit_allowed`가 먼저 켜져서 `FULL_EXIT`로 확정된다는 점이었다.

## 패치 원칙

`full_exit_allowed`를 전역적으로 약하게 만들지 않는다.

대신 아래 조건을 만족하는 `moderate protective backfill loss`에 대해서만
`full_exit_allowed`보다 먼저 `WAIT` 예외를 둔다.

- `hold_score >= 0.30`
- `partial_score >= 0.44`
- `0.54 <= full_exit_score <= 0.57`
- `abs(continuation - reversal) <= 0.08`
- `gap <= 0.125`

즉:

- `strong full-exit`
- `extreme pressure`
- `deep reversal`

은 그대로 두고,

- `moderate backfill protective loss`
- `partial/hold가 아직 살아 있는 late retest`

만 `WAIT`로 되돌린다.

## 변경 파일

- `backend/services/path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_dataset.py`

## 기대 효과

- `NAS/XAU open_loss_protective FULL_EXIT -> WAIT` 잔여 top group 축소
- `PA7 review queue` 상단 mismatch 더 감소
- `strong protective full-exit` 샘플은 그대로 유지
