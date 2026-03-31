# 진입 / 청산 / 대기 사유가 지금 구조에서 어떻게 표현되는가

## 문서 목적
이 문서는 다음 질문에 답하기 위해 작성한 문서입니다.

- 예전에는 점수와 예외 규칙으로 진입/청산/대기를 설명했는데, 지금은 무엇으로 설명하는가
- 위치 에너지(`PositionEnergySnapshot`)가 생긴 뒤, 그것이 바로 진입/청산 점수가 되는가
- 지금 구조에서 “진입 사유”, “기다림 사유”, “청산 사유”는 각각 어떤 변수와 계약으로 표현되는가
- 다른 스레드가 봐도 현재 표현 체계를 이해할 수 있게, 변수 의미까지 포함해서 한 번에 설명할 수 있는가

이 문서는 **예전 점수형 구조**와 **현재 semantic contract 구조**의 차이를 정리하고,  
현재 코드베이스에서 이유(reason)가 실제로 어디에 표현되는지를 설명합니다.

---

## 한 줄 핵심

지금 구조에서는 더 이상  
**“점수 하나가 높아서 진입했다 / 점수 하나가 낮아서 기다렸다 / 점수 하나가 꺾여서 청산했다”**  
처럼 표현하지 않습니다.

대신 이유는 다음처럼 분해되어 표현됩니다.

1. **무슨 거래인가**  
- `archetype_id`

2. **지금 행동할 준비가 됐는가**  
- `confidence`
- `Evidence / Belief / Barrier / Forecast`

3. **왜 아직 안 들어가는가**  
- `state`
- `action`
- `blocked_reason`
- consumer block reason

4. **무엇이 깨지면 틀린 거래인가**  
- `invalidation_id`

5. **들어간 뒤 어떻게 관리할 거래인가**  
- `management_profile_id`
- `TradeManagementForecast`

즉 지금 구조는 **점수 하나로 모든 걸 설명하는 방식이 아니라,  
거래의 정체성 / 준비도 / 차단 사유 / 실패 조건 / 관리 사유를 분리해서 표현하는 방식**입니다.

---

## 1. 예전 구조와 지금 구조의 차이

## 예전 구조
예전에는 대체로 다음처럼 해석되었습니다.

- 위치 점수
- 반응 점수
- noise penalty
- soft-pass
- hard guard
- setup reason

이 값들이 서로 섞여서
- 왜 들어갔는지
- 왜 안 들어갔는지
- 왜 빨리 정리했는지

가 한 덩어리로 표현되는 경향이 있었습니다.

그래서 생기는 문제:
- 위치 의미와 행동 결정이 섞임
- 상단에 있다는 사실과 상단에서 실패했다는 사실이 쉽게 혼동됨
- 점수는 있는데 거래의 정체성이 문장으로 안 읽힘

## 지금 구조
지금은 아래처럼 분리합니다.

```text
Position
-> Response
-> State
-> Evidence
-> Belief
-> Barrier
-> Forecast
-> Observe / Confirm / Action
-> Consumer
```

즉:
- `Position`은 위치
- `Response`는 전이 반응
- `State`는 해석 계수
- `Evidence`는 즉시 증거
- `Belief`는 누적 확신
- `Barrier`는 구조 장벽
- `Forecast`는 다음 전개 예측
- `OCA`는 lifecycle 결정
- `Consumer`는 실행

이제 이유는 이 체인 위에서 분해되어 표현됩니다.

---

## 2. 위치 에너지(Position Energy)는 지금 어떤 의미인가

여기서 가장 중요한 오해를 먼저 정리해야 합니다.

### 위치 에너지는 직접 행동 점수가 아닙니다
`PositionEnergySnapshot`의 대표 필드:
- `upper_position_force`
- `lower_position_force`
- `middle_neutrality`
- `position_conflict_score`

이 값들은:
- 지금 상단/하단/중앙 중 어디 에너지가 더 센지
- 위치 충돌이 얼마나 큰지

