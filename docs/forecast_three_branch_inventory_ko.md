# Forecast 3갈래 상세 정리

## 1. 왜 이 문서를 따로 만드나

`Forecast`는 그냥 하나의 예측 덩어리가 아니라, 원래부터 역할이 다른 갈래로 나뉘어 있었다.

그런데 실제 점검을 하다 보면 아래가 자주 섞인다.

- `forecast_features_v1`
- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1`
- `forecast_effective_policy_v1`

그래서 이 문서에서는 `Forecast`를 아래 구조로 다시 분리해서 본다.

```text
semantic inputs
-> forecast_features_v1
-> transition_forecast_v1
-> trade_management_forecast_v1
-> forecast_gap_metrics_v1
-> forecast_effective_policy_v1
```

중요한 점:

- `forecast_features_v1`는 `3갈래 출력`이 아니라 입력 번들이다
- 실제 `3갈래`는
  - `transition_forecast_v1`
  - `trade_management_forecast_v1`
  - `forecast_gap_metrics_v1`
  이 세 개다

---

## 2. 한눈에 보는 구조

| 층 | 이름 | 역할 | 성격 |
|---|---|---|---|
| 입력 번들 | `forecast_features_v1` | upstream semantic layer를 Forecast에 넘김 | input bundle |
| 1갈래 | `transition_forecast_v1` | 지금 반응이 어떤 방향 전개로 이어질지 예측 | transition branch |
| 2갈래 | `trade_management_forecast_v1` | 보유/청산/재진입 관리 쪽 예측 | management branch |
| 3갈래 | `forecast_gap_metrics_v1` | 위 두 forecast 차이를 요약 | comparison branch |
| 래퍼 | `forecast_effective_policy_v1` | layer mode/effective 경로로 넘김 | effective wrapper |

---

## 3. 입력 번들: `forecast_features_v1`

### 3-1. 의미

이건 Forecast 자체가 아니라, Forecast가 판단하는 데 필요한 semantic 입력을 한데 묶은 것이다.

즉:

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

를 한 번에 받아서, 그 위에서 forecast를 만든다.

### 3-2. 현재 실제로 담기는 것

주요 입력은 대략 아래와 같다.

- `position_snapshot_v2`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`

또한 context 쪽에서 signal metadata도 같이 실린다.

- `signal_timeframe`
- `signal_bar_ts`
- `transition_horizon_bars`
- `management_horizon_bars`

### 3-3. 현재 상태

이 입력 번들은 구조적으로는 꽤 잘 되어 있다.

좋은 점:

- upstream semantic 6층이 거의 다 연결됨
- `State v2`, `Belief vNext`, `Barrier vNext`까지 반영 가능
- 이후 offline dataset으로도 넘기기 좋음

아쉬운 점:

- branch별로 어떤 입력이 실제 math에 많이 쓰이는지 체감이 약함
- rich metadata가 있어도 branch 수학에는 아직 얇게 쓰이는 값들이 있음

---

## 4. 1갈래: `transition_forecast_v1`

### 4-1. 이 갈래가 답하는 질문

`지금 나온 반응이 앞으로 어떤 전개로 이어질까?`

즉:

- confirm으로 갈까
- reversal이 성공할까
- continuation이 붙을까
- false break일까

를 말하는 갈래다.

### 4-2. 대표 출력 성격

현재 엔진은 이런 성격의 값을 만든다.

- `p_buy_confirm`
- `p_sell_confirm`
- `p_reversal_success`
- `p_continuation`
- `p_false_break`

그리고 내부 metadata에는 이런 gap/보조 해석이 붙는다.

- `side_separation`
- `confirm_fake_gap`
- `reversal_continuation_gap`

### 4-3. 주로 쓰는 근거

이 갈래는 아래를 많이 본다.

- `Evidence`
  - `buy_total_evidence`
  - `sell_total_evidence`
  - `buy_reversal_evidence`
  - `sell_reversal_evidence`
  - `buy_continuation_evidence`
  - `sell_continuation_evidence`
- `Belief`
  - `buy_belief`
  - `sell_belief`
  - `buy_persistence`
  - `sell_persistence`
  - `transition_age`
- `Barrier`
  - `buy_barrier`
  - `sell_barrier`
- `Position / Response`
  - reversal fit
  - continuation fit
  - response 6축 우세 정도

### 4-4. 이미 잘 되는 부분

- `Response 6축`과 `Evidence/Belief`를 같이 쓰는 구조가 이미 있음
- `reversal fit`, `continuation fit`이 들어가서 position-aware함
- `false break`를 따로 떼어보는 구조가 있음

### 4-5. 있는데 덜 쓰는 부분

