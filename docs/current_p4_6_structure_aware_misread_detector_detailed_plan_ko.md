# P4-6 구조형 오판 관찰 확장 상세 계획

## 목적

기존 `P4-5`에서 추가한

- 상하단 방향 오판 detector
- 캔들/박스 위치 대비 방향 해석 불일치 detector
- 위/아래 힘 우세 설명 surface

를 한 단계 더 정교하게 만든다.

이번 단계의 핵심은 거래 로직을 바꾸는 것이 아니다.
이미 열려 있는 `observe -> detect -> feedback -> propose -> review` 루프 안에서

1. 사람이 실제 차트에서 보는 기준을 더 직접적으로 surface 하고
2. detector가 더 구체적인 evidence로 issue를 만들게 하고
3. hindsight 기준으로 detector 정밀도를 측정할 수 있게 만드는 것

이다.

## 이 단계의 가장 중요한 전제

이 문서는 `모델이 틀렸으니 새 모델을 만들자`는 문서가 아니다.
정확히는 `사람이 차트에서 보는 좌표계를 기존 관찰 루프 안으로 가져오자`는 문서다.

즉 이번 단계의 성공 기준은

- 매매 성능 즉시 개선

이 아니라

- 오판처럼 느껴지는 장면을 더 잘 분해하고
- detector feedback이 가능한 evidence로 만들고
- 나중에 proposal로 끌어올릴 수 있는 관찰 재료를 쌓는 것

이다.

## 배경

지금 시스템은 이미 다음을 하고 있다.

- `scene disagreement`를 잡는다
- `upper/lower force`를 읽는다
- `consumer_check_side`, `consumer_check_reason`를 남긴다
- `/detect -> /detect_feedback -> /propose` 학습 루프를 갖고 있다

하지만 사용자가 실제 차트를 볼 때는 아래 기준을 같이 본다.

- 현재 가격이 박스 상단/하단 어디쯤 있는가
- 윗꼬리/아랫꼬리 비중이 어떤가
- 최근 2~3봉 흐름이 어떤 방향인가
- 지금 시스템 방향과 구조 위치가 정합인지 엇갈리는지

즉 현재 부족한 것은 새 전략이 아니라 `사람이 보는 좌표계`를 기존 관찰 루프에 넣는 것이다.

## 이번 단계에서 하지 않는 것

- 실제 진입/청산/반전 로직 변경
- detector 결과의 자동 apply
- force 수치만으로 매매 방향 강제 교정
- 여러 symbol에 대한 wide rollout

이번 단계는 끝까지 `관찰 / 설명 / 학습` 축에 머문다.

## canonical evidence shape

이번 단계 이후 detector가 다루는 evidence는 가능한 한 아래 shape로 수렴시킨다.

```python
{
    "symbol": "BTCUSD",
    "scope_key": "...",
    "consumer_side": "BUY",
    "position_dominance": "UPPER",
    "structure_alignment": "MISMATCH",
    "context_flag": "breakout_context",
    "context_confidence": 0.72,
    "box_relative_position": 0.82,
    "box_zone": "UPPER",
    "upper_wick_body_ratio": 2.4,
    "lower_wick_body_ratio": 0.3,
    "recent_3bar_direction": "WEAK_DOWN",
    "reason_tokens": ["upper", "reject", "wick"],
    "misread_confidence": 0.68,
    "explainability_snapshot": {
        "force": "상단 우세 (하단 0.05 / 상단 0.34 / 중립 0.00)",
        "alignment": "구조 엇갈림 ⚠️",
        "context": "breakout_context",
    },
    "result_type": "result_unresolved",
    "explanation_type": "explanation_gap",
}
```

이 shape의 목적은 detector를 새로 만들기 위한 것이 아니라,

- DM 설명
- detector evidence
- feedback 저장
- `/propose` 우선순위

가 같은 언어를 쓰게 만드는 데 있다.

## context_flag

`box_relative_position`, `wick/body`, `recent_3bar`는 맥락 없이 읽으면 오탐이 늘어난다.
따라서 detector evidence에는 가능한 한 아래 context flag를 함께 실어야 한다.

