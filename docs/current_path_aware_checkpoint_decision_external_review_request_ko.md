# Current Path-Aware Checkpoint Decision External Review Request

## 목적

이 문서는 외부 리뷰어 또는 다른 LLM에게,
현재 CFD runtime이 왜 `한 점(point)`처럼 차트를 읽어서 반복적으로 잘못된 hold/exit/re-entry 판단을 내리는지,
그리고 이를 `경로(path)`와 `체크포인트(checkpoint)` 중심 구조로 어떻게 바꾸는 것이 맞는지
상세히 묻기 위한 요청서다.

이 문서의 초점은 `P0 wrong-side active-action conflict` 응급처치 그 자체가 아니다.

- `P0`는 지금 당장 잘못된 방향 진입을 막는 응급수술이고
- 이 문서는 그 다음 단계인
  `path-aware hold / partial-exit / full-exit / rebuy decision`
  구조를 어떻게 설계해야 하는지 묻는 것이다

즉 핵심 질문은 아래와 같다.

> 우리는 이미 `wrong-side SELL/BUY conflict`를 감지하고 일부는 차단/harvest하기 시작했다.
> 하지만 실제 차트는 한 번의 entry로 끝나지 않고,
> 큰 상승/하락 leg 안에서 `1, 2, 3, 4, 5` 같은 체크포인트가 반복된다.
> 이 각 체크포인트에서
> `HOLD / PARTIAL_EXIT / FULL_EXIT / REBUY / WAIT`
> 를 판단하도록 시스템을 어떻게 바꾸는 것이 맞는가?

## 이 문제를 쉽게 말하면

지금 시스템의 가장 큰 구조적 약점은 아래다.

- `point decision`에는 꽤 많이 투자했다
  - 지금 살까
  - 지금 기다릴까
  - 지금 팔까
- 하지만 실제 차트는 `path decision`이다
  - 처음 진입 후 첫 눌림
  - 다음 고점 전후
  - 되돌림 이후 재상승 여부
  - 부분청산 후 runner 유지 여부
  - 재매수 여부

즉 실제 시장은
`한 번 잘 사면 끝`
이 아니라
`그 뒤에 같은 포지션/같은 leg를 계속 다시 읽는 구조`
다.

그래서 지금처럼

- `local reversal`
- `upper reject`
- `break fail`

같은 짧은 장면만 세게 읽으면,
위로 가는 큰 흐름 안에서도 계속 아래만 보게 된다.

한 줄로 줄이면:

> 지금까지 주로 잡은 것은 `wrong-side SELL/BUY conflict`이고,
> 이번에 풀고 싶은 더 큰 본질은
> **차트를 한 점이 아니라 경로(path)로 읽게 만드는 것**이다.

## 실제로 어떤 장면에서 문제가 드러나는가

최근 NAS/XAU 차트를 사람이 읽으면 대략 아래 식으로 본다.

### 예시: 상승 leg 안의 체크포인트들

1. `1번`
   - 처음 사야 하는 자리
   - 즉 `initial_entry_surface`

2. `1번과 2번 사이`
   - 산 뒤 첫 눌림
   - 이게 건강한 눌림인지,
     아니면 바로 무너지는지 봐야 한다
   - 즉 `follow_through_surface`

3. `2번`
   - 수익 중이라면
     `더 들고 갈지 / 일부 팔지 / 전량 팔지`
     판단해야 한다
   - 즉 `continuation_hold_surface + protective_exit_surface`

4. `3번`
   - 다시 같은 질문이 반복된다
   - 이 하락이 진짜 전환인지,
     건강한 눌림인지 봐야 한다

5. `4번`, `5번`
   - 계속 똑같다
   - `지금 팔아야 하나`
   - `계속 들고 가야 하나`
   - `여기서 다시 사야 하나`

즉 사람이 보는 실제 차트는
`entry 한 번`이 아니라,
**한 leg 안에서 체크포인트를 계속 다시 읽는 구조**다.

