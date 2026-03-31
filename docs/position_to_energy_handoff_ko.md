# Position부터 Energy까지 정리 상태와 세부조정 가이드

## 문서 목적

이 문서는 `Position`부터 `Energy`까지 현재 CFD 의사결정 구조가 어떻게 정리되었는지, 어디까지가 이미 끝난 계약인지, 이후 세부조정은 어느 레이어에서 어떻게 해야 하는지를 한글로 정리한 handoff 문서다.

이 문서가 답하려는 질문은 아래와 같다.

- 지금 구조에서 각 레이어는 정확히 무엇을 담당하는가
- 어디까지가 semantic owner이고 어디부터는 execution/policy/helper 인가
- 무엇이 이미 freeze 되었고 무엇만 조정 가능한가
- 실제로 `wait`, `confirm`, `entry priority`, `soft block` 같은 문제는 어느 레이어에서 조정해야 하는가
- 앞으로 남은 실무 후속은 무엇인가

---

## 한눈에 보는 현재 구조

```text
Market Data
-> Position
-> Response
-> State
-> Evidence
-> Belief
-> Barrier
-> Forecast Features
-> Transition Forecast / Trade Management Forecast
-> Observe / Confirm / Action
-> Consumer

Policy / Utility Overlay
raw semantic outputs
-> Layer Mode
-> effective semantic outputs
-> Energy Helper
-> consumer hint usage

Offline path
semantic + forecast snapshots
-> OutcomeLabeler
-> validation / replay / dataset / calibration
```

핵심 요약은 이렇다.

- `Position ~ Barrier`는 semantic foundation이다.
- `Forecast`는 semantic foundation 위에 올라가는 예측층이다.
- `ObserveConfirm`는 live identity owner다.
- `Consumer`는 실행 경계다.
- `Layer Mode`는 raw를 끄는 계층이 아니라 raw 위에 얹는 policy overlay다.
- `Energy`는 더 이상 의미층이 아니고, post-layer-mode utility/helper다.

중요한 주의점도 하나 있다.

- `PositionEnergySnapshot`은 `Position` 내부의 위치 에너지 표현이지, `13단계 Energy`와 같은 개념이 아니다.
- 현재 `Energy`의 canonical runtime surface는 `energy_helper_v2`다.

---

## 1. Position부터 Forecast까지 무엇이 정리되었는가

## 1.1 Position

- 역할: 가격이 지금 어디에 있는지를 말한다.
- 대표 출력: `PositionSnapshot`, `PositionInterpretation`, `PositionEnergySnapshot`
- 하지 않는 일: 방향 결정, 진입 결정, 청산 결정
- 현재 상태: semantic foundation으로 고정

`Position`은 좌표, 정렬, 충돌, 위치 에너지를 설명하는 층이다. 여기서 `BUY/SELL`을 직접 소유하면 안 된다.

## 1.2 Response

- 역할: 그 위치에서 어떤 반응 전이가 나오고 있는지를 말한다.
- 대표 출력: `ResponseRawSnapshot`, `ResponseVectorV2`
- canonical axis 예시: `lower_hold_up`, `lower_break_down`, `mid_reclaim_up`, `upper_reject_down`
- 현재 상태: semantic foundation으로 고정

`Response`는 패턴 이름을 만드는 층이 아니라 canonical response axis로 정리된 반응 설명층이다.

## 1.3 State

- 역할: 현재 반응을 얼마나 믿어야 하는지에 대한 해석 강도를 조절한다.
- 대표 출력: `StateRawSnapshot`, `StateVectorV2`
- 대표 coefficient: `range_reversal_gain`, `noise_damp`, `alignment_gain`, `countertrend_penalty`
- 현재 상태: semantic foundation으로 고정

`State`는 방향을 만들지 않는다. 방향 해석의 gain/damp를 조절할 뿐이다.

## 1.4 Evidence

- 역할: 지금 당장의 setup strength를 action-friendly한 immediate proof로 압축한다.
- 대표 출력: `EvidenceVector`
- 대표 필드: `buy_total_evidence`, `sell_total_evidence`, `buy_reversal_evidence`, `buy_continuation_evidence`
- 현재 상태: semantic foundation으로 고정

