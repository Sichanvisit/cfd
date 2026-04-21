# Feedback-Aware Learning Loop 운영 설명서

## 목적

이 문서는 현재 CFD 시스템에서 새로 붙은 `feedback-aware learning loop`를 운영자가 실제로 어떻게 써야 하는지 빠르게 이해하도록 돕기 위한 설명서다.

이 설명서는 특히 아래를 명확히 하는 데 목적이 있다.

1. 어떤 방에서 어떤 명령을 써야 하는가
2. detector, feedback, proposal이 어떻게 이어지는가
3. 지금 단계에서 자동으로 되는 것과 사람이 봐야 하는 것이 무엇인가
4. 무엇은 절대 자동 반영되지 않는가

---

## 한 줄 요약

지금 시스템은 아래 순서로 움직인다.

```text
관찰(/detect) -> 피드백(/detect_feedback) -> 우선 검토 승격(feedback-aware promotion) -> 수동 제안(/propose) -> 사람 승인
```

즉 detector는 문제를 “관찰”하고, 피드백은 detector 품질을 “평가”하고, `/propose`는 그 결과를 “검토 후보”로 끌어올린다.

자동 적용은 아직 하지 않는다.

---

## 텔레그램 방 역할

### 1. Trading_Bot 1:1 방

역할:

- 실시간 진입
- 실시간 대기
- 실시간 청산
- 실시간 반전

주의:

- 이 방은 실행 알림 방이다.
- 승인용 버튼 방이 아니다.

### 2. CFD 체크방 / 체크 topic

역할:

- detector 관찰 inbox
- `/detect` 결과 요약
- `/detect_feedback` 입력
- `/propose` 요약 inbox
- readiness 요약

### 3. CFD 체크방 / 보고서 topic

역할:

- `/detect` 원문 보고서
- `/propose` 원문 보고서
- review packet
- apply packet

### 4. CFD Pnl

역할:

- 15분 / 1시간 / 4시간 / 1일 / 1주 / 1달 손익 보고
- 오늘의 교훈
- readiness 요약

---

## 명령어 사용법

### `/detect`

목적:

- 현재 detector가 넓게 관찰한 문제 후보를 surface한다.

효과:

- 체크 topic에 짧은 요약
- 보고서 topic에 원문 detector 보고서

예:

```text
/detect
/detect 50
```

### `/detect_feedback`

목적:

- detector가 올린 항목에 대해 운영자가 피드백을 남긴다.

형식:

```text
/detect_feedback D1 맞았음
/detect_feedback D2 놓쳤음
/detect_feedback D3 과민했음
/detect_feedback D4 애매함 메모
```

허용 판정:

- `맞았음`
- `과민했음`
- `놓쳤음`
- `애매함`

의미:

- `맞았음`: detector가 제대로 짚었다
- `과민했음`: detector가 너무 민감했다
- `놓쳤음`: detector가 더 강하게 봤어야 했다
- `애매함`: 아직 판단 보류

### `/propose`

목적:

- 최근 closed trade와 detector feedback을 합쳐, 지금 손대볼 가치가 있는 문제 패턴을 한국어 보고서로 surface한다.

효과:

- 체크 topic에 짧은 inbox 요약
- 보고서 topic에 원문 proposal 보고서

중요:

- detector feedback이 충분히 쌓이면 `/propose` 상단에 `feedback-aware 우선 검토`가 생긴다.

---

## 실제 학습 루프

### 1단계. detector가 넓게 본다

`/detect`는 아래 같은 것을 넓게 surface한다.

- scene disagreement
- missed reverse
- candle overweight
- semantic trace 누락

이 단계에서는 틀려도 괜찮다.

### 2단계. 사람이 피드백을 준다

운영자는 detector 항목을 보고

- 맞았는지
- 과민했는지
- 놓쳤는지

를 표시한다.

### 3단계. confusion snapshot이 누적된다

시스템은 detector별, scope별로 아래를 누적한다.

- confirmed count
- oversensitive count
- missed count
- ambiguous count

### 4단계. narrowing과 promotion이 결정된다

