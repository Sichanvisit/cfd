# P4-6B box_relative_position 상세 계획

## 목표

`P4-6A`가 장면 기준 설명 surface였다면,
이번 `P4-6B`는 detector evidence에 `현재 가격이 박스 상단/중단/하단 어디쯤 있는지`를 직접 또는 proxy 방식으로 넣는 단계다.

핵심 목적은 방향 판단을 바꾸는 것이 아니라,
`캔들/박스 위치 대비 방향 해석 불일치`를 더 설명 가능하게 만드는 것이다.

## 왜 지금 이 단계인가

사용자는 차트를 볼 때 힘 수치만 보지 않는다.

- 지금 위치가 박스 상단인지
- 하단 반등인지
- 상단 추격인지

를 먼저 본다.

따라서 detector가 `방향 오판 가능성`이나 `캔들/박스 위치 불일치`를 surface할 때도,
`박스 위치` evidence가 같이 있어야 피드백 품질이 올라간다.

## 범위

이번 단계에서 한다.

- detector evidence에 `box_relative_position`
- detector evidence에 `box_zone`
- detector evidence에 `range_too_narrow`
- detector evidence에 `source_mode`

이번 단계에서 하지 않는다.

- 거래 로직 변경
- DM 상시 노출
- box high / box low를 외부 새 소스로 대규모 연결

## 구현 원칙

첫 버전은 `직접 측정 우선 + runtime proxy fallback`으로 간다.

이유:

- 현재 latest signal payload에는 항상 `box_high`, `box_low`가 직접 있지는 않다
- 하지만 이미 `box_state`, `source_position_in_session_box`, `recent_range_mean`은 들어오고 있다
- 따라서 이번 단계에서는 detector evidence를 먼저 안정적으로 만들고,
  나중에 runtime에 explicit box high/low가 올라오면 direct 계산 비중을 늘린다

## 입력 신호

- `box_state`
- `barrier_state_v1.metadata.semantic_barrier_inputs_v2.runtime_source_inputs.source_position_in_session_box`
- `barrier_state_v1.metadata.semantic_barrier_inputs_v2.secondary_source_inputs.source_recent_range_mean`
- future-ready:
  - `box_relative_position`
  - `current_box_relative_position`
  - `box_range`
  - `atr`

## 계산 규칙

### 1. direct 우선

아래 값이 있으면 direct로 쓴다.

- `box_relative_position`
- `current_box_relative_position`

### 2. proxy fallback

direct 값이 없으면 `box_state`를 수치 proxy로 바꾼다.

- `BELOW` -> `0.05`
- `LOWER` -> `0.18`
- `LOWER_EDGE` -> `0.25`
- `MIDDLE / MID` -> `0.50`
- `UPPER_EDGE` -> `0.75`
- `UPPER` -> `0.82`
- `ABOVE` -> `0.95`

### 3. zone

- `<= 0.25` -> `LOWER`
- `0.25 ~ 0.75` -> `MIDDLE`
- `>= 0.75` -> `UPPER`

### 4. 좁은 박스 예외

가능할 때만 아래를 쓴다.

- `box_range < atr * 0.3` -> `range_too_narrow = True`

지금 runtime payload에 `box_range`, `atr`가 없으면
이 값은 기본적으로 `False`로 두고, future-ready field로 유지한다.

## detector 적용 위치

이번 step에서는 두 군데에 먼저 넣는다.

1. `scene-aware detector`
- force evidence 뒤에 `박스 위치`를 추가

2. `candle/weight detector`
- `why_now_ko`에 현재 박스 위치를 설명형으로 추가
- `evidence_lines_ko`에 `박스 위치`를 추가

## DM 노출 정책

이번 단계에서는 DM 상시 노출 안 한다.

이유:

- `box_relative_position`은 detector evidence로는 가치가 크지만
- 모든 DM에 항상 붙이면 noise가 커질 수 있다

따라서 지금은 detector evidence에만 넣고,
나중에 `P4-6H 복합 불일치`가 붙을 때만 DM 1줄로 surface한다.

## 건드릴 파일

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)
- [test_improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_improvement_log_only_detector.py)

## 출력 예시

```text
- 박스 위치: 상단 영역 (0.82 / state UPPER / proxy / 최근 range 23.17)
```

## 완료 조건

- scene-aware detector evidence에 `박스 위치`가 보인다
- candle/weight detector evidence에 `박스 위치`가 보인다
- direct 값이 없을 때도 `box_state` proxy로 fallback 한다
- 거래 로직은 바뀌지 않는다

## 다음 단계

- `P4-6C` doji-aware wick/body ratio
- `P4-6D` recent_3bar_direction

즉 `P4-6B`는 위치 좌표를 detector evidence에 넣는 단계이고,
다음 단계부터 캔들 구조와 최근 흐름까지 더 직접적인 구조 증거가 붙는다.
