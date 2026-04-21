# Current Shadow Auto System Implementation Roadmap

## 목적

이 로드맵은 shadow auto 전략을 실제 구현 단계로 나눈 실행 순서를 정의한다.

고정 원칙은 다음과 같다.

- `auto-run in shadow first`
- `do not directly modify live behavior`
- `promote only through bounded review`

단, 2026-04-08 기준으로 다음 해석을 추가 고정한다.

> 지금 병목은 "자동화 부족"이 아니라 "shadow가 baseline과 충분히 다르게 행동하지 못하는 것"이다.

즉 다음 구현 블록의 목적은 더 많은 자동화가 아니라:

- 행동 차이 생성
- 차이의 품질 검증
- 첫 비-HOLD 의사결정 확보

이다.

---

## 현재 스냅샷

2026-04-08 기준 shadow 상태는 다음과 같다.

- training corpus rows: `180`
- training bridge matched rows: `180 / 180`
- preview bundle status: `preview_bundle_ready`
- activation demo rows: `64`
- available rows: `64`
- `shadow_enter_count = 0`
- `value_diff = 0.118`
- `drawdown_diff = 0.0`
- `manual_alignment_improvement = 1.0`
- SA5 decision: `accept_preview_candidate`
- SA6 decision: `APPLY_CANDIDATE`
- bounded gate decision: `ALLOW_BOUNDED_LIVE_CANDIDATE`
- active runtime readiness: `candidate_stage_ready`
- bounded candidate stage: `candidate_runtime_staged`
- bounded candidate approval: `approved_pending_activation`
- active runtime activation: `activated_candidate_runtime_forced`
- runtime hot reload result: `semantic_shadow_loaded = true`
- shadow runtime diagnostics: `state=active / reason=loaded`

현재 해석:

- preview/offline shadow는 실제로 존재한다
- baseline과의 비교 저장층도 있다
- 그러나 실행 레벨에서 차이와 edge를 만들지 못하고 있다

따라서 다음 메인 블록은 SA4 이후의 "edge creation phase"로 본다.

---

## 이미 구현된 블록

### SA0. Scope Lock

- shadow는 non-live
- baseline은 live authority 유지

### SA1. Runtime Mode Split

구현 상태:

- 완료
- outputs:
  - `data/analysis/shadow_auto/shadow_runtime_modes_latest.csv`
  - `data/analysis/shadow_auto/shadow_runtime_modes_latest.json`
  - `data/analysis/shadow_auto/shadow_runtime_modes_latest.md`

### SA2. Shadow Candidate Input Bridge

구현 상태:

- 완료
- outputs:
  - `data/analysis/shadow_auto/shadow_candidates_latest.csv`
  - `data/analysis/shadow_auto/shadow_candidates_latest.json`
  - `data/analysis/shadow_auto/shadow_candidates_latest.md`

### SA3. Shadow vs Baseline Storage

구현 상태:

- 완료
- outputs:
  - `data/analysis/shadow_auto/shadow_vs_baseline_latest.csv`
  - `data/analysis/shadow_auto/shadow_vs_baseline_latest.json`
  - `data/analysis/shadow_auto/shadow_vs_baseline_latest.md`

메모:

- current + legacy `entry_decisions`를 같이 읽는다
- freeze-monitor family overlap도 대부분 확보했다

### SA4. Shadow Evaluation Layer

구현 상태:

- preview/offline 레벨 완료
- outputs:
  - `data/analysis/shadow_auto/shadow_evaluation_latest.csv`
  - `data/analysis/shadow_auto/shadow_evaluation_latest.json`
  - `data/analysis/shadow_auto/shadow_evaluation_latest.md`
  - `data/analysis/shadow_auto/shadow_signal_activation_bridge_latest.csv`
  - `data/analysis/shadow_auto/semantic_shadow_training_bridge_adapter_latest.csv`
  - `data/analysis/shadow_auto/semantic_shadow_training_corpus_latest.csv`
  - `data/analysis/shadow_auto/semantic_shadow_preview_bundle_latest.csv`
  - `data/analysis/shadow_auto/semantic_shadow_runtime_activation_demo_latest.csv`
  - `data/analysis/shadow_auto/shadow_execution_evaluation_latest.csv`