- `range_context`
- `breakout_context`
- `reclaim_context`
- `compression_context`
- `reversion_context`
- `unknown_context`

낮은 확신 context는 억지 분류하지 않고 아래처럼 다룬다.

- `context_confidence >= 0.7` -> 해당 context 채택
- `0.4 <= context_confidence < 0.7` -> caution context
- `< 0.4` -> `unknown_context`

## 전체 단계

### P4-6A. 구조 정합/엇갈림 surface

#### 목표

실시간 DM에서 현재 방향과 현재 위치 우세가 구조적으로 맞는지 엇갈리는지 바로 읽히게 한다.

#### 입력

- `consumer_check_side`
- `position_dominance`
- `upper_position_force`
- `lower_position_force`
- `middle_neutrality`
- `runtime_scene_fine_label`

#### 왜 먼저 이것부터 하는가

이 단계는 정답 판정기가 아니라 관계 표지판이다.
사용자가 지금까지는 `위/아래 힘` 수치를 보고 머릿속으로 직접 비교해야 했다면,
이제는 시스템이 그 관계를 한 줄로 surface 한다.

즉 이 단계의 목적은 오판을 확정하는 것이 아니라,

- 설명 부족
- 진짜 구조 엇갈림
- scene 맥락 차이

를 분리하기 위한 최소 관측면을 여는 데 있다.

#### 기본 규칙

초기 thin slice는 아래처럼 간단히 간다.

- `BUY + LOWER` -> `구조 정합 ✅`
- `SELL + UPPER` -> `구조 정합 ✅`
- `BUY + UPPER` -> `구조 엇갈림 ⚠️`
- `SELL + LOWER` -> `구조 엇갈림 ⚠️`
- `MIDDLE / MIXED / UNRESOLVED` -> `중립 ➖`

#### scene 계열별 분기

다만 위 규칙은 추세 추종/눌림 계열에는 잘 맞지만, 돌파/반전 계열에는 과하게 보수적일 수 있다.
따라서 정식 버전에서는 scene family 분기를 같이 넣는다.

##### 추세/눌림 계열

예:

- `pullback_continuation`
- `runner_hold`
- `reaccumulation`
- `range_reclaim`

이 계열에서는

- `BUY + LOWER` -> 정합 ✅
- `SELL + UPPER` -> 정합 ✅
- `BUY + UPPER` -> 엇갈림 ⚠️
- `SELL + LOWER` -> 엇갈림 ⚠️

##### 돌파/반전 계열

예:

- `breakout`
- `breakout_retest_hold`
- `liquidity_sweep_reclaim`
- `range_break`

이 계열에서는

- `BUY + UPPER` -> 정합 ✅
- `SELL + LOWER` -> 정합 ✅
- `BUY + LOWER` -> 엇갈림 ⚠️
- `SELL + UPPER` -> 엇갈림 ⚠️

##### scene 불명 시

- `중립 ➖`

#### 주의

- 이 정합은 `방향 예측 정답`이 아니라 `현재 구조 위치와 현재 실행 방향의 정합`이다.
- 즉 이 단계는 매매 참/거짓 판정이 아니라 설명 surface다.

#### 건드릴 파일

- `backend/integrations/notifier.py`
- `tests/unit/test_telegram_notifier.py`

#### 산출물

- 실시간 `진입 / 대기 / 반전` DM에 `구조 정합:` 1줄 추가

#### 완료 조건

- 사용자가 `위/아래 힘`을 보고 직접 비교하지 않아도 정합/엇갈림 여부를 즉시 읽을 수 있다.

#### thin slice -> 정식 버전 전환 트리거

초기 thin slice는 빠른 체감 확보를 위한 버전이다.
다만 아래를 기준으로 scene-aware 정식 버전으로 전환 시점을 판단한다.

- live DM에서 thin slice가 `3일 이상` 운영됨
- 사용자가 `엇갈림 ⚠️`를 보고 실제 느낌과 맞는지 확인한 건수 `5건 이상`
- 돌파 계열 진입에서 `엇갈림 ⚠️`가 떴지만 실제로는 정합이었던 사례를 집계

