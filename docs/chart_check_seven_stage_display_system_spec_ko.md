# Chart Check 7-Stage Display System Spec

## 1. 목적

차트 위 체크 표기를 아래 7단계로 통일한다.

- `SELL-3`
- `SELL-2`
- `SELL-1`
- `WAIT`
- `BUY-1`
- `BUY-2`
- `BUY-3`

핵심 목표는 3가지다.

1. 차트만 봐도 `약한 체크 / 강한 체크 / 진입 직전`이 바로 읽혀야 한다.
2. 체크 표기와 실제 진입 체인이 따로 놀지 않고 같은 Consumer chain 위에서 설명돼야 한다.
3. `BTC / NAS / XAU`가 심볼마다 제멋대로 다른 그림을 그리지 않고, 같은 stage/strength면 같은 시각 규칙을 써야 한다.

---

## 2. 왜 7단계가 필요한가

현재 체감상 차트는 주로 아래 2단계처럼 보이는 문제가 있다.

- 약한 체크: 하늘색 / 주황색
- 강한 체크: 초록색 / 빨간색

하지만 실제 운영에서 필요한 정보는 더 세밀하다.

- 그냥 지켜보는 약한 방향성인지
- 꽤 괜찮은 probe인지
- 거의 진입 직전인지
- 반대로 방향성이 없는 neutral wait인지

그래서 시각 체계를 `3 + 1 + 3` 구조로 명확히 고정한다.

- `SELL-1/2/3`
- `WAIT`
- `BUY-1/2/3`

---

## 3. owner 구조

이 7단계는 painter가 독립적으로 만들면 안 된다.

올바른 owner 구조는 아래와 같다.

