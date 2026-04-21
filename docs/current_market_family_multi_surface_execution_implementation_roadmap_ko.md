# Current Market-Family Multi-Surface Execution Implementation Roadmap

## Overall Progress Summary

이 로드맵은 크게 두 덩어리로 읽는 것이 맞다.

1. `PF0 ~ MF17`
- market-family + multi-surface 구조를 실제 runtime, dataset, eval, signoff gate까지 만드는 단계

2. `CL0 ~ CL9`
- 위에서 만든 부품들을 실제 운영 루프로 닫는 단계

현재 상태를 큰 틀로 요약하면 아래와 같다.

- `PF0` 성능 baseline hold: 완료
- `MF1 ~ MF16`: 구현 완료
- `MF17`: 구조 구현 완료, 운영상 남은 것은 `manual signoff -> bounded activation`
- 다만 실제 runtime에서는 `old baseline SELL vs directional BUY` 충돌이 확인되어, `MF17 signoff`와 `CL1`로 넘어가기 전에 `P0 wrong-side active-action conflict hotfix`를 선행해야 한다
- 따라서 기존 로드맵은 "구축" 관점에서는 거의 끝까지 왔고, "운영 전환" 관점에서는 마지막 관문과 runtime 교정 트랙이 함께 남아 있다

조금 더 실무적으로 말하면:

- 기존에 하던 일:
  - `NAS100 / BTCUSD / XAUUSD`
  - `initial_entry / follow_through / continuation_hold / protective_exit`
  구조를 실제 데이터/평가/승인 체인으로 올리는 것
- 지금 남은 일:
  - `P0 wrong-side active-action conflict hotfix`
  - `BTCUSD / NAS100 / XAUUSD initial_entry_surface` 3개 수동 signoff
  - signoff 후 bounded activation
  - `follow_through negative expansion`
  - `continuation_hold / protective_exit` 데이터 보강

즉 이 문서는 이제

- `기존 MF 로드맵의 남은 마지막 관문`
- `그 뒤에 이어질 CL 운영층`

을 하나로 이어서 보는 문서다.

권장 해석 순서는 아래와 같다.

1. `MF17`까지 무엇이 이미 구축됐는지 확인
2. `P0 wrong-side active-action conflict`가 왜 signoff/CL보다 먼저인지 확인
3. `MF17`에서 무엇이 실제로 남았는지 확인
4. signoff/activation 이후 왜 `CL1`부터 운영층이 필요한지 확인

한 줄로 요약하면:

> 기존 로드맵은 `만들기` 단계가 거의 끝났고,
> 이제는 `wrong-side runtime 교정 -> bounded activation -> 운영 루프로 닫기`
> 순서로 넘어가는 시점이다.

## P0. Wrong-Side Active-Action Conflict Hotfix

목적:

- `old baseline`이 이미 `SELL/BUY`를 쥔 상태에서, 새 directional layer가 반대 방향을 강하게 보고 있어도 실행 우선권을 못 뒤집는 문제를 먼저 교정한다
- 특히 최근 XAU runtime에서 반복되는 `baseline SELL vs directional BUY(UP_PROBE)` 충돌을 signoff/CL 이전의 선행 blocker로 다룬다

왜 지금 먼저 하는가:

- 현재 문제는 센서 부재가 아니라 `owner 우선순위 + conflict resolution 부재`다
- 이 상태에서 `MF17 signoff`나 `CL1 orchestrator`를 먼저 열면 잘못된 baseline action을 더 체계적으로 운영하게 될 수 있다

현재 근거:

- 최근 XAU runtime row에서는
  - 실제 실행: `action = SELL`
  - 실행 owner: `entry_candidate_action_source = baseline_score`
  - 같은 row의 directional layer:
    - `countertrend_action_state = UP_PROBE`
    - `countertrend_directional_candidate_action = BUY`
    - `countertrend_directional_up_bias_score`가 높은 사례가 반복적으로 관측됨
- 최근 샘플 기준 `XAUUSD SELL vs directional BUY` conflict row가 다수 누적되어 있고,
  중심 scene family는 `range_upper_reversal_sell` / `shadow_upper_break_fail_confirm` 계열이다

### P0A. Wrong-Side Active-Action Conflict Audit

목적:

- `baseline action`과 `directional candidate action`이 실제로 충돌하는 row를 symbol/setup/state 기준으로 계량한다

주요 산출물:

- `wrong_side_active_action_conflict_audit_latest.csv`
- `wrong_side_active_action_conflict_audit_latest.json`
- `wrong_side_active_action_conflict_audit_latest.md`

완료 기준:

- symbol/setup/setup_reason/action/directional_action 기준 충돌 분포가 latest artifact로 정리된다
- `baseline_score`, `semantic_candidate`, `countertrend_candidate` 등 owner/source 분포가 함께 보인다

### P0B. Active-Action Conflict Guard

목적:

- baseline이 이미 `SELL` 또는 `BUY`를 들고 있어도,
  반대 directional owner가 충분히 강하면 현재 active action을 `WAIT` 또는 `WATCH/PROBE`로 강등한다

핵심 규칙:

- `baseline SELL` + `UP_PROBE/UP_ENTER` + 높은 `up_bias` -> `SELL` 강등
- 대칭 규칙:
  - `baseline BUY` + `DOWN_PROBE/DOWN_ENTER` + 높은 `down_bias` -> `BUY` 강등
- 1차 runtime 구현은 `XAU upper-reversal SELL` 충돌을 우선 타깃으로 삼는다
- 1차 guard는 `override`가 아니라 `SELL/BUY -> WAIT` 강등만 수행한다
- 1차 trace 필드:
  - `active_action_conflict_detected`
  - `active_action_conflict_guard_applied`
  - `active_action_conflict_resolution_state`
  - `active_action_conflict_kind`
  - `active_action_conflict_bias_gap`
  - `active_action_conflict_reason_summary`

실행 우선 원칙:

- 첫 단계는 `override`가 아니라 `downgrade`다
- 즉 곧바로 반대 방향을 강제 실행하지 않고,
  current wrong-side active action을 먼저 `WAIT / WATCH / PROBE`로 낮춘다

권장 상태기계:

- `KEEP`
- `WATCH`
- `PROBE`
- `OVERRIDE`

권장 해석:

- 약한 충돌: `KEEP`
- 중간 충돌: `WATCH`
- 강한 충돌: `PROBE`
- 확정 충돌: bounded `OVERRIDE candidate`

완료 기준:

- wrong-side active action이 더 이상 바로 broker 진입으로 이어지지 않는다
- fresh runtime row에 `conflict_guard_downgrade` 흔적이 남는다

### P0C. Baseline-vs-Directional Bridge Conflict Resolution

목적:

- 기존 `baseline_no_action`에서만 작동하던 candidate bridge를
  `baseline active-action conflict`까지 다루는 구조로 확장한다

핵심 포인트:

- `baseline_no_action rescue`와 별도로 `active_action_conflict_resolution` 경로를 둔다
- bridge는 더 이상 "baseline이 비었을 때만" candidate를 고르지 않고,
  active baseline과 directional candidate가 충돌할 때의 resolution state를 계산한다

bridge mode:

1. `no_action_rescue`
2. `active_action_conflict_resolution`

1차 구현 메모:

- guard로 이미 `WAIT` 강등된 row에서 conflict bridge를 우선 연다
- `active_action_conflict_resolution`에서는 baseline과 반대 방향 candidate만 bridge 대상으로 본다
- latest row flat fields는 아래를 포함한다
  - `entry_candidate_bridge_mode`
  - `entry_candidate_bridge_active_conflict`
  - `entry_candidate_bridge_conflict_selected`
  - `entry_candidate_bridge_effective_baseline_action`
  - `entry_candidate_bridge_conflict_kind`

권장 중간 상태:

- `baseline_action_conflict`
- `conflict_guard_downgrade`
- `directional_override_candidate`

의미:

- bridge는 이제 단순 candidate picker가 아니라
  `execution precedence resolver`의 일부가 된다

완료 기준:

- `entry_candidate_bridge` latest row에 `active_action_conflict`와 `conflict_resolution_state`가 남는다
- `baseline SELL vs directional BUY` 같은 장면에서 bridge가 실제로 `WAIT` 또는 bounded candidate를 선택할 수 있다

### P0D. Wrong-Side Conflict Harvest

목적:

- wrong-side row를 단순 로그로 남기지 말고,
  이후 dataset rebuild와 preview eval에 다시 들어갈 학습 라벨로 승격한다

예시 failure label:

- `wrong_side_sell_pressure`
- `wrong_side_buy_pressure`
- `missed_up_continuation`
- `missed_down_continuation`

추가 context label:

- `false_down_pressure_in_uptrend`
- `false_up_pressure_in_downtrend`

권장 묶음:

- `follow_through_negative`
- `directional_conflict_failure`

완료 기준:

- conflict row가 failure harvest artifact에 자동 반영된다
- 이후 `follow_through` 또는 `initial_entry regret` 계열 preview dataset으로 편입 가능하다

### P0E. XAU Upper-Reversal Conflict Validation

목적:

- 기존 validation이 `range_lower_reversal_buy` 중심이었던 한계를 보완하고,
  실제 문제 장면인 `range_upper_reversal_sell -> UP_* conflict`를 검증 범위에 포함한다

우선 보강 구조 증거:

- `higher high count`
- `higher low count`
- `mid/upper reclaim success`
- `bars since failed reject`
- `upside continuation persistence`

핵심 방향:

- 단순 `anti_short` 보강보다
  `pro_up structure`를 강화한다

완료 기준:

- current XAU upper-reversal conflict family가 별도 validation artifact로 latest에 남는다
- `UP_WATCH / UP_PROBE / UP_ENTER`와 baseline action의 충돌/강등 상태가 검증된다

## PF0. Entry Performance Baseline Hold

목적:

- 현재 entry 성능 상태를 baseline으로 잠근다
- 추가 미세 최적화는 중단한다
- 실제 live symbol에서 `elapsed_ms >= 200`이 다시 발생할 때만 성능 작업으로 재진입한다

산출물:

- [entry_performance_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/entry_performance_baseline_latest.json)
- [entry_performance_regression_watch_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/entry_performance_regression_watch_latest.json)
- [entry_performance_baseline_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/entry_performance_baseline_latest.md)

완료 기준:

- baseline lock이 고정됨
- regression watch가 `resume_market_family_roadmap` 또는 `reenter_entry_performance_optimization`를 명시함
- 로드맵 재개 전에는 성능 미세 최적화보다 시장/상황 surface 작업을 우선함

상태:

- implemented
- next roadmap resume point: `P0A Wrong-Side Active-Action Conflict Audit`

## MF15 Status

- implemented
- outputs:
  - [multi_surface_preview_dataset_export_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/multi_surface_preview_dataset_export_latest.csv)
  - [multi_surface_preview_dataset_export_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/multi_surface_preview_dataset_export_latest.json)
  - [multi_surface_preview_dataset_export_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/multi_surface_preview_dataset_export_latest.md)
  - [initial_entry_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/initial_entry_dataset.csv)
  - [follow_through_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/follow_through_dataset.csv)
  - [continuation_hold_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/continuation_hold_dataset.csv)
  - [protective_exit_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/protective_exit_dataset.csv)
- recommended next action: `MF16 Symbol-Surface Preview Evaluation`

## MF16 Status

- implemented
- outputs:
  - [symbol_surface_preview_evaluation_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/symbol_surface_preview_evaluation_latest.csv)
  - [symbol_surface_preview_evaluation_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/symbol_surface_preview_evaluation_latest.json)
  - [symbol_surface_preview_evaluation_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/symbol_surface_preview_evaluation_latest.md)
- recommended next action: `MF17 Bounded Rollout`

## MF17 Status