`Evidence`는 미래 예측이 아니라 현재 증거의 합성이다.

## 1.5 Belief

- 역할: evidence가 시간축에서 얼마나 유지되고 누적되는지를 설명한다.
- 대표 출력: `BeliefState`
- 대표 필드: `buy_belief`, `sell_belief`, `buy_persistence`, `sell_persistence`
- 현재 상태: semantic foundation으로 고정

`Belief`는 한 봉짜리 spike와 여러 봉에 걸친 persistence를 분리하는 층이다.

## 1.6 Barrier

- 역할: 증거가 있더라도 왜 지금 action을 미루거나 눌러야 하는지를 설명한다.
- 대표 출력: `BarrierState`
- 대표 필드: `buy_barrier`, `sell_barrier`, `conflict_barrier`, `middle_chop_barrier`, `direction_policy_barrier`, `liquidity_barrier`
- 현재 상태: semantic foundation으로 고정

`Barrier`는 direction creator가 아니라 suppression/risk pressure 설명층이다.

## 1.7 Semantic Foundation Freeze의 의미

현재 semantic foundation으로 고정된 층은 아래 여섯 개다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

이 말의 실제 의미는 아래와 같다.

- 이후 ML/DL이 붙어도 이 층들은 feature foundation으로 남는다.
- 새 아이디어가 나올 때마다 이 층을 다시 갈아엎는 구조가 아니다.
- 이 층에서는 주로 bug fix, acceptance correction, contract clarification만 허용된다.
- 최종 live action은 이 층이 직접 소유하지 않는다.

## 1.8 Forecast

- 역할: semantic foundation을 받아 근미래 전이와 entry 이후 management 시나리오를 예측한다.
- 대표 출력: `ForecastFeaturesV1`, `TransitionForecastV1`, `TradeManagementForecastV1`
- 대표 필드:
- `p_buy_confirm`, `p_sell_confirm`, `p_false_break`, `p_reversal_success`
- `p_continue_favor`, `p_fail_now`, `p_recover_after_pullback`, `p_reach_tp1`, `p_better_reentry_if_cut`
- 현재 상태: semantic foundation 위의 예측층으로 정리 완료

현재 `Forecast`는 calibrated probability라기보다 scenario score에 가깝다. 따라서 forecast tuning의 핵심은 separation과 calibration이지, semantic identity를 만드는 것이 아니다.

---

## 2. 10A~13에서 무엇이 마무리되었는가

## 2.1 Observe / Confirm / Action

`ObserveConfirm`은 현재 live identity owner다.

- canonical output: `observe_confirm_v2`
- canonical identity fields:
- `archetype_id`
- `side`
- `invalidation_id`
- `management_profile_id`
- 역할: semantic + forecast 상태를 받아 `observe`, `confirm`, `wait/no-trade` 같은 lifecycle과 identity를 결정

여기서 중요한 점은 다음이다.

- identity는 여기서 결정된다.
- consumer는 이 identity를 읽어서 실행할 뿐, 다시 만들지 않는다.
- energy는 이 identity를 바꾸지 못한다.

## 2.2 Consumer

`Consumer`는 semantic layer도 아니고 forecast layer도 아니다. 실행 경계다.

- `SetupDetector`: naming/mapping
- `EntryService`: execution guard
- `WaitEngine`: enter vs wait 비교
- `Exit` / `ReEntry`: management handoff

현재 consumer boundary는 아래처럼 정리되었다.

- observe-confirm의 canonical handoff를 읽는다.
- semantic vector를 다시 해석하지 않는다.
- raw detector를 직접 읽지 않는다.
- energy는 helper-only usage boundary로만 읽는다.

## 2.3 Layer Mode

`Layer Mode`는 semantic을 켜고 끄는 층이 아니다. raw semantic outputs는 항상 계산된다.

현재 정리된 의미는 이렇다.

- raw는 항상 남는다.
- effective는 raw 옆에 policy overlay 결과로 같이 남는다.
- mode는 semantic 존재 자체가 아니라 influence strength를 바꾼다.
- identity를 덮어쓰지 않는다.

