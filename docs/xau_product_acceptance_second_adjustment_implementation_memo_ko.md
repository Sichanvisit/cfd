# XAU Product Acceptance Second Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 이번 2차 패스의 목표

XAU는 NAS/BTC보다 `왔다갔다하는 장세`에서 차트가 더 쉽게 난잡해질 수 있다.

그래서 이번 2차는 scene 자체를 더 여는 패스가 아니라,
`state/position energy 기반으로 혼잡 구간을 soft-cap` 하는 패스로 잡았다.

핵심 의도는 아래다.

- 좋은 자리 uplift는 유지
- 혼잡/왕복 구간이면 importance를 한 단계 낮춤
- 그래서 `좋은 자리만 남고, confetti는 줄이는` 방향으로 간다

## 2. 이번 패스에서 실제로 쓴 자료

이번 2차는 아래 자료를 같이 본다.

- `position_snapshot_v2.interpretation`
- `position_snapshot_v2.energy`
- `state_vector_v2`

실제로 사용한 핵심 값:

- `middle_neutrality`
- `position_conflict_score`
- `lower_position_force`
- `upper_position_force`
- `fast_exit_risk_penalty`
- `conflict_damp`

## 3. 해석 방식

### 3-1. strong directional context

아래가 같이 맞으면 `강한 방향 우위`로 본다.

- side와 bias label이 맞음
- 해당 side force가 충분히 큼
- opposing force보다 우위
- `middle_neutrality`와 `position_conflict_score`가 낮음

이 경우에는 high importance를 그대로 살릴 수 있다.

### 3-2. chop pressure

아래 중 하나라도 강하면 `혼잡/왕복 pressure`로 본다.

- `middle_neutrality` 높음
- `position_conflict_score` 높음
- `fast_exit_risk_penalty` 높음
- `conflict_damp` 낮고 directional context도 약함

이 경우에는 XAU importance를 한 단계 낮춘다.

## 4. 실제 결과

- XAU second support medium 장면
  - chop pressure가 강하면 `2개 -> 1개`
- XAU upper reject high 장면
  - chop pressure가 강하면 `3개 -> 2개`

즉:

- 좋은 자리 uplift는 유지
- 혼잡 구간이면 `high -> medium`, `medium -> none`

## 5. 추가된 표면

`consumer_check_state_v1`에 아래 디버그 표면을 추가했다.

- `display_importance_adjustment_reason`

현재 XAU chop soft-cap reason은:

- `xau_state_chop_soft_cap`

## 6. 테스트 결과

실행:

- `pytest tests/unit/test_consumer_check_state.py tests/unit/test_chart_painter.py tests/unit/test_entry_service_guards.py tests/unit/test_entry_engines.py -q`
- `pytest tests/unit -q`

결과:

- targeted: `187 passed`
- full unit: `1158 passed, 127 warnings`

## 7. 다음 확인 포인트

다음 XAU screenshot에서는 아래를 본다.

- second support / middle reclaim이 여전히 살아 있는지
- 혼잡 구간에서 lower/upper가 같이 confetti처럼 늘지 않는지
- upper reject 핵심은 남고, 의미 없는 왕복 체크는 줄었는지