- implemented through candidate gate, review manifest, and signoff criteria
- outputs:
  - [bounded_rollout_candidate_gate_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_rollout_candidate_gate_latest.json)
  - [bounded_rollout_review_manifest_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_rollout_review_manifest_latest.json)
  - [bounded_rollout_signoff_criteria_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_rollout_signoff_criteria_latest.json)
  - [symbol_surface_canary_signoff_packet_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/symbol_surface_canary_signoff_packet_latest.json)
  - [bounded_symbol_surface_activation_contract_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_symbol_surface_activation_contract_latest.json)
  - [btc_initial_entry_canary_signoff_packet_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/btc_initial_entry_canary_signoff_packet_latest.json)
  - [bounded_btc_review_canary_activation_contract_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_btc_review_canary_activation_contract_latest.json)
  - [initial_entry_label_resolution_queue_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/initial_entry_label_resolution_queue_latest.json)
  - [initial_entry_label_resolution_draft_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/initial_entry_label_resolution_draft_latest.json)
  - [initial_entry_label_resolution_apply_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/initial_entry_label_resolution_apply_latest.json)
  - [initial_entry_dataset_resolved.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/initial_entry_dataset_resolved.csv)
  - [multi_surface_data_gap_queue_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/multi_surface_data_gap_queue_latest.json)
  - [follow_through_negative_expansion_draft_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/follow_through_negative_expansion_draft_latest.json)
  - [hold_exit_augmentation_draft_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/hold_exit_augmentation_draft_latest.json)
- current status:
  - `symbol-surface canary signoff packet -> generic structure ready`
  - `symbol-surface activation contract -> generic structure ready`
  - `BTCUSD/NAS100/XAUUSD initial_entry_surface -> MANUAL_SIGNOFF_APPROVED`
  - `bounded activation apply -> BTC/XAU = APPROVED_PENDING_RUNTIME_IDLE, NAS = APPROVED_PENDING_PERFORMANCE_RECOVERY`
  - `current runtime open_positions_count = 4` so no canary is actively live yet
- next roadmap action: `wait_for_runtime_idle_then_retry_btc_xau_canary_activation`
- remaining roadmap after activation apply:
  - `NAS100` entry performance recovery under `200ms`
  - bounded symbol-surface canary live observation after idle
  - follow-through negative-row expansion apply completed, eval refresh completed
  - continuation_hold / protective_exit augmentation apply completed, eval refresh completed

## CL0. Transition Note

- `PF0 ~ MF17`은 market-family + multi-surface 구조와 bounded rollout gate를 만드는 단계였다.
- 현재는 `BTCUSD / NAS100 / XAUUSD initial_entry_surface` 3개가 모두 `READY_FOR_MANUAL_SIGNOFF`이며, 공통 activation contract는 `PENDING_MANUAL_SIGNOFF` 상태다.
- 다만 최근 runtime에서는 `old baseline active action`과 `directional owner`가 충돌하는 wrong-side 장면이 반복 관측되어, signoff/activation/CL 이전에 `P0 wrong-side active-action conflict hotfix`가 선행되어야 한다.
- 따라서 다음 큰 줄기는
  1. `P0 runtime correction`
  2. `MF17 manual signoff -> bounded activation`
  3. `continuous harvest -> rebuild -> eval -> candidate package -> signoff queue -> canary -> rollback -> observability`
  순서로 읽는 것이 맞다.

## CL1. Continuous Learning Orchestrator

목적:

- runtime에서 계속 쌓이는 row, trade close, failure/regret 데이터를 자동으로 수집하고, harvest/rebuild/eval/signoff/canary까지 한 파이프라인으로 묶는다.

주요 산출물:

- `continuous_learning_orchestrator_latest.json`
- `continuous_learning_pipeline_run_latest.json`
- `continuous_learning_pipeline_run_latest.md`

핵심 작업:

- `runtime rows -> auto-harvest -> dataset rebuild -> preview eval refresh -> candidate package refresh -> signoff queue refresh -> canary monitor` 순서를 상위 orchestration으로 고정
- 현재 분산된 watch task를 "운영 흐름" 관점에서 재정렬
- 실패 시 어느 stage에서 멈췄는지 한 번에 볼 수 있는 pipeline status row 추가

완료 기준:

- 하루 동안 수집된 fresh row를 입력으로 삼아 preview/eval/candidate/signoff packet이 자동 갱신된다
- manual intervention 없이도 high-confidence harvest와 preview rebuild가 한 루프로 이어진다

우선순위:

- `P0`

## CL2. Candidate Package Schema Standardization

목적:

- 후보를 `symbol + surface + version` 단위의 표준 package로 관리해서 signoff, canary, rollback, retirement를 같은 언어로 다룬다.

주요 산출물:

- `symbol_surface_candidate_package_latest.csv`
- `symbol_surface_candidate_package_latest.json`
- `symbol_surface_candidate_package_latest.md`

필수 필드:

- `candidate_id`
- `candidate_version`
- `symbol`
- `surface`
- `scope`
- `created_at`
- `based_on_dataset_version`
- `based_on_eval_version`
- `expected_change_summary`
- `dominant_improvement_metric`
- `dominant_risk_metric`
- `recent_sample_count`
- `top_scene_families`
- `top_failure_labels`
- `activation_recommendation`
- `rollback_trigger_set`
- `status`
  - `preview_only`
  - `ready_for_signoff`
  - `canary_live`
  - `rolled_back`
  - `retired`

완료 기준:

- review manifest, signoff criteria, signoff packet, activation contract가 동일 `candidate_id / candidate_version`를 기준으로 연결된다
- BTC/NAS/XAU initial-entry canary와 이후 follow-through/hold/exit 후보가 같은 package schema를 공유한다

우선순위:

- `P0`

## CL3. Signoff Queue / Lifecycle Status

목적:

- 사용자가 가끔 와서 `YES / NO / HOLD / REVIEW LATER`만 선택할 수 있도록 signoff queue를 운영형으로 만든다.

주요 산출물:

- `signoff_queue_latest.csv`
- `signoff_queue_latest.json`
- `candidate_lifecycle_status_latest.json`

queue card 필드:

- `symbol`
- `surface`
- `candidate_version`
- `what_changes_if_enabled`
- `primary_expected_gain`
- `main_risk_if_wrong`
- `dominant_regime_concern`
- `why_canary_only`
- `scope`
- `canary_strength`
- `rollback_conditions`
- `decision_prompt`

완료 기준:

- 각 candidate를 사람이 한 줄 질문과 핵심 근거만 보고 승인/보류/거절할 수 있다
- lifecycle status가 `draft -> preview -> ready_for_signoff -> canary_live -> stable/rolled_back/retired`로 이어진다

우선순위:

- `P0`

## CL4. Symbol-Specific Observability Registries

목적:

- shared surface를 유지하되, 실제 망가지는 방식과 drift는 symbol별로 분리 관측한다.

주요 registry:

1. `symbol_surface_registry_latest`
2. `symbol_transition_registry_latest`
3. `symbol_scene_family_registry_latest`
4. `symbol_drift_registry_latest`

권장 필드:

- `symbol_surface_registry_latest`
  - `recent_row_count`
  - `action_distribution`
  - `wait/watch/probe/enter ratios`
  - `top_blockers`
  - `top_failures`
  - `avg_pnl`
  - `avg_hold_duration`
  - `giveback_summary`
  - `drift_flag`
- `symbol_transition_registry_latest`
  - `WAIT->WATCH`
  - `WATCH->PROBE`
  - `PROBE->ENTER`
  - `ENTER->HOLD`
  - `ENTER->EXIT`
- `symbol_scene_family_registry_latest`
  - `row_count`
  - `enter_rate`
  - `false_positive_rate`
  - `continuation_capture_rate`
  - `review_needed`
- `symbol_drift_registry_latest`
  - `state_distribution_drift`
  - `blocker_drift`
  - `family_drift`
  - `pnl_regime_drift`
  - `warning_level`

완료 기준:

- signoff와 canary review는 `symbol + surface` 단위로 단순하게 유지하되, 근거는 위 registry에서 끌어올 수 있다
- NAS/BTC/XAU가 같은 `initial_entry_surface`라도 왜 다른지 registry에서 바로 보인다

우선순위:

- `P0`

## CL5. Surface KPI Collector

목적:

- PnL 하나로 평가하지 않고 surface별 목적 함수에 맞는 KPI를 지속 수집한다.

surface별 KPI:

- `initial_entry_surface`
  - `early_adverse_excursion`
  - `favorable_excursion`
  - `false_entry_rate`
  - `n_bar_continuation_quality`
  - `blocked_good_entry_regret`
- `follow_through_surface`
  - `continuation_capture_rate`
  - `false_continuation_fire_rate`
  - `wait_to_probe_promotion_precision`
  - `follow_through_miss_rate`
- `continuation_hold_surface`
  - `runner_retention`
  - `premature_exit_regret`
  - `hold_continuation_quality`
  - `runner_giveback_balance`
- `protective_exit_surface`
  - `giveback_reduction`
  - `adverse_move_containment`
  - `protect_exit_precision`
  - `false_protect_exit_rate`
- 공통:
  - `false_positive_rate`
  - `repeated_fire_rate`
  - `overtrading_rate`
  - `drift_stability`
  - `symbol_performance_stability`

완료 기준:

- preview eval, signoff packet, canary monitor가 동일 KPI collector를 참조한다
- surface별 개선과 부작용이 한 장표에서 비교 가능하다

우선순위:

- `P1`

## CL6. Canary Runtime Guard / Rollback Engine

목적:

- manual signoff 이후 canary를 안전하게 열고, 이상 징후가 나오면 자동 downgrade/rollback한다.

주요 산출물:

- `canary_runtime_guard_latest.json`
- `canary_runtime_guard_latest.md`
- `rollback_event_log_latest.csv`

필수 가드:

- `symbol_allowlist`
- `surface_allowlist`
- `size_cap`
- `promotion_cap`
- `repeated_fire_throttle`
- `max_daily_exposure_cap`
- `rollback_trigger_set`

rollback 단계:

- `immediate_rollback`
  - false positive spike
  - drawdown spike
  - repeated fire explosion
  - scene-family collapse
- `soft_rollback_or_downgrade`
  - probe 성능 악화
  - enter 유지 가능하지만 watch-only로 강등 필요

완료 기준:

- YES 이후 canary activation, 모니터링, rollback이 사람 개입 없이 bounded하게 작동한다
- rollback은 `전부 끄기` 뿐 아니라 `watch-only`, `probe-only`, `size downgrade`로 단계적으로 실행된다

우선순위:

- `P0`

## CL7. Auto-Apply / Manual-Exception / Diagnostic Policy

목적:

- 어떤 것은 자동 반영하고, 어떤 것은 사람 승인만 받고, 어떤 것은 진단 전용으로만 남길지 정책을 분리한다.

정책 버킷:

- `auto_apply`
  - clear failure harvest
  - obvious negative continuation sample
  - high-confidence label apply
- `manual_exception`
  - signoff 직결 candidate
  - new scene family
  - drift 급증
  - watch/probe 경계
- `diagnostic_only`
  - sample 부족
  - 구조적 개선 불명확
  - regime drift 중 임시 후보

우선순위:

- `P1`

## CL8. LLM Summary Layer

목적:

- LLM은 결정자가 아니라 요약/설명자 역할만 하도록 natural-language summary layer를 붙인다.

필수 설명 필드:

- `what_changes_if_enabled`
- `primary_expected_gain`
- `main_risk_if_wrong`
- `dominant_regime_concern`
- `why_canary_only`

우선순위:

- `P2`

## CL9. Operating Mode System

목적:

- 시스템이 성숙해질수록 candidate 생성 빈도와 signoff 빈도를 다르게 운영할 수 있게 한다.

모드 예시:

- `exploration_mode`
- `stabilization_mode`
- `maintenance_mode`

완료 기준:

- 초반에는 candidate 생성/rollback이 활발하고, 성숙기에는 drift와 novelty 중심으로만 새 후보가 생성된다

우선순위:

- `P2`

## 목적

이 로드맵은
[current_market_family_multi_surface_execution_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_design_ko.md)
의 설계를 실제 구현 순서로 내린 것이다.

핵심 목표는 아래 두 가지다.

1. 시장별 과잉 차단 원인을 따로 푼다
2. `initial_entry / follow_through / continuation_hold / protective_exit`
   4개 surface를 실제 코드와 데이터에 올린다

---

## 현재 위치

기준 데이터:

- [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)

현재 요약:

- `NAS100`
  - 최근 80행 전부 `wait`
  - 전부 `observe_state_wait`
