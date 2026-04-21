# P4-4 Feedback-Aware Proposal Promotion

## 목적

`/detect_feedback`로 쌓인 detector 피드백을 바로 적용으로 보내지 않고, `/propose`가 검토할 후보의 우선순위를 올리는 데만 쓰는 기준을 고정한다.

즉 이번 단계의 핵심은 아래 한 줄이다.

`observe -> feedback -> promotion -> review`

여기까지는 자동으로 연결하되,

`apply`

는 여전히 사람 승인 이후에만 간다.

---

## 이번 단계에서 해결하는 문제

기존에는 detector가 넓게 관찰하고 `/detect_feedback`로 피드백을 받을 수는 있었지만, 그 피드백이 `/propose`로 이어지지 않았다.

그래서 실제 학습 루프 체감이 약했다.

이번 단계에서는 다음을 해결한다.

1. `맞았음 / 놓쳤음`이 반복된 detector scope를 proposal 우선 검토 대상으로 올린다.
2. detector 피드백과 문제 패턴 보고서가 서로 따로 놀지 않게 연결한다.
3. 자동 적용은 막고, review 우선순위만 조정한다.

---

## 핵심 원칙

### 1. detector는 여전히 관찰기다

- detector는 문제를 발견한다.
- feedback은 detector 품질을 평가한다.
- promotion은 review 우선순위만 올린다.
- apply는 하지 않는다.

### 2. feedback-aware는 가속 장치이지 자동 patch가 아니다

`feedback-aware promotion`이 붙었다고 바로 weight patch나 action patch로 가면 안 된다.

이번 단계에서 하는 일은 오직 이것뿐이다.

- `/propose` 보고서 상단에 먼저 보이게 한다.
- 기존 문제 패턴 정렬 점수를 조금 올린다.

### 3. 긍정 피드백만 promotion에 쓴다

`맞았음`과 `놓쳤음`은 “이 scope를 더 봐야 한다”는 신호다.

반면 `과민했음`은 detector를 좁혀야 한다는 신호이므로 promotion에 쓰지 않는다.

---

## promotion 규칙

detector confusion snapshot에서 scope별 narrowing 결과를 읽는다.

### promotion 대상으로 인정하는 narrowing

- `PROMOTE`
- `KEEP`

### promotion 대상에서 제외하는 narrowing

- `CAUTION`
- `SUPPRESS`
- `NEUTRAL`

### scope별 기본 해석

- `PROMOTE`
  - 같은 detector scope에서 `맞았음` 또는 `놓쳤음`이 반복되었고
  - `과민했음`이 거의 없거나 없다
  - `/propose`에서 우선 검토 대상으로 승격

- `KEEP`
  - 아직 강한 승격까지는 아니지만
  - 긍정 피드백이 누적되어 계속 관찰할 가치가 있다
  - `/propose`에서 우선 검토 대상으로 함께 노출

---

## `/propose` 반영 방식

`/propose`는 최근 closed trade를 읽어 문제 패턴을 surface한다.

여기에 detector feedback promotion을 추가로 반영한다.

### 새로 추가되는 필드

- `feedback_promotion_count`
- `feedback_promotion_rows`

### 새로 추가되는 보고서 섹션

- `feedback-aware 우선 검토`

이 섹션은 기존 `문제 패턴`보다 위에 온다.

### 문제 패턴 직접 승격

특정 detector feedback scope가 기존 문제 패턴과 직접 맞닿는 경우, 해당 issue에 아래 필드를 추가한다.

- `feedback_priority_score`
- `feedback_priority_summary_ko`
- `feedback_priority_matches`

현재는 특히 `candle_weight_detector`가 `entry_reason`과 직접 맞는 경우에 효과가 크다.

---

## 텔레그램 운영 흐름

### 1. detector 관찰

체크방에서:

```text
/detect
```

### 2. detector 피드백

체크방에서:

```text
/detect_feedback D1 맞았음
/detect_feedback D2 놓쳤음
/detect_feedback D3 과민했음
/detect_feedback D4 애매함 메모
```

### 3. proposal 생성

체크방 또는 운영 흐름에서:

```text
/propose
```

### 4. 결과

- 보고서 topic에는 원문 보고서
- 체크 topic에는 짧은 inbox 요약
- `feedback-aware 우선 검토`가 있으면 보고서 상단에 먼저 보인다

---

## 실제 예시

### detector feedback이 아직 없는 경우

```text
[수동 제안 분석]
최근 50건 기준 문제 패턴 3건 / feedback-aware 0건 / 보고서 topic 확인
```

### feedback-aware promotion이 생긴 경우

```text
feedback-aware 우선 검토:
- candle weight detector / BTCUSD / 상단 거부 혼합 확인
  - 제안: candle weight detector에서 반복 긍정 피드백이 쌓여 proposal 우선 검토 대상으로 승격했습니다.

문제 패턴:
1. 상단 거부 혼합 확인 | 표본 8건 | 승률 25.0% | 손익 -18.40 USD
   - 판단: 같은 패턴에서 최근 3연속 손실이 발생했습니다.
   - feedback-aware: detector 피드백 승격이 함께 잡혀 우선 확인 가치가 높습니다.
```

---

## 안전장치

이번 단계에서도 아래는 하지 않는다.

- detector feedback만으로 자동 apply
- detector feedback만으로 weight patch 자동 생성
- detector feedback만으로 multi-symbol rollout
- detector feedback만으로 live rule 변경

즉 feedback-aware promotion은 어디까지나 `review priority boost`다.

---

## 영향 파일

- `backend/services/trade_feedback_runtime.py`
- `backend/services/telegram_ops_service.py`
- `backend/services/improvement_detector_feedback_runtime.py`
- `tests/unit/test_trade_feedback_runtime.py`
- `tests/unit/test_telegram_ops_service_p3.py`

---

## 완료 조건

아래가 모두 만족되면 이번 단계는 닫힌다.

1. `/propose` payload가 `feedback_promotion_count`, `feedback_promotion_rows`를 포함한다.
2. `PROMOTE / KEEP` scope만 proposal 우선 검토에 반영된다.
3. detector 긍정 피드백이 있는 issue는 기존 문제 패턴보다 위로 올라갈 수 있다.
4. 자동 apply는 여전히 일어나지 않는다.
5. 텔레그램 보고서에 `feedback-aware 우선 검토`가 보인다.

---

## 다음 단계

다음으로 가장 자연스러운 건 아래 둘 중 하나다.

1. 실제 detector feedback이 쌓인 뒤 `/propose` 보고서 우선순위 변화를 운영에서 확인
2. 반복적으로 `PROMOTE`되는 scope만 반자동 proposal detector의 seed로 승격
