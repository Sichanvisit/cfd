# BTC Product Acceptance Second Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 이번 2차 패스의 목표

BTC 첫 패스는 전반적으로 크게 나쁘지 않았기 때문에,
이번 2차는 아래 두 가지만 미세 보정하는 패스로 잡았다.

- middle reclaim / middle anchor 장면을 조금 더 살리기
- upper breakout/reclaim confirm이 continuation처럼 묻히지 않게 하기

단, 상단 continuation 남발은 여전히 금지한다.

## 2. 이번 패스에서 실제로 바꾼 것

변경 파일:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

핵심 변화:

- BTC `middle_sr_anchor_required_observe`가 lower/middle reclaim 문맥이면 `medium`
- BTC `lower_rebound_confirm`는 upper breakout/reclaim confirm 문맥에서 `medium`
- 기존 `lower_rebound_probe_observe` upper continuation 비과장 원칙은 유지

## 3. 이번 패스의 해석

### 3-1. middle reclaim

이전에는 probe scene이 없으면 BTC middle reclaim 장면이 잘 묻힐 수 있었다.

이번에는 아래 장면을 `2개 체크`까지 허용한다.

- `middle_sr_anchor_required_observe`
- `box_state = MIDDLE`
- `bb_state = MID`

### 3-2. breakout reclaim confirm

이전에는 BTC upper 쪽 장면을 너무 강하게 막다 보니,
상단 continuation뿐 아니라 `실제로 의미 있는 breakout reclaim confirm`까지 묻힐 수 있었다.

이번에는 아래 장면을 `2개 체크`까지 허용한다.

- `lower_rebound_confirm`
- `box_state = UPPER`
- `bb_state = UPPER_EDGE`

단, probe observe upper continuation은 여전히 uplift하지 않는다.

## 4. 그대로 유지한 것

이번 2차에서도 아래 보호장치는 유지했다.

- `btc_lower_probe_downgrade`
- `btc_lower_probe_late_downgrade`
- `btc_lower_structural_cadence_suppressed`
- `btc_lower_probe_cadence_suppressed`

즉 이번 2차는 `살려야 할 자리만 조금 더 살린 패스`이지,
`남발 억제 규칙을 풀어버린 패스`는 아니다.

## 5. 테스트 결과

실행:

- `pytest tests/unit/test_consumer_check_state.py tests/unit/test_chart_painter.py tests/unit/test_entry_service_guards.py tests/unit/test_entry_engines.py -q`
- `pytest tests/unit -q`

결과:

- targeted: `185 passed`
- full unit: `1156 passed, 127 warnings`

## 6. 다음 확인 포인트

다음 BTC screenshot에서는 아래를 본다.

- middle reclaim이 이전보다 더 명확히 보이는지
- breakout reclaim confirm이 continuation에 묻히지 않는지
- 상단 continuation이 여전히 confetti처럼 늘어나지 않는지