아래는 upstream엔 있는데 transition forecast 수학에 아직 약하게만 반영되거나 거의 안 쓰인다.

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`
- `topdown_spacing_state`
- `topdown_slope_state`
- `topdown_confluence_state`
- `execution_friction_state`
- `event_risk_state`
- `flip_readiness`
- `belief_instability`
- `edge_turn_relief_v1`
- `breakout_fade_barrier_v1`

즉 지금은 `TransitionForecast`가 semantic 구조를 알고는 있지만, 장면별 세밀한 state/barrier 조정은 아직 덜 먹고 있다.

### 4-6. 있으면 더 좋은 것

다음에 이 branch에 추가하면 좋은 것:

- `edge_turn_success`
  - 하단/상단 edge 전환 성공 확률
- `failed_breakdown_reclaim_success`
  - sell 실패 후 reclaim 성공 확률
- `failed_breakout_flush_success`
  - breakout 실패 후 flush 전개 확률
- `continuation_exhaustion_risk`
  - continuation처럼 보이지만 이미 확장 피로가 큰지
- `belief_flip_alignment`
  - 반대 thesis로 전환되는 중인지

---

## 5. 2갈래: `trade_management_forecast_v1`

### 5-1. 이 갈래가 답하는 질문

`지금 들어갔거나 들고 있다면 어떻게 관리하는 게 좋을까?`

즉:

- 계속 들고 갈까
- 지금 실패로 끝날까
- TP1까지 갈까
- 지금 끊고 나중에 다시 타는 게 낫나
- 눌렸다가 다시 회복할 수 있나

를 말하는 갈래다.

### 5-2. 대표 출력 성격

현재 엔진은 이런 성격의 값을 만든다.

- `p_continue_favor`
- `p_fail_now`
- `p_reach_tp1`
- `p_better_reentry_if_cut`
- `p_recover_after_pullback`

그리고 내부 metadata로:

- `continue_fail_gap`
- `recover_reentry_gap`

같은 값이 붙는다.

### 5-3. 주로 쓰는 근거

이 갈래는 아래를 특히 중요하게 볼 수밖에 없다.

- `Belief`
  - 같은 thesis가 유지되는가
- `Barrier`
  - 지금 execution 환경이 나빠지는가
- `State`
  - hold patience / fast exit risk / friction / event risk
- `Response`
  - continuation vs reversal이 실제로 어느 쪽인가

### 5-4. 이미 잘 되는 부분

- `continue / fail / recover / reentry`처럼 관리 질문이 분리돼 있음
- `exit_profile_router`, `wait_engine`, `energy_helper`와 연결할 기반이 있음
- `Belief`와 `State`가 이미 일부 연결됨

### 5-5. 있는데 덜 쓰는 부분

아래는 이 branch에서 앞으로 더 직접적으로 먹어야 하는 값들이다.

- `hold_patience_gain`
- `fast_exit_risk_penalty`
- `session_exhaustion_state`
- `execution_friction_state`
- `event_risk_state`
- `buy_streak`
- `sell_streak`
- `flip_readiness`
- `belief_instability`
- `post_event_cooldown_barrier_v1`
- `micro_trap_barrier_v1`

즉 지금 `TradeManagementForecast`는 뼈대는 있는데,
네가 계속 말한

- `좋은 진입 후 방관`
- `중간 흔들림에 덜 털리기`
- `청산 후 다시 더 좋은 재진입`

쪽은 더 강해질 여지가 많다.

### 5-6. 있으면 더 좋은 것

- `hold_through_noise_score`
  - 흔들림을 견딜 가치
- `premature_exit_risk`
  - 너무 빨리 자를 위험
- `edge_to_edge_completion_prob`
  - 레인지에서 반대 edge까지 갈 확률
- `flip_after_exit_quality`
  - 청산 후 반대 thesis 진입 품질
- `stop_then_recover_risk`
  - SL 걸렸다가 다시 가는 구간 위험

---

## 6. 3갈래: `forecast_gap_metrics_v1`

### 6-1. 이 갈래가 답하는 질문

`위 두 forecast가 얼마나 선명하게 갈라져 있나?`

즉 이건 독립적인 예측기라기보다,
두 forecast 결과를 비교해서 execution이 읽기 쉽게 만든 요약 branch다.

### 6-2. 현재 실제로 있는 값

예를 들면:

- `transition_side_separation`
- `transition_confirm_fake_gap`
- `transition_reversal_continuation_gap`
- `management_continue_fail_gap`
- `management_recover_reentry_gap`

### 6-3. 이미 잘 되는 부분

- `Transition`과 `Management`를 따로 만들고 끝내지 않고,
  gap으로 요약해 execution helper가 읽기 쉽게 만든 점이 좋다
- [energy_contract.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/energy_contract.py) 에서 실제로 이 gap을 같이 본다

### 6-4. 있는데 덜 쓰는 부분

현재는 값은 있는데, 이걸 직접 runtime 행동에 강하게 쓰는 정도가 아직 제한적이다.

특히 부족한 것:

- `WAIT vs CONFIRM` 차이를 gap으로 직접 강하게 쓰기
- `HOLD vs EXIT` 차이를 gap으로 더 직관적으로 쓰기
- `same side hold`와 `opposite side flip` 사이 gap을 execution에 직접 반영하기

### 6-5. 있으면 더 좋은 것

- `wait_confirm_gap`
- `hold_exit_gap`
- `same_side_flip_gap`
- `continuation_reversal_gap_cleaned`
- `belief_barrier_tension_gap`

즉 지금의 gap metrics는 좋지만, 이후 ML이나 execution assist를 생각하면 더 많이 자랄 수 있다.

---

## 7. `forecast_effective_policy_v1`는 무엇인가

### 7-1. 현재 역할

이건 `Forecast`의 네 번째 branch가 아니라, `effective wrapper`에 가깝다.

즉:

- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1`