를 설명합니다.

하지만 이 값이 바로
- 진입 점수
- 청산 점수
- 대기 점수

가 되는 것은 아닙니다.

### 지금 구조에서 위치 에너지는 어떻게 쓰이나
위치 에너지는 보통 다음 용도로만 씁니다.

1. `PositionInterpretation` 보조
- 정렬
- bias
- conflict
- unresolved

2. `State`에서 quality source
- `conflict_damp`
- `alignment_gain`

3. `Barrier`에서 구조 장벽 source
- `position_conflict_score`
- `middle_neutrality`

4. `ForecastFeatures` input
- 현재 구조 품질의 일부 입력

즉 위치 에너지는 **상류 semantic source**이지,  
직접 `BUY/SELL/EXIT/WAIT` 점수 그 자체가 아닙니다.

---

## 3. 지금 구조에서 “진입 사유”는 무엇으로 표현되는가

현재 구조에서 진입 사유는 한 변수로 끝나지 않습니다.

진입 사유는 최소한 아래 5개의 조합으로 표현됩니다.

### A. 거래 정체성
- `archetype_id`

이게 “무슨 거래인가”를 가장 먼저 말해줍니다.

예:
- `upper_reject_sell`
- `upper_break_buy`
- `lower_hold_buy`
- `lower_break_sell`
- `mid_reclaim_buy`
- `mid_lose_sell`

즉 예전의 “setup reason”보다 더 근본적인 **거래 identity** 입니다.

### B. 방향
- `side`

값:
- `BUY`
- `SELL`
- `""`

의미:
- 현재 archetype이 어느 방향 거래인지를 말합니다

### C. lifecycle 상태
- `state`

값:
- `OBSERVE`
- `CONFIRM`
- `CONFLICT_OBSERVE`
- `NO_TRADE`
- `INVALIDATED`

의미:
- 지금 거래 정체성이 있는지 없는지보다
- **지금 lifecycle 단계가 어디인지**를 말합니다

즉 `state`는 패턴 이름이 아닙니다.

### D. 실행 여부
- `action`

값:
- `WAIT`
- `BUY`
- `SELL`
- `NONE`

의미:
- 지금 실제로 실행 가능한 행동이 있는지

중요:
- 같은 `archetype_id`라도 `state=OBSERVE`, `action=WAIT`일 수 있습니다
- 즉 거래 정체성이 있는데도 아직 실행 준비가 안 됐다는 뜻입니다

### E. 실행 준비도
- `confidence`

의미:
- 이건 확률이 아니라 **execution readiness score** 입니다
- “이 거래가 얼마나 준비됐는가”를 말합니다

즉 지금의 진입 사유는:

```text
무슨 거래인가(archetype_id)
+ 어느 방향인가(side)
+ 지금 confirm/action 준비가 됐는가(confidence)
+ 그래서 지금 실행인가(action)
```

이 조합으로 표현됩니다.

---

## 4. 진입 사유에서 각 semantic layer가 맡는 역할

진입 사유는 지금 아래처럼 만들어집니다.

## Position + Response
역할:
- archetype 후보 생성

즉:
- `PositionSnapshot + ResponseVectorV2`
가 어떤 거래 archetype인지 정체성을 만듭니다.

예:
- `UPPER + upper_reject_down -> upper_reject_sell`
- `LOWER + lower_hold_up -> lower_hold_buy`
- `MIDDLE + mid_reclaim_up -> mid_reclaim_buy`

중요:
- 여기서 거래 정체성이 만들어집니다
- 이게 예전 점수식과 가장 큰 차이입니다

## State
역할:
- 해석 계수

예:
- `range_reversal_gain`
- `trend_pullback_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`

의미:
- 거래 identity를 바꾸는 게 아니라
- 그 거래를 얼마나 믿을지 조절합니다

## Evidence
역할:
- immediate proof

