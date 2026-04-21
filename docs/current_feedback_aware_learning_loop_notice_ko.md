# 공지: Feedback-Aware Learning Loop 운영 개시

기준일: 2026-04-12

## 무엇이 달라졌나

이제 detector 관찰 결과가 단순 로그로 끝나지 않고, 운영자가 남긴 피드백을 통해 `/propose` 우선 검토 순서에 반영됩니다.

즉 아래 흐름이 실제로 연결되었습니다.

```text
/detect -> /detect_feedback -> feedback-aware promotion -> /propose
```

---

## 운영자가 새로 할 수 있는 것

### 1. detector 관찰 보기

체크방에서:

```text
/detect
```

### 2. detector 항목에 피드백 남기기

체크방에서:

```text
/detect_feedback D1 맞았음
/detect_feedback D2 놓쳤음
/detect_feedback D3 과민했음
```

### 3. 수동 제안 보고서 보기

체크방 또는 운영 흐름에서:

```text
/propose
```

이제 `/propose`에는 필요 시 `feedback-aware 우선 검토` 섹션이 먼저 나옵니다.

---

## 핵심 의미

이 기능은 detector를 바로 적용 시스템으로 바꾸는 것이 아닙니다.

이번 변경의 목적은 아래 하나입니다.

`사람이 맞다고 느낀 detector 관찰을 다음 제안의 우선순위로 끌어올린다`

즉 지금은 “자동 수정”이 아니라 “더 똑똑한 검토 순서”를 만드는 단계입니다.

---

## 아직 자동으로 하지 않는 것

아래는 여전히 자동으로 하지 않습니다.

- detector -> 자동 patch apply
- detector -> 자동 live rule 변경
- detector -> 자동 multi-symbol rollout
- detector -> 자동 strategy 승격

즉 review와 approval 단계는 그대로 유지됩니다.

---

## 기대 효과

- detector가 실제 학습 루프 안에서 살아 움직이기 시작함
- 운영자가 느낀 `맞았음 / 놓쳤음 / 과민했음`이 제안 우선순위에 반영됨
- 체크방이 단순 관찰 로그가 아니라 “다음 제안 입력창” 역할을 하게 됨

---

## 권장 사용 순서

1. 이상했던 장면이 있으면 `/detect`
2. detector 항목에 `/detect_feedback`
3. 몇 건 쌓이면 `/propose`
4. 보고서 topic에서 `feedback-aware 우선 검토`부터 확인

---

## 참고

상세 설명서는 아래 문서를 보면 됩니다.

- [current_feedback_aware_learning_loop_operator_guide_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_feedback_aware_learning_loop_operator_guide_ko.md)
- [current_p4_4_feedback_aware_proposal_promotion_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_p4_4_feedback_aware_proposal_promotion_ko.md)
