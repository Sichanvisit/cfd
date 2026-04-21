# 세션 인지 방향/지속성 학습 상세 계획

## 1. 목적

이 문서는 단순히 표기를 하나 더 늘리는 계획이 아니다.
지금 시스템을 `패턴 인식` 중심에서 `구조 인식` 중심으로 옮기기 위한 최소 계약을 정의하는 문서다.

핵심 문제는 재료 부족이 아니다. 이미 현재 시스템에는 아래 재료가 있다.

- `box_state`, `previous_box_*`
- `bb_state`
- `HTF / trend / context_conflict`
- `forecast`, `belief`, `barrier`
- `state25`
- `execution_diff`
- `flow history`
- `continuation accuracy`
- `window timebox audit`

즉 지금 부족한 것은 입력이 아니라, **같은 위치를 다른 의미로 읽는 해석 구조**다.

예시:

- 같은 `ABOVE`
  - 미국장에서는 `상승 지속`
  - 아시아장에서는 `false break`
- 같은 `SELL_WATCH`
  - 상단 경계
  - top warning
  - 실제 하락 전환

이 문서는 이 차이를 구조적으로 다루기 위한 최소 annotation 계약과 학습 방향을 정리한다.

## 2. 왜 지금 이 축이 필요한가

현재까지의 시스템은 방향 표기와 실행 정렬을 많이 개선했지만, 여전히 다음 문제가 남아 있다.

1. 같은 box 위치라도 세션에 따라 의미가 달라진다.
2. 방향과 지속성이 아직 같은 축처럼 섞여 읽히는 경우가 있다.
3. 차트에서 `BUY_WATCH`, `SELL_WATCH`가 떠도, 그것이
   - 지속 신호인지
   - 경계 신호인지
   - 전환 신호인지
   구분이 약하다.
4. 운영자가 “이때는 이렇게 했어야 했다”를 남겨도, 그 메모를 공용 학습 데이터로 축적하는 계약이 아직 없다.

즉 지금부터는 `오름/내림`만이 아니라, **이어짐/안 이어짐**, **초기 재개/경계/전환**을 함께 다뤄야 한다.

## 3. 현재까지 확보된 근거

실제 timebox 대조 결과는 이미 이 필요성을 보여준다.

기준 아티팩트:

- [nas_xau_btc_window_timebox_audit_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/nas_xau_btc_window_timebox_audit_latest.json)
- [nas_xau_btc_window_timebox_audit_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/nas_xau_btc_window_timebox_audit_latest.md)

핵심 관찰:

- `NAS100`
  - `2026-04-14 16:36 / 25548.517` 이후는 상승 지속 구조였는데
  - 실제 시스템은 `SELL_WATCH / WAIT / SELL_ENTER`를 과도하게 냈다.
- `XAUUSD`
  - 초반 상승 구간은 과도한 `WAIT/SELL`이 섞였고
  - 중후반 상단 SELL 경계와 하락 전환은 비교적 맞았다.
- `BTCUSD`
  - grind-up 구간을 `WAIT/SELL_PROBE`로 오래 끌었고
  - 후반 전환 구간은 비교적 맞았다.

이건 심볼별 직감 문제가 아니라, **해석 언어가 아직 세션/지속성/phase를 충분히 분리하지 못한 결과**로 보는 게 맞다.

## 4. 기본 원칙

### 4-1. 세션은 방향 결정기가 아니다

세션은 `BUY/SELL`을 직접 결정하면 안 된다.

금지:

- `US = BUY`
- `ASIA = SELL`

허용:

- `US에서는 continuation confidence를 더 높게 본다`
- `ASIA에서는 false-break 가능성을 더 조심한다`

즉 세션은 **bias layer**로만 써야 한다.

### 4-2. direction과 continuation은 분리한다

`UP`인데도 `비지속`일 수 있고, `DOWN`인데도 `반등 경계`일 수 있다.
따라서 `direction`과 `continuation`은 별도 축으로 둔다.