scope별로 아래 중 하나가 붙는다.

- `NEUTRAL`
- `KEEP`
- `PROMOTE`
- `CAUTION`
- `SUPPRESS`

이 중 `KEEP`, `PROMOTE`만 feedback-aware proposal promotion 대상으로 쓴다.

### 5단계. `/propose`가 우선순위를 올려준다

즉, 사람이 “이건 맞았다 / 놓쳤다”고 누적한 detector scope만 다음 제안 보고서에서 먼저 보이게 된다.

---

## 지금 단계에서 자동으로 되는 것

- detector 관찰
- detector feedback 누적
- confusion snapshot 생성
- narrowing 결정
- feedback-aware proposal priority boost
- `/propose` 보고서 생성

---

## 지금 단계에서 자동으로 안 되는 것

이건 매우 중요하다.

아래는 아직 자동으로 하지 않는다.

- detector -> 자동 patch apply
- detector -> 자동 weight 수정
- detector -> 자동 strategy 변경
- detector -> 자동 multi-symbol rollout
- detector -> 자동 live adoption

즉 지금은 “생각해서 surface하는 단계”이지 “혼자 바꾸는 단계”가 아니다.

---

## 보고서에서 꼭 봐야 할 것

### detector 보고서

아래를 먼저 본다.

- 어떤 detector인지
- 어떤 symbol인지
- 왜 이상하다고 보는지
- ref가 무엇인지 (`D1`, `D2` ...)

### proposal 보고서

아래를 먼저 본다.

- `feedback-aware 우선 검토`가 있는지
- `문제 패턴` 표본이 충분한지
- 승률 / 손익 / MFE 포착률이 왜 나쁜지
- 추천 조치가 “관찰 유지”인지 “weight/scene 제안 후보”인지

---

## 운영자가 체감해야 하는 변화

이 기능이 붙고 나면 예전과 달라지는 점은 이거다.

예전:

- detector가 넓게 올림
- 체크방에 쌓이지만 proposal과 연결이 약함

지금:

- detector가 넓게 올림
- 운영자가 `맞았음/놓쳤음/과민했음`을 남김
- 그 결과가 `/propose` 우선 검토에 반영됨

즉 “봤다”에서 끝나지 않고, “봤던 것이 다음 제안의 우선순위를 바꾼다”는 체감이 생긴다.

---

## 권장 운영 흐름

하루 운영 기준으로는 아래 순서가 가장 자연스럽다.

1. 실시간 Trading_Bot DM으로 진입/대기/청산 설명 확인
2. 이상한 장면이 있으면 체크방에서 `/detect`
3. detector 항목에 `/detect_feedback`
4. 몇 건 쌓인 뒤 `/propose`
5. 보고서 topic에서 우선 검토 항목 먼저 확인
6. 정말 수정 가치가 있는 것만 review/apply 후보로 넘김

---

## 장애나 헷갈림이 있을 때 먼저 볼 것

1. `/detect`는 뜨는데 `/propose`에 반영이 안 되는 경우
- detector feedback이 실제로 누적됐는지 확인
- `feedback_promotion_count`가 0인지 확인

2. detector가 너무 많이 뜨는 경우
- detector confusion snapshot에서 `과민했음`이 누적되는지 확인
- narrowing이 `CAUTION / SUPPRESS`로 가는지 확인

3. proposal이 너무 공격적으로 느껴지는 경우
- feedback-aware는 review priority boost일 뿐, apply가 아님을 다시 확인

---

## 참고 문서

- [current_p4_4_feedback_aware_proposal_promotion_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_p4_4_feedback_aware_proposal_promotion_ko.md)
- [current_p4_3_detector_confusion_and_feedback_narrowing_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_p4_3_detector_confusion_and_feedback_narrowing_ko.md)
- [current_p4_2_detector_feedback_lane_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_p4_2_detector_feedback_lane_detailed_plan_ko.md)
- [current_p3_manual_propose_and_pnl_lesson_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_p3_manual_propose_and_pnl_lesson_detailed_plan_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
