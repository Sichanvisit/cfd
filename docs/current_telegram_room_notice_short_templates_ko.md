# 텔레그램 방별 공지용 압축본

## 목적

이 문서는 실제 텔레그램 방에 고정 공지로 올려둘 수 있는 짧은 안내문을 정리한 템플릿이다.

대상 방은 아래 3개다.

1. 실시간 알림방
2. 체크방
3. PnL방

필요하면 그대로 복붙해서 쓰고, 방 이름만 조금 바꿔도 된다.

---

## 1. 실시간 알림방 공지 압축본

```text
[공지]
이 방은 실시간 실행 알림 전용입니다.

- 자동 진입 / 대기 / 청산 / 반전 알림만 올라옵니다.
- 이 방에서는 승인/거부를 하지 않습니다.
- 왜 그렇게 판단했는지 짧은 설명이 함께 붙습니다.

개선안 검토, detector 관찰, 제안 보고서는 체크방을 확인해 주세요.
손익 요약과 일간/주간 보고는 PnL방을 확인해 주세요.
```

### 더 짧은 1줄 버전

```text
[공지] 이 방은 실시간 실행 알림 전용입니다. 개선안 검토는 체크방, 손익 요약은 PnL방을 확인해 주세요.
```

---

## 2. 체크방 공지 압축본

```text
[공지]
이 방은 개선안 관찰/피드백/제안 검토용입니다.

- /detect : detector 관찰 결과 보기
- /detect_feedback D번호 맞았음|과민했음|놓쳤음|애매함 : detector 피드백 남기기
- /propose : 최근 거래 기준 수동 제안 보고서 보기

흐름:
/detect -> /detect_feedback -> feedback-aware 우선 검토 -> /propose

주의:
- 여기서 바로 전략이 자동 변경되지는 않습니다.
- detector 피드백은 제안 우선순위를 올리는 데만 사용됩니다.
- 실제 적용은 review/승인 이후에만 진행됩니다.

원문 보고서는 보고서 topic을 확인해 주세요.
```

### 더 짧은 1줄 버전

```text
[공지] 이 방은 개선안 체크방입니다. /detect, /detect_feedback, /propose 명령으로 관찰과 피드백, 제안 검토를 진행합니다.
```

---

## 3. 체크방 보고서 topic 공지 압축본

```text
[공지]
이 topic은 detector / proposal / review 원문 보고서용입니다.

- 체크 topic은 짧은 inbox
- 보고서 topic은 상세 원문

먼저 체크 topic에서 요약을 보고,
상세 확인이 필요할 때 이 topic의 원문 보고서를 보면 됩니다.
```

---

## 4. PnL방 공지 압축본

```text
[공지]
이 방은 손익 요약과 운영 교훈 확인용입니다.

- 15분 / 1시간 / 4시간 / 1일 / 1주 / 1달 손익 보고가 올라옵니다.
- 순손익, 총손익, 총 비용, 승패율, 진입 횟수, 총 랏을 봅니다.
- 오늘의 교훈과 readiness 요약이 함께 붙습니다.

실시간 실행 알림은 실시간 알림방,
개선안 검토와 detector 피드백은 체크방을 이용해 주세요.
```

### 더 짧은 1줄 버전

```text
[공지] 이 방은 손익 요약과 운영 교훈 확인용입니다. 실시간 실행은 알림방, 개선안 검토는 체크방을 확인해 주세요.
```

---

## 추천 고정 순서

### 실시간 알림방

1. 짧은 1줄 버전
2. 필요하면 긴 버전

### 체크방

1. 체크방 공지 압축본
2. 보고서 topic 공지 압축본

### PnL방

1. 짧은 1줄 버전
2. 필요하면 긴 버전

---

## 참고 문서

- [current_feedback_aware_learning_loop_operator_guide_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_feedback_aware_learning_loop_operator_guide_ko.md)
- [current_feedback_aware_learning_loop_notice_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_feedback_aware_learning_loop_notice_ko.md)
- [current_p4_4_feedback_aware_proposal_promotion_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_p4_4_feedback_aware_proposal_promotion_ko.md)