즉 `Layer Mode`는 semantic layer 아래가 아니라, semantic output 위의 policy 조절층이다.

## 2.4 Energy Re-definition

`Energy`는 이제 독립 의미층이 아니다.

현재 canonical 정의는 아래와 같다.

- runtime field: `energy_helper_v2`
- 입력: `evidence_vector_effective_v1`, `belief_state_effective_v1`, `barrier_state_effective_v1`, `forecast_effective_policy_v1`, 그리고 필요 시 `observe_confirm_v2.action/side`
- 역할: effective semantics를 action-friendly 숫자와 hint로 압축
- 비역할: semantic truth 생성, identity 생성, archetype/side/invalidation/management ownership

canonical output shape는 아래 10개로 고정되었다.

- `selected_side`
- `action_readiness`
- `continuation_support`
- `reversal_support`
- `suppression_pressure`
- `forecast_support`
- `net_utility`
- `confidence_adjustment_hint`
- `soft_block_hint`
- `metadata`

그리고 중요한 freeze가 같이 끝났다.

- `Energy`는 `Layer Mode` 이후 helper다.
- `Energy`는 `net_utility`로 직접 주문 판단을 하면 안 된다.
- `Energy`는 `confidence_adjustment_hint`, `soft_block_hint`, `priority_hint`, `wait_vs_enter_hint` 같은 중간 힌트를 제공한다.
- migration 동안 `energy_snapshot`과 dual-write 하되 canonical은 `energy_helper_v2`다.
- replay/log에서 왜 이 점수가 나왔는지 추적 가능해야 한다.

---

## 3. 지금 구조를 owner 기준으로 다시 보면

| 구간 | 지금 owner가 답하는 질문 | canonical output | 하면 안 되는 일 |
|---|---|---|---|
| Position | 가격이 어디 있나 | `PositionSnapshot` 계열 | 방향 결정 |
| Response | 그 위치에서 무슨 반응이 나오나 | `ResponseVectorV2` | 최종 진입 판단 |
| State | 이 반응을 얼마나 믿나 | `StateVectorV2` | 방향 생성 |
| Evidence | 지금 증거가 얼마나 강한가 | `EvidenceVector` | 미래 예측 |
| Belief | 그 증거가 얼마나 유지되는가 | `BeliefState` | raw semantic 재해석 |
| Barrier | 왜 미뤄야 하거나 눌려야 하는가 | `BarrierState` | 방향 생성 |
| Forecast | 앞으로 어떤 전이/관리 시나리오가 유력한가 | `TransitionForecastV1`, `TradeManagementForecastV1` | identity ownership |
| ObserveConfirm | 지금 어떤 lifecycle/identity로 읽어야 하나 | `observe_confirm_v2` | raw detector 재해석 |
| Consumer | 그 identity를 실제 실행 경계로 어떻게 쓰나 | consumer handoff payload | semantic 재구성 |
| Layer Mode | raw 위에 어떤 policy influence를 적용할까 | raw/effective dual-write | semantic 끄기 |
| Energy | effective semantics를 실행 친화 숫자와 hint로 얼마나 압축할까 | `energy_helper_v2` | 의미층 소유, identity 소유 |

이 표를 한 줄로 요약하면 아래와 같다.

- semantic truth는 `Position ~ Barrier`
- predictive view는 `Forecast`
- live identity는 `ObserveConfirm`
- execution boundary는 `Consumer`
- policy overlay는 `Layer Mode`
- utility/helper 압축은 `Energy`

---

## 4. 현재 완료 상태의 의미

여기까지 오면서 구조는 아래 순서로 완결되었다.

1. `Position ~ Barrier`를 semantic foundation으로 고정
2. `Forecast`를 semantic foundation 위의 예측층으로 분리
3. `ObserveConfirm`를 identity/lifecycle owner로 고정
4. `Consumer`를 실행 경계로 고정
5. `Layer Mode`를 raw 위의 policy overlay로 고정
6. `Energy`를 post-layer-mode utility helper로 재정의

즉 지금 구조는 아래 문장으로 정리된다.