- `BTCUSD`
  - 최근 80행 전부 `wait`
  - `observe_state_wait` 다수
  - 일부 `middle_sr_anchor_guard`
- `XAUUSD`
  - 최근 80행 전부 `wait`
  - 전부 `outer_band_guard + probe_not_promoted`

XAU 별도 관찰:

- `2026-04-09 00:15:30` BUY 체결
- `2026-04-09 00:29:12` BUY 체결
- 이후 비슷한 장면 `131행`이 연속 `wait`
- 막는 이유는 전부 `outer_band_guard + probe_not_promoted`

즉 지금은 이미
`좋은 initial entry는 일부 열리지만, follow-through와 runner 보존이 매우 약한 상태`
까지 확인된 상태다.

---

## MF0. Scope Lock

목적:

- 이 트랙의 범위를 market-family + multi-surface로 고정

범위:

- `NAS100 / BTCUSD / XAUUSD`
- `entry / follow-through / continuation_hold / protective_exit`

비범위:

- 전 시장 글로벌 threshold 완화
- semantic live owner 전면 교체

완료 기준:

- 상세 설계 문서 1개
- 구현 로드맵 문서 1개
- 외부 조언 요청 문서 1개

상태:

- 이번 턴에서 완료

---

## MF1. Market-Family Audit Snapshot

목적:

- 시장별로 어디서 막히는지 고정 snapshot을 만든다

출력:

- `data/analysis/shadow_auto/market_family_entry_audit_latest.csv`
- `data/analysis/shadow_auto/market_family_entry_audit_latest.md`
- `data/analysis/shadow_auto/market_family_exit_audit_latest.csv`

필수 지표:

- symbol별 outcome 분포
- symbol별 `blocked_by`
- symbol별 `action_none_reason`
- symbol별 `observe_reason`
- symbol별 exit reason top distribution
- symbol별 average profit / average hold duration

완료 기준:

- NAS/BTC/XAU가 서로 다른 blocker를 가진다는 것이 latest 산출물로 보임

우선순위:

- `P1`

상태:

- 구현 완료
- 최신 산출물:
  - [market_family_entry_audit_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_family_entry_audit_latest.csv)
  - [market_family_entry_audit_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_family_entry_audit_latest.md)
  - [market_family_exit_audit_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_family_exit_audit_latest.csv)
  - [market_family_exit_audit_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_family_exit_audit_latest.md)

---

## MF2. Surface Objective / EV Specification

목적:

- surface를 상태 이름이 아니라
  서로 다른 목적 함수와 EV 비교 대상으로 고정

산출물:

- `surface_objective_spec_latest.json`
- `surface_ev_proxy_spec_latest.json`

필수 정의:

- `initial_entry_surface`
  - `entry_forward_ev`
  - `entry_regret_if_wait`
- `follow_through_surface`
  - `follow_through_extension_ev`
  - `miss_if_wait_cost`
- `continuation_hold_surface`
  - `runner_hold_ev`
  - `partial_then_hold_ev`
  - `runner_giveback_risk`
- `protective_exit_surface`
  - `protect_exit_loss_avoidance_ev`
  - `protect_exit_false_cut_cost`
- 공통:
  - `do_nothing_ev`

완료 기준:

- 최소 1개 spec 산출물에서
  surface별 목적 함수와 EV proxy가 고정됨

우선순위:

- `P1`

---

### MF2 Status

- implemented
- outputs:
  - [surface_objective_spec_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/surface_objective_spec_latest.json)
  - [surface_objective_spec_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/surface_objective_spec_latest.md)
  - [surface_ev_proxy_spec_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/surface_ev_proxy_spec_latest.json)

## MF3. Check / Color Label Formalization

목적:

- 사용자가 시각적으로 구분해 둔 체크/색 정보를
  약한 supervision 라벨 구조로 승격

새 라벨 축 예:

- `initial_break`
- `reclaim`
- `continuation`
- `pullback_resume`
- `runner_hold`
- `protect_exit`
- `failed_follow_through`

추가 실패 라벨:

- `false_breakout`
- `early_exit_regret`
- `late_entry_chase_fail`
- `missed_good_wait_release`

대상 파일:

- 새 label schema helper
- manual seed draft writer
- breakout / manual truth bridge

완료 기준:

- 최소 1개 CSV/JSON 산출물에
  `surface_label_family`와 `surface_label_state`가 materialize됨

우선순위:

- `P1`

---

### MF3 Status

- implemented
- outputs:
  - [check_color_label_formalization_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/check_color_label_formalization_latest.csv)
  - [check_color_label_formalization_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/check_color_label_formalization_latest.json)
  - [check_color_label_formalization_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/check_color_label_formalization_latest.md)

## MF4. Time-Axis Contract

목적:

- snapshot 기반 surface에 시간 축을 추가

필수 시간 축:

- `time_since_breakout`
- `time_since_entry`
- `bars_in_state`
- `bars_since_probe_activation`
- `momentum_decay`
- `time_since_last_relief`

완료 기준:

- 최소 1개 runtime/export row에
  time-axis field가 materialize됨

우선순위:

- `P1`

---

### MF4 Status

- implemented
- outputs:
  - [surface_time_axis_contract_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/surface_time_axis_contract_latest.csv)
  - [surface_time_axis_contract_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/surface_time_axis_contract_latest.json)
  - [surface_time_axis_contract_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/surface_time_axis_contract_latest.md)

## MF5. Initial Entry Surface Split

목적:

- 기존 single entry path에서
  `initial_entry_surface`를 따로 추출

대상 파일:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [entry_candidate_bridge.py](/C:/Users\bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)

구현 포인트:

- baseline first-entry
- probe promotion
- breakout initial entry
- semantic/state25 bounded hint

현재 상태:

- 구현 완료
- [entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)에서
  `entry_candidate_surface_family/state`,
  `breakout_candidate_surface_family/state`를 materialize
- [entry_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py),
  [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)에
  runtime row append 컬럼 반영 완료