판단 기준:

- `1 + 2` 충족 -> scene family 분기 적용 준비
- `3 == 0건` -> thin slice 유지 가능
- `3 >= 2건` -> scene family 분기 우선 적용

### P4-6B. box_relative_position 직접 측정

#### 목표

현재 가격이 최근 박스 내부에서 상단/중단/하단 어디쯤 있는지 직접 측정해 detector 입력으로 쓴다.

#### 입력

- 최근 `N`봉 `high`
- 최근 `N`봉 `low`
- 현재가
- ATR

#### 기본 계산

- `box_high = rolling max(high, N)`
- `box_low = rolling min(low, N)`
- `box_range = box_high - box_low`
- `box_relative_position = (current_price - box_low) / box_range`

#### 초기 N값

첫 버전은 `N = 20`으로 통일한다.

이유:

- 너무 작으면 거의 모든 가격이 상단/하단으로 치우친다
- 너무 크면 대부분 중단으로 눌려서 불일치를 못 잡는다
- 5분봉 기준 20봉은 BTC/NAS/XAU 모두 첫 버전으로 무난하다

운영 안정화 후 필요하면 자산별로 아래처럼 분기한다.

- `BTCUSD = 20`
- `NAS100 = 20`
- `XAUUSD = 15`

#### 좁은 박스 예외

`box_range < ATR * 0.3`이면 박스가 너무 좁은 상태로 본다.

이 경우:

- `box_relative_position`는 계산하되
- detector mismatch evidence에서는 직접 사용하지 않거나
- `range_too_narrow` flag를 세운다

#### 해석 기준

- `<= 0.25` -> 하단 영역
- `0.25 ~ 0.75` -> 중단 영역
- `>= 0.75` -> 상단 영역

#### 용도

- `BUY + 상단 영역`이면 `box mismatch` 관찰 후보
- `SELL + 하단 영역`이면 `box mismatch` 관찰 후보
- 단, breakout 계열은 바로 오판으로 확정하지 않고 `주의 관찰`만 한다

#### 주의

`box_relative_position`은 방향 판정의 단독 근거가 아니다.
이 값은 현재가의 상대적 위치를 설명하는 구조형 evidence이며,
breakout / reclaim / range reversion처럼 서로 다른 맥락을 구분하지 못한다.

따라서 detector는 이 값을 `위치 evidence`로만 사용하고,
최종 surface는 wick/body, recent_3bar_direction, current reason과 함께 묶어서 판단한다.

#### 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- 필요 시 공통 helper 신설
- `tests/unit/test_improvement_log_only_detector.py`

#### 완료 조건

- detector evidence에 `박스 상대 위치`, `box_zone`, `range_too_narrow 여부`가 직접 들어간다.

### P4-6C. wick/body ratio 직접 측정

#### 목표

캔들 꼬리/몸통 구조를 간접 reason token이 아니라 직접 값으로 측정한다.

#### 입력

- 최근 1봉 OHLC
- ATR

#### 기본 계산

- `body = abs(close - open)`
- `upper_wick = high - max(open, close)`
- `lower_wick = min(open, close) - low`
- `upper_wick_body_ratio = upper_wick / max(body, eps)`
- `lower_wick_body_ratio = lower_wick / max(body, eps)`

#### doji 예외

`body < ATR * 0.05`면 doji 성격으로 본다.

이 경우:

- `wick/body ratio`는 직접 판단에 쓰지 않는다
- 대신 `total_range = high - low`를 기준으로
  - `upper_wick_pct = upper_wick / total_range`
  - `lower_wick_pct = lower_wick / total_range`
  를 계산한다

해석:

- `upper_wick_pct > 0.7` -> 상단 거부형 doji
- `lower_wick_pct > 0.7` -> 하단 방어형 doji
- 그 외 -> 우유부단 doji

#### 해석 예

- `BUY + upper_wick_body_ratio >= 2.0` -> 상단 거부 가능성
- `SELL + lower_wick_body_ratio >= 2.0` -> 하단 방어 가능성

#### 주의

