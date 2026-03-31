# XAU Product Acceptance First Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 이번 패스에서 바꾼 것

변경 파일:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

핵심 변화:

- XAU 전용 `display importance` helper 추가
- 기존 NAS 전용 importance 연결을 공통 helper로 확장
- XAU lower / second support / upper reject 핵심 장면의 importance uplift 추가

## 2. 이번 패스의 해석

### 2-1. 하단 회복 시작

XAU BUY에서

- `lower_rebound_confirm`
- `lower_rebound_probe_observe`

가 lower context에 있으면 `high` importance로 본다.

즉:

- stage는 owner에 따라 `PROBE`일 수 있어도
- chart에는 `3개 체크`가 가능하다

### 2-2. second support 반등

XAU BUY에서

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `probe_scene_id = xau_second_support_buy_probe`

조합이면 `medium` importance로 본다.

즉:

- chart에는 `2개 체크`

### 2-3. upper reject 핵심

XAU SELL에서

- `upper_reject_confirm`
- `upper_break_fail_confirm`

이 upper context에 있으면 `high`,
그 외 upper reject 전개는 `medium`으로 본다.

즉:

- 핵심 upper reject는 `3개 체크`
- 전개형 upper reject는 `2개 체크`

## 3. 이번 패스에서 의도적으로 안 바꾼 것

아래 보호장치는 그대로 유지했다.

- `xau_upper_reject_guard_wait_hidden`
- `xau_upper_reject_cadence_suppressed`
- `xau_upper_sell_repeat_suppressed`
- `xau_middle_anchor_cadence_suppressed`

이유:

- 첫 패스 목표는 `좋은 자리 살리기`
- 목표가 `상단 reject 억제 해제`는 아니기 때문

## 4. 테스트 결과

실행:

- `pytest tests/unit/test_consumer_check_state.py tests/unit/test_chart_painter.py tests/unit/test_entry_service_guards.py tests/unit/test_entry_engines.py -q`
- `pytest tests/unit -q`

결과:

- targeted: `180 passed`
- full unit: `1151 passed, 127 warnings`

## 5. 다음 확인 포인트

다음 XAU screenshot에서 아래를 본다.

- lower recovery가 충분히 살아났는지
- second support가 2개 수준으로 보이는지
- upper reject 핵심만 살아나고 과표시는 없는지
- wait hidden / cadence suppression은 여전히 잘 작동하는지