## 현재 시스템이 잘하는 것 / 못하는 것

### 이미 어느 정도 되는 것

- `market-family` 분리
  - `NAS100`
  - `BTCUSD`
  - `XAUUSD`
- `4개 surface` 분리
  - `initial_entry_surface`
  - `follow_through_surface`
  - `continuation_hold_surface`
  - `protective_exit_surface`
- `wrong-side active-action conflict` 감지
- 일부 장면에서 `SELL -> WAIT` 강등과 반대 candidate bridge
- failure harvest, preview dataset, evaluation, signoff packet, activation contract

즉 시스템은 이미
`진입 / 추종 / 보유 / 보호청산`
을 surface 단위로는 많이 나눠놨다.

### 아직 부족한 것

하지만 지금은 여전히 많은 row가
`독립된 한 점의 판단`
처럼 남는다.

즉 현재 row는 잘 남아도,

- 이 row가 같은 leg의 `몇 번째 checkpoint`인지
- 직전 pivot 이후 얼마나 왔는지
- 지금 하락이 건강한 눌림인지 전환인지
- 여기서 가장 맞는 행동이 `HOLD`인지 `PARTIAL_EXIT`인지 `FULL_EXIT`인지 `REBUY`인지

가 구조적으로 약하다.

즉 현재 gap은:

> `surface 분리`는 되어 있는데,
> 아직 `path memory / checkpoint context`가 약하다.

## 현재 구조와 이번 질문의 연결

이 질문은 기존 로드맵과 완전히 별개가 아니다.

### 현재까지 진행된 것

- `PF0` 성능 baseline hold: 완료
- `MF1 ~ MF16`: 구현 완료
- `MF17`: 구조 구현 완료
- `BTCUSD / NAS100 / XAUUSD initial_entry_surface`
  3개는 공통 signoff packet과 activation contract에 올라와 있음
- `P0`는 wrong-side active-action conflict를 먼저 잡는 hotfix로 진행 중

즉 현재 큰 줄기는:

1. `P0 runtime correction`
2. `MF17 manual signoff / bounded activation`
3. `CL operating layer`

이다.

이번 질문은 이 중 어디에 끼느냐 하면,

- `P0`가 응급처치라면
- 이번 path-aware checkpoint 문제는
  `follow_through / continuation_hold / protective_exit`
  를 실제 차트 경로 단위로 더 정교하게 만드는
  **다음 구조 설계 질문**
  이다.

## 현재 문제를 구조적으로 다시 쓰면

### 현재

```text
row 하나 = action 하나
```

예:

- BUY
- SELL
- WAIT
- EXIT

처럼 한 row를 한 번의 결론으로 많이 읽는다.

### 앞으로 필요한 것

```text
leg 하나 = checkpoint 여러 개
checkpoint마다 best action을 다시 판단
```

즉 바뀌어야 할 구조는:

```text
[leg detection]
    ↓
[checkpoint segmentation]
    ↓
[checkpoint state + odds]
    ↓
[best action label]
```

여기서 `best action label`은 예를 들면:

- `HOLD`
- `PARTIAL_EXIT`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

가 된다.

## 우리가 생각하는 목표 구조

### 1. Point Decision 에서 Path Checkpoint Decision 으로

즉 기존에는

- `지금 사나 마나`
- `지금 파나 마나`

였다면,

앞으로는

- 이 leg의 현재 checkpoint는 어디인가
- continuation 확률이 reversal 확률보다 높은가
- 포지션 상태를 유지할지, 줄일지, 끊을지, 다시 늘릴지

를 본다.

### 2. 같은 leg를 계속 추적

필요한 건 최소 아래다.

- `leg_id`
- `leg_direction`
- `checkpoint_id`
- `checkpoint_index_in_leg`
- `last_pivot_distance`
- `bars_since_last_push`
- `bars_since_last_checkpoint`