wick/body ratio는 `거부/방어 가능성`을 나타내는 캔들형 evidence다.
이 값이 높다고 해서 곧바로 방향 오판으로 확정하지 않는다.

같은 윗꼬리라도

- 상단 영역에서 최근 3봉이 약화 중인 경우
- 추세 중간에서 continuation 과정에서 나온 경우

의 의미는 다르다.

따라서 wick/body ratio는 반드시

- box 위치
- recent_3bar_direction
- force surface

와 함께 읽는다.

#### 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `tests/unit/test_improvement_log_only_detector.py`

#### 완료 조건

- detector evidence에 `윗꼬리/아랫꼬리 비율`, doji 여부, doji subtype이 보인다.

### P4-6D. recent_3bar_direction 직접 측정

#### 목표

사람이 자주 보는 `최근 2~3봉 흐름`을 detector 입력으로 넣는다.

#### 입력

- 최근 3봉 close

#### 계산

- 3봉 모두 상승 -> `STRONG_UP`
- 2상승 1하락 -> `WEAK_UP`
- 혼조 -> `MIXED`
- 2하락 1상승 -> `WEAK_DOWN`
- 3봉 모두 하락 -> `STRONG_DOWN`

#### 용도

- `BUY + STRONG_DOWN` -> 구조 불일치 후보
- `SELL + STRONG_UP` -> 구조 불일치 후보

#### 의미

recent_3bar_direction은 추세의 크기나 절대 강도를 나타내는 지표가 아니다.
사람이 차트에서 즉시 체감하는 `짧은 구간 방향 일관성`을 detector에 넣기 위한 것이다.

이 값은 force dominance나 box 위치와 달리 시간축 정보를 담고 있으므로,
나중에 `timing_mismatch`와 `true_misread`를 분리할 때 중요한 근거가 된다.

#### 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `tests/unit/test_improvement_log_only_detector.py`

#### 완료 조건

- detector evidence에 최근 3봉 방향 일관성이 들어간다.

### P4-6E. misread_type 2축 분리

#### 목표

모든 문제를 `오판` 하나로 뭉개지 않고, 결과 축과 설명 축으로 분리해 proposal 우선순위를 더 정교하게 만든다.

#### 결과 축

- `result_correct`
- `result_misread`
- `result_timing`
- `result_unresolved`

#### 설명 축

- `explanation_clear`
- `explanation_gap`
- `explanation_unknown`

#### 예시 조합

- `result_correct + explanation_clear`
  - 문제 없음
- `result_correct + explanation_gap`
  - 결과는 좋았지만 설명이 부족했다
- `result_misread + explanation_clear`
  - 설명은 됐지만 판단이 틀렸다
- `result_misread + explanation_gap`
  - 설명도 안 되고 판단도 틀렸다
- `result_timing + explanation_clear`
  - 방향은 맞았지만 timing이 나빴다
- `result_unresolved + explanation_unknown`
  - 아직 확정 이르다

#### 왜 2축인가

`explanation_gap`은 결과가 나쁘다고 확정된 후에만 생기는 문제가 아니다.
수익으로 끝난 장면도 사용자가 납득하지 못하면 설명 품질 문제는 남는다.

따라서

- 결과 기반 문제
- 설명 기반 문제

를 따로 기록해야 한다.

#### 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `backend/services/improvement_detector_feedback_runtime.py`
- `backend/services/trade_feedback_runtime.py`
- 관련 tests

#### 완료 조건

- detector feedback과 proposal에서 결과 축과 설명 축이 분리되어 보인다.

### P4-6F. generic reason filter

#### 목표

generic detector surface를 줄여 detector 신뢰를 지킨다.

#### generic 토큰 후보

- `manual`
- `h1`
- `rsi`
- `general`
- `default`
- `unknown`
- `mixed`

#### 규칙

- generic-only reason은 detector surface하지 않고 log-only에 남긴다
- specific reason이 같이 있으면 specific 근거만 surface한다

#### 왜 필요한가

generic reason은 운영자에게 `무슨 일이 있었는가`를 직접 설명해주지 못한다.
따라서 detector가 generic 표현을 surface하기 시작하면
사용자는 detector를 읽고도 무엇을 feedback 해야 하는지 알기 어렵다.

