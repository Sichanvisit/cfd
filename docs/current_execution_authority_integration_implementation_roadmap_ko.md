# Current Execution Authority Integration Implementation Roadmap

## 목적

이 로드맵은 authority map 진단을 실제 구현 순서로 변환한다.

핵심 목적은 다음 하나다.

> semantic / state25 / shadow가 advisory layer를 넘어서
> bounded execution authority를 실제 진입 경로에 갖기 시작하게 만든다

현재 고정 전제:

- hard risk guard finality 유지
- broker finality 유지
- exit orchestrator 전면 교체 금지
- bounded rollout / approval / audit discipline 유지

---

## 현재 위치

2026-04-08 기준 현재 상태는 아래와 같다.

- manual-truth calibration: 거의 완료
- shadow preview / bounded candidate: 완료에 가까움
- semantic live rollout: `log_only`
- latest observation:
  - `entry_threshold_applied_total = 0`
  - `entry_partial_live_total = 0`
  - `recent_threshold_would_apply_count = 0`
  - `recent_partial_live_would_apply_count = 0`
  - `rollout_promotion_readiness = blocked_no_eligible_rows`
- 주요 blocker:
  - `baseline_no_action`
  - `symbol_not_in_allowlist`
  - `timing_probability_too_low`
  - `semantic_unavailable`

이 말은:

- 지금은 rollout mode를 더 올릴 단계가 아니라
- authority integration을 시작해야 할 단계라는 뜻이다

추가 해석:

- `AI1 Entry Authority Trace Extraction`은 이미 구현됐다
- 최신 authority trace 기준 최근 200행에서 `baseline_no_action = 175`
- 즉 다음 우선순위는 `AI2 Baseline-No-Action Candidate Bridge`
- 그리고 이 AI2는 semantic/state25/shadow만이 아니라
  이미 offline 검증과 preview export까지 닫힌 `breakout_candidate` source를 함께 편입하는 방향으로 재정립한다
- 다만 breakout 쪽은 최신 raw audit 기준
  - `breakout_up_nonzero_count = 0`
  - `breakout_down_nonzero_count = 0`
  - `direction_none_count = 145`
  - `raw_blocker_family = missing_breakout_response_axis`
  상태라서, AI2는 단순 candidate bridge가 아니라
  `breakout axis recovery -> readiness surrogate -> overlay 재검증 -> candidate surface 재연결`
  순서로 다시 본다

---

## AI0. Scope Lock

목적:

- authority integration의 범위를 entry-first로 고정

규칙:

- entry부터 통합
- exit는 trace/contract normalization만 먼저
- hard risk / broker finality는 유지

완료 기준:

- 설계 문서 1개
- 구현 로드맵 1개
- 기존 shadow/manual roadmap에 링크 연결

현재 상태:

- 문서화 완료

---

## AI1. Entry Authority Trace Extraction

목적:

- entry authority가 실제로 어디서 결정됐는지 구조적으로 기록

대상 파일:

- `backend/services/entry_try_open_entry.py`

추가 필드 예:

- `entry_authority_owner`
- `entry_candidate_action_source`
- `entry_candidate_action`
- `entry_candidate_rejected_by`
- `entry_authority_stage`

권장 owner 값:

- `baseline_score`
- `semantic_candidate`
- `state25_candidate`
- `utility_gate`
- `post_entry_guard`
- `broker`

출력:

- `entry_decisions.csv` 신규 flat fields
- `runtime_status` summary extension
- `data/analysis/shadow_auto/entry_authority_trace_latest.csv`
- `data/analysis/shadow_auto/entry_authority_trace_latest.md`

완료 기준:

- 최근 200행 기준 authority owner 분포를 볼 수 있음
- `baseline_no_action` row가 몇 건인지와 semantic/state25 candidate 가능 row를 분리해 볼 수 있음

우선순위:

- `P1`

현재 상태:

- 구현 완료
- 최신 산출물:
  - `data/analysis/shadow_auto/entry_authority_trace_latest.csv`
  - `data/analysis/shadow_auto/entry_authority_trace_latest.md`
- 현재 최신 요약:
  - `baseline_no_action_count = 175`
  - `utility_gate_veto_count = 0`
  - `post_entry_guard_veto_count = 1`
  - `recommended_next_action = implement_ai2_baseline_no_action_candidate_bridge`

---

## AI2. Baseline-No-Action Candidate Bridge

목적:

- `baseline_no_action`일 때도 semantic/state25/shadow/breakout이 bounded candidate action을 제안할 수 있게 함

대상 파일:

- `backend/services/entry_try_open_entry.py`
- `ml/semantic_v1/promotion_guard.py`
- `backend/services/breakout_event_runtime.py`
- `backend/services/breakout_event_overlay.py`

핵심 해석:

- AI2는 이미 코드상 live runtime에 올라와 있다
- 하지만 breakout source는 현재 `WAIT_MORE / NONE`만 만들고 있다
- 원인은 threshold가 아니라 breakout runtime input contract mismatch다

즉 AI2는 이제 하나의 구현이 아니라 아래 하위 단계 묶음으로 본다.

우선순위:

- `P1`

재정의 메모:

- breakout 라인은 별도 owner 승격 트랙이 아니다
- `AI2 unified candidate surface`에 편입되는 검증된 candidate source다
- 즉 `AI2`는 사실상 `AI2 + breakout candidate bridge`로 본다
- 그리고 breakout 쪽은 `bridge = 응급처치`, `upstream axis = 정식 수선`으로 분리한다

### AI2a. Breakout Response-Axis Bridge

목적:

- 현재 없는 `breakout_up/down` 축을 기존 response axis에서 bounded proxy로 유도

대상 파일:

- `backend/services/breakout_event_runtime.py`

구현 방향:

- 상단 proxy
  - `upper_break_up`
  - `mid_reclaim_up`
- 하단 proxy
  - `lower_break_down`
  - `mid_lose_down`

중요 원칙:

- 첫 구현은 상하단 대칭 proxy bridge로 시작 가능
- 하지만 `initial / reclaim / continuation` type은 분리 기록한다
- threshold는 아직 손대지 않는다

출력:

- `breakout_event_runtime_v1` detail payload 확장
- `data/analysis/shadow_auto/breakout_runtime_raw_audit_latest.csv`
- `data/analysis/shadow_auto/breakout_runtime_raw_audit_latest.md`

완료 기준:

- `breakout_up_nonzero_count > 0`
  또는
- `breakout_down_nonzero_count > 0`

현재 상태:

- 구현 완료
- 최신 raw audit 기준:
  - `breakout_up_nonzero_count = 94`
  - `breakout_down_nonzero_count = 94`
  - `breakout_axis_mode_counts = {"proxy": 94}`
  - `breakout_up_source_counts = {"upper_break_up": 51, "mid_reclaim_up_proxy": 43}`
  - `breakout_down_source_counts = {"lower_break_down": 4, "mid_lose_down_proxy": 90}`
- 즉 `missing_breakout_response_axis` 단계는 벗어났고,
  다음 병목은 `direction/state/readiness` 쪽으로 이동했다

### AI2b. Breakout Direction Resolver Debug Audit

목적:

- axis bridge 뒤에 왜 `direction = NONE`이 계속 남는지 더 세분화해서 계량

대상 파일:

- `backend/services/breakout_runtime_raw_audit.py`

확인 지표:

- `up_score_raw`
- `down_score_raw`
- `normalized_gap`
- `selected_axis_family`
- `why_none_reason`
- `direction_none_count`
- `state_pre_breakout_count`
- `overlay_wait_more_count`
- `raw_blocker_family_counts`

완료 기준:

- `direction != NONE`가 일부라도 생김
- `why_none_reason`이 `direction_threshold_not_met` 한 종류가 아니라
  `gap_too_small / mixed_axis_conflict / reclaim_without_break / readiness_not_ready`
  같은 하위 이유로 분해됨
- `pre_breakout` 외 상태가 분포에 나타남
- blocker가 `missing_breakout_response_axis`에서 다른 실제 분포로 이동

현재 상태:

- 부분 달성
- 최신 raw audit 기준:
  - `direction_counts = {"NONE": 93, "UP": 1}`
  - `state_counts = {"initial_breakout": 1, "pre_breakout": 93}`
  - `raw_blocker_family_counts = {"direction_threshold_not_met": 93, "overlay_confidence_below_enter_threshold": 1}`
- axis는 살아났고 state도 일부 살아났지만,
  아직 direction 대부분이 `NONE`이라 resolver 세분화가 다음 병목이다

### AI2c. Breakout Readiness Surrogate

목적:

- 비어 있는 `micro_breakout_readiness_state`를 bounded surrogate로 채움

대상 파일:

- `backend/services/breakout_event_runtime.py`
- 필요시 helper file 추가

구현 방향:

- response axis
- confirm score
- continuation score
- volatility / structure proximity
를 조합해 최소 `PRE / READY` 구분 생성

완료 기준:

- readiness 분포가 빈 dict가 아님
- `READY` 상태가 일부 생김

현재 상태:

- 구현 완료
- 최신 raw audit 기준:
  - `effective_breakout_readiness_counts = {"BUILDING_BREAKOUT": 1, "COILED_BREAKOUT": 3}`
  - `state_counts = {"initial_breakout": 1, "pre_breakout": 93}`
- 즉 readiness surrogate가 실제로 분포를 만들었고,
  축만 살아 있던 상태에서 `state = initial_breakout` 사례가 1건 생겼다
- 다음 우선순위는 `AI2d Breakout Type Split / Resolver Separation`

### AI2d. Breakout Type Split / Resolver Separation

목적:

- breakout을 하나의 점수로 보지 않고 최소한 `initial / reclaim / continuation`으로 분리
- 타입별로 다른 direction resolver를 적용

대상 파일:

- `backend/services/breakout_event_runtime.py`
- 필요시 helper file 추가

구현 방향:

- `initial_breakout` resolver
  - `upper_break_up / lower_break_down` 비중을 더 높게
- `reclaim_breakout / continuation_breakout` resolver
  - `mid_reclaim_up / mid_lose_down`
  - `continuation_score`
  - confirm 보정
  비중을 더 높게

완료 기준:

- recent row에서 `selected_axis_family`가 빈 값이 아님
- direction resolver가 타입별 분포를 남김
- `direction = NONE` 비율이 현재보다 줄어듦

### AI2e. Breakout Conflict Resolver Separation

목적:

- breakout owner와 forecast confirm owner를 분리하고,
  conflict를 `즉시 무효`가 아니라 `강등`으로 처리

대상 파일:

- `backend/services/breakout_event_overlay.py`
- 필요시 helper file 추가

구현 방향:

- forecast confirm은 owner가 아니라 `veto or confidence adjuster`
- conflict 시 아래 필드 추가:
  - `direction_conflict_level`
  - `confirm_alignment_score`
  - `action_demotion_rule`
- 결과는
  - `ENTER_NOW`
  - `WATCH_BREAKOUT`
  - `PROBE_BREAKOUT`
  - `WAIT_MORE`
  중 하나로 강등

완료 기준:

- `confirm_conflict_hold` 단일 상태가 아니라
  `watch/probe/wait`로 분해된 분포가 생김
- breakout 후보가 conflict 때문에 완전히 사라지지 않음

### AI2f. Breakout Overlay Recheck

목적:

- direction/state/readiness가 살아난 뒤 overlay가 `WAIT_MORE`만 내는지 재검증

대상 파일:

- `backend/services/breakout_event_overlay.py`
- `backend/services/entry_candidate_bridge.py`

완료 기준:

- `overlay_enter_now_count > 0`
  또는
- `WAIT_MORE -> WATCH_BREAKOUT / PROBE_BREAKOUT / ENTER_NOW` 전환 후보가 일부 관측됨

현재 상태:

- 구현 완료, 결과는 재검증 단계
- 최신 raw audit 기준:
  - `overlay_enter_now_count = 0`
  - `overlay_target_counts = {"WAIT_MORE": 94}`
  - `overlay_reason_summary_counts = {"confirm_conflict_hold|wait_more": 1, "pre_breakout|wait_more": 93}`
- 의미:
  - overlay는 이제 readiness/state를 실제로 읽고 있다
  - 다만 current window에서는 `ENTER_NOW`가 아직 안 생겼고,
    유일한 `initial_breakout` row도 `confirm_conflict_hold`로 보류되었다
- 즉 다음 병목은
  - direction이 대부분 아직 `NONE`인 점
  - breakout direction과 forecast confirm이 충돌할 때 action 단계가 너무 거친 점
  으로 좁혀졌다

권고 메모:

- 현재 단계에서 `confirm_conflict_hold`는 기본적으로 안전한 보류 정책이지만,
  다음 단계에서는 이것을 단일 veto로 남기지 말고
  `WATCH_BREAKOUT / PROBE_BREAKOUT / WAIT_MORE` 같은 강등 규칙으로 분해하는 것이 맞다

### AI2g. Unified Candidate Surface Reconciliation

목적:

- 축/상태/readiness가 살아난 breakout을 AI2 candidate surface에 다시 연결

구현 방향:

- `candidate_action_surface_v1` 유지
- baseline action이 없을 때도
  - semantic prediction
  - state25 candidate hint
  - shadow bounded candidate
  - breakout candidate
  중 조건 충족 시 `candidate_action` 제안

bounded 조건 예:

- symbol allowlist
- trace quality pass
- semantic available
- timing / entry_quality probability floor
- state25 candidate rollout phase in `log_only` or above
- breakout candidate는 runtime breakout 감지 + preview-trained output만 사용
- manual canonical seed는 훈련/검증 자산으로만 쓰고 live 직접 입력으로 쓰지 않음