- `2026-04-09 01:58 KST` 재기동 후
  [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
  fresh row에서
  `XAUUSD -> follow_through_surface / pullback_resume`,
  `BTCUSD -> initial_entry_surface / timing_better_entry`
  실제 기록 확인

완료 기준:

- entry latest row에
  `entry_surface_type = initial_entry`
  같은 필드가 남음

완료 판정:

- 충족

우선순위:

- `P1`

---

## MF6. Distribution-Based Promotion Gate Baseline

목적:

- 절대 score만으로 promotion하지 않고
  같은 market-family / scene / surface 안에서의 상대 위치를 같이 보게 함

핵심:

- `score > x` 단독 구조 축소
- `cluster-relative percentile`
- `market-family-relative rank`

완료 기준:

- 최소 1개 bounded gate에서
  절대 threshold + 상대 분포 기반 판단이 같이 남음

우선순위:

- `P1`

상태:

- implemented
- absolute threshold + cluster-relative percentile + market-family-relative percentile
  baseline 산출물 구현 완료
- outputs:
  - [distribution_promotion_gate_baseline_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/distribution_promotion_gate_baseline_latest.csv)
  - [distribution_promotion_gate_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/distribution_promotion_gate_baseline_latest.json)
  - [distribution_promotion_gate_baseline_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/distribution_promotion_gate_baseline_latest.md)

---

## MF7. XAU Follow-Through Bounded Bridge

목적:

- XAU의 좋은 initial entry 이후 구간을
  전부 `outer_band_guard + probe_not_promoted`로 눌러버리는 문제 완화
- 동시에 XAU 하락 continuation 구간을
  SELL-specific bootstrap이 아니라
  이후 `UP/DOWN` 대칭 continuation owner로 확장 가능한 형태로 만든다

대상 파일:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)

조건 예:

- scene family가 XAU second-support / outer-band reversal 계열
- `blocked_by = outer_band_guard`
- `same_side_barrier`가 extreme이 아님
- `wait_confirm_gap`가 너무 나쁘지 않음
- `structural_relief_applied = true` 또는 follow-through supportive

행동:

- `WAIT_MORE` 대신
  `PROBE_ENTRY` 또는 bounded small lot entry 후보

현재 상태:

- 1차 구현 완료
- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)에
  `bounded_xau_outer_band_followthrough_probe`
  및 `xau_outer_band_follow_through` relief 추가
- 조건은 `outer_band_guard` 전부 완화가 아니라
  supportive probe plan + bounded barrier window에서만 허용
- 재기동 후
  [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
  fresh XAU rows에
  `follow_through_surface / pullback_resume`
  surface tagging이 실제 반영됨
- 아직 live recent slice에서는
  `outer_band_guard`가 주 blocker로 남아 있으므로
  MF7은 "bridge 설치 완료, 체감 개선 관측 중" 상태
- 추가 bootstrap 구현:
  - XAU lower-reversal / outer-band BUY family에서
    `countertrend_continuation_signal_v1`
    및 `countertrend_candidate_action = SELL`
    생성 경로 추가
  - 단, 이 경로는 최종 SELL 전용 owner가 아니라
    추후 `DOWN_*` 상태로 일반화할 bootstrap으로만 취급

완료 기준:

- XAU recent slice에서
  `outer_band_guard + probe_not_promoted` 독점이 줄어듦
- 최소 일부가 `PROBE_ENTRY` 또는 equivalent bounded path로 승격

완료 판정:

- 부분 충족
- bounded bridge는 운영 경로에 반영됨
- 다음 관측 창에서 `PROBE_ENTRY`/bounded 승격 비율 재확인 필요
- `countertrend_continuation_*` fresh runtime materialization 확인 필요
- SELL-specific bootstrap을 `direction-agnostic` 상태기계로 확장해야 함

우선순위:

- `P1`

---

## MF7A. Fresh Countertrend Materialization Check

목적:

- 현재 추가된
  `countertrend_continuation_*`
  및
  `countertrend_candidate_action = SELL`
  이 실제 fresh runtime row에 남는지 확인

필수 확인 필드:

- `countertrend_continuation_enabled`
- `countertrend_continuation_state`
- `countertrend_continuation_action`
- `countertrend_continuation_confidence`
- `countertrend_candidate_action`
- `countertrend_candidate_confidence`

완료 기준:

- fresh XAU row에서 위 필드가 실제 append됨
- lower-reversal / outer-band family 장면과 주로 정렬됨
- 다른 family로 과도하게 leak되지 않음

우선순위:

- `P1`

상태:

- implemented
- outputs:
  - [countertrend_materialization_check_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/countertrend_materialization_check_latest.csv)
  - [countertrend_materialization_check_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/countertrend_materialization_check_latest.json)
  - [countertrend_materialization_check_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/countertrend_materialization_check_latest.md)
- current snapshot:
  - `field_presence_ok = true`
  - `recent_row_count = 4`
  - `symbol_row_count = 2`
  - `target_family_row_count = 0`
  - `countertrend_enabled_count = 0`
  - `countertrend_candidate_sell_count = 0`
  - `recommended_next_action = await_fresh_xau_lower_reversal_rows`

완료 판정:

- 부분 충족
- fresh runtime row에 countertrend scalar 필드가 실제 존재함은 확인
- 하지만 현재 fresh XAU slice는 `range_upper_reversal_sell`만 포함하고 있어
  target family materialization은 아직 실관측 전
  즉 현재 단계 해석은
  `배선/스키마는 정상, target-family fresh row 대기`
  이다

---

## MF7B. Direction-Agnostic Evidence Split

목적:

- current XAU SELL bootstrap을
  direction-agnostic continuation contract로 일반화하기 위해
  evidence를 dual-write로 분리

필수 evidence field:

- `anti_long_score`
- `anti_short_score`
- `pro_up_score`
- `pro_down_score`

원칙:

- 기존
  `countertrend_continuation_*`
  필드는 유지
- 새 evidence는 parallel dual-write로 추가
- `anti-buy != pro-sell`
  원칙을 코드/로그에 반영

완료 기준:

- fresh/runtime or exported row에
  4개 evidence score가 같이 남음
- current XAU down path를
  `anti_long + pro_down`
  조합으로 설명할 수 있음

우선순위:

- `P1`

상태:

- implemented
- live XAU `range_upper_reversal_sell` recent rows에서
  `UP_PROBE` materialization 확인

---

## MF7C. Directional State Machine

목적:

- SELL-specific candidate를
  direction-independent 상태기계로 승격

필수 상태:

- `DO_NOTHING`
- `UP_WATCH`
- `DOWN_WATCH`
- `UP_PROBE`
- `DOWN_PROBE`
- `UP_ENTER`
- `DOWN_ENTER`

원칙:

- `WATCH`는 관찰 상태
- `PROBE`부터 bounded execution 후보
- `ENTER`는 마지막 bounded live 단계
- `BUY/SELL` 실행 변환은 state machine 뒤에서만 수행

완료 기준:

- 최근 row/log/latest artifact에
  최소 `DOWN_WATCH` 또는 `DOWN_PROBE`가 materialize됨
- 현재 XAU bootstrap이
  `SELL candidate`
  가 아니라
  `DOWN_* state`
  로 표현됨

우선순위:

- `P1`

상태:

- pending

---

## MF7D. DOWN Bootstrap Validation

목적:

- 현재 XAU 하락 continuation bootstrap을
  `DOWN_*` 상태기계에서 먼저 안정화

핵심 검증:

- `anti_long strong + pro_down weak -> DOWN_WATCH`
- `anti_long strong + pro_down medium -> DOWN_PROBE`
- 충분한 continuation persistence + guard pass -> `DOWN_ENTER`

완료 기준:

- fresh runtime에서
  XAU down continuation 장면이
  `DOWN_WATCH / DOWN_PROBE`
  로 의미 있게 분포를 가짐
- false escalation이 관리 가능

우선순위:

- `P1`

상태:

- pending

---

## MF7E. UP Symmetry Extension

목적:

- current down-only bootstrap을
  상승 continuation까지 확장

필수 대칭 피처 예:

- `recent_higher_high_count`
- `recent_higher_low_count`
- `bb20_mid_reject_failed`
- `same_side_up_follow_through_strength`
- `break_above_local_resistance_recent`

완료 기준:

- `UP_WATCH / UP_PROBE`
  상태가 최소 preview/logging 레벨에서 materialize됨
- continuation 구조가 하락 편향 전용으로 고정되지 않음

우선순위:

- `P2`

상태:

- pending

---

## MF8. BTC Middle-Anchor Observe Relief

목적:

- BTC의 `middle_sr_anchor_guard`와 observe 정체 완화

대상 파일:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)