본 필터의 목적은 신호를 줄이는 것이 아니라,
feedback 가능한 detector만 surface하여 학습 루프의 질을 유지하는 것이다.

#### 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `tests/unit/test_improvement_log_only_detector.py`

#### 완료 조건

- detector summary가 `manual/H1/unknown` 식의 generic 표현으로만 뜨지 않는다.

### P4-6G. hindsight validator + fast promotion rule

#### 목표

detector가 실제로 맞았는지, 과민했는지, 아직 미해결인지 hindsight 기준으로 계량화한다.

#### hindsight 상태

- `confirmed_misread`
- `false_alarm`
- `partial_misread`
- `unresolved`

#### 추가 필드

- `time_to_resolution_bars`
- `time_to_resolution_minutes`

이 값은 `timing_mismatch`와 `true_misread`를 나누는 데 중요한 힌트가 된다.

#### fast promotion rule

아래를 모두 만족하면 `/propose` 우선 검토로 더 빨리 올린다.

- `confirmed_misread` 비율 `>= 70%`
- 최소 표본 `>= 5건`
- 평균 손실 `<= -0.7R`
- 동일 symbol에서 `>= 3건`
- 최근 `2주` 이내 발생
- 최소 `3 거래일` 이상에 분산

#### fast promotion으로 할 수 있는 것

- `/propose` 우선순위 상승
- check topic에 `반복 감지` 배지 추가
- review backlog에서 상위 정렬

#### fast promotion으로도 하면 안 되는 것

- 자동 weight 변경
- 자동 진입 차단
- 자동 apply
- 다른 symbol로 확대 적용

#### 건드릴 파일

- `backend/services/improvement_detector_feedback_runtime.py`
- `backend/services/trade_feedback_runtime.py`
- `backend/services/telegram_ops_service.py`
- 관련 tests

#### 완료 조건

- 반복적으로 명확한 detector scope는 `/propose`에서 우선 검토 대상으로 surface된다.

### P4-6H. 복합 불일치 단일 surface

#### 목표

같은 포지션/같은 scope에서 `box/wick/3bar`가 동시에 불일치일 때, 여러 detector 건으로 쪼개지 않고 하나의 복합 issue로 묶는다.

#### 규칙

같은 포지션 또는 같은 detector scope에서 아래 중 2개 이상이 동시에 성립하면:

- `box mismatch`
- `wick rejection/defense mismatch`
- `recent_3bar mismatch`

개별 2~3건으로 surface하지 않고 다음처럼 1건으로 묶는다.

예:

`BTCUSD BUY 구조 복합 불일치 관찰`

- 박스 상단 82% 위치
- 윗꼬리 몸통 대비 2.5배
- 최근 3봉 하락 중

#### 기대 효과

- 알림 폭탄 감소
- feedback 대상 단순화
- proposal 우선순위 정리 용이

#### 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `backend/services/improvement_detector_feedback_runtime.py`
- 관련 tests

#### 완료 조건

- 같은 scope에서 `B/C/D`가 동시에 뜰 때 detector가 하나의 복합 issue로 묶인다.

### P4-6I. confidence / explainability / cooldown 보강층

#### 목표

detector가 더 정교하게 읽히고, 같은 scope가 과도하게 반복 surface되지 않게 만드는 운영 보강층을 둔다.

#### 포함 요소

##### 1. context_confidence

context 분류가 얼마나 확실한지 기록한다.

- `0.7 이상` -> 신뢰 가능
- `0.4 ~ 0.7` -> caution
- `0.4 미만` -> `unknown_context`

##### 2. misread_confidence

복수 evidence를 바탕으로 오판 가능성 자체의 confidence를 남긴다.

구성 후보:

- evidence 개수
- evidence 강도
- context 일관성
- force conflict 여부

주의:
- 이 값은 자동 apply 점수가 아니다
- detector 정렬과 review 우선순위 힌트로만 쓴다

##### 3. explainability_snapshot

해당 시점의 설명 surface를 그대로 남긴다.