즉 row가 독립적으로 흩어지는 게 아니라,
같은 leg 안의 checkpoint로 묶여야 한다.

### 3. action도 entry/exit 이분법으로 보지 않는다

지금부터는 최소 아래 행동을 구분해야 한다.

- `HOLD`
- `PARTIAL_EXIT`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

그리고 이 행동은 symbol + surface + checkpoint context 위에서 판단해야 한다.

## checkpoint row에 넣고 싶은 필드 초안

아래는 우리가 현재 생각하는 최소 schema 초안이다.

- `checkpoint_id`
- `leg_id`
- `symbol`
- `surface_name`
- `leg_direction`
- `checkpoint_index_in_leg`
- `checkpoint_type`
  - `initial_push`
  - `first_pullback`
  - `reclaim_check`
  - `late_trend_check`
  - `runner_check`
- `last_pivot_price`
- `last_pivot_distance`
- `bars_since_last_push`
- `bars_since_last_checkpoint`
- `continuation_odds`
- `reversal_odds`
- `hold_quality_score`
- `partial_exit_ev`
- `full_exit_risk`
- `rebuy_readiness`
- `current_pnl_state`
- `best_action_label`
  - `HOLD`
  - `PARTIAL_EXIT`
  - `FULL_EXIT`
  - `REBUY`
  - `WAIT`

핵심은:

> 지금은 주로 `BUY / SELL / WAIT`가 앞에 서 있는데,
> 앞으로는 `best action label`이
> hold/partial/full-exit/rebuy까지 포함해야 한다.

## checkpoint 상태기계 초안

### A. leg 시작

- `LEG_START`
- 여기서는 주로 `initial_entry_surface`

### B. 첫 push 이후

- `FIRST_PUSH`
- continuation quality를 본다

### C. 첫 눌림

- `FIRST_PULLBACK_CHECK`
- 건강한 눌림인지, 바로 무너지는지 본다

### D. 재상승 / reclaim

- `RECLAIM_CHECK`
- 여기서 `HOLD / PARTIAL_EXIT / REBUY` 판단이 중요하다

### E. 늦은 구간

- `LATE_TREND_CHECK`
- 이미 많이 온 leg에서
  `runner 유지`와 `protective exit`를 다시 판단한다

즉 action state는 단순히
`BUY / SELL`
이 아니라
`leg의 어느 checkpoint에 있느냐`
와 같이 봐야 한다.

## 현재 4개 surface와의 연결 방식

이 path-aware 구조가 4개 surface를 대체하는지는 아직 열려 있다.
현재 내부 생각은 `대체`보다는 `연결`이 맞다.

### `initial_entry_surface`

- `1번` 같은 첫 진입

### `follow_through_surface`

- 진입 직후 첫 눌림 / 첫 재가속
- `1번과 2번 사이`

### `continuation_hold_surface`

- `2, 3, 4, 5` 같은 중간 checkpoint
- hold / runner / partial exit

### `protective_exit_surface`

- 건강한 눌림이 아니라 thesis 붕괴일 때
- full exit 쪽

즉 현재 생각은:

> `surface`는 유지하고,
> 그 위에 `checkpoint / leg memory`를 추가하는 쪽이 더 맞아 보인다.

## 현재 시스템이 왜 이 구조를 특히 필요로 하는가

최근 NAS/XAU를 보면,
문제는 단순히 "BUY를 못 잡는다"가 아니라 아래와 같다.

- 위로 가는 큰 흐름 안에서도
  중간 눌림만 보고 계속 아래를 세게 읽는다
- local reversal / upper reject / break fail을 과하게 읽는다
- 그래서
  - 너무 빨리 판다
  - 부분청산과 전량청산이 분리되지 않는다
  - 재매수 타이밍을 놓친다

즉 지금 gap은 단순 prediction gap이 아니라,

> `path checkpoint action gap`

에 가깝다.

## 외부 리뷰에서 특히 묻고 싶은 것

