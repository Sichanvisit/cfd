# Product Acceptance PA1 XAU Upper-Reject Probe Promotion Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목표 축

이번 PA1 하위축의 대상 family는 아래다.

- `XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`

직전 PA0 기준으로 이 family는 아래 queue를 채우고 있었다.

- `must_show_missing = 15`
- `must_block_candidates = 5`

핵심 문제는 `probe scene`이 이미 붙어 있고 `promotion gate`만 남아 있는 WAIT family가
`xau_upper_reject_cadence_suppressed`로 다시 숨겨지면서 chart에서 사라진다는 점이었다.

## 2. 이번 축의 해석

이 family는 `leakage`가 아니라 아래처럼 본다.

- 아직 entry로 승격되지는 않음
- `probe_not_promoted`라서 계속 확인은 필요함
- `xau_upper_sell_probe`가 이미 붙어 있어 구조적 대기 신호임
- 따라서 chart에는 `WAIT + repeated checks`로 보여야 함

즉 방향성 SELL ready가 아니라 `WAIT contract`로 올리는 축이다.

## 3. 타겟 계약

이번 축의 최종 chart 계약은 아래다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_promotion_wait_as_wait_checks`

추가로 resolve 단계에서는 이 family가 repeated runtime에서도
`xau_upper_reject_cadence_suppressed`로 다시 꺼지지 않아야 한다.

## 4. 대표 근거

Representative replay row:

- `2026-04-01T01:11:30`

fresh live exact row:

- `2026-04-01T01:16:23`

두 경우 모두 기대 surface는 동일하다.

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = probe_promotion_gate`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_promotion_wait_as_wait_checks`

## 5. 구현 owner

- `backend/trading/chart_flow_policy.py`
- `backend/services/consumer_check_state.py`
- `scripts/product_acceptance_pa0_baseline_freeze.py`
- `tests/unit/test_consumer_check_state.py`
- `tests/unit/test_chart_painter.py`
- `tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

## 6. 종료 기준

이번 축은 아래가 닫히면 성공으로 본다.

1. representative replay에서 새 wait contract가 build/resolve 둘 다 유지됨
2. live fresh exact row에서도 새 reason이 실제로 기록됨
3. PA0 refreeze에서 target family의 `must_block`이 `0`으로 내려감
4. `must_show`는 recent window turnover에 따라 추가 감소를 확인함