- semantic/scene owner:
  - [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- late guard reconciliation owner:
  - [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- rendering owner:
  - [chart_painter.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- visual constants owner:
  - [chart_flow_policy.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)

즉:

- `entry_service`가 체크 후보와 방향, stage를 만든다.
- `entry_try_open_entry`가 late block 이후 최종 effective check state를 조정한다.
- `chart_painter`는 그 결과를 그리기만 한다.

이 원칙을 깨면:

- 차트에는 `READY`처럼 보이는데 실제 entry는 막히고
- visually similar scene인데 symbol마다 전혀 다른 해석이 튀어나오고
- ML을 붙여도 체크와 진입이 따로 놀게 된다.

---

## 4. canonical payload

7단계 체계는 [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)의 `consumer_check_state_v1` 위에 세운다.

필수 필드:

- `check_candidate`
- `check_display_ready`
- `entry_ready`
- `check_side`
- `check_stage`
- `check_reason`
- `entry_block_reason`
- `blocked_display_reason`
- `display_strength_level`

현재 핵심 해석은 이렇다.

- `check_side`
  - `BUY / SELL / ""`
- `check_stage`
  - `OBSERVE / PROBE / READY / BLOCKED / ""`
- `check_display_ready`
  - 실제 차트에 체크를 보여줄지 여부
- `entry_ready`
  - 실제 진입 게이트를 통과했는지 여부

즉:

- `차트 체크`와
- `실제 진입`

은 같은 chain 위에 있지만 서로 다른 floor를 갖는다.

---

## 5. 7단계 정의

### 5.1 SELL-1

- 의미:
  - 약한 sell 방향성
  - 아직 기다림/관찰 단계
- 대표 semantic:
  - weak observe
  - weak watch
  - blocked observe 중 꼭 보여야 하는 구조 장면
- 시각:
  - 연한 주황
  - 1개 체크

### 5.2 SELL-2

- 의미:
  - 꽤 괜찮은 sell probe
  - 방향성은 명확하지만 entry는 아직 아님
- 대표 semantic:
  - PROBE
  - blocked probe
  - 승격 직전 scene
- 시각:
  - 더 진한 주황/빨강
  - 2개 체크

### 5.3 SELL-3

- 의미:
  - 강한 sell
  - READY 또는 entry 직전/직후
- 대표 semantic:
  - READY
  - explicit confirm
  - strong probe with no late block
- 시각:
  - 진한 빨강
  - 3개 체크

### 5.4 WAIT

- 의미:
  - neutral wait
  - 방향성 없이 관찰만 하는 상태
- 대표 semantic:
  - `check_side == ""`
  - `observe_state_wait`
  - balanced conflict
  - generic wait
- 시각:
  - 캔들 중간 흰 가로선
  - 단일 표기

### 5.5 BUY-1

- 의미:
  - 약한 buy 방향성
  - 아직 기다림/관찰 단계
- 대표 semantic:
  - weak observe
  - weak watch
  - blocked observe 중 꼭 보여야 하는 구조 장면
- 시각:
  - 연한 하늘색
  - 1개 체크

### 5.6 BUY-2

- 의미:
  - 꽤 괜찮은 buy probe
  - 방향성은 명확하지만 entry는 아직 아님
- 대표 semantic:
  - PROBE
  - blocked probe
  - 승격 직전 scene
- 시각:
  - 선명한 청록/초록
  - 2개 체크

### 5.7 BUY-3

- 의미:
  - 강한 buy
  - READY 또는 entry 직전/직후
- 대표 semantic:
  - READY
  - explicit confirm
  - strong probe with no late block
- 시각:
  - 진한 초록
  - 3개 체크

---

## 6. 점수 ladder 제안

### 6.1 기준

지금까지 본 실데이터 기준으로 `60/75/90`은 너무 닫혀 있다.

현재 체감상 체크가 너무 많이 남기 때문에, 반복 표기는 더 보수적으로 가져간다.

- `< 0.70`
  - 방향 체크 없음
- `0.70 ~ 0.79`
  - 1개 체크
- `0.80 ~ 0.89`
  - 2개 체크
- `>= 0.90`
  - 3개 체크

### 6.2 왜 0.70/0.80/0.90인가

이유:

- 현재 화면 체감상 약한 `WAIT/OBSERVE/PROBE`까지 너무 자주 남고 있다.
- 사용자는 `정말 의미 있는 순간만 1개`, `강한 진입/청산 후보만 2개`, `거의 확정에 가까운 순간만 3개`를 원한다.
- 따라서 반복 표기는 `약한 표시 확장`이 아니라 `강한 표시 압축 강화` 쪽으로 설계하는 것이 맞다.

중요:

- 이 threshold는 기존 history의 raw `score`에 바로 쓰면 안 된다.
- 현재 raw flow score는 일부 row에서 쉽게 `1.0`으로 포화된다.
- 실제 구현은 별도 `display_score(0~1)`를 만든 뒤 그 값에 적용해야 한다.

---

## 7. hysteresis

경계값만 그대로 쓰면 체크가 깜빡인다.

그래서 hysteresis를 같이 둔다.

권장 예시:

- 1개 진입:
  - `>= 0.70`
- 1개 해제:
  - `< 0.67`

- 2개 진입:
  - `>= 0.80`
- 2개 해제:
  - `< 0.77`

- 3개 진입:
  - `>= 0.90`
- 3개 해제:
  - `< 0.87`

---

## 8. display score와 entry gate 관계

가장 중요한 원칙:

- `display score`
  - 차트에 몇 개 체크를 그릴지 결정
- `entry gate`
  - 실제 진입 가능 여부 결정

둘은 연결되지만 동일하지 않다.

즉:

- 3개 체크라고 무조건 진입은 아님
- 2개 체크라도 late guard가 풀리면 진입으로 갈 수 있음
- 1개 체크는 주로 scene awareness 용도

정리하면:

- chart는 `display score ladder`
- entry는 `display score + hard block + readiness gate`

를 같이 본다.

---

## 9. current implementation vs target

### 9.1 현재 이미 구현된 것

- `consumer_check_state_v1` 기반 표기 체계
- `entry_try_open_entry`에서 late guard 이후 effective consumer check state 재조정
- `chart_painter`가 `consumer_check_state_v1`를 우선 번역
- line width, color binding, probe/watch geometry 일부 통일

### 9.2 아직 목표 상태로 안 닫힌 것

- 공통 `display_score(0~1)` ladder의 완전한 코드화
- `1개/2개/3개 체크` 반복 표기의 정식 구현
- scene별 `must-show`, `must-hide` contract의 완전 고정
- `BTC / NAS / XAU` visually similar scene의 semantic alignment

즉 현재는:

- 구조는 많이 정리됐고
- 7단계 목표는 명확해졌지만
- ladder 자체는 아직 완전 구현 전이다.

---

## 10. must-show / must-hide 원칙

### 10.1 must-show

아래는 약한 체크라도 살아야 한다.

- 구조적 upper reject
- 구조적 lower rebound
- middle reclaim / middle anchor guard observe
- explicit watch
- explicit probe observe

단, neutral conflict는 예외다.

### 10.2 must-hide

아래는 체크를 숨기거나 최소 neutral wait로 내려야 한다.

- balanced conflict observe
- late blocked row인데 candidate가 없는 경우
- 계속 하락 중인 `lower_rebound_confirm`가 soft block만 반복되는 경우
- scene contract 없이 fallback으로만 채워진 synthetic side

---

## 11. symbol-specific tuning 원칙

심볼별 특성은 허용하지만, 7단계 시각 체계는 공통으로 유지한다.

허용:

- scene relief
- threshold relaxation
- display suppression
- must-show whitelist

금지:

- 심볼마다 완전히 다른 도형 체계
- 같은 stage인데 다른 색/두께/반복 수 사용

즉 `BTC / NAS / XAU`는 해석은 조금 다를 수 있어도, 최종 표기 체계는 같은 문법을 써야 한다.

---

## 12. 권장 구현 순서

1. `display_score`를 `consumer_check_state_v1`에 명시적으로 추가
2. `0.70 / 0.80 / 0.90` ladder를 policy에 고정
3. `chart_painter`에서 1개/2개/3개 체크 반복 표기 구현
4. `WAIT`는 neutral 전용으로 유지
5. `must-show / must-hide` scene casebook을 별도 문서로 고정
6. `BTC / NAS / XAU` visually similar scene를 다시 맞춤

---

## 13. 한 줄 결론

7단계 차트 체계는 아래로 요약된다.

- `SELL-3 / SELL-2 / SELL-1 / WAIT / BUY-1 / BUY-2 / BUY-3`
- `0.70 / 0.80 / 0.90` ladder
- `display`와 `entry`는 연결되지만 동일하지 않음
- owner는 painter가 아니라 `consumer_check_state_v1`

즉 앞으로의 수정 방향은:

`체크를 예쁘게 따로 그리는 것`이 아니라  
`같은 Consumer chain 위에서 7단계 display ladder를 정식 구현하는 것`