현재 의미:

- preview bundle까지는 생성됐다
- offline activation도 성공했다
- execution-level preview evaluation도 돈다
- 하지만 value/alignment 차이가 아직 없다

### SA5. Shadow Correction Loop

Updated status (2026-04-08):

- latest result: `accept_preview_candidate`
- current edge snapshot:
  - `value_diff = 0.118`
  - `manual_alignment_improvement = 1.0`
  - `drawdown_diff = 0.0`
- interpretation:
  - preview correction is no longer stuck at `REJECT/HOLD`
  - the current bottleneck is safe rollout and observation after activation

구현 상태:

- preview/offline 레벨 완료
- outputs:
  - `data/analysis/shadow_auto/shadow_correction_loop_latest.csv`
  - `data/analysis/shadow_auto/shadow_correction_loop_latest.json`
  - `data/analysis/shadow_auto/shadow_correction_loop_latest.md`

현재 결과:

- `hold_for_more_shadow_data`

### SA6. Auto Decision Engine

Updated status (2026-04-08):

- latest result: `APPLY_CANDIDATE`
- interpretation:
  - the preview bundle is now treated as a bounded live candidate
  - final rollout authority still stays behind stage / approval / activation gates

구현 상태:

- preview/offline 레벨 완료
- outputs:
  - `data/analysis/shadow_auto/shadow_auto_decision_latest.csv`
  - `data/analysis/shadow_auto/shadow_auto_decision_latest.json`
  - `data/analysis/shadow_auto/shadow_auto_decision_latest.md`

현재 결과:

- `HOLD`

---

## 다음 메인 블록: Edge Creation Phase

이제부터 중요한 것은 SA1~SA6을 "더 많이" 만드는 것이 아니라,
이미 열린 shadow가 baseline과 실제로 다르게 행동하도록 만드는 것이다.

이를 위해 아래 서브단계를 추가한다.

---

## SA4b. Shadow Behavior Divergence Audit

목적:

- baseline과 shadow가 얼마나 다르게 행동하는지 직접 계량한다

핵심 질문:

- `baseline_action != shadow_action`가 실제로 얼마나 발생하는가
- divergence가 특정 symbol/family에서만 생기는가
- divergence가 생겨도 모두 무의미한 noise인가

출력:

- `data/analysis/shadow_auto/shadow_divergence_audit_latest.csv`
- `data/analysis/shadow_auto/shadow_divergence_audit_latest.md`

권장 필드:

- `candidate_id`
- `family_key`
- `row_count`
- `same_action_count`
- `different_action_count`
- `divergence_rate`
- `enter_flip_count`
- `wait_flip_count`
- `exit_flip_count`
- `manual_reference_row_count`
- `manual_alignment_delta`
- `bounded_risk_flag`

완료 기준:

- 최소 1개 family에서 divergence rate가 0보다 큼
- divergence 결과를 symbol/family별로 읽을 수 있음

Current status (2026-04-08):

- implemented
- outputs:
  - `data/analysis/shadow_auto/shadow_divergence_audit_latest.csv`
  - `data/analysis/shadow_auto/shadow_divergence_audit_latest.json`
  - `data/analysis/shadow_auto/shadow_divergence_audit_latest.md`
- latest result:
  - `overall_divergence_rate = 0.953125`
  - `recommended_next_action_counts = {redesign_target_mapping_or_thresholds: 4}`
- interpretation:
  - divergence itself is already present
  - the current blocker is not lack of action difference, but the fact that this divergence conflicts with the mapped action target

---

## SA4c. Threshold Sweep

목적:

- 너무 보수적인 threshold 때문에 shadow가 baseline을 복제하는지 확인한다

출력:

- `data/analysis/shadow_auto/shadow_threshold_sweep_latest.csv`
- `data/analysis/shadow_auto/shadow_threshold_sweep_latest.md`

실험 축 예시:

- confidence threshold
- family별 apply threshold
- wait / protect / reversal class별 threshold

