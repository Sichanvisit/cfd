# 기다림 정리 Phase W3 상세 문서

부제: 이미 구현된 W2-4 surface를 기준으로 W3를 다시 정의하는 운영 관측 정리 문서

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 핵심 집계 및 read path 반영 완료

## 1. 문서 목적

이 문서는 원래 roadmap에 적혀 있던 `Phase W3. Wait Runtime Observability 강화`를
현재 실제 코드 상태에 맞게 다시 정의하기 위한 문서다.

초기 roadmap에서의 W3는
`recent wait semantic summary를 추가하는 단계`였다.
하지만 2026-03-27에 진행한 `W2-4 runtime surface` 구현에서
W3의 핵심 일부가 이미 선반영되었다.

따라서 지금의 W3는
처음 생각했던 “새로운 observability 시작 단계”가 아니라,
이미 열어둔 wait surface 위에서
`빠진 semantic summary를 메우고, 읽는 면을 정리하고, 완료 조건을 닫는 단계`
로 보는 편이 정확하다.


## 2. 원래 W3가 의도했던 것

원래 W3의 핵심 질문은 아래였다.

- 최근 window에서 어떤 wait state가 많았는가
- 어떤 wait가 hard wait로 굳었는가
- state와 decision 사이가 어떻게 이어졌는가
- energy trace 말고 wait semantic 자체를 어떻게 읽을 것인가

즉 W3는
`왜 wait가 많았는가`를 energy branch만으로 보지 말고,
wait state, hard/soft 성격, decision 분포까지 포함해서
운영자가 최근 흐름을 해석할 수 있게 만드는 단계였다.


## 3. 지금 이미 구현된 것

현재 코드는 W2-4 구현으로 아래를 이미 확보한 상태다.

### 3-1. wait contract가 row와 CSV에 남는다

이제 entry 경로 row에는 아래 wait 계약이 남는다.

- compact wait context
- compact wait bias bundle
- compact wait state-policy input
- wait energy trace
- wait decision energy trace

즉 “wait를 왜 그렇게 읽었는가”의 중간 의미가
개별 row와 hot payload에 남기 시작했다.

### 3-2. latest signal 표면에서도 wait를 읽을 수 있다

`latest_signal_by_symbol` compact row에서는 이제 아래를 바로 읽을 수 있다.

- 현재 wait policy state / reason
- release source / wait-lock source
- required side
- probe scene
- threshold shift summary

즉 최신 한 줄 기준으로도
wait semantic의 핵심 단서를 바로 볼 수 있다.

### 3-3. recent diagnostics에도 wait semantic 일부가 올라온다

현재 recent diagnostics에는 이미 아래 요약이 있다.

- `wait_energy_trace_summary`
- `wait_bias_bundle_summary`
- `wait_state_policy_surface_summary`
- `wait_special_scene_summary`
- `wait_threshold_shift_summary`

즉 “최근 wait가 어떤 bias/source/scene 성격을 가졌는가”는
예전보다 훨씬 빠르게 읽을 수 있다.


## 4. 그런데도 W3가 아직 남아 있는 이유

W2-4가 강해졌다고 해서 W3가 완전히 사라진 것은 아니다.
현재 surface는 `wait를 만든 재료`를 잘 보여주지만,
`wait semantic의 최종 분포`는 아직 부분적으로만 보인다.

핵심 부족점은 아래다.

### 4-1. wait state 분포가 아직 recent summary의 1급 표면이 아니다

현재 recent summary는 bias, scene, threshold shift는 잘 보여주지만,
정작 아래 질문에는 직접 답하지 않는다.

- 최근 `CENTER`, `CONFLICT`, `HELPER_SOFT_BLOCK`, `POLICY_BLOCK` 중 무엇이 많았는가
- hard wait는 어느 state에 집중됐는가
- state reason은 어떤 조합으로 반복됐는가

즉 W3의 본래 의도였던
`wait state semantic summary`
는 아직 완전히 닫히지 않았다.

### 4-2. decision 분포가 따로 요약돼 있지 않다

CSV에는 이미 아래 값이 남는다.

- wait selected 여부
- wait decision 값
- enter value / wait value

하지만 recent summary에서는
`state는 이랬는데 실제 decision은 wait였는가 skip이었는가`
를 한눈에 보게 해주는 요약이 아직 없다.

즉 지금은
“왜 이런 state가 나왔는가”는 잘 보이는데,
“그 state가 실제 선택으로 어떻게 이어졌는가”는 덜 보인다.

### 4-3. state와 decision을 잇는 bridge summary가 없다

운영에서 정말 자주 필요한 질문은 아래다.

- `HELPER_SOFT_BLOCK`가 실제로 wait로 많이 이어졌는가
- `CENTER`는 주로 skip으로 떨어지는가
- hard wait state는 거의 항상 wait를 선택하는가

이 질문은 단순 state count나 decision count만으로는 부족하고,
`state -> decision`을 잇는 bridge summary가 있어야 답할 수 있다.

### 4-4. handoff와 checklist는 아직 energy 중심이다

현재 handoff/read path는 많이 좋아졌지만,
wait 쪽에서는 아직 energy trace 읽는 법이 상대적으로 더 강하다.