출력:

- `entry_decisions`에 `entry_candidate_action_source`
- `entry_decisions`에 `entry_candidate_action_reason`
- `entry_decisions`에 `entry_candidate_confidence`
- `data/analysis/shadow_auto/baseline_no_action_bridge_latest.csv`
- `data/analysis/shadow_auto/baseline_no_action_bridge_latest.md`

완료 기준:

- 최근 행에서 `baseline_no_action`이어도 `candidate_action_source != ''` 인 케이스가 생김
- source 분포에 `breakout_candidate`가 별도 집계됨
- `baseline_no_action -> breakout_candidate -> guard/utility outcome` trace가 보임

### AI2h. Breakout Threshold / Overlay Tuning

목적:

- 축/방향/readiness가 실제로 살아난 뒤에만 threshold/overlay 문턱을 조정

중요 원칙:

- `AI2a ~ AI2g` 전에는 threshold 조정 금지
- 지금 문제는 tuning보다 translation/contract mismatch 해결이 먼저다

완료 기준:

- direction/state/readiness가 실제 분포를 가진 상태에서만 tuning 시작
- tuning은 `ENTER_NOW` 남발이 아니라 bounded candidate coverage 개선에 한정

---

## AI3. Utility Gate Recast

목적:

- utility gate를 hard skip authority에서 bounded decision consumer로 변경

대상 파일:

- `backend/services/entry_try_open_entry.py`
- `backend/core/config.py`

구현 방향:

- 기존
  - `utility_u < u_min -> skip`
- 변경
  - `utility_decision_v2`
    - `reject`
    - `approve`
    - `partial_size`
    - `shadow_only_hold`
    - `candidate_hold_for_more_truth`

새 설정 예:

- `ENTRY_UTILITY_DECISION_MODE=v2`
- `ENTRY_UTILITY_ALLOW_SEMANTIC_CANDIDATE=true`
- `ENTRY_UTILITY_ALLOW_STATE25_CANDIDATE=true`
- `ENTRY_UTILITY_ALLOW_BREAKOUT_CANDIDATE=true`

출력:

- `data/analysis/shadow_auto/utility_gate_recast_latest.csv`
- `data/analysis/shadow_auto/utility_gate_recast_latest.md`

완료 기준:

- utility gate가 semantic/state25/breakout candidate를 무조건 kill하지 않음
- `utility_reject`와 `utility_partial_size`가 구분됨

우선순위:

- `P1`

---

## AI4. State25 Live Consumer Bridge

목적:

- state25 hint를 bounded runtime에서 실제 execution surface가 소비하게 만들기

대상 파일:

- `backend/services/teacher_pattern_active_candidate_runtime.py`
- `backend/services/entry_try_open_entry.py`

구현 방향:

- `candidate_log_only_entry_threshold_hint`를 bounded flag 아래서 `dynamic_threshold` candidate로 반영
- `candidate_log_only_size hint`를 bounded flag 아래서 lot candidate로 반영
- 실제 live write는
  - `off`
  - `log_only`
  - `bounded_apply`
  3단계로 나눔

새 설정 예:

- `STATE25_ENTRY_HINT_BINDING_MODE=log_only|bounded_apply`
- `STATE25_SIZE_HINT_BINDING_MODE=log_only|bounded_apply`

출력:

- `data/analysis/state25/state25_live_consumer_bridge_latest.csv`
- `data/analysis/state25/state25_live_consumer_bridge_latest.md`

완료 기준:

- `actual_live_entry_threshold != baseline_entry_threshold` 사례가 bounded mode에서 생김
- `actual_live_size_multiplier != 1.0` 사례가 bounded mode에서 생김

우선순위:

- `P1`

---

## AI5. Unified Entry Authority Contract

목적:

- baseline / semantic / state25 / utility / guards를 하나의 contract로 정렬

대상 파일:

- `backend/services/entry_try_open_entry.py`

핵심 계약:

- `entry_authority_contract_v1`
  - `baseline_action`
  - `candidate_action`
  - `candidate_action_source`
  - `candidate_action_reason`
  - `candidate_action_confidence`
  - `utility_decision`
  - `guard_veto_owner`
  - `broker_result`
  - `final_action_owner`

출력:

- `entry_decisions` flat fields + detail payload
- `data/analysis/shadow_auto/entry_authority_contract_latest.csv`
- `data/analysis/shadow_auto/entry_authority_contract_latest.md`

완료 기준:

- 어떤 row가 왜 열렸고 왜 막혔는지를 owner 기준으로 설명 가능
- semantic/state25/breakout source별 성능 비교가 가능

우선순위:

- `P2`

---

## AI6. Exit Authority Trace / Normalization

목적:

- exit는 바로 통합하지 말고 authority trace를 먼저 정규화

대상 파일:

- `backend/services/exit_manage_positions.py`
- `backend/services/exit_execution_orchestrator.py`

추가 필드 예:

- `exit_authority_owner`
- `exit_selected_candidate_phase`
- `exit_veto_owner`
- `exit_hold_veto_active`

owner 값 예:

- `hard_risk_guard`
- `recovery_plan`
- `recovery_wait_hold`
- `partial_manager`
- `managed_exit_policy`
- `ai_exit_overlay`
- `reversal_exit`

출력:

- `data/analysis/shadow_auto/exit_authority_trace_latest.csv`
- `data/analysis/shadow_auto/exit_authority_trace_latest.md`

완료 기준:

- exit authority owner 분포를 설명 가능
- utility winner와 실제 final owner의 차이를 계량 가능

우선순위:

- `P3`

---

## AI7. Bounded Canary for Integrated Entry Authority

목적:

- authority integration 결과를 곧바로 full live에 넣지 않고 bounded canary로 관찰

구현 방향:

- symbol allowlist 매우 제한
- session allowlist 제한
- `log_only -> threshold_only -> partial_live` 순서
- integrated candidate action은 처음엔 `log_only` trace만 남김

출력:

- `data/analysis/shadow_auto/integrated_entry_canary_observation_latest.csv`
- `data/analysis/shadow_auto/integrated_entry_canary_observation_latest.md`

성공 기준:

- `recent_threshold_would_apply_count > 0`
  또는
- integrated candidate source row에서 bounded decision이 실제 생김

우선순위:

- `P2`

---

## AI8. Authority Retrospective / Knowledge Base Expansion

목적:

- SA9를 authority integration retrospective까지 확장

대상 파일:

- `backend/services/shadow_correction_knowledge_base.py`

추가 필드 예:

- `entry_authority_owner_counts`
- `entry_candidate_source_counts`
- `utility_reject_counts`
- `post_guard_veto_counts`
- `baseline_no_action_bridge_count`
- `integrated_candidate_apply_count`

출력:

- `data/analysis/shadow_auto/correction_knowledge_base.csv`
- `data/analysis/shadow_auto/correction_knowledge_base_latest.md`

완료 기준:

- threshold/profile retrospective뿐 아니라 authority retrospective가 가능

우선순위:

- `P3`

---

## 권장 순서

다음 실제 구현 순서는 아래가 가장 좋다.

1. `AI1 Entry Authority Trace Extraction`
2. `AI2a Breakout Response-Axis Bridge`
3. `AI2b Breakout Direction / State Revalidation Audit`
4. `AI2c Breakout Readiness Surrogate`
5. `AI2d Breakout Type Split / Resolver Separation`
6. `AI2e Breakout Conflict Resolver Separation`
7. `AI2f Breakout Overlay Recheck`
8. `AI2g Unified Candidate Surface Reconciliation`
9. `AI2h Breakout Threshold / Overlay Tuning`
10. `AI3 Utility Gate Recast`
11. `AI4 State25 Live Consumer Bridge`
12. `AI5 Unified Entry Authority Contract`
13. `AI7 Bounded Canary`
14. `AI6 Exit Authority Trace`
15. `AI8 Authority Retrospective`

핵심 이유:

- 지금 가장 큰 막힘은 entry authority
- 그 안에서도 breakout은 threshold 문제가 아니라 language / contract mismatch와 owner conflict 정리가 먼저다
- 따라서 axis -> direction -> readiness -> type split -> conflict resolver -> overlay -> candidate 순서가 먼저다
- exit는 위험도가 더 높으므로 trace normalization이 먼저

---

## 중지 조건

아래 상황이면 authority integration을 더 밀지 말고 다시 분석한다.

- integrated candidate action이 생겨도 utility/post-guard veto가 100% 유지됨
- `baseline_no_action_bridge_count = 0` 상태가 계속 유지됨
- integrated candidate가 생기지만 value / drawdown이 즉시 악화됨
- broker failure나 order-block collision이 급증함

---

## 한 줄 결론

다음 단계는 semantic 튜닝이 아니라 authority 재배치다.

> `entry_try_open_entry.py` 안에서
> baseline / semantic / state25 / utility / post-guard의 권한 구조를 다시 짜는 것

이것이 지금 로드맵의 실제 다음 메인 축이다.