예:
- `buy_reversal_evidence`
- `sell_reversal_evidence`
- `buy_total_evidence`
- `sell_total_evidence`

의미:
- 지금 당장 어느 쪽 증거가 더 강한가

## Belief
역할:
- persistence / time accumulation

예:
- `buy_belief`
- `sell_belief`
- `belief_spread`
- `transition_age`

의미:
- confirm로 믿을 만한 누적성이 있는가

## Barrier
역할:
- action suppression

예:
- `buy_barrier`
- `sell_barrier`
- `middle_chop_barrier`
- `conflict_barrier`

의미:
- 증거가 있어도 왜 아직 action을 누르는가

## Forecast
역할:
- 시나리오 예측

예:
- `p_buy_confirm`
- `p_sell_confirm`
- `p_false_break`
- `p_continue_favor`
- `p_fail_now`

의미:
- 지금 이 구조가 다음에 confirm/fake/continue/fail 중 어디로 갈 가능성이 큰가

즉 지금 진입 사유는  
**semantic bundle + forecast가 `archetype_id`, `state`, `action`, `confidence`로 번역된 결과**입니다.

---

## 5. 지금 구조에서 “기다림 사유”는 무엇으로 표현되는가

예전에는 기다림도 그냥 점수가 낮거나 패스가 안 돼서라고 설명되기 쉬웠습니다.

지금은 기다림도 분해됩니다.

## A. semantic non-action
이건 애초에 semantic layer 기준으로 action이 안 나오는 경우입니다.

표현:
- `state = OBSERVE`
- `action = WAIT`
- 또는 `state = CONFLICT_OBSERVE`

즉:
- 거래 방향감은 있을 수 있음
- 하지만 아직 confirm/action으로 올릴 수 없음

대표 원인:
- evidence는 있는데 belief가 약함
- barrier가 높음
- forecast가 fake risk를 높게 봄
- conflict/chop이 큼

이 경우 reason은 보통:
- `reason`
- `metadata.blocked_reason`
- `metadata.winning_evidence`
- `metadata.effective_contributions`
로 설명됩니다.

## B. execution block
이건 semantic layer 기준으로는 action이 있었지만, consumer가 실행을 막은 경우입니다.

예:
- spread 너무 큼
- opposite position lock
- price cluster
- bb touch 조건 부족

이건 semantic wait와 다릅니다.

표현:
- `consumer_guard_result = EXECUTION_BLOCK`
- `consumer_block_reason`
- `consumer_block_kind`
- `consumer_block_source_layer`

즉 지금 기다림 사유는 크게 둘로 나눠서 봐야 합니다.

1. semantic wait
- 아직 confirm/action이 아님

2. execution block
- confirm/action은 맞지만 실행 guard에서 막힘

이 둘을 섞으면 안 됩니다.

---

## 6. 지금 구조에서 “청산 사유”는 무엇으로 표현되는가

청산은 아직 진입만큼 완전히 새 contract로 통합되었다고 보긴 이르지만,
이미 canonical handoff는 있습니다.

핵심은:
- 청산도 더 이상 “점수 하나 꺾였다”가 아니라
- **이 거래의 관리 프로필과 실패 조건이 무엇인가**로 표현해야 한다는 점입니다.

## A. 실패 조건
- `invalidation_id`

예:
- `upper_reject_sell -> upper_break_reclaim`
- `upper_break_buy -> breakout_failure`
- `lower_hold_buy -> lower_support_fail`
- `mid_reclaim_buy -> mid_relose`

의미:
- 이 거래가 틀렸다고 볼 canonical 실패 조건

즉 청산 사유의 첫 번째 축은:
- “무엇이 깨졌는가”

입니다.

## B. 관리 방식
- `management_profile_id`

예:
- `reversal_profile`
- `breakout_hold_profile`
- `support_hold_profile`
- `breakdown_hold_profile`
- `mid_reclaim_fast_exit_profile`
- `mid_lose_fast_exit_profile`