- identity는 `ObserveConfirm`
- execution policy overlay는 `Layer Mode`
- utility-friendly compression은 `Energy`

이제 `Energy`가 끝났다는 말은 roadmap 본체가 한 번 닫혔다는 뜻이다. 다만 실무는 아직 몇 가지 후속이 남아 있다.

- migration cleanup
- legacy field 제거
- live gate 승격
- replay calibration 재점검
- 운영 문서와 기준 정리

---

## 5. 세부조정은 어디서 해야 하는가

실무에서 가장 중요한 건 "문제가 보이는 위치"가 아니라 "그 문제의 owner"를 찾는 것이다.

| 증상 | 먼저 봐야 하는 레이어 | 여기서 조정할 것 | 여기서 조정하면 안 되는 것 |
|---|---|---|---|
| 위치 해석 자체가 이상함 | `Position`, `Response`, `State` | 좌표 기준, detector mapping, gain/damp | consumer guard, energy hint |
| setup strength가 너무 약하거나 강함 | `Evidence` | 합성 방식, support/reversal/continuation 비중 | archetype 결정 |
| 눌림/충돌 때문에 너무 자주 wait 됨 | `Barrier`, `Layer Mode`, `Energy` | barrier weight, effective influence, soft block hint | semantic side 재정의 |
| persistence가 너무 빨리 죽거나 오래 감 | `Belief` | decay, persistence window, accumulation logic | entry guard 직접 수정으로 덮기 |
| confirm/fake separation이 약함 | `Forecast` | calibration, gap, competition scoring | consumer에서 side 임의 수정 |
| archetype 또는 invalidation이 잘못 붙음 | `ObserveConfirm` | routing rule, taxonomy mapping, confidence semantics | Energy에서 side/identity 변경 |
| 같은 identity인데 entry priority가 이상함 | `Energy` | readiness, priority hint, wait-vs-enter hint | archetype 변경 |
| live entry gate가 너무 보수적/공격적임 | `Consumer`, `Layer Mode` | entry guard, policy overlay, wait engine use | semantic foundation 재정의 |
| replay에서 왜 wait인지 설명이 안 됨 | `Energy` logging, consumer logging | trace/log/replay contract 보강 | 의미층에 설명 라벨 덕지덕지 추가 |

간단히 말하면 아래처럼 보면 된다.

- "무슨 상황인가"가 틀리면 semantic foundation 또는 `ObserveConfirm`
- "앞으로 뭐가 더 유력한가"가 약하면 `Forecast`
- "정책상 얼마나 약하게/강하게 반영할까"는 `Layer Mode`
- "실행 친화 숫자로 얼마나 밀어주거나 누를까"는 `Energy`
- "실제로 enter/wait/block를 어떻게 처리할까"는 `Consumer`

---

## 6. 레이어별 세부조정 원칙

## 6.1 Position / Response / State

허용되는 조정:

- detector acceptance correction
- 좌표 기준 보정
- canonical axis mapping 보정
- gain/damp 계수 보정
- bug fix

피해야 하는 조정:

- `BUY/SELL` identity를 여기서 직접 만들기
- consumer 문제를 semantic layer로 덮어쓰기
- 새 아이디어가 나올 때마다 foundation 구조를 갈아엎기

## 6.2 Evidence / Belief / Barrier

허용되는 조정:

- evidence aggregation 비율
- persistence 누적/감쇠 방식
- barrier suppression 계수
- conflict/chop/liquidity/policy friction의 normalization

피해야 하는 조정:

- future prediction을 이 층에 밀어넣기
- belief가 raw semantic을 다시 읽도록 만들기
- barrier가 direction creator가 되게 만들기

## 6.3 Forecast

허용되는 조정:

- transition/management separation 개선
- calibration gap 조정
- competition-aware scoring 보정
- future model replacement 준비

피해야 하는 조정:

- forecast를 곧바로 lifecycle/identity로 취급하기
- low-quality forecast를 consumer rule로 덮어서 숨기기
- energy가 forecast identity를 다시 만들게 두기

## 6.4 Observe / Confirm / Action

허용되는 조정:

- dominant side/path routing
- confirm vs fake 비교 규칙
- continue vs fail 비교 규칙
- archetype / invalidation / management profile taxonomy 보정
- confidence semantics 보정

피해야 하는 조정:

- raw detector 직접 읽기
- consumer에서 observe-confirm를 우회해서 identity를 다시 만들기
- energy에서 identity ownership을 가져가게 만들기

## 6.5 Consumer

허용되는 조정:

- setup naming/mapping
- entry guard 기준
- wait engine 비교 규칙
- exit / re-entry handoff 방식

피해야 하는 조정:

- semantic vector 재해석
- raw detector 직독
- `net_utility` 직접 주문 게이트화

## 6.6 Layer Mode

허용되는 조정:

- raw와 effective 사이 influence strength
- mode별 layer influence policy
- shadow -> assist -> enforce 운영 방식
- logging / replay overlay trace 강화

피해야 하는 조정:

- raw semantic computation 비활성화
- identity field rewrite
- consumer execution path 안으로 semantic reinterpretation 재도입

## 6.7 Energy

허용되는 조정:

- support/suppression 합성 weight
- `action_readiness` 계산 비중
- `confidence_adjustment_hint` 기준
- `soft_block_hint` 기준
- `priority_hint`, `wait_vs_enter_hint` 기준
- logging / replay trace의 설명력 강화

피해야 하는 조정:

- semantic truth 생성
- `archetype_id`, `side`, `invalidation_id`, `management_profile_id` 생성 또는 수정
- raw semantic output 직접 읽기
- `net_utility`를 바로 주문 실행 또는 차단 기준으로 승격

---

## 7. 세부조정 추천 순서

운영에서는 아래 순서가 가장 안전하다.

1. 증상을 replay row 기준으로 재현한다.
2. 문제가 semantic인지, predictive인지, identity인지, policy인지, utility인지 먼저 분류한다.
3. 가장 아래 owner 레이어부터 조정한다.
4. raw와 effective를 같이 본다.
5. `ObserveConfirm` identity는 유지한 채 `Layer Mode`와 `Energy` 조정으로 해결 가능한지 먼저 확인한다.
6. replay/log에서 설명 가능성이 유지되는지 확인한다.
7. 테스트가 깨지지 않는지 확인한 뒤에만 live gate 승격 여부를 검토한다.

추천 진단 질문은 아래와 같다.

- 지금 문제는 "상황 해석" 문제인가
- "미래 시나리오 분리" 문제인가
- "identity routing" 문제인가
- "policy overlay 강도" 문제인가
- "utility hint 압축" 문제인가
- "consumer guard" 문제인가

질문에 대한 답이 정리되면 레이어 선택이 쉬워진다.

---

## 8. 운영상 가장 자주 생기는 오해

## 8.1 `Forecast`가 곧바로 `ObserveConfirm`은 아니다

`Forecast`는 예측이고 `ObserveConfirm`은 lifecycle/identity다. 둘은 관련 있지만 같은 층이 아니다.

## 8.2 `Energy`가 side를 고르면 identity owner라고 착각하기 쉽다

`selected_side`는 utility-facing compression일 뿐이다. semantic `side` ownership은 아니다.

## 8.3 `Layer Mode`가 raw를 끈다고 착각하기 쉽다

지금 구조에서 raw는 항상 계산된다. `Layer Mode`는 influence strength와 effective world를 만든다.

## 8.4 consumer에서 semantic을 다시 보면 빨라 보이지만 구조가 무너진다

실행 경계가 semantic layer를 재해석하기 시작하면 replay, migration, ownership 분리가 다시 깨진다.

---

## 9. 지금 시점에서 남은 실무 후속

roadmap 본체는 `13.12 Freeze / Handoff`까지로 한 번 닫혔다. 하지만 실무 후속은 아래가 남아 있다.

- migration cleanup
- legacy runtime field 제거
- live gate 승격 여부 검토
- replay calibration 재점검
- 운영 기준과 알람 기준 정리
- Energy의 일부를 장기적으로 `utility/decision helper` 쪽에 흡수

이 후속은 "구조 재정의"라기보다 "정리된 구조 위에서 승격과 청소를 하는 작업"에 가깝다.

