# Product Acceptance PA1 NAS Upper-Break-Fail Confirm Energy Soft-Block Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목표 축

이번 PA1 하위축의 대상 family는 아래다.

- `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`

직전 PA0 기준으로 이 family는 아래 queue를 채우고 있었다.

- `must_block_candidates = 12`

raw row를 보면 이미 `display_ready = True`, `check_stage = BLOCKED`, `blocked_display_reason = energy_soft_block` 상태인데,
chart contract가 비어 있어서 PA0에서는 block backlog로만 쌓이는 상황이었다.

## 2. 이번 축의 해석

이 family는 숨겨야 하는 leakage가 아니라 아래처럼 본다.

- upper break-fail confirm은 이미 방향성이 분명함
- 다만 `energy_soft_block` 때문에 execution은 아직 막힘
- 따라서 chart에는 `blocked but watchable wait`로 보여야 함

즉 entry는 아니지만 `WAIT + repeated checks`로 chart에 올라가야 한다.

## 3. 타겟 계약

이번 축의 최종 chart 계약은 아래다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks`

대표 replay에서는 아래도 같이 유지돼야 한다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`

## 4. 대표 근거

Representative replay row:

- `2026-04-01T01:36:21`

current build / resolve 결과:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks`

## 5. 구현 owner

- `backend/trading/chart_flow_policy.py`
- `backend/services/consumer_check_state.py`
- `scripts/product_acceptance_pa0_baseline_freeze.py`
- `tests/unit/test_consumer_check_state.py`
- `tests/unit/test_chart_painter.py`
- `tests/unit/test_product_acceptance_pa0_baseline_freeze.py`

## 6. 종료 기준

이번 축은 아래 두 단계로 본다.

1. 코드/회귀/replay에서 새 wait contract가 닫히는 것
2. fresh live exact row 재발 뒤 PA0 refreeze에서 block queue가 실제로 줄어드는 것

현재는 1단계는 닫혔고, 2단계는 fresh exact recurrence 대기 상태다.