### 4-3. 처음부터 단계 수를 너무 늘리지 않는다

phase는 처음부터 7단계로 시작하지 않는다.
표본 부족과 annotation noise를 막기 위해 **3단계 v1**으로 시작한다.

### 4-4. should-have-done은 혼합형으로 시작한다

전부 수동이면 느리고, 전부 자동이면 오염될 수 있다.
따라서 자동 후보 생성 + 운영자 확인 + confidence 관리 구조로 시작한다.

## 5. 최소 annotation 계약

이 문서에서 제안하는 최소 계약은 다음과 같다.

### 5-1. 계층 구조

#### Level 1: 필수

- `direction_annotation`
  - `UP`
  - `DOWN`
  - `NEUTRAL`
- `continuation_annotation`
  - `CONTINUING`
  - `NON_CONTINUING`
  - `UNCLEAR`

#### Level 2: 핵심

- `continuation_phase_v1`
  - `CONTINUATION`
  - `BOUNDARY`
  - `REVERSAL`

#### Level 3: 보조

- `session_bucket`
- `annotation_invalidators`

이 계층 구조를 유지해야 조합 폭발을 막고, 데이터가 쌓여도 관리가 가능하다.

### 5-2. phase v1 정의

`continuation_phase_v1`는 시간 흐름을 단순하게 표현한다.

- `CONTINUATION`
  - 기존 방향이 유효하고 이어질 가능성이 높은 상태
- `BOUNDARY`
  - 경계/과열/되밀림/재테스트처럼 방향은 있으나 전환 가능성이 높아진 상태
- `REVERSAL`
  - 기존 방향보다 반대 방향 전환이 더 유력한 상태

이후 데이터가 충분히 쌓이면 v2에서 다음처럼 세분화한다.

- `EARLY_RESUME`
- `BREAKOUT_RESUME`
- `TOP_WARNING`
- `TURNING_DOWN`
- `DOWN_CONTINUATION`

하지만 초기 구현은 어디까지나 `CONTINUATION / BOUNDARY / REVERSAL` 3단계로 고정한다.

## 6. session_bucket 정의

KST 기준으로 세션을 아래처럼 정의한다.

### 6-1. v1 기본 버킷

- `ASIA`
  - `06:00 ~ 15:00`
- `EU`
  - `15:00 ~ 21:00`
- `EU_US_OVERLAP`
  - `21:00 ~ 00:00`
- `US`
  - `00:00 ~ 06:00`

### 6-2. v1 원칙

- 첫 버전에서는 **고정 4구간**으로 시작한다.
- 첫 버전에서는 **서머타임 자동 보정은 하지 않는다.**
- 첫 버전에서는 `ASIA_TO_EU_TRANSITION` 같은 별도 전환 버킷을 만들지 않는다.

### 6-3. 이후 확장 조건

아래 조건이 확인되면 그때 전환 구간을 별도 bucket으로 분리한다.

- `R1`, `R5` 결과에서 세션 경계 전후 정확도 차이가 눈에 띄게 다름
- `EU 시작 직후`, `US 시작 직후` 30분이 별도 성격을 가짐
- session-aware accuracy에서 transition 구간의 오차가 지속적으로 큼

즉 전환 구간은 좋은 아이디어이지만, **v1의 일관성을 흔들지 않기 위해 나중 단계에서만 분리**한다.

### 6-4. 주의 사항

- 심볼마다 “주요 세션”의 의미는 다를 수 있지만, 계약 자체는 공용으로 유지한다.
- `session_bucket`은 direction rule이 아니라 annotation과 accuracy 분해용 bias/context 필드로 사용한다.

## 7. should-have-done 학습 축

### 7-1. 왜 필요한가

운영자는 이미 스크린샷과 메모로 “이때는 이렇게 했어야 했다”를 남기고 있다.
하지만 그 메모를 현재는 공용 학습 데이터로 축적하지 못한다.