권장 필드:

- `sweep_id`
- `threshold_family`
- `threshold_value`
- `divergence_rate`
- `value_diff`
- `drawdown_diff`
- `manual_alignment_improvement`
- `new_false_positive_count`
- `recommended_next_action`

완료 기준:

- 적어도 한 구간에서 divergence가 증가함
- 그 divergence가 즉시 큰 음수 value/drawdown으로 무너지지 않음

Current status (2026-04-08):

- implemented
- outputs:
  - `data/analysis/shadow_auto/shadow_threshold_sweep_latest.csv`
  - `data/analysis/shadow_auto/shadow_threshold_sweep_latest.json`
  - `data/analysis/shadow_auto/shadow_threshold_sweep_latest.md`
- latest result:
  - `row_count = 81`
  - `recommended_next_action_counts = {reject_or_redesign_targets: 64, reject_threshold_profile: 17}`
  - `best_profile_id = threshold::0.55::0.99`
- interpretation:
  - threshold profiles are creating action differences
  - but no current profile qualifies as a bounded positive candidate yet
  - the dominant signal is target conflict or value deterioration, not “no divergence”

---

## SA4d. Target Mapping Redesign

목적:

- shadow가 무엇을 바꾸어야 하는지 더 명확히 알게 한다

현재 문제:

- wait-family / barrier-family만으로는 target semantics가 약할 수 있다

다음 목표:

- manual truth family를 더 직접적인 action target으로 다시 매핑

예시 target:

- `enter_now`
- `wait_more`
- `exit_protect`

출력:

- `docs/current_shadow_target_mapping_v1_ko.md`
- `data/analysis/shadow_auto/shadow_target_mapping_latest.csv`

권장 필드:

- `manual_wait_teacher_family`
- `manual_wait_teacher_label`
- `target_action_class`
- `target_reason`
- `confidence_floor`
- `shadow_usage_rule`

완료 기준:

- 모든 주요 manual family가 action target으로 매핑됨
- ambiguous family는 `hold/freeze`로 별도 관리됨

Current status (2026-04-08):

- implemented as a redesign reference artifact
- outputs:
  - `data/analysis/shadow_auto/shadow_target_mapping_latest.csv`
  - `data/analysis/shadow_auto/shadow_target_mapping_latest.json`
  - `data/analysis/shadow_auto/shadow_target_mapping_latest.md`
- latest result:
  - `row_count = 15`
  - `namespace_counts = {bridge_entry_wait_quality_label: 9, manual_wait_teacher_label: 6}`
  - `target_action_class_counts = {wait_more: 6, enter_now: 5, exit_protect: 4}`
- interpretation:
  - current proxy targets and coarse action targets are now explicitly separable
  - this artifact is the basis for detecting target ambiguity in threshold sweeps and divergence runs

---

## SA4e. Dataset Bias Audit / Rebalance

목적:

- dataset이 baseline 복제를 유도하는 구조인지 확인하고 완화한다

출력:

- `data/analysis/shadow_auto/shadow_dataset_bias_audit_latest.csv`
- `data/analysis/shadow_auto/shadow_dataset_bias_audit_latest.md`
- `data/analysis/shadow_auto/shadow_rebalanced_training_corpus_latest.csv`

권장 필드:

- `dataset_bucket`
- `row_count`
- `manual_truth_share`
- `baseline_copy_share`
- `freeze_family_share`
- `collect_more_truth_share`
- `target_action_entropy`
- `recommended_rebalance_action`

권장 액션:

- manual truth anchored row 비중 증가
- baseline dominant row downweight
- freeze-only family 분리
- divergence 실험용 family oversample

완료 기준:

- dataset에서 baseline_copy bias를 계량 가능
- rebalanced corpus 1회 생성

Current status (2026-04-08):

- implemented
- outputs:
  - `data/analysis/shadow_auto/shadow_dataset_bias_audit_latest.csv`
  - `data/analysis/shadow_auto/shadow_dataset_bias_audit_latest.json`
  - `data/analysis/shadow_auto/shadow_dataset_bias_audit_latest.md`
  - `data/analysis/shadow_auto/shadow_rebalanced_training_corpus_latest.csv`
