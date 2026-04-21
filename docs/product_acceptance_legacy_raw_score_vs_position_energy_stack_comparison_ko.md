# legacy raw score vs current position-energy stack 비교

## 한 줄 결론

지금 런타임에서 `buy_score / sell_score / entry_threshold`는 아직 남아 있지만, **메인 해석축은 이미 `position -> response -> state -> forecast -> observe/guard` 쪽으로 이동한 상태**입니다.

즉:

- `raw score`는 호환성과 디버그를 위한 **legacy surface**
- `position-energy stack`은 현재 런타임 설명의 **main surface**

## 왜 `359 / 292`가 나와도 그 자체로 메인 의미가 아니냐

`buy_score / sell_score`는 예전 `BB breakout + flow + trigger` 누적형 가산 점수 구조를 아직 그대로 포함합니다.
그래서 `300+` 값 자체는 코드상 비정상이 아닐 수 있습니다.

하지만 현재 실제 진입 해석은 아래 정보가 더 우선입니다.

- `position_snapshot_v2`
- `response_vector_v2`
- `state_vector_v2`
- `transition_forecast_v1`
- `observe_confirm_v2`
- `blocked_by`
- `action_none_reason`
- `consumer_check_*`

즉 이제는 `점수가 높다`보다 `어디에 있고`, `어떤 반응이 나왔고`, `state/forecast가 어느 쪽을 지지하며`, `observe/guard가 왜 막았는지`가 더 중요합니다.

## 비교표

| 구분 | legacy raw score stack | current position-energy stack |
|---|---|---|
| 중심 질문 | `점수가 몇 점인가?` | `지금 어디에 있고 어떤 반응/상태/예측이 나왔는가?` |
| 주 입력 | `structure`, `flow`, `vp`, `trigger`, `topdown` | `position`, `response`, `state`, `forecast`, `observe_confirm` |
| 대표 필드 | `buy_score`, `sell_score`, `wait_score`, `entry_threshold` | `position_snapshot_v2`, `position_energy_v2`, `response_vector_v2`, `state_vector_v2`, `transition_forecast_v1`, `observe_confirm_v2` |
| 해석 단위 | 가산 점수 우위 | 위치, 힘, 반응, guard, readiness |
| 진입 설명 | `threshold 넘었는가` | `entry_ready / display_ready / blocked_by / action_none_reason / wait_policy_state` |
| 장점 | 기존 호환성, 빠른 raw 비교 | 현재 구조와 실제 판단축에 더 가깝다 |
| 한계 | 현재 메인 의미를 과대표현하기 쉽다 | 초기엔 필드 수가 많아 보일 수 있다 |
| 현재 역할 | 보조/legacy/debug | 주 설명 표면 |

## 현재 런타임에서 이렇게 읽으면 된다

### 1. 먼저 볼 것

- `position_energy_surface_v1.summary.decision_state`
- `position_energy_surface_v1.summary.state_reason`
- `position_energy_surface_v1.observe`
- `position_energy_surface_v1.readiness`

이 4개를 보면 지금 행이:

- `ENTRY_READY`
- `WAIT`
- `BLOCKED`
- `DISPLAY_READY`
- `INACTIVE`

중 어디에 있는지 빠르게 읽을 수 있습니다.

### 2. 그다음 볼 것

- `position_energy_surface_v1.location`
- `position_energy_surface_v1.position`
- `position_energy_surface_v1.energy`

이 블록은 “지금 lower/upper/middle 어느 쪽 힘이 우세한가”를 읽기 위한 메인 위치 정보입니다.

### 3. 마지막에 참고할 것

- `legacy_raw_score_v1`

여기는 이제:

- 기존 rule/threshold가 어느 정도였는지
- raw score가 어느 쪽으로 더 기울었는지
- threshold 대비 얼마나 멀었는지

를 보는 보조 레이어로 해석하면 됩니다.

## 패치 반영 원칙

이번 정리에서 적용한 원칙은 아래와 같습니다.

- raw score 필드는 **지우지 않는다**
- 대신 `legacy_raw_score_v1`로 **의미를 명시적으로 낮춘다**
- 메인 표면은 `position_energy_surface_v1`로 올린다
- 콘솔 dashboard와 runtime status 모두 같은 surface 언어를 쓰게 맞춘다

## 다른 스레드 전달용 문장

다른 스레드에는 이렇게 전달하면 됩니다.

> 현재 런타임은 raw BB/flow score를 내부 호환용으로 유지하지만, 사용자 기준 메인 판단축은 이미 position-energy/state/forecast 쪽이다. 따라서 runtime 설명은 `legacy_raw_score_v1`보다 `position_energy_surface_v1`을 먼저 읽어야 한다.