의미:
- 이 거래를 어떤 철학으로 관리할 것인가

즉 청산 사유의 두 번째 축은:
- “원래 이 거래는 어떻게 관리되어야 하는가”

입니다.

## C. management forecast
- `p_continue_favor`
- `p_fail_now`
- `p_recover_after_pullback`
- `p_reach_tp1`
- `p_opposite_edge_reach`
- `p_better_reentry_if_cut`

의미:
- 지금 hold가 더 낫나
- 지금 fail/cut이 더 낫나
- 흔들려도 회복 가능한가
- 차라리 끊고 재진입하는 게 낫나

즉 청산 사유의 세 번째 축은:
- “지금 관리 시나리오가 어느 쪽으로 기울었는가”

입니다.

현재 canonical exit handoff는:
- `management_profile_id`
- `invalidation_id`

이고,
이 위에 management forecast가 붙어서 나중에 더 정교한 exit/re-entry로 가는 구조입니다.

---

## 7. 현재 구조에서 reason 문자열은 무엇을 의미하는가

많이 헷갈리는 부분이라 따로 적습니다.

`ObserveConfirmSnapshot.reason`은  
**최종적인 짧은 routing/decision 설명 문자열**입니다.

즉 이 문자열 하나가 시스템의 모든 의미를 다 담는 건 아닙니다.

지금 구조에서 이유는 여러 층에 나눠져 있습니다.

### 정체성
- `archetype_id`

### lifecycle
- `state`
- `action`

### 준비도
- `confidence`

### 짧은 라우팅 설명
- `reason`

### 세부 기여도
- `metadata.raw_contributions`
- `metadata.effective_contributions`
- `metadata.winning_evidence`
- `metadata.blocked_reason`

### consumer 실행 차단 상세
- `consumer_guard_result`
- `consumer_block_reason`
- `consumer_block_kind`
- `consumer_block_source_layer`

즉 지금은 `reason` 하나만 보면 부족하고,  
**정체성 + 준비도 + block metadata까지 같이 봐야 진짜 이유가 읽힙니다.**

---

## 8. 지금 구조에서 변수별 의미 정리

아래는 다른 스레드가 가장 빨리 이해해야 하는 핵심 변수들입니다.

## Position 쪽
- `primary_label`
  - 현재 위치 해석의 주 라벨
- `bias_label`
  - 완전 정렬은 아니지만 어느 쪽 bias인지
- `secondary_context_label`
  - 2차 축 맥락
- `position_conflict_score`
  - 위치 충돌 정도
- `middle_neutrality`
  - 중앙 중립성

## Response 쪽
- `lower_hold_up`
  - 하단 지지/반등
- `lower_break_down`
  - 하단 실패/이탈
- `mid_reclaim_up`
  - 중심 재탈환
- `mid_lose_down`
  - 중심 상실
- `upper_reject_down`
  - 상단 실패/저항
- `upper_break_up`
  - 상단 돌파/유지

## State 쪽
- `range_reversal_gain`
  - range 반전 강화
- `trend_pullback_gain`
  - trend 눌림/continuation 강화
- `noise_damp`
  - 노이즈 감쇠
- `conflict_damp`
  - 충돌 감쇠
- `alignment_gain`
  - 정렬 강화
- `countertrend_penalty`
  - 역방향 페널티

## Evidence 쪽
- `buy_reversal_evidence`
  - buy 반전 증거
- `sell_reversal_evidence`
  - sell 반전 증거
- `buy_continuation_evidence`
  - buy 연장 증거
- `sell_continuation_evidence`
  - sell 연장 증거
- `buy_total_evidence`
  - buy 총합 증거
- `sell_total_evidence`
  - sell 총합 증거

## Belief 쪽
- `buy_belief`
  - buy 누적 확신
- `sell_belief`
  - sell 누적 확신
- `buy_persistence`
  - buy 지속성
- `sell_persistence`
  - sell 지속성