- latest result:
  - `audit_row_count = 4`
  - `rebalanced_row_count = 180`
  - `recommended_rebalance_action_counts = {rebuild_targets_from_action_mapping: 3, expand_scene_coverage: 1}`
  - `rebalance_bucket_counts = {retarget_priority: 175, balanced_review: 5}`
- interpretation:
  - the main dataset issue is not simple class imbalance alone
  - target-mapping disagreement is dominating the preview corpus
  - scene coverage is also highly concentrated

---

## SA5a. First Divergence Run

목적:

- 실제로 baseline과 다른 shadow 행동을 한 번 만들어본다

원칙:

- freeze-only family는 우선 제외
- `collect_more_truth_before_patch`가 아닌 family 또는 threshold sweep에서 가장 유망한 family를 사용

출력:

- `data/analysis/shadow_auto/shadow_first_divergence_run_latest.csv`
- `data/analysis/shadow_auto/shadow_first_divergence_run_latest.md`

완료 기준:

- `different_action_count > 0`
- 특정 family에서 shadow 행동 차이가 확인됨

Current status (2026-04-08):

- implemented
- outputs:
  - `data/analysis/shadow_auto/shadow_first_divergence_run_latest.csv`
  - `data/analysis/shadow_auto/shadow_first_divergence_run_latest.json`
  - `data/analysis/shadow_auto/shadow_first_divergence_run_latest.md`
- latest result:
  - `selected_sweep_profile_id = threshold::0.55::0.75`
  - `divergence_rate = 0.96875`
  - `proxy_alignment_improvement = 0.96875`
  - `mapped_alignment_improvement = -0.875`
  - `value_diff_proxy = -0.15`
  - `run_decision = reject_preview_candidate`
- interpretation:
  - the first divergence run exists
  - but the first real result is not a positive apply candidate
  - it is a rejection signal showing that divergence without target consistency is not enough

---

## SA5b. First Accept/Reject-worthy Correction Run

목적:

- correction loop가 무한 HOLD에만 머물지 않도록 첫 명시적 판정을 만든다

가능한 결과:

- `accept_preview_candidate`
- `reject_preview_candidate`
- `hold_for_more_shadow_data`

완료 기준:

- 최소 한 번은 `HOLD`가 아닌 결과가 생성됨
- 이유와 side-effect가 함께 기록됨

Current status (2026-04-08):

- partially satisfied through SA5a/SA6a linkage
- first non-HOLD preview judgment now exists as `reject_preview_candidate`
- next maturity step:
  - create either a second rejected profile for repeated evidence
  - or the first bounded-positive candidate after target/dataset fixes

---

## SA6a. First Non-HOLD Decision
Updated status (2026-04-08):

- latest result: `APPLY_CANDIDATE`
- bounded apply state: `preview_divergence_candidate`
- edge snapshot:
  - `value_diff_proxy = 0.118`
  - `manual_alignment_improvement = 1.0`
- interpretation:
  - the first explicit non-HOLD decision on the edge-creation branch is now positive
  - the remaining blocker is controlled rollout and post-activation observation, not preview rejection

목적:

- decision engine에서 첫 `APPLY_CANDIDATE` 또는 명시적 `REJECT`를 만든다

현재:

- `HOLD`

다음 목표:

- `APPLY_CANDIDATE`
- 또는 `REJECT`

왜 중요한가:

- 이 단계가 되어야 shadow decision이 실제 operational decision surface로 작동하기 시작한다

출력:

- 기존 `shadow_auto_decision_latest.*` 활용
- 필요시 `shadow_auto_decision_history.csv` 추가

완료 기준:

- 첫 비-HOLD 결과 1건 이상
- decision reason이 threshold/target/dataset 수정과 연결됨

Current status (2026-04-08):

- implemented
- outputs:
  - `data/analysis/shadow_auto/shadow_first_non_hold_latest.csv`
  - `data/analysis/shadow_auto/shadow_first_non_hold_latest.json`
  - `data/analysis/shadow_auto/shadow_first_non_hold_latest.md`
