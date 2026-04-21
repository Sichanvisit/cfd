# Current PA7-PA9 Roadmap Realignment v1

## 목적

이 문서는 기존 `PA` 로드맵을 갈아엎는 문서가 아니다.

대신 아래 사실을 반영해서
특히 `PA7 ~ PA9`의 의미를 현재 구현 상태에 맞게 다시 맞추는 문서다.

- path-aware checkpoint 뼈대는 이미 많이 구현됨
- scene axis가 별도 `SA` 트랙으로 실제로 붙음
- `trend_exhaustion` scene bias는 아직 `preview-only`
- `time_decay_risk`는 아직 `log-only`
- live `exit_manage_runner` source가 실제로 들어오기 시작함
- PA7 review packet과 manual-exception queue packet이 생김

즉 지금은 예전 초안처럼
`PA7 -> 바로 adoption 준비 -> PA8 live bounded adoption`
으로 보기보다,
`PA7 review packet -> PA8 action-only adoption review -> PA9 CL handoff`
로 읽는 게 맞다.

---

## 왜 재정의가 필요한가

처음 PA 로드맵을 잡을 때는 checkpoint 엔진 자체가 핵심이었다.

하지만 지금은 구조가 이렇게 바뀌었다.

```text
checkpoint row
-> passive score
-> best action resolver
-> hindsight dataset/eval
-> scene axis (별도 SA)
-> scene candidate / log-only bridge
-> trend_exhaustion preview-only bias
```

즉 `action baseline`과 `scene bias`가 분리되었다.

그래서 현재 상태에서
`PA8 bounded runtime adoption`
을 그대로 읽으면 오해가 생긴다.

지금 당장 bounded adoption review가 가능한 것은
`action baseline` 쪽이고,
`scene bias`는 아직 아니다.

---

## 재정의 결론

### PA7

기존 의미:

- harvest
- manual-exception queue

현재 의미:

- **review-ready packet 단계**
- manual-exception을 사람이 실제로 검토할 수 있게 group으로 묶는 단계
- live runner가 들어온 최신 dataset/eval을 review packet으로 정리하는 단계

즉 PA7은 단순 harvest가 아니라
`review packet / queue organization` 단계로 보는 것이 맞다.

### PA8

기존 의미:

- bounded runtime adoption

현재 의미:

- **action baseline의 bounded adoption review 단계**
- scene bias는 아직 preview-only라 PA8의 포함 대상이 아님

즉 현재 PA8은
`checkpoint action baseline을 bounded review/canary로 넘길 수 있는가`
를 보는 단계다.

여기서 `trend_exhaustion` scene bias는
참고 축일 뿐, 채택 대상은 아직 아니다.

### PA9

기존 의미:

- CL hand-off preparation

현재 의미:

- **action-stable handoff 먼저**
- scene-preview observability는 별도 조건이 찬 뒤 붙는 단계

즉 PA9은
`baseline action pipeline을 CL 운영층으로 넘길 준비`
가 우선이고,
scene bias는 SA8이 닫힌 뒤에 합류하는 게 맞다.

---

## 현재 상태 기준으로 다시 쓴 PA7-PA9

## PA7. Review Packet / Manual-Exception Queue

### 목적

- live runner가 실제로 들어온 최신 dataset/eval을 review-ready packet으로 정리한다
- manual-exception을 사람이 실제로 읽을 수 있는 queue로 묶는다
- 어떤 symbol/surface/checkpoint/family가 우선 review 대상인지 명확히 한다

### 현재 근거 산출물

- `checkpoint_pa78_review_packet_latest.json`
- `checkpoint_pa7_review_queue_packet_latest.json`

### 현재 상태 해석

- `PA7 review-ready`
- review packet은 충분히 형성됨
- top group부터 실제 검토 순서를 만들 수 있음

---

## PA8. Action-Only Bounded Adoption Review

### 목적

- checkpoint action baseline만 bounded adoption review 대상으로 본다
- scene bias는 아직 preview-only로 유지한다

### 포함 대상

- `management_action_label`
- action eval KPI
- live runner source가 반영된 position-side dataset

### 아직 제외 대상

- `trend_exhaustion` scene bias live adoption
- `time_decay_risk` scene bias adoption

### 현재 상태 해석

- action baseline은 review할 만큼 좋아짐
- 하지만 scene disagreement가 아직 높고
- trend_exhaustion은 preview sample이 작음
- 따라서 `PA8 = hold`, 정확히는 `bounded adoption review 전 보류`

---

## PA9. CL Hand-Off Preparation

### 목적

- PA baseline을 continuous operating layer로 넘길 준비를 한다

### 현재 우선순위

1. action baseline handoff
2. manual review queue 연결
3. canary/rollback 조건 고정
4. scene bias는 SA8 뒤에 합류

즉 PA9은 이제
`action-stable CL handoff`
로 읽는 게 맞다.

---

## SA와의 관계

현재는 PA와 SA를 섞지 않는 게 중요하다.

### 지금 가능한 것

- `PA7` 진행
- `PA8 review 기준 정리`
- `PA9 준비`

### 아직 더 봐야 하는 것

- `SA8`
- 이유:
  - scene high-confidence disagreement가 아직 큼
  - scene expected action alignment가 아직 더 올라와야 함
  - trend_exhaustion은 preview-only로는 좋지만 live bias로는 표본이 작음

즉 지금은

```text
PA는 계속 전진 가능
SA는 preview-only 관찰을 더 본 뒤 adoption 결정
```

으로 이해하는 게 맞다.

---

## 현재 한 줄 상태

```text
PA7 = 지금 진행
PA8 = action baseline review까지만
PA9 = baseline handoff 준비
SA8 = 아직 대기
```

---

## 최종 결론

네 말이 맞다.

현재 구조는 처음 PA 로드맵을 잡을 때와 달라졌고,
특히 `PA7 / PA8 / PA9`는 지금 실제 구현 상태에 맞게 해석을 바꿔야 한다.

가장 중요한 한 줄은 이거다.

> 지금 `PA8`은 scene bias까지 포함한 adoption 단계가 아니라,
> checkpoint action baseline을 bounded review 대상으로 올릴 수 있는지 보는 단계다.

그리고

> `scene bias`는 아직 `SA8`에서 더 로그를 보면서 결정하는 것이 맞다.
