# P5-5 First Symbol Closeout/Handoff Transition Alerting

## 목표

`P5-4`에서 surface한 `first symbol closeout/handoff`와 `PA7 narrow review lane`을
상태판에만 남겨두지 않고, 실제로 중요한 전이가 발생하는 순간 `체크 topic / 보고서 topic`에 좁게 알린다.

## 왜 이 단계가 필요한가

- `WATCHLIST -> CONCENTRATED -> READY_*` 전이는 실제 운영에서 놓치기 쉬운 순간이다.
- `PA7 narrow review`가 다시 `REVIEW_NEEDED`로 올라오면 closeout 직전의 좁은 재검토가 필요하다.
- board를 계속 열어보지 않아도, 중요한 전이만 topic에 surface되면 운영 집중도가 훨씬 좋아진다.

## 구현 범위

### 1. first symbol 전이 알림

대상 전이:

- `CONCENTRATED`
- `READY_FOR_CLOSEOUT_REVIEW`
- `READY_FOR_HANDOFF_REVIEW`
- `READY_FOR_HANDOFF_APPLY`
- `APPLIED`

발송 조건:

- 이전 snapshot보다 status rank가 올라갔을 때
- 같은 rank라도 primary symbol이 바뀌었을 때

발송 route:

- `check`: 짧은 운영 요약
- `report`: 상세 원문 보고서

### 2. PA7 narrow review 전이 알림

대상 전이:

- `REVIEW_NEEDED`로 상승
- `REVIEW_NEEDED -> CLEAR` 해소

이 정보는 first symbol 알림과 함께 보고서에 포함한다.

### 3. 중복 방지

- 이전 상태 snapshot을 남긴다.
- 같은 symbol / 같은 status / 같은 narrow review 상태면 다시 보내지 않는다.

## 산출물

- `checkpoint_improvement_p5_observation_latest.json`
- `checkpoint_improvement_p5_observation_latest.md`
- orchestrator watch payload 안의 `p5_observation`

## 완료 조건

- `orchestrator watch`가 끝난 뒤 `P5-5` runtime이 같이 실행된다.
- first symbol이 `CONCENTRATED` 이상으로 올라가면 check/report에 좁게 surface된다.
- `PA7 narrow review`가 다시 필요해질 때도 같은 runtime에서 함께 surface된다.
- 같은 상태는 snapshot으로 dedupe된다.
