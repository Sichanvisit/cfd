# CFD 시스템 전체 인계 문서

## 문서 목적
이 문서는 다른 스레드나 다른 에이전트가 지금 프로젝트 상태를 바로 이해하고 이어받을 수 있도록 만든 단일 인계 문서입니다.

이 문서에서 설명하는 것:

- 현재 전체 아키텍처가 어떻게 생겼는지
- 어떤 레이어가 이미 구현되었는지
- 각 레이어가 정확히 무슨 의미를 가지는지
- `Forecast`와 `Observe / Confirm / Action` 사이에 어떤 번역층이 필요한지
- `OutcomeLabeler`가 정확히 어떤 역할인지
- 지금 기준으로 다음 작업은 어디서부터 이어야 하는지

이 문서는 아이디어 메모가 아니라, **현재 코드베이스와 계약 문서 기준으로 정리한 실무용 상태 설명서**입니다.

---

## 한눈에 보는 전체 구조

```text
시장 데이터
-> Context 정규화
-> Position
-> Response Raw
-> Response Vector
-> State Vector
-> Evidence
-> Belief
-> Barrier
-> Forecast Features
-> Transition Forecast / Trade Management Forecast
-> Observe / Confirm / Action
-> Consumer

오프라인 병렬 경로:
Semantic + Forecast snapshot
-> OutcomeLabeler
-> Validation Report / Replay Dataset Builder
-> Rule vs Model 비교
```

현재 시스템은 크게 두 경로로 나뉩니다.

1. 실시간 의사결정 경로
- semantic layer
- forecast
- `Observe / Confirm / Action`
- consumer

2. 오프라인 검증/학습 준비 경로
- semantic layer
- forecast
- `OutcomeLabeler`
- validation / dataset / 향후 모델 학습

이 둘은 서로 연결되어 있지만, 같은 역할을 하는 것은 아닙니다.

---

## 현재 레이어별 의미

## Position
역할:
- 현재 가격이 어디에 있는지를 말합니다

주요 출력:
- `PositionSnapshot`
- `PositionInterpretation`
- `PositionEnergySnapshot`

의미:
- 방향 결론을 만들지 않음
- 진입/청산 결론을 만들지 않음
- 위치, 정렬, 충돌, 위치 에너지까지만 설명

구현 위치:
- `backend/trading/engine/position/*`
- `backend/trading/engine/core/models.py`

상태:
- 구현 완료
- semantic foundation으로 취급

## Response
역할:
- 그 위치에서 어떤 전이 반응이 나왔는지 말합니다

주요 출력:
- `ResponseRawSnapshot`
- `ResponseVectorV2`

canonical response 축:
- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

의미:
- 패턴 이름은 최종 의사결정 단위가 아님
- 패턴은 canonical response 축의 증폭기 역할만 함

구현 위치:
- `backend/trading/engine/response/*`

상태:
- 구현 완료
- semantic foundation으로 취급

## State
역할:
- 지금 이 반응을 얼마나 믿어야 하는지 말합니다

주요 출력:
- `StateRawSnapshot`
- `StateVectorV2`