### 질문 1. 이 문제는 새 surface로 보는 게 맞는가, 아니면 기존 4 surface 위의 checkpoint layer가 맞는가

즉:

- `5번째 surface`를 따로 만들지
- 아니면
  `follow_through / continuation_hold / protective_exit`
  위에 공통 `checkpoint context`를 얹을지

어느 쪽이 더 안정적인가.

### 질문 2. leg / checkpoint segmentation을 어떤 기준으로 자르는 것이 가장 실무적인가

예:

- pivot 기반
- breakout/pullback/reclaim 기반
- volatility / bar-count 기반
- hybrid 기반

어느 방식이 가장 좋은가.

### 질문 3. `best_action_label`은 어떤 taxonomy가 가장 좋은가

현재 초안:

- `HOLD`
- `PARTIAL_EXIT`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

이 5개면 충분한지,
아니면

- `HOLD_RUNNER`
- `PARTIAL_THEN_HOLD`
- `TRAIL_EXIT`

같은 세분이 필요한지 묻고 싶다.

### 질문 4. checkpoint action을 어떤 evidence 층으로 계산하는 게 좋은가

현재 생각은 아래 3층이다.

1. `structure`
   - higher high / lower low
   - reclaim success / failure
2. `time`
   - bars since last push
   - bars since last checkpoint
3. `position state`
   - current pnl
   - runner already secured?

이 3층이 충분한지 묻고 싶다.

### 질문 5. 어떤 라벨은 자동 적용하고 어떤 라벨은 manual-exception으로 남겨야 하는가

예:

- obvious `premature_full_exit`
- obvious `missed_rebuy`
- ambiguous `partial_exit vs hold`

처럼 confidence가 다를 수 있다.

어디까지 auto-apply가 안전한지 묻고 싶다.

### 질문 6. 이 구조가 CL operating layer보다 먼저 필요한가, 아니면 CL 안에서 흡수하는 게 맞는가

현재 내부 생각은:

- `P0`는 먼저
- `MF17 initial_entry`는 signoff/activation 계속
- `path-aware checkpoint design`은
  다음으로 `follow_through / hold / exit` 쪽의 핵심 구조

로 보는 것이 맞아 보인다.

이 순서가 맞는지 묻고 싶다.

## 우리가 현재 보는 유력 방향

현재 내부에서는 아래 방향을 유력하게 본다.

1. `P0 wrong-side conflict`는 응급처치로 계속 진행
2. `MF17 initial_entry`는 signoff/activation 문으로 유지
3. 그 다음
   `path-aware checkpoint decision`
   을
   - `follow_through`
   - `continuation_hold`
   - `protective_exit`
   위에 얹는 공통 구조로 설계
4. 그 뒤에
   `continuous harvest -> rebuild -> eval -> candidate -> canary`
   운영 루프로 연결

즉 지금은
`새 BUY/SELL 신호 하나 더 만들기`
보다,
**상승/하락 leg 안의 checkpoint마다 가장 맞는 action을 고르는 구조**
가 더 중요하다고 본다.

## 아주 짧은 질문 블록

아래 질문에 대한 의견을 듣고 싶다.

1. NAS/XAU 차트처럼 한 번의 큰 상승/하락 leg 안에서 `1,2,3,4,5` 체크포인트마다 `HOLD / PARTIAL_EXIT / FULL_EXIT / REBUY / WAIT`를 다시 판단해야 하는 문제를, 기존 4-surface 위의 `checkpoint layer`로 푸는 것이 맞는가?
2. 이 checkpoint layer의 최소 row schema와 상태기계는 어떻게 잡는 것이 가장 안정적인가?
3. `point decision`에서 `path checkpoint decision`으로 넘어갈 때, 어떤 라벨은 auto-apply로, 어떤 라벨은 manual-exception으로 남겨야 하는가?
4. 이 구조를 `P0 -> MF17 -> CL` 흐름 안에서 어디에 두는 것이 가장 실무적으로 맞는가?