를 layer mode/effective 경로로 넘기는 포장층이다.

### 7-2. 현재 상태

지금은 사실상 `bridge` 성격이 강하다.

즉:

- `policy_overlay_applied = False`
- `effective_equals_raw = True`

처럼 raw와 크게 다르지 않게 전달하는 경우가 많다.

### 7-3. 의미

이 말은 곧:

- `effective wrapper`는 존재함
- 하지만 아직 진짜 `policy/utility overlay`가 강하게 얹히는 단계는 아님

즉 이 부분은 앞으로 더 커질 수 있다.

### 7-4. 있으면 더 좋은 방향

- `Layer Mode`에 따라 forecast branch별 영향 강도 조절
- `Policy Overlay`가 `wait/confirm/hold/exit`에 미세 보정 적용
- `Utility Overlay`가 execution hint까지 연결

---

## 8. 현재 Forecast에서 이미 잘 쓰는 것

정리하면 아래는 이미 꽤 괜찮다.

### A. 구조

- 입력 번들과 3갈래 구조가 분리돼 있다
- wrapper까지 존재한다

### B. semantic input quality

- `Position / Response / State / Evidence / Belief / Barrier`를 받아쓴다

### C. branch separation

- `Transition`과 `Management`가 역할상 분리돼 있다
- `Gap metrics`로 다시 비교 요약한다

### D. downstream handoff

- `ContextClassifier`에서 runtime metadata로 저장된다
- `Energy helper`에서 읽을 수 있다
- `EntryService`에도 전달된다

---

## 9. 현재 Forecast에서 놀고 있는 것

이 문서 기준으로 `놀고 있는 것`은 크게 세 부류다.

### A. 이미 upstream에 있는데 branch 수학에서 덜 쓰는 것

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`
- `topdown_spacing_state`
- `topdown_slope_state`
- `topdown_confluence_state`
- `spread_stress_state`
- `volume_participation_state`
- `execution_friction_state`
- `event_risk_state`
- `flip_readiness`
- `belief_instability`
- `edge_turn_relief_v1`
- `breakout_fade_barrier_v1`
- `micro_trap_barrier_v1`
- `post_event_cooldown_barrier_v1`

### B. branch는 있는데 execution이 덜 활용하는 것

- `forecast_gap_metrics_v1`
- `forecast_effective_policy_v1`

### C. branch는 있는데 layer-mode assist가 약한 것

- `forecast_effective_policy_v1`가 아직 실질 assist보다 bridge에 가까움

---

## 10. 있으면 더 좋은 것

### Transition 쪽

- edge turn success
- failed breakdown reclaim
- failed breakout flush
- continuation exhaustion risk

### Management 쪽

- hold through noise
- premature exit risk
- edge to edge completion
- stop then recover risk
- flip after exit quality

### Gap 쪽

- wait confirm gap
- hold exit gap
- same side vs flip gap
- belief barrier tension gap

### Effective wrapper 쪽

- policy overlay applied
- utility overlay applied
- layer mode assist score
- consumer hint weighting

---

## 11. 현재 진짜 병목

Forecast가 없어서가 아니다.

병목은 이쪽이다.

1. `Forecast 3갈래`는 이미 있다
2. 그런데 이 rich forecast가 execution에 충분히 강하게 먹지 않는다
3. `effective wrapper`는 아직 bridge 성격이 강하다
4. gap metrics는 있는데 행동 층에서 적극 소비가 약하다

즉 한 줄로:

`Forecast의 문제는 부재가 아니라 활용 강도와 연결성이다.`

---

## 12. 실무용 한 줄 요약

### 가장 짧게

`Forecast는 이미 입력 번들 + transition + trade management + gap metrics + effective wrapper 구조로 존재한다. 지금 필요한 건 새 branch 발명이 아니라, 이미 있는 3갈래를 execution과 offline calibration에서 더 강하게 활용하는 일이다.`

### 조금 더 실무적으로

- `forecast_features_v1`
  - semantic 입력 번들
- `transition_forecast_v1`
  - 반응의 다음 방향 전개
- `trade_management_forecast_v1`
  - 보유/청산/재진입 관리
- `forecast_gap_metrics_v1`
  - 두 forecast의 차이 요약
- `forecast_effective_policy_v1`
  - 아직은 bridge 성격이 큰 effective wrapper