구현 포인트:

- already-added bounded middle anchor probe를
  BTC family 기준으로 재계량
- `observe -> probe -> ready`
  전환 조건을 더 명확히 남김

완료 기준:

- BTC recent slice에서
  `middle_sr_anchor_guard` 비중 감소
- `probe_not_promoted` 일부가 bounded probe로 이동

우선순위:

- `P1`

---

## MF9. NAS Conflict Observe Decomposition

목적:

- NAS의 `conflict_box_*` 계열 observe를
  한 덩어리 wait에서 분리

대상 파일:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- conflict/observe helper

구현 포인트:

- conflict를 전부 `observe_state_wait`로 두지 않음
- `WATCH`
- `PROBE`
- `HARD_WAIT`
로 나누기

완료 기준:

- NAS recent slice에서 `observe_state_wait` 독점이 깨짐
- 최소 일부가 `WATCH` 또는 `PROBE`로 materialize됨

우선순위:

- `P1`

---

## MF10. Follow-Through Surface Materialization

목적:

- initial entry와 분리된
  `follow_through_surface`를 실제 데이터 필드로 만든다

출력 필드 예:

- `follow_through_surface_state`
- `follow_through_candidate_action`
- `follow_through_confidence`
- `follow_through_blocker`

완료 기준:

- recent rows에서
  `follow_through` 관련 분포가 보임
- XAU/NAS/BTC가 같은 규칙으로만 취급되지 않음

우선순위:

- `P1`

---

## MF11. Continuation Hold / Runner Preservation Split

목적:

- exit를 전부 보호청산 언어로 보지 않고
  `continuation_hold_surface`를 분리

대상 파일:

- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
- [exit_execution_orchestrator.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_execution_orchestrator.py)

구현 포인트:

- `Target`, `Lock Exit`, `profit_giveback`이
  곧바로 full exit만 뜻하지 않도록 분리
- 최소 아래 중 일부 도입:
  - `partial_then_runner_hold`
  - `runner_lock_only`
  - `runner_continue`
  - `partial_close_then_rearm`

현재 상태:

- 1차 구현 완료
- [exit_runner_preservation_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_runner_preservation_policy.py)
  추가
- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
  에서 managed full exit 직전
  `Target / Lock Exit / adverse_recheck_lock`
  을 `partial_then_runner_hold` 또는 `runner_lock_only`로 강등 가능
- 현재 bounded 조건:
  - peak profit이 충분히 있고
  - giveback이 아직 moderate이며
  - hold strength가 lock에 비해 완전히 밀리지 않고
  - favorable move가 continuation 구간으로 읽힐 때만
  full exit 대신 runner 보존 분기 허용
- `2026-04-09 02:08 KST` 코어 재기동으로
  최신 runtime에 로드 완료
- 관측 산출물 추가:
  - [exit_surface_observation_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/exit_surface_observation_latest.json)
  - 현재 `runner_preservation_total_count = 0`
  - 즉 runner 보존 분기는 runtime에 올라왔지만
    아직 실제 live/open/closed 로그에는 한 번도 잡히지 않음

완료 기준:

- 좋은 initial entry 뒤
  full exit 외의 continuation action이 실제 로그에 생김

완료 판정:

- 부분 충족
- runtime 분기와 helper는 구현/로드 완료
- 다음 관측 창에서
  `partial_then_runner_hold`, `runner_lock_only`
  가 실제 open trade/exit live metrics에 잡히는지 확인 필요

우선순위:

- `P1`

---

## MF12. Protective Exit Surface Split

목적:

- 진짜 위험 청산과
  단순 수익 보호를 분리

필수 상태 예:

- `EXIT_PROTECT`
- `LOCK_PROFIT`
- `PARTIAL_REDUCE`
- `HOLD_RUNNER`

