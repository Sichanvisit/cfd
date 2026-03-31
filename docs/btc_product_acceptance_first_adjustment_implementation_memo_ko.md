# BTC Product Acceptance First Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 이번 패스에서 바꾼 것

변경 파일:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

핵심 변화:

- BTC 전용 `display importance` helper 추가
- 공통 importance 연결에 BTC 포함
- BTC lower / structural rebound 장면 uplift 추가

## 2. 이번 패스의 해석

### 2-1. lower recovery start

BTC BUY에서

- `lower_rebound_probe_observe`
- `lower_rebound_confirm`
- `probe_scene_id = btc_lower_buy_conservative_probe`

가 lower context에 있으면 `high` importance로 본다.

즉:

- stage는 owner에 따라 `PROBE` 또는 `OBSERVE`일 수 있어도
- chart에는 `3개 체크`가 가능하다

### 2-2. structural rebound

BTC BUY에서

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `probe_scene_id = btc_lower_buy_conservative_probe`

가 lower / middle reclaim 문맥이면 `medium`으로 본다.

즉:

- chart에는 `2개 체크`

### 2-3. upper continuation

BTC upper continuation은 첫 패스에서 uplift하지 않는다.

즉:

- 기본 `1개 체크`
- confetti 방지

## 3. 이번 패스에서 의도적으로 안 바꾼 것

아래 보호장치는 그대로 유지했다.

- `btc_lower_probe_downgrade`
- `btc_lower_probe_late_downgrade`
- `btc_lower_structural_cadence_suppressed`
- `btc_lower_probe_cadence_suppressed`

이유:

- 첫 패스 목표는 `좋은 자리 살리기`
- 목표가 `lower probe 반복 억제 해제`는 아니기 때문

## 4. 테스트 결과

실행:

- `pytest tests/unit/test_consumer_check_state.py tests/unit/test_chart_painter.py tests/unit/test_entry_service_guards.py tests/unit/test_entry_engines.py -q`
- `pytest tests/unit -q`

결과:

- targeted: `183 passed`
- full unit: `1154 passed, 127 warnings`

## 5. 다음 확인 포인트

다음 BTC screenshot에서 아래를 본다.

- lower recovery가 충분히 살아났는지
- structural rebound가 2개 수준으로 보이는지
- upper continuation이 과하게 늘어나지 않는지
- lower cadence suppression은 여전히 잘 작동하는지