- `belief_spread`
  - buy vs sell 차이
- `transition_age`
  - 현재 dominant transition의 나이

## Barrier 쪽
- `buy_barrier`
  - buy action 장벽
- `sell_barrier`
  - sell action 장벽
- `conflict_barrier`
  - conflict 장벽
- `middle_chop_barrier`
  - middle/chop 장벽
- `direction_policy_barrier`
  - policy 장벽
- `liquidity_barrier`
  - 유동성/실행 품질 장벽

## Forecast 쪽
- `p_buy_confirm`
  - buy confirm 시나리오 점수
- `p_sell_confirm`
  - sell confirm 시나리오 점수
- `p_false_break`
  - fake break 시나리오 점수
- `p_reversal_success`
  - reversal 성공 시나리오 점수
- `p_continuation_success`
  - continuation 성공 시나리오 점수
- `p_continue_favor`
  - hold/연장 우세 시나리오 점수
- `p_fail_now`
  - 즉시 실패/정리 우세 시나리오 점수
- `p_recover_after_pullback`
  - 흔들린 뒤 회복 가능성
- `p_better_reentry_if_cut`
  - 끊고 재진입이 더 좋은 시나리오

## OCA 쪽
- `state`
  - lifecycle 상태
- `action`
  - 현재 실행 가능한 행동
- `side`
  - 방향
- `confidence`
  - 실행 준비도
- `reason`
  - 짧은 라우팅 이유
- `archetype_id`
  - 거래 정체성
- `invalidation_id`
  - canonical 실패 조건
- `management_profile_id`
  - canonical 관리 프로필

## Consumer 쪽
- `consumer_guard_result`
  - PASS / SEMANTIC_NON_ACTION / EXECUTION_BLOCK
- `consumer_block_reason`
  - 왜 실행이 막혔는지
- `consumer_block_kind`
  - semantic인지 execution인지
- `consumer_block_source_layer`
  - 어디서 막혔는지

---

## 9. 지금 구조에서 진입/기다림/청산을 읽는 가장 실용적인 방법

다른 스레드가 실제 row 하나를 읽을 때는 이 순서가 가장 좋습니다.

### 진입 사유 읽기
1. `archetype_id`
2. `side`
3. `state`
4. `action`
5. `confidence`
6. `reason`
7. `winning_evidence`
8. `effective_contributions`

### 기다림 사유 읽기
1. `state=OBSERVE/CONFLICT_OBSERVE` 인가
2. `action=WAIT` 인가
3. `blocked_reason`이 semantic wait인가
4. 아니면 consumer에서 execution block인가
5. `consumer_block_reason` 확인

### 청산/관리 사유 읽기
1. `management_profile_id`
2. `invalidation_id`
3. `TradeManagementForecast`
4. 이후 exit/re-entry consumer에서 실제 실행 이유 확인

즉:
- 진입은 `archetype + confirm readiness`
- 기다림은 `semantic wait vs execution block`
- 청산은 `management profile + invalidation + management forecast`

로 읽는 게 지금 구조에 가장 맞습니다.

---

## 10. 최종 요약

지금 시스템은 더 이상

```text
점수 높음 -> 진입
점수 낮음 -> 대기
점수 꺾임 -> 청산
```

으로 표현되는 구조가 아닙니다.

지금은:

```text
Position / Response
-> 거래 정체성(archetype_id)

State / Evidence / Belief / Barrier / Forecast
-> confirm/action 준비도(confidence)
-> wait or confirm split

invalidation_id
-> 무엇이 깨지면 틀린 거래인가

management_profile_id + TradeManagementForecast
-> 들어간 뒤 어떻게 관리할 것인가
```

즉 현재 구조에서 이유는
- **정체성**
- **준비도**
- **차단 사유**
- **실패 조건**
- **관리 프로필**

로 나뉘어 표현됩니다.

이게 예전 점수형 구조와 가장 큰 차이입니다.