현재 상태:

- 1차 구현 완료
- [exit_surface_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_surface_state_policy.py)
  추가
- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
  에서
  - recovery / managed exit -> `EXIT_PROTECT`, `LOCK_PROFIT`
  - pre-exit partial / runner preservation -> `PARTIAL_REDUCE`, `HOLD_RUNNER`
  로 정규화
- 관측 빌더 추가:
  - [exit_surface_observation.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_surface_observation.py)
  - [build_exit_surface_observation.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_exit_surface_observation.py)
  - [exit_surface_observation_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/exit_surface_observation_latest.json)
- 최신 관측:
  - `status = await_live_runner_preservation`
  - `protective_surface_total_count = 1`
  - `surface_state_counts = {EXIT_PROTECT: 1}`
  - 즉 protective split은 실제 최근 로그에서 최소 1건 잡혔고,
    continuation hold 쪽은 아직 실관측 대기 상태

완료 기준:

- exit latest 산출물에서
  full exit 하나만이 아니라 surface state가 분리됨

완료 판정:

- 충족
- protective vs continuation state를 구분하는 helper/관측 산출물 존재
- live 최근 산출물에서 `EXIT_PROTECT` 실관측 확인

우선순위:

- `P2`

---

## MF13. Failure Label Harvest

목적:

- 성공 케이스뿐 아니라 실패 케이스를 독립 라벨로 축적

라벨 예:

- `failed_follow_through`
- `false_breakout`
- `early_exit_regret`
- `late_entry_chase_fail`
- `missed_good_wait_release`

완료 기준:

- 최소 3개 실패 라벨이 csv/json surface로 누적됨

우선순위:

- `P1`

---

### MF13 Status

- implemented
- outputs:
  - [failure_label_harvest_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/failure_label_harvest_latest.csv)
  - [failure_label_harvest_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/failure_label_harvest_latest.json)
  - [failure_label_harvest_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/failure_label_harvest_latest.md)
- current snapshot:
  - `confirmed_row_count = 25`
  - `candidate_row_count = 188`
  - `failure_label_counts = {"early_exit_regret": 3, "failed_follow_through": 110, "false_breakout": 44, "late_entry_chase_fail": 2, "missed_good_wait_release": 54}`
  - `recommended_next_action = extend_mf7_follow_through_bridge`

---

## MF14. Market Adapter Layer

목적:

- 시장별 모델을 완전 분리하지 않고
  공통 surface + market adapter 구조를 도입

원칙:

- 공통 모델 유지
- `market_family` feature 또는 bounded adapter 추가
- NAS/BTC/XAU 모델 완전 분리 금지

완료 기준:

- spec/feature contract에 `market_family adapter`가 공식 반영됨

우선순위:

- `P2`

상태:

- implemented
- 공통 surface 위에 `market_family` adapter contract를 공식 반영
- outputs:
  - [market_adapter_layer_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_adapter_layer_latest.csv)
  - [market_adapter_layer_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_adapter_layer_latest.json)
  - [market_adapter_layer_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_adapter_layer_latest.md)

---

## MF15. Multi-Surface Preview Dataset Export

목적:

- 단일 타점 학습이 아니라
  surface별 preview dataset을 만든다

출력 예:

- `initial_entry_dataset`
- `follow_through_dataset`
- `continuation_hold_dataset`
- `protective_exit_dataset`

완료 기준:

- 최소 2개 이상 surface dataset이 parquet/csv로 export됨

우선순위:

- `P2`

---

## MF16. Symbol-Surface Preview Evaluation

목적:

- 시장별/상황별로 모델이 다른 행동을 배우는지 평가

필수 평가 축:

- symbol별
- surface별
- underfire / overfire
- follow-through miss
- early exit / runner preservation

완료 기준:

- `single score improved`가 아니라
  `symbol-surface별로 어떤 behavior가 개선됐는지`가 보임

우선순위:

- `P2`

---

## MF17. Bounded Rollout

목적:

- 검증된 surface만 bounded live에 연결

원칙:

- initial entry와 follow-through는 분리 rollout
- exit continuation hold는 더 보수적으로 rollout
- market-family allowlist 유지

완료 기준:

- symbol-surface 단위 bounded rollout manifest 존재

우선순위:

- `P3`

---

## 지금 바로 다음 우선순위

1. `MF7A fresh XAU lower-reversal observation refresh`
2. `MF7B Direction-Agnostic Evidence Split`
3. `MF7C Directional State Machine`
4. `MF6 Distribution-Based Promotion Gate Baseline`
5. `MF14 Market Adapter Layer`

이 순서가 맞는 이유:

- 시장별 병목 분리는 이미 MF1에서 고정됨
- current XAU continuation bootstrap이
  SELL-specific으로 굳기 전에
  direction-agnostic migration 원칙을 먼저 반영해야 함
- fresh runtime materialization check는 구현됐고
  현재는 `target-family fresh row`가 아직 부족하다는 사실까지 확인됨
- 따라서 다음 단계는
  fresh lower-reversal 관측을 갱신하면서
  parallel dual-write 설계를 준비하는 것
- `anti-buy/pro-sell`을
  `anti_long/anti_short/pro_up/pro_down`
  으로 분리해야
  상승 continuation까지 같은 구조로 확장 가능함
- MF5 runtime split과 MF7 bounded bridge는 이미 운영 경로에 반영됨
- MF11 runner preservation도 1차 구현과 runtime load까지 완료됨
- MF12 protective split까지 끝났고 MF13 failure harvest도 구현되어
  이제 다음 큰 축은
  `direction-agnostic continuation state machine`
  을 먼저 닫은 뒤
  분포 기반 gate와 market adapter를 얹는 것

---

## 한 줄 결론

다음 단계는
`조금 더 잘 들어가게 만들자`가 아니다.

> NAS / BTC / XAU를 각기 다른 문제로 보고,
> initial 진입, follow-through, runner 보존, 보호청산을
> 각기 다른 목적 함수와 시간축을 가진 surface로 분리해,
> do-nothing EV와 실패 라벨까지 같이 배우게 만드는 단계

이 로드맵이 그 작업의 실제 구현 순서를 정의한다.
