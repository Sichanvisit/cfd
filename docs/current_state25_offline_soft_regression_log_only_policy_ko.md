# State25 Offline Soft Regression Log-Only Policy

## 목적

이 문서는 `offline compare에서 약한 회귀가 나왔을 때 왜 바로 hold_offline으로 막지 않고 log_only_review_ready를 두는지`를 정리한다.

핵심은 간단하다.

- baseline보다 조금 나빠진 후보와
- baseline보다 확실히 위험한 후보를

같은 단계로 묶지 않는 것이다.

## 왜 필요한가

기존에는 offline compare가 사실상 이렇게 읽혔다.

- 좋아졌으면 `promote_review_ready`
- 아니면 `hold_regression`
- 별 차이 없으면 `hold_no_material_gain`

이 구조는 안전하지만 너무 보수적이다.

특히 log-only 단계에서는:

- threshold/size를 실제 주문에 강하게 반영하지 않고
- 후보가 어떤 식으로 움직일지 먼저 관찰하는 목적이 크기 때문에

`조금 나빠졌다는 이유만으로` 무조건 막을 필요는 없다.

## 이번에 추가한 decision

offline compare decision을 이제 이렇게 본다.

- `promote_review_ready`
- `log_only_review_ready`
- `hold_regression`
- `hold_no_material_gain`

### `promote_review_ready`

주요 task에서 개선이 확인된 상태다.

### `log_only_review_ready`

주요 task에서 약한 회귀는 있지만, 아직 log-only로는 검토해볼 수 있는 상태다.

이 단계는:

- canary/live 승인 아님
- log-only 검토 전용

이다.

### `hold_regression`

회귀가 너무 커서 log-only로도 올리면 안 되는 상태다.

### `hold_no_material_gain`

특별히 좋아진 것도, log-only로 굳이 검토할 이유도 없는 상태다.

## 현재 기준

이번 기준은 이렇게 나뉜다.

### hard regression

- task ready를 잃음
- macro F1 하락폭이 너무 큼

이 경우는 `hold_regression`

### soft regression

- task는 여전히 ready
- macro F1은 조금 떨어졌지만 catastrophic하지 않음

이 경우는 `log_only_review_ready`

## 왜 log-only까지만 허용하나

soft regression 후보는 아직 위험성이 남아 있다.

그래서:

- log-only는 허용 가능
- canary/live는 불가

로 가는 게 맞다.

즉 이 정책은 `막무가내로 문턱을 낮추는 것`이 아니라

`낮은 단계 rollout에 맞는 더 현실적인 문턱을 만드는 것`

이다.

## AI4 / AI5 / AI6 연결

이번 분리 이후 흐름은 이렇게 된다.

1. AI3가 `log_only_review_ready`를 만든다
2. AI4가 이를 받아 `log_only_ready`를 만들 수 있다
3. AI5는 threshold/size log-only를 검토할 수 있다
4. AI6는 `promote_log_only_ready` 후보로 계산할 수 있다

단, canary/live readiness는 여전히 별도다.

## 한 줄 요약

`약한 회귀는 곧바로 퇴출할 이유가 아니라, log-only로 먼저 관찰할 이유일 수 있다. 강한 회귀만 hold_regression으로 막고, 약한 회귀는 log_only_review_ready로 분리하는 것이 이번 정책의 핵심이다.`