- latest result:
  - `decision = REJECT`
  - `bounded_apply_state = preview_divergence_rejected`
  - reason:
    - divergence existed
    - but mapped alignment worsened and value proxy also deteriorated
- interpretation:
  - this is the first explicit non-HOLD decision on the new edge-creation branch
  - the current shadow problem is therefore no longer “no signal at all”
  - it is “divergence exists, but current targets/dataset make it a bad divergence”

---

## SA7. Bounded Candidate Stage / Post-Shadow Audit
Updated status (2026-04-08):

- implemented
- latest state progression:
  - `candidate_runtime_staged`
  - `approved_pending_activation`
  - `activated_candidate_runtime_forced`
- runtime verification:
  - `semantic_shadow_loaded = true`
  - `shadow_runtime_state = active`
  - `shadow_runtime_reason = loaded`
  - `semantic_live.mode = disabled`
- note:
  - activation was force-run once with a manual override because open positions were explicitly
    treated as user-managed positions for activation verification
  - this proves bundle cutover and runtime hot reload, but does not yet mean semantic live rollout
    mode is enabled

목적:

- 한 번 좋아 보인 preview 후보를 과대승격하지 않기 위함

출력:

- `data/analysis/shadow_auto/semantic_shadow_bounded_candidate_stage_latest.csv`
- `data/analysis/shadow_auto/semantic_shadow_bounded_candidate_stage_latest.md`
- `data/analysis/shadow_auto/semantic_shadow_bounded_candidate_approval_latest.csv`
- `data/analysis/shadow_auto/semantic_shadow_bounded_candidate_approval_latest.md`
- `data/analysis/shadow_auto/semantic_shadow_active_runtime_activation_latest.csv`
- `data/analysis/shadow_auto/semantic_shadow_active_runtime_activation_latest.md`
- `models/semantic_v1_bounded_candidate/semantic_shadow_bounded_candidate_manifest.json`
- `models/semantic_v1_bounded_candidate/semantic_shadow_bounded_candidate_approval.md`
- `models/semantic_v1_bounded_approved_pending_activation/semantic_shadow_bounded_candidate_activation_manifest.json`
- `data/analysis/shadow_auto/shadow_post_audit_latest.csv`
- `data/analysis/shadow_auto/shadow_post_audit_latest.md`

완료 기준:

- bounded candidate runtime package가 실제 stage directory에 복사됨
- approval packet이 생성됨
- approval entry를 받아 `pending / approve / reject` 상태를 latest output으로 남김
- approved candidate는 live 반영 전 `approved_pending_activation` 단계까지만 승격됨
- runtime idle 조건에서만 active model dir activation을 허용하고, 포지션 보유 중이면 `blocked_runtime_not_idle`로 유지함
- 필요시 manual override로 강제 activation을 수행할 수 있지만, 이 경우 activation output에 `force_activate=true`와 override reason이 남아야 함
- 반복 run 기준 consistency를 판정
- bounded apply readiness를 기록

---

## SA8. Bounded Apply Gate
Updated status (2026-04-08):

- implemented
- latest result: `ALLOW_BOUNDED_LIVE_CANDIDATE`
- current gate evidence:
  - `value_diff_proxy = 0.118`
  - `manual_reference_row_count = 64`
  - `manual_target_match_rate = 1.0`
  - `drawdown_diff = 0.0`
- interpretation:
- the bounded gate has already been cleared for candidate staging and approval
- the remaining work is runtime observation and rollout discipline
- runtime has now been switched into bounded `log_only` observation mode
- current observation still shows:
  - `entry_threshold_applied_total = 0`
  - `entry_partial_live_total = 0`
  - `recent_threshold_would_apply_count = 0`
  - `recent_partial_live_would_apply_count = 0`
  - `rollout_promotion_readiness = blocked_no_eligible_rows`
  - `recommended_next_action = retain_log_only_and_improve_baseline_action_or_semantic_quality`
  - latest blockers in the last `200` rows:
    - `baseline_no_action = 70`
    - `rollout_disabled = 65`
    - `symbol_not_in_allowlist = 45`
    - `timing_probability_too_low = 14`
    - `semantic_unavailable = 6`
  - worker hygiene has also been tightened:
    - `manage_cfd.bat` now matches bare `main.py` command lines
    - duplicate `main.py` workers are de-duped after boot
    - current runtime has been verified back to a single `main.py` worker