canonical state 계수:
- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`

의미:
- 방향을 만들지 않음
- 반응 해석 강도를 조절하는 계수층

구현 위치:
- `backend/trading/engine/state/*`

상태:
- 구현 완료
- semantic foundation으로 취급

## Evidence
역할:
- 지금 당장 어느 쪽 증거가 더 강한지 immediate proof로 정리합니다

주요 출력:
- `EvidenceVector`

canonical 필드:
- `buy_reversal_evidence`
- `sell_reversal_evidence`
- `buy_continuation_evidence`
- `sell_continuation_evidence`
- `buy_total_evidence`
- `sell_total_evidence`

의미:
- 미래 예측이 아님
- 현재 시점의 즉시 증거를 정리하는 층

구현 위치:
- `backend/trading/engine/core/evidence_engine.py`

상태:
- 구현 완료
- semantic foundation으로 취급

## Belief
역할:
- evidence가 시간 축에서 얼마나 유지되고 있는지 누적합니다

주요 출력:
- `BeliefState`

canonical 필드:
- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`

의미:
- 1봉짜리 스파이크와 여러 봉 누적을 분리함
- `Position/Response/State`를 다시 읽지 않고 `Evidence`만 누적함

구현 위치:
- `backend/trading/engine/core/belief_engine.py`

상태:
- 구현 완료
- semantic foundation으로 취급

## Barrier
역할:
- 증거가 있어도 왜 지금 action이 막혀야 하는지 구조 장벽으로 설명합니다

주요 출력:
- `BarrierState`

canonical 필드:
- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

의미:
- conflict / chop / policy / liquidity 마찰을 설명
- 방향을 만들지 않음
- semantic layer를 다시 raw처럼 해석하지 않음

구현 위치:
- `backend/trading/engine/core/barrier_engine.py`

상태:
- 구현 완료
- semantic foundation으로 취급

---

## Semantic Foundation Freeze

다음 6개 레이어는 이제 semantic foundation으로 고정합니다.

- Position
- Response
- State
- Evidence
- Belief
- Barrier

이 말의 의미:
- 나중에 ML/DL이 들어와도 이 레이어는 유지합니다
- 앞으로는 이 레이어를 feature layer로 봅니다
- 큰 구조 변경이 아니라 버그 수정과 acceptance 보정만 허용합니다
- 매번 새로운 아이디어가 나올 때마다 foundation을 다시 뜯지 않습니다

이게 중요한 이유:
- 앞으로 `ForecastRuleV1`, `ForecastModelV1`, 이후 sequence model까지 모두 같은 semantic foundation 위에 올라가야 하기 때문입니다

---

## Forecast 레이어

## ForecastFeaturesV1
역할:
- semantic layer를 forecast engine이 읽기 쉬운 하나의 입력 패키지로 묶습니다

주요 필드:
- `position_primary_label`
- `position_bias_label`
- `position_secondary_context_label`
- `position_conflict_score`
- `middle_neutrality`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`

구현 위치:
- `backend/trading/engine/core/forecast_features.py`

## TransitionForecastV1
역할:
- 진입 전/직후에 현재 상태가 어떤 전이로 흘러갈지 예측합니다

주요 필드:
- `p_buy_confirm`
- `p_sell_confirm`
- `p_false_break`
- `p_reversal_success`
- `p_continuation_success`

의미:
- calibrated probability가 아니라 scenario score
- 지금 어떤 전이 시나리오가 더 유력한지 상대적으로 보는 점수

구현 위치:
- `backend/trading/engine/core/forecast_engine.py`

## TradeManagementForecastV1
역할:
- 진입 후 hold / cut / recover / re-entry 관련 시나리오를 예측합니다

주요 필드:
- `p_continue_favor`
- `p_fail_now`
- `p_recover_after_pullback`
- `p_reach_tp1`
- `p_opposite_edge_reach`
- `p_better_reentry_if_cut`

의미:
- 이것도 calibrated probability가 아니라 scenario score
- 포지션 관리 시 어떤 전개가 더 유력한지 보는 점수

구현 위치:
- `backend/trading/engine/core/forecast_engine.py`

## Forecast 인터페이스
설계 의도:
- forecast는 교체 가능한 인터페이스여야 함
- 현재는 rule-based baseline
- 나중에는 ML/DL 구현으로 교체 가능

현재 구현:
- `ForecastRuleV1`

향후:
- `ForecastModelV1`
- `ForecastSequenceModelV1`

---

## Forecast Calibration 상태

처음 forecast를 붙였을 때 주요 문제는 separation이 약하다는 점이었습니다.

대표 문제:
- `confirm`과 `false_break`가 너무 붙어 있었음
- `continue_favor`와 `fail_now`가 너무 붙어 있었음
- `WAIT/OBSERVE` 자리에서도 confirm score가 너무 높게 뜨는 경우가 있었음

그래서 calibration을 넣었습니다.

이미 들어간 calibration 성격:
- separation metric 추가
- competition-aware scoring
- 곱셈 과압축 완화
- transition calibration
- management calibration
- gap logging

지금 확인 가능한 주요 metric:
- `side_separation`
- `confirm_fake_gap`
- `reversal_continuation_gap`
- `continue_fail_gap`
- `recover_reentry_gap`

현재 상태를 한 줄로 정리하면:
- forecast 방향성은 대체로 맞음
- transition 쪽은 꽤 usable한 수준
- management 쪽은 `OutcomeLabeler` 기반 검증이 더 필요함

---

## Forecast와 Observe / Confirm / Action 사이 빈 구간

다른 스레드가 가장 많이 헷갈릴 수 있는 부분입니다.

`Forecast`가 바로 `Observe / Confirm / Action`은 아닙니다.

그 사이에는 반드시 번역층이 필요합니다.

구조:

```text
Forecast
-> Decision Translation
-> Observe / Confirm / Action Contract
-> Consumer
```

이 중간 레이어가 해야 하는 일:

1. dominant side 선택
- `BUY`
- `SELL`
- `BALANCED`

2. dominant path 선택
- `REVERSAL`
- `CONTINUATION`
- `UNRESOLVED`

3. confirm vs fake 비교
- confirm 점수 자체만 높다고 충분하지 않음
- fake pressure보다 충분히 높아야 함

4. continue vs fail 비교
- hold 쪽이 우세한지
- fail/cut 쪽이 우세한지 정리해야 함

5. lifecycle 결정
- `WAIT`
- `OBSERVE`
- `CONFIRM`
- `ACTION`

즉:
- `Forecast`는 예측층
- `Observe / Confirm / Action`은 정책/lifecycle 층

같은 층이 아닙니다.

---

## Observe / Confirm / Action

이건 실시간 의사결정 레이어입니다.

역할:
- semantic + forecast 상태를 읽어 lifecycle state를 결정

나중에 읽어야 하는 것:
- semantic foundation
- transition forecast
- trade management forecast

출력해야 하는 것:
- lifecycle state
- side
- confidence
- archetype
- invalidation id
- management profile id

하면 안 되는 것:
- raw position 좌표 직접 재해석
- raw response detector 직접 재해석
- forecast semantics 재창조

관련 문서:
- `docs/observe_confirm_input_contract.md`
- `docs/observe_confirm_output_contract.md`
- `docs/observe_confirm_routing_policy.md`
- `docs/observe_confirm_confidence_semantics.md`
- `docs/observe_confirm_archetype_taxonomy.md`
- `docs/observe_confirm_invalidation_taxonomy.md`
- `docs/observe_confirm_management_profile_taxonomy.md`

현재 프로젝트 현실:
- 관련 계약과 문서는 많이 준비됨
- forecast를 실제 lifecycle에 본격 소비하는 연결이 다음 큰 단계

---

## Consumer

Consumer는 semantic layer도 아니고 forecast layer도 아닙니다.

역할:
- 이미 정해진 결정을 실행하는 층

주요 구성:
- `SetupDetector`
- `EntryService`
- exit / re-entry 실행 경로

올바른 책임:
- `SetupDetector`: confirm 결과에 이름만 붙임
- `EntryService`: guard 적용 후 실행
- exit/re-entry: management profile과 forecast를 소비

잘못된 책임:
- band/box 의미를 다시 해석
- 두 번째 방향 엔진 만들기
- lifecycle 의미를 raw에서 다시 만들기

현재 프로젝트 방향:
- consumer는 실행 전용으로 계속 줄여나가는 중
- 이 방향을 유지하는 게 맞음

---

## OutcomeLabeler가 왜 필요한가

`OutcomeLabeler`는 live action path에 속하지 않습니다.

이건 offline validation / ML 준비 경로에 속합니다.

역할:
- 과거의 semantic snapshot + forecast snapshot을 가져오고
- 그 뒤 미래 결과를 보고
- “당시 예측이 맞았는지”를 라벨로 확정합니다

이게 없으면:
- management forecast가 맞는지 진짜 검증 못 함
- rule forecast를 baseline이라고 부르기 어려움
- 나중에 ML/DL 학습 라벨이 엉망이 됨

한 줄:
- forecast는 예측
- outcome labeler는 채점

---

## OutcomeLabeler 7~9가 실제로 의미하는 것

이 부분이 가장 헷갈릴 수 있어서 아주 명확히 씁니다.

## L7. Ambiguity / Censoring 규칙
뜻:
- 미래 결과가 불충분하거나 애매하면 억지 라벨을 만들지 말자

대표 상태:
- `INSUFFICIENT_FUTURE_BARS`
- `NO_EXIT_CONTEXT`
- `NO_POSITION_CONTEXT`
- `AMBIGUOUS`
- `CENSORED`

왜 중요하냐:
- 라벨러가 무조건 0/1만 찍으면 데이터가 오염됨
- 데이터 누락이나 애매한 케이스를 실패로 잘못 학습하게 됨

즉 `L7`은:
- 라벨을 많이 만드는 단계가 아니라
- 나쁜 라벨을 줄이는 품질 보호 단계

## L8. Outcome Signal Source 정의
뜻:
- 미래 결과를 무엇으로 판단할지 source와 matching rule을 고정하는 단계

대표 소스:
- `entry_decisions.csv`
- `trade_closed_history.csv`
- 필요시 exit / lifecycle 로그

대표 연결키:
- `symbol`
- row timestamp
- `signal_bar_ts`
- `ticket` 또는 position id
- side/action/setup context

왜 중요하냐:
- source와 key가 흔들리면 forecast row와 실제 outcome이 엉뚱하게 매칭됨

즉 `L8`은:
- 라벨 의미 정의가 아니라
- outcome source와 매칭 기준 정의

## L9. Labeler Engine 구현
뜻:
- 위에서 정한 규칙들을 실제 코드로 구현하는 offline labeler 엔진

주요 역할:
- anchor 해석
- future horizon 자르기
- positive/negative/unknown/censored 판정
- metadata와 reason 생성

중요:
- offline only
- live decision 엔진이 아님

즉 `L7~L9`를 짧게 다시 말하면:
- `L7` = 라벨 품질 보호
- `L8` = outcome source / matching 계약
- `L9` = 실제 labeler 엔진

---

## OutcomeLabeler 현재 상태

OutcomeLabeler는 더 이상 아이디어 단계가 아닙니다.

코드베이스 기준으로 실제 구현물이 있습니다.

주요 구현 파일:
- `backend/trading/engine/offline/outcome_labeler.py`
- `backend/services/outcome_labeler_contract.py`
- `backend/trading/engine/offline/outcome_label_validation_report.py`
- `backend/trading/engine/offline/replay_dataset_builder.py`

관련 문서:
- `docs/outcome_labeler_labeling_philosophy.md`
- `docs/outcome_labeler_anchor_definition.md`
- `docs/outcome_labeler_horizon_definition.md`
- `docs/outcome_labeler_transition_label_rules.md`
- `docs/outcome_labeler_management_label_rules.md`
- `docs/outcome_labeler_ambiguity_censoring_rules.md`
- `docs/outcome_labeler_outcome_signal_source.md`
- `docs/outcome_labeler_label_metadata.md`
- `docs/outcome_labeler_shadow_output.md`
- `docs/outcome_labeler_dataset_builder_bridge.md`
- `docs/outcome_labeler_validation_report.md`

즉 이건:
- 개념만 적힌 상태가 아니라
- 구현 + 문서 + 리포트 경로까지 상당 부분 들어간 상태

---

## 무엇이 구현됐고 무엇이 아직 더 필요하나

## 이미 구현되어 비교적 안정된 것
- semantic foundation
- forecast feature packaging
- transition forecast
- trade management forecast
- forecast calibration logging
- outcome labeler contract와 구현
- validation report 경로
- replay dataset builder 경로

## 아직 acceptance나 후속 연결이 더 필요한 것
- `Forecast -> Observe / Confirm / Action` 정책 번역층
- management forecast의 실제 outcome 기반 검증
- rule baseline vs 이후 model 비교 준비
- consumer 최종 연결과 semantic 재해석 완전 제거

---

## 다른 스레드가 읽을 때 추천 순서

다른 스레드가 이어받아야 하면 이 순서가 가장 빠릅니다.

1. 이 문서
2. `docs/observe_confirm_output_contract.md`
3. `docs/observe_confirm_routing_policy.md`
4. `docs/outcome_labeler_labeling_philosophy.md`
5. `docs/outcome_labeler_anchor_definition.md`
6. `docs/outcome_labeler_ambiguity_censoring_rules.md`
7. `backend/trading/engine/core/forecast_engine.py`
8. `backend/trading/engine/offline/outcome_labeler.py`

만약 다음 작업이 live decision 안정화라면:
- `Forecast -> OCA -> Consumer` 쪽을 우선

만약 다음 작업이 ML/DL 준비라면:
- `OutcomeLabeler -> Validation Report -> Replay Dataset Builder` 쪽을 우선

---

## 실무적으로 다음에 무엇을 하면 되나

## 목표가 실시간 의사결정 품질 개선이라면
다음 작업:
- forecast-to-OCA translation layer 구축
- lifecycle gating 확정
- consumer를 실행 전용으로 고정

## 목표가 ML/DL 준비라면
다음 작업:
- outcome label 품질 보강
- validation report 범위 확대
- shadow compare baseline 구축
- dataset builder 결과를 학습셋으로 연결

## 목표가 다른 스레드에서 바로 이어받는 것이라면
이 문서를 시작점으로 보고:
- semantic foundation은 freeze
- forecast는 calibrated baseline
- outcome labeler는 offline grader
로 이해하면 됩니다.

---

## 최종 요약

현재 시스템은 더 이상 단순히:

```text
Position -> Response -> State -> decision
```

이 아닙니다.

지금 구조는:

```text
Semantic Foundation
(Position / Response / State / Evidence / Belief / Barrier)
-> Forecast
-> Observe / Confirm / Action
-> Consumer

오프라인 병렬 경로:
Semantic + Forecast
-> OutcomeLabeler
-> Validation / Dataset / Model readiness
```

핵심 구분:
- `Forecast`는 예측
- `Observe / Confirm / Action`은 결정
- `Consumer`는 실행
- `OutcomeLabeler`는 채점

이 구분을 앞으로도 유지하는 게 중요합니다.