이 축이 없으면

- 운영자 메모는 일회성
- hindsight는 숫자만 남음
- 공용 규칙 보정은 감에 의존

하게 된다.

### 7-2. 기본 구조

- `expected_direction`
- `expected_continuation`
- `expected_phase_v1`
- `expected_surface`
- `operator_note`
- `annotation_confidence`

### 7-3. confidence 등급

- `MANUAL_HIGH`
  - 운영자가 명시적으로 남긴 강한 정답
- `AUTO_HIGH`
  - hindsight와 execution mismatch가 명확하게 일치하는 자동 후보
- `AUTO_MEDIUM`
  - 방향은 맞지만 WAIT도 일부 합리적일 수 있는 자동 후보
- `AUTO_LOW`
  - 자동 후보이지만 불확실성이 큰 경우

초기 원칙:

- `MANUAL_HIGH`, `AUTO_HIGH`는 바로 학습 후보로 사용 가능
- `AUTO_MEDIUM`은 일정 누적 후 사용
- `AUTO_LOW`는 참고용으로만 보관

## 8. canonical surface가 필요한 이유

현재는 chart, runtime, execution, hindsight가 비슷한 의미를 다른 이름으로 들고 있는 경우가 있다.
이걸 통일하려면 annotation에서 canonical surface를 만들 필요가 있다.

예시:

- `BUY_WATCH + CONTINUING + CONTINUATION`
- `SELL_WATCH + CONTINUING + BOUNDARY`
- `SELL_PROBE + NON_CONTINUING + REVERSAL`

이 surface는 나중에 chart, execution, hindsight, state25 bridge가 같은 언어를 쓰게 만드는 중심 계약이 된다.

단, 이 문서 단계에서는 canonical surface의 **전체 구현**이 아니라, 그것이 왜 필요한지와 최소 입력 축만 정의한다.

## 9. 지금 이미 있는 것과 아직 부족한 것

### 9-1. 이미 있는 것

- `runtime row`
- `execution_diff`
- `continuation_accuracy`
- `flow history`
- `window timebox audit`
- `state25 / forecast / belief / barrier`

### 9-2. 아직 부족한 것

- 최소 annotation contract
- 세션 분해 기준이 붙은 accuracy/should-have-done layer
- chart/runtime/execution이 공유할 canonical surface
- confidence 관리가 붙은 should-have-done dataset

즉 지금은 재료 수집 단계가 아니라, **이 재료들을 같은 해석 언어로 묶는 구조**가 부족한 단계다.

## 10. 실행 원칙

이 축은 크게 세 단계로 진행한다.

1. 최소 contract를 정의한다
2. 기존 CA2/accuracy를 세션별로 분해해서 읽는다
3. 유의미한 차이가 확인되면 그때 chart/runtime/execution/state25로 영향력을 확장한다

즉 annotation contract 자체는 지금 시작하되,

- 세션-aware weighting
- execution 직접 반영
- state25 연결

은 **세션 분해 근거가 쌓인 뒤**에 진행한다.

## 11. 하지 말아야 할 것

- 세션을 방향 규칙으로 직접 하드코딩
- phase를 처음부터 과도하게 세분화
- 운영자 메모를 confidence 없이 전부 같은 강도로 학습
- annotation intuition만으로 bounded live를 바로 바꾸기
- NAS/XAU/BTC 전용 예외를 annotation contract에 심기

## 12. 이 문서의 결론

지금은 더 많은 패치를 얹는 단계가 아니라,
이미 있는 state/forecast/box/BB/HTF/state25/flow/accuracy 재료를

- `direction`
- `continuation`
- `phase`
- `session`
- `should-have-done`

축으로 묶어 **같은 장면을 더 정확한 언어로 읽게 만드는 단계**다.

즉 다음 단계의 목표는 더 많은 시그널이 아니라,
**더 적은 오해와 더 좋은 해석 언어**다.