목적:

- shadow preview 성공과 live bounded promotion 사이에 마지막 게이트를 둔다

원칙:

- narrow scope
- rollback ready
- human approval required

출력:

- `data/analysis/shadow_auto/bounded_apply_candidates_latest.csv`
- `data/analysis/shadow_auto/bounded_apply_candidates_latest.md`

현재 주의:

- 현재는 아직 이 단계로 진입하면 안 된다
- divergence와 edge가 먼저 확인되어야 한다

---

## SA9. Correction Knowledge Base
Updated status (2026-04-08):

- started
- outputs:
  - `data/analysis/shadow_auto/correction_knowledge_base.csv`
  - `data/analysis/shadow_auto/correction_knowledge_base_latest.json`
  - `data/analysis/shadow_auto/correction_knowledge_base_latest.md`
- current state:
  - first shadow correction knowledge rows are now being accumulated
  - current sequence includes:
    - forced activation verification snapshot
    - disabled -> log_only rollout transition snapshot
  - richer retrospective columns now include:
    - `recent_fallback_reason_counts`
    - `recent_activation_state_counts`
    - `recent_threshold_would_apply_count`
    - `recent_partial_live_would_apply_count`
    - `rollout_promotion_readiness`
- still missing:
  - family / threshold-profile level success patterns across multiple bounded rollout cycles
  - rollback outcome patterns across multiple bounded rollout cycles

목적:

- 어떤 family / patch / threshold / target mapping이 성공했는지 누적 기억한다

출력:

- `data/analysis/shadow_auto/correction_knowledge_base.csv`

완료 기준:

- 성공/실패 패턴이 누적되고, 다음 shadow 실험 설계에 재사용됨

---

## 다음 구현 우선순위

현재 시점에서 실제 우선순위는 아래와 같다.

1. `SA7 Post-Activation Observation`
2. `SA7 Idle-Safe Non-Forced Activation Replay`
3. `SA7 Post-Shadow Audit`
4. `SA8 Bounded Rollout Observation`
5. `SA9 Correction Knowledge Base`
6. `AI1 Entry Authority Trace Extraction`
7. `AI2 Baseline-No-Action Candidate Bridge`
8. `AI3 Utility Gate Recast`
9. `AI4 State25 Live Consumer Bridge`

Authority integration 상세:

- `docs/current_execution_authority_integration_design_ko.md`
- `docs/current_execution_authority_integration_implementation_roadmap_ko.md`

---

## 진행 금지 조건

아래 상황이면 live promotion 쪽으로 넘어가면 안 된다.

- divergence rate가 0에 가깝다
- `value_diff <= 0`이 반복된다
- `manual_alignment_improvement <= 0`이 계속 유지된다
- SA5/SA6가 계속 `HOLD`만 낸다
- shadow 차이가 random noise 수준이다

즉 지금은 "더 많은 automation"보다 "의미 있는 차이 생성"이 선행 조건이다.

---

## 현재 위치 해석

이 로드맵상 현재 위치는 다음과 같다.

- SA1~SA6 preview/offline 체인은 구현 완료
- 그러나 결과는 아직 `edge creation before promotion` 단계
- 따라서 현재 프로젝트는:

> `shadow rollout complete`가 아니라
> `shadow edge creation phase start`

로 읽는 것이 맞다.

---

## 짧은 결론

다음 단계는 full automation이 아니다.

다음 단계는:

- shadow가 baseline과 실제로 다르게 행동하게 만들고
- 그 차이의 품질을 검증하고
- 첫 비-HOLD 의사결정을 얻는 것이다

즉 지금부터의 핵심 키워드는:

- divergence
- threshold
- target
- dataset
- first accept/reject

이다.