---

## 10. 핵심 참조 문서

- `docs/system_handoff_overview.md`
- `docs/observe_confirm_scope_contract.md`
- `docs/observe_confirm_freeze_handoff.md`
- `docs/consumer_scope_contract.md`
- `docs/consumer_freeze_handoff.md`
- `docs/layer_mode_scope_contract.md`
- `docs/layer_mode_freeze_handoff.md`
- `docs/energy_scope_contract.md`

이 문서를 빠르게 읽고 싶다면 아래 순서를 추천한다.

1. 이 문서
2. `observe_confirm_scope_contract.md`
3. `consumer_scope_contract.md`
4. `layer_mode_scope_contract.md`
5. `energy_scope_contract.md`

---

## 최종 한 줄 요약

현재 CFD 구조는 `Position ~ Barrier`를 semantic foundation으로 고정하고, `Forecast`를 그 위의 예측층으로 분리한 뒤, `ObserveConfirm`가 identity를 소유하고, `Consumer`가 실행을 담당하며, `Layer Mode`가 policy overlay를 적용하고, `Energy`가 effective semantics를 utility-friendly hint로 압축하는 구조로 정리 완료되었다.
---

## 11. 14.0 Scope Freeze

`13.12 Freeze / Handoff`까지로 구조 정리는 끝났지만, runtime이 문서 설명과 완전히 일치한다고 바로 볼 수는 없습니다. 그래서 다음 단계의 시작점은 새 의미층 추가가 아니라 `문서-코드 정합화`를 위한 `14.0 Scope Freeze`입니다.

이 단계에서 먼저 고정한 원칙은 아래와 같습니다.

- 범위는 `docs/position_to_energy_handoff_ko.md`와 실제 runtime ownership을 맞추는 작업이다.
- 새 semantic layer를 만들지 않는다.
- 우선순위는 `identity ownership -> live consumer wiring -> truthful logging` 순서다.

이 freeze는 runtime metadata의 `runtime_alignment_scope_contract_v1`로도 남습니다. 즉 이후 `14.1 ~ 14.8`은 새로운 구조를 만드는 작업이 아니라, 이미 정리된 구조가 live code에서도 그대로 작동하도록 ownership과 handoff를 공고히 하는 단계입니다.

구체적으로는 아래 세 축을 순서대로 맞춥니다.

- `ObserveConfirm`가 legacy `energy_snapshot` 없이 identity를 소유하도록 정렬
- `Consumer`가 실제 live path에서 `ObserveConfirm + Layer Mode + Energy`를 함께 읽도록 연결
- `Energy` replay/log가 실제 사용된 field만 기록하도록 교정

관련 계약 문서는 `docs/runtime_alignment_scope_contract.md`입니다.

---

## 12. 14.6 Compatibility / Migration Guard

`14.6`의 목적은 legacy field를 당장 지우는 것이 아니라, legacy가 남아 있어도 ownership과 live gate를 다시 오염시키지 못하게 막는 것입니다.

이번 단계에서 실제로 고정한 것은 아래와 같습니다.

- `observe_confirm_v1`은 consumer가 읽을 수는 있지만, `observe_confirm_v2`가 비어 있을 때만 쓰는 `migration bridge`다.
- `observe_confirm_v2`가 존재하면 `observe_confirm_v1`은 identity를 덮어쓰지 못한다.
- `energy_snapshot`은 유지되지만, `energy_helper_v2`가 없을 때 helper replay 재구성용으로만 쓰인다.
- `energy_snapshot`은 identity input도 아니고 direct live gate input도 아니다.
- `EntryService`와 replay 복원 경로는 shared migration guard helper를 통해서만 legacy fallback을 사용한다.

즉 이제 legacy field의 의미는 아래처럼 정리된다.

- `observe_confirm_v1`: compatibility shadow / migration fallback
- `energy_snapshot`: compatibility shadow / replay bridge

반대로 legacy field가 할 수 없는 일도 명확하다.