예:

- `force`
- `alignment`
- `context`

목적:

- hindsight 시점에 `그때 왜 그렇게 읽었는지` 재현 가능하게 하기

##### 4. detector cooldown

같은 `scope_key`가 짧은 시간 동안 계속 반복 surface되는 걸 억제한다.

원칙:

- same scope -> 일정 시간 suppress
- 더 강한 evidence가 생기면 cooldown 중에도 update 가능
- cooldown은 detector를 끄는 것이 아니라 운영 피로를 낮추는 장치다

#### 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `backend/services/improvement_detector_feedback_runtime.py`
- 필요 시 watch/report render layer
- 관련 tests

#### 완료 조건

- detector가 confidence와 snapshot을 함께 남긴다
- 같은 scope가 짧은 시간에 연속 폭발하지 않는다

## DM 노출 정책

`B/C/D`의 구조형 측정값은 기본적으로 detector evidence 전용으로 취급한다.

즉 평소 실시간 DM에는 아래를 상시 노출하지 않는다.

- box relative
- wick/body ratio
- recent 3bar direction

이유:

- 평소에는 정상 상태가 많아 DM이 길어지기 쉽다
- 사용자는 실시간 DM에서 핵심만 빨리 읽는 편이 더 좋다

대신 아래 경우에만 DM에 1줄을 추가할 수 있다.

- `P4-6H 복합 불일치 단일 surface`가 감지된 경우

예:

`⚠️ 구조 복합 불일치: 박스상단 82% + 윗꼬리 2.5x + 3봉하락`

즉 정책은 다음과 같다.

- 평소: DM은 짧게 유지
- 문제 있을 때만: 복합 불일치 1줄 추가
- 상세 근거: detector report/check topic에서 확인

## 실제 구현 순서

1. `P4-6A` 구조 정합/엇갈림 surface
2. `P4-6B` box_relative_position
3. `P4-6C` wick/body ratio
4. `P4-6D` recent_3bar_direction
5. `P4-6E` misread_type 2축 분리
6. `P4-6F` generic reason filter
7. `P4-6I` confidence / explainability / cooldown 보강층
8. `P4-6G` hindsight validator + fast promotion rule
9. `P4-6H` 복합 불일치 단일 surface

## 왜 이 순서인가

- `A 먼저`
  - 새 데이터 없이 즉시 체감되는 설명면 확보
- `B/C/D 다음`
  - 사람 좌표계를 detector evidence로 직접 끌어오기
- `E 그다음`
  - 새 evidence가 들어오는 순간부터 결과/설명 축으로 분류되게 하기
- `F 그 후`
  - 분류된 evidence 중 surface 가치가 낮은 generic을 제거
- `I 그다음`
  - confidence, explainability snapshot, cooldown으로 detector 운영 품질을 보강
- `G 마지막`
  - hindsight는 evidence와 type 분리가 어느 정도 자리 잡은 뒤에 붙여야 의미가 있다
- `H 맨 끝`
  - 복합 묶음은 구성 요소가 모두 준비된 뒤에야 제대로 작동한다

## 이번 턴에서 이미 들어간 첫 slice

이번 턴에서는 위험이 가장 낮고 체감이 가장 큰 `P4-6A`의 thin slice를 먼저 구현했다.

현재 구현 상태:

- `위/아래 힘` line은 이미 live DM에 있다
- `구조 정합:` line도 thin slice 기준으로 들어갔다
- 아직 scene family 분기까지는 안 들어갔고, 다음 patch에서 보강할 대상이다

## 기대 효과

- 사용자가 `위/아래 힘`과 현재 방향의 관계를 더 빨리 이해한다
- `설명 부족`과 `진짜 오판`을 구분하기 쉬워진다
- 이후 `box/wick/3bar` 측정이 들어가도 기존 루프와 자연스럽게 이어진다

## 연계 문서

- `docs/current_p4_5_direction_misread_candle_box_force_surface_ko.md`
- `docs/current_external_review_request_direction_misread_learning_loop_ko.md`
- `docs/current_detailed_reinforcement_master_roadmap_ko.md`