즉 W3가 끝나려면
“recent wait semantic summary를 어떻게 읽는가”
도 문서 쪽에서 같이 닫혀야 한다.


## 5. 지금 시점에서 다시 정의한 W3의 목표

지금의 W3 목표는 아래 한 문장으로 정리하는 것이 가장 정확하다.

> 이미 구현된 wait context/bias/policy surface 위에,
> recent window 기준 `wait state`, `hard/soft`, `decision`, `state->decision bridge`
> 요약을 추가해 운영 해석을 완성한다.

즉 W3는 더 이상 “처음 observability를 여는 단계”가 아니라,
`wait semantic final layer를 마감하는 단계`
다.


## 6. W3에 포함해야 할 것

### 6-1. wait state semantic summary

반드시 있어야 할 기본 요약이다.

권장 항목:

- `wait_state_counts`
- `hard_wait_state_counts`
- `wait_reason_counts`
- `hard_wait_true_rows`

### 6-2. wait decision summary

state가 실제 선택으로 어떻게 이어졌는지 보기 위한 요약이다.

권장 항목:

- `wait_decision_counts`
- `wait_selected_rows`
- `wait_skipped_rows`
- `wait_selected_rate`

### 6-3. wait state-decision bridge summary

이 요약이 있어야 `왜 그 state가 문제가 되는가`를 운영에서 빠르게 읽을 수 있다.

권장 항목:

- `state_to_decision_counts`
- `hard_wait_selected_rows`
- `soft_wait_selected_rows`
- `selected_by_state_counts`

### 6-4. symbol summary parity

window 전체 요약만 있고 symbol summary가 약하면
실전 운영에서는 다시 CSV를 뒤지게 된다.

따라서 위 semantic summary들은
window 수준과 symbol 수준에 모두 있어야 한다.

### 6-5. handoff/read path sync

문서에도 아래가 추가되어야 한다.

- recent wait state counts 읽는 법
- hard wait와 soft wait의 차이
- state->decision bridge를 어떻게 해석하는지
- 어떤 패턴이면 rule 문제이고, 어떤 패턴이면 scene 문제인지


## 7. W3에 넣지 말아야 할 것

W3 범위를 불필요하게 키우지 않기 위해,
아래는 W3에 넣지 않는 편이 좋다.

### 7-1. alerting

예: 특정 count가 임계치를 넘으면 자동 경고.

이건 observability 확장이지
wait semantic summary의 core는 아니다.

### 7-2. 시계열 대시보드

예: 어제/오늘 비교, window 추세 비교.

이건 나중 단계다.
W3는 먼저 현재 window 해석을 완성하는 데 집중하는 편이 낫다.

### 7-3. chart correlation view

`consumer -> wait -> chart`를 한 화면으로 묶는 건
더 넓은 운영 표면 과제다.
W3 단독 범위를 넘는다.

### 7-4. exit/manage observability

이건 W6 이후 트랙에 가깝다.
지금 W3에 같이 넣으면 범위가 너무 커진다.


## 8. W3를 어떻게 쪼개는 게 적당한가

W1/W2처럼 아주 깊게 쪼갤 필요는 없다.
하지만 완전히 한 덩어리로 가기엔
의미 정의와 구현 면이 섞일 수 있다.

지금 시점에 가장 적당한 W3 분할은 아래 3단이다.

### W3-1. semantic summary inventory freeze

무엇을 recent summary에 넣을지 먼저 고정한다.

핵심:

- state semantic summary
- decision summary
- state-decision bridge summary
- symbol parity 여부

### W3-2. runtime aggregation implementation

실제 `trading_application.py` recent window 집계에
W3 semantic summary를 붙인다.

핵심:

- CSV row parsing 재활용
- window summary 추가
- symbol summary 추가
- slim default summary surface 추가

### W3-3. read path / test close-out

운영자가 읽는 면과 회귀 테스트를 마감한다.

핵심:

- runtime status test 추가
- handoff/checklist sync
- “이제 CSV 없이도 읽히는가” 기준 확인


## 9. W3 완료 선언 조건

아래를 만족하면 W3를 완료로 봐도 된다.

1. recent window에서 `wait_state_counts`를 바로 볼 수 있다.
2. hard wait 분포를 별도 요약으로 바로 볼 수 있다.
3. `wait_decision_counts`와 `wait_selected_rows`를 바로 볼 수 있다.
4. `state -> decision` bridge를 최소 count 수준으로는 읽을 수 있다.
5. 위 요약이 symbol summary에도 같이 존재한다.
6. slim/runtime top-level에도 기본 방향을 읽을 수 있는 요약이 있다.
7. handoff/checklist에 읽는 법이 정리돼 있다.
8. targeted runtime tests가 추가돼 있다.


## 10. 다음 문서

이 문서가 `W3가 지금 무엇이 되어야 하는가`를 정리한 기준서라면,
다음 문서인
`current_wait_architecture_reorganization_phase_w3_implementation_breakdown_ko.md`
는
실제로 어떤 순서로 구현할지를 적는 실행 문서가 된다.