- `ObserveConfirm` identity를 다시 소유하는 일
- `Consumer`가 canonical handoff를 무시하고 legacy field로 직접 분기하는 일
- `Energy`가 `energy_snapshot`만으로 live gate를 다시 장악하는 일

실무적으로는 이 단계 덕분에 migration cleanup 전까지도 dual-write를 유지할 수 있고, replay도 깨지지 않으면서 ownership 분리는 계속 보장된다.

---

## 13. 14.7 Test Hardening

`14.7`은 구조를 더 바꾸는 단계가 아니라, 여기까지 맞춘 ownership과 handoff가 다시 무너지지 않도록 회귀 테스트를 명시적으로 잠그는 단계다.

이번 단계에서 고정한 테스트 축은 아래와 같다.

- `energy_snapshot`을 바꿔도 `observe_confirm_v2`의 `archetype_id / side / invalidation_id / management_profile_id`는 바뀌지 않는다.
- `layer_mode_policy_v1`만 바꾸면 consumer decision은 바뀔 수 있지만 canonical identity는 유지된다.
- `energy_helper_v2`만 바꾸면 `priority / wait / soft block`은 바뀔 수 있지만 canonical identity는 유지된다.
- `consumer_usage_trace.consumed_fields`는 실제 live branch에서 사용한 helper field와 일치해야 한다.
- `WaitEngine`는 `wait_vs_enter_hint`를 실제 valuation과 decision에서 반영해야 한다.
- `EntryService`는 `soft_block_hint`와 `priority_hint`를 실제 live branch에서 반영해야 한다.

즉 `14.7`이 끝난 뒤에는 “문서는 이렇게 말하는데 테스트가 못 막는다”는 상태를 줄이고, ownership 분리와 consumer wiring이 회귀 테스트로도 공고해진다.

---

## 14. 14.8 Docs / Handoff Re-freeze

`14.8`은 새 의미층이나 새 helper를 추가하는 단계가 아니다. `14.1 ~ 14.7`에서 실제 코드에 반영된 ownership과 handoff를 문서 문장에도 그대로 다시 고정해서, 설명서와 runtime이 같은 말을 하도록 만드는 단계다.

이번 단계 이후 현재 runtime ownership을 한 줄씩 다시 정리하면 아래와 같다.

- `ObserveConfirm`는 legacy `energy_snapshot` 없이 identity를 소유한다.
- `ObserveConfirm`의 confirm / wait 분기는 semantic bundle과 forecast modulation으로만 결정되고, legacy energy force는 더 이상 identity 입력이 아니다.
- `Consumer`의 live path는 `ObserveConfirm`에서 identity를 읽고, `Layer Mode`에서 policy를 읽고, `Energy`에서 utility hint를 읽는다.
- `EntryService`는 `action_readiness`, `confidence_adjustment_hint`, `soft_block_hint`, `priority_hint`만 실제 live 분기에 사용한다.
- `WaitEngine`는 `wait_vs_enter_hint`, `action_readiness`, `soft_block_hint`와 `Layer Mode` policy를 함께 읽는다.
- `selected_side`와 `net_utility`는 여전히 identity owner나 direct order gate가 아니다.
- `observe_confirm_v1`과 `energy_snapshot`은 남아 있어도 compatibility bridge일 뿐이고, canonical ownership을 되찾지 못한다.
- replay와 audit의 `consumer_usage_trace`는 실제로 사용한 helper field만 기록한다.

이 단계에서 같이 다시 얼린 참조 문서는 아래와 같다.

- `docs/observe_confirm_scope_contract.md`
- `docs/consumer_scope_contract.md`
- `docs/layer_mode_scope_contract.md`
- `docs/energy_scope_contract.md`
- `docs/runtime_alignment_scope_contract.md`

즉 `14.8`까지 끝난 현재 기준으로는, 이 문서를 읽는 사람이 그대로 가져가도 되는 ownership 문장은 아래와 같다.

- identity owner는 `ObserveConfirm`
- policy owner는 `Layer Mode`
- utility/helper owner는 `Energy`
- legacy field는 migration / replay bridge

이제 `docs/position_to_energy_handoff_ko.md`의 설명과 실제 runtime handoff는 같은 구조를 말한다.
