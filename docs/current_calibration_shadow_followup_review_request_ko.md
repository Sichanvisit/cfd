# Calibration / Shadow Follow-up External Review Request

## 목적

이 문서는 CFD 자동매매 프로젝트에서 이전에 받은 조언을 실제 구조/코드/운영으로 어떻게 반영했는지 정리하고,
현재 어디까지 왔는지와 다음 병목이 무엇인지 설명한 뒤 추가 조언을 받기 위한 요청서다.

이번 요청의 핵심은 단순 상태 요약이 아니다.

- 어떤 조언을 받았고
- 무엇을 실제로 구현했으며
- 그 결과 무엇이 좋아졌고
- 지금은 어디서 막혀 있는지
- 다음 우선순위를 어디에 둬야 하는지

를 한 번에 보이게 하는 것이 목적이다.

---

## 1. 전체 구조와 현재 단계

현재 시스템은 크게 세 층으로 본다.

### 1) Live Baseline Execution

- 기존 execution engine이 실제 enter / wait / exit를 수행한다.
- 실제 돈이 걸리는 live authority는 아직 baseline 쪽에만 있다.

### 2) Manual Truth Calibration Layer

- manual truth answer key
- manual vs heuristic comparison
- mismatch family ranking
- correction loop
- current-rich promotion gate / workflow / trace
- promotion discipline / approval log / post-promotion audit

즉 현재 프로젝트는 owner를 더 만드는 단계보다,
manual truth를 기준으로 heuristic owner를 교정하는 calibration phase에 들어와 있다.

### 3) Shadow Auto Layer

- shadow candidate bridge
- shadow_vs_baseline storage
- semantic shadow training bridge / preview corpus
- preview semantic shadow bundle
- offline runtime activation demo
- execution-level preview evaluation
- SA5 shadow correction loop
- SA6 auto decision / bounded apply recommendation

즉 바로 live 자동화가 아니라,
먼저 shadow에서 자동으로 돌려보고 검증된 것만 bounded review로 올리는 단계다.

---

## 2. 이전에 받은 핵심 조언

### 조언 A. manual truth는 replay reconstruction이 아니라 standalone answer key다

의미:

- actual replay matching 자체를 성공 조건으로 보지 말 것
- training seed로 바로 쓰지 말 것
- heuristic 판단을 교정하는 상위 기준층으로 사용할 것

### 조언 B. mismatch를 발견해도 즉시 rule edit 하지 말고
`correction-worthy / freeze-worthy / hold-for-more-truth`로 나눌 것

의미:

- evidence quality가 낮으면 수정 대신 hold/freeze가 맞다
- `wrong_failed_wait` 같은 family를 바로 failed_wait 쪽으로 밀지 말 것

### 조언 C. current-rich draft와 canonical을 분리하고
promotion discipline을 운영 객체로 만들 것

의미:

- draft 수집
- review workflow
- review trace
- validated / canonical 분리
- post-promotion audit

까지 있어야 corpus 오염을 막을 수 있다

### 조언 D. comparison을 단순 리포트가 아니라 우선순위 결정 표면으로 만들 것

의미:

- family ranking
- bias sandbox
- patch draft
- correction loop

까지 이어져야 실제 운영 의사결정에 쓸 수 있다

### 조언 E. 자동화는 바로 live auto-edit가 아니라 shadow + bounded review로 갈 것

의미:

- baseline은 그대로 두고
- shadow에서 자동 실험을 먼저 수행하고
- preview/offline 검증이 쌓인 뒤에만 bounded candidate로 올릴 것

---

## 3. 각 조언을 실제로 어떻게 반영했는가

### 3-1. manual truth를 answer key로 고정

적용 방식:

- manual truth를 `episode-first / wait-first` 구조로 유지
- canonical corpus와 current-rich draft를 분리
- actual replay reconstruction이 아니라 answer key layer로 해석

현재 상태:

- canonical corpus rows: `106`
- symbol distribution:
  - `BTCUSD = 36`
  - `NAS100 = 35`
  - `XAUUSD = 35`

관련 파일:

- [manual_wait_teacher_annotations.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_wait_teacher_annotations.csv)
- [current_manual_trade_episode_truth_model_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_model_v1_ko.md)

의미:

- manual truth는 더 이상 참고 메모가 아니라 calibration answer key다.

---

### 3-2. comparison을 priority decision surface로 승격

적용 방식:

- match/mismatch만 보는 비교에서
  - correction_worthiness
  - freeze_worthiness
  - rule_change_readiness
  - recommended_next_action
  을 계산하도록 확장
- family ranking / bias sandbox / patch draft / correction loop까지 연결

현재 상태:

- manual episodes: `106`
- heuristic matched rows: `27`
- global detail fallback used rows: `15`
- miss_type counts:
  - `insufficient_heuristic_evidence = 90`
  - `aligned = 13`
  - `wrong_failed_wait_interpretation = 3`
- correction priority tier:
  - 현재 전부 `hold`

관련 파일:

- [manual_vs_heuristic_comparison_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_vs_heuristic_comparison_latest.json)
- [manual_vs_heuristic_family_ranking_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_vs_heuristic_family_ranking_latest.csv)
- [manual_vs_heuristic_patch_draft_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_vs_heuristic_patch_draft_latest.csv)
- [manual_vs_heuristic_correction_runs_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_vs_heuristic_correction_runs_latest.csv)

의미:

- comparison은 이제 "어디를 고칠지 / 얼릴지 / 더 모을지"를 분기하는 운영 표면이다.

---

### 3-3. wrong_failed_wait를 hold / freeze 쪽으로 정리

적용 방식:

- gap-aware audit
- current-rich proxy review
- additional follow-up review

를 통해 즉시 rule patch를 막았다.

현재 상태:

- top family는 여전히 `wrong_failed_wait_interpretation`
- 하지만 disposition은 `collect_more_truth_before_patch`
- correction run first result는 `hold_for_more_truth`

관련 파일:

- [manual_vs_heuristic_wrong_failed_wait_audit_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_vs_heuristic_wrong_failed_wait_audit_latest.csv)
- [manual_current_rich_wrong_failed_wait_review_results_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_current_rich_wrong_failed_wait_review_results_latest.csv)
- [manual_vs_heuristic_correction_runs_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_vs_heuristic_correction_runs_latest.csv)

의미:

- mismatch를 봤다고 바로 patch하지 않고, hold/freeze discipline을 실제 운영에 반영했다.

---

### 3-4. current-rich promotion discipline 구축

적용 방식:

- promotion gate
- review workflow
- review trace
- validated / canonical discipline
- approval log
- post-promotion audit

까지 실제 산출물로 구현했다.

현재 상태:

- promotion discipline rows: `13`
- promotion levels:
  - `draft = 12`
  - `canonical = 1`
- approval events:
  - `promotion_gate_review = 6`
  - `correction_loop_accept_reject = 1`
- first current-rich canonical merge row: `1`
- first post-promotion audit row: `1`
- first post-promotion audit status: `scheduled`

관련 파일:

- [manual_current_rich_promotion_gate_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_current_rich_promotion_gate_latest.csv)
- [manual_current_rich_review_workflow_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_current_rich_review_workflow_latest.csv)
- [manual_current_rich_review_trace_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_current_rich_review_trace_latest.csv)
- [manual_current_rich_promotion_discipline_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_current_rich_promotion_discipline_latest.csv)
- [manual_current_rich_post_promotion_audit_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_current_rich_post_promotion_audit_latest.csv)
- [manual_calibration_approval_log.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_calibration_approval_log.csv)

의미:

- current-rich row는 더 이상 임시 메모가 아니라 `draft -> validated -> canonical` discipline 아래 관리된다.

---

### 3-5. barrier/wait 자동화를 human-gated calibration automation으로 유지

적용 방식:

- `manage_cfd.bat` / calibration watch를 통해
  comparison / ranking / sandbox / patch draft / gate / audit 표면을 자동 갱신
- 그러나 canonical merge와 BCE rule edit는 사람 검토 게이트 유지

관련 파일:

- [manual_truth_calibration_watch.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/manual_truth_calibration_watch.py)
- [manual_truth_calibration_watch_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/manual_truth_calibration/manual_truth_calibration_watch_latest.json)

의미:

- 현재 자동화는 `auto-prepare + auto-prioritize + human-gated review`
- 아직 `auto-edit live system`이 아니다

---

### 3-6. calibration 위에 shadow auto layer 추가

적용 방식:

조언대로 live 자동화를 바로 하지 않고,
shadow preview chain을 실제로 구현했다.

#### (a) training bridge / preview bundle

현재 상태:

- training corpus rows: `180`
- training bridge matched rows: `180 / 180`
- training bridge match rate: `1.0`
- preview bundle trained targets: `3`
- bootstrap status: `preview_bundle_ready`

관련 파일:

- [semantic_shadow_training_corpus_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/semantic_shadow_training_corpus_latest.json)
- [semantic_shadow_training_bridge_adapter_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/semantic_shadow_training_bridge_adapter_latest.json)
- [semantic_shadow_preview_bundle_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/semantic_shadow_preview_bundle_latest.json)
- [semantic_shadow_bundle_bootstrap_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/semantic_shadow_bundle_bootstrap_latest.json)

#### (b) preview runtime activation

현재 상태:

- offline activation demo rows: `64`
- available rows: `64`
- alignment:
  - `aligned = 61`
  - `misaligned = 3`

관련 파일:

- [semantic_shadow_runtime_activation_demo_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/semantic_shadow_runtime_activation_demo_latest.json)

#### (c) execution-level preview evaluation

현재 상태:

- baseline_value_sum = `1.92`
- shadow_value_sum = `1.92`
- value_diff = `0.0`
- drawdown_diff = `0.0`
- manual_alignment_improvement = `0.0`

관련 파일:

- [shadow_execution_evaluation_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_execution_evaluation_latest.json)

#### (d) SA5 / SA6

현재 상태:

- SA5 decision: `hold_for_more_shadow_data`
- SA6 decision: `HOLD`

관련 파일:

- [shadow_correction_loop_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_correction_loop_latest.json)
- [shadow_auto_decision_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_auto_decision_latest.json)

#### (e) preview vs live 경계 명시

현재 activation bridge 상태:

- `preview_bundle_ready = true`
- `activation_bridge_status_counts = {preview_bundle_ready: 5, candidate_precedence_blocked: 1}`
- `effective_runtime_stage_counts = {preview_only: 5, inactive: 1}`

관련 파일:

- [shadow_signal_activation_bridge_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_signal_activation_bridge_latest.json)

의미:

- preview bundle은 실제로 만들어졌고 offline activation도 성공했다
- 그러나 live active model dir는 아직 비워둔 상태다
- 즉 shadow는 실현됐지만 live promotion은 아직 보류 중이다

---

### 3-7. 최신 조언에 따라 edge-creation 블록 추가 구현

최근 추가 조언의 핵심은 다음과 같았다.

- 문제는 "자동화가 부족한 것"이 아니라
- `shadow가 baseline과 충분히 다르게 행동하지 못하거나`,
- 혹은 다르게 행동해도 그것이 `나쁜 divergence`일 수 있다는 점을 먼저 분해해야 한다

이 조언을 받아 아래 블록을 새로 구현했다.

#### (a) SA4b divergence audit

- `overall_divergence_rate = 0.953125`
- recommended_next_action:
  - `redesign_target_mapping_or_thresholds = 4`

파일:

- [shadow_divergence_audit_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_divergence_audit_latest.json)

해석:

- action divergence 자체는 이미 존재한다
- 즉 병목은 "shadow가 전혀 다르게 행동하지 못하는 것"만은 아니다
- 지금은 그 divergence가 mapped action target과 충돌하는 쪽이 더 강하다

#### (b) SA4c threshold sweep

- `row_count = 81`
- recommended_next_action_counts:
  - `reject_or_redesign_targets = 64`
  - `reject_threshold_profile = 17`

파일:

- [shadow_threshold_sweep_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_threshold_sweep_latest.json)

해석:

- threshold를 완화/조정해도 현재는 bounded-positive profile이 잘 나오지 않는다
- 문제는 단순 threshold tuning 하나로 끝나지 않고 target semantics까지 연결된다

#### (c) SA4d target mapping redesign

- `row_count = 15`
- target action counts:
  - `wait_more = 6`
  - `enter_now = 5`
  - `exit_protect = 4`

파일:

- [shadow_target_mapping_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_target_mapping_latest.json)

해석:

- current proxy target과 coarse action target을 분리해서 보기 시작했다
- 이 레이어가 생기면서 "현재 모델이 왜 mapped target과 엇나가는지"를 계산할 수 있게 됐다

#### (d) SA4e dataset bias audit / rebalance

- `audit_row_count = 4`
- `rebalanced_row_count = 180`
- recommended_rebalance_action_counts:
  - `rebuild_targets_from_action_mapping = 3`
  - `expand_scene_coverage = 1`
- rebalance_bucket_counts:
  - `retarget_priority = 175`
  - `balanced_review = 5`

파일:

- [shadow_dataset_bias_audit_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_dataset_bias_audit_latest.json)
- [shadow_rebalanced_training_corpus_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_rebalanced_training_corpus_latest.csv)

해석:

- 현재 preview corpus의 주된 문제는 단순 class imbalance가 아니라
  `target mapping disagreement`가 크게 깔려 있다는 점이다
- 동시에 scene coverage도 매우 편중되어 있다

#### (e) SA5a first divergence run

- selected profile:
  - `threshold::0.55::0.75`
- `divergence_rate = 0.96875`
- `proxy_alignment_improvement = 0.96875`
- `mapped_alignment_improvement = -0.875`
- `value_diff_proxy = -0.15`
- `run_decision = reject_preview_candidate`

파일:

- [shadow_first_divergence_run_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_first_divergence_run_latest.json)

해석:

- 첫 divergence run은 성공적으로 만들었다
- 그러나 그것은 "좋은 첫 divergence"가 아니라 "거절해야 하는 divergence"였다

#### (f) SA6a first non-HOLD decision

- first non-HOLD result:
  - `REJECT`
- bounded_apply_state:
  - `preview_divergence_rejected`

파일:

- [shadow_first_non_hold_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/shadow_first_non_hold_latest.json)

해석:

- 이제 shadow edge-creation 트랙에서도 첫 비-HOLD 결과가 나왔다
- 즉 문제는 더 이상 "판정이 전부 HOLD라서 모른다"가 아니라
  "현재 divergence는 나쁜 divergence라서 reject된다"는 쪽으로 구체화됐다

---

## 4. 현재 퍼센트 해석

### calibration 축

- `manual truth 운영 모델`: `92%`
- `manual vs heuristic calibration`: `90%`
- `current-rich -> canonical 승격 운영`: `88~90%`
- `next mismatch family ranking`: `90%`
- `barrier bias correction`: `85%`
- `manual truth freshness / coverage`: `85~88%`

### shadow 축

- `training bridge / preview corpus`: `88~90%`
- `preview semantic shadow bundle`: `80~85%`
- `shadow runtime activation`: `75%`
- `shadow availability bridge / overlap`: `78~80%`
- `execution-level preview evaluation`: `70%`
- `SA5 shadow correction loop`: `70%`
- `SA6 bounded decision`: `68~70%`

### 전체 축

- `기능 구축 기준`: `82~85%`
- `calibration + shadow 운영 기준`: `75~78%`
- `완전 자율 운영 기준`: `50~55%`

---

## 5. 지금 실제로 된 것 / 일부러 안 한 것

### 이미 된 것

- answer key based calibration system
- mismatch ranking / sandbox / patch draft / correction loop
- promotion gate / workflow / trace / discipline
- first canonical merge
- first post-promotion audit queue
- approval log
- preview shadow training chain
- preview bundle 생성
- offline shadow activation demo
- execution-level preview evaluation
- SA5 / SA6 first loop

### 일부러 아직 안 한 것

- preview bundle을 active live model dir로 승격
- shadow 결과를 live BCE / live execution에 직접 반영
- manual truth를 training seed로 바로 사용

이건 "못 해서"가 아니라 bounded gate를 지키기 위해 의도적으로 안 한 것이다.

---

## 6. 지금 핵심 병목

### 병목 1. shadow가 아직 실제 edge를 만들지 못함

현재 수치:

- `shadow_enter_count = 64`
- `value_diff = 0.0`
- `drawdown_diff = 0.0`
- `manual_alignment_improvement = 0.0`

해석:

> shadow가 "없는 것"이 아니라
> shadow가 baseline과 충분히 다르게 행동하지 못해서 edge를 만들지 못하고 있다.

최근 추가 조언에서는 이 점을 핵심으로 짚었다.

- 지금 문제는 automation completeness 부족이 아니다
- 지금 문제는 `baseline_action != shadow_action`을 의미 있게 만들어내지 못하는 것이다

즉 다음 단계의 핵심은:

- threshold tuning
- target label 명확화
- dataset bias 완화

를 통해 baseline과 실제로 다른 shadow 행동을 만들고,
그 차이가 bounded risk 안에서 유효한지 확인하는 것이다.

### 병목 2. correction loop가 아직 accept/reject를 충분히 만들지 못함

현재:

- correction loop first result = `hold_for_more_truth`
- shadow correction first result = `hold_for_more_shadow_data`

즉 decision discipline은 생겼지만, 명시적 accept/reject 사례가 아직 적다.

### 병목 3. post-promotion audit 누적이 아직 없음

- queue는 열렸지만
- completed audit 결과 누적은 아직 없다

### 병목 4. bounded apply candidate가 아직 없음

- SA6는 존재하지만 current decision은 `HOLD`
- `APPLY_CANDIDATE`가 아직 나오지 않았다

---

## 7. 지금 해야 할 것 / 하지 말아야 할 것

### 지금 해야 할 것

1. preview shadow가 baseline과 실제로 다르게 행동하게 만들기
2. threshold / target / dataset 문제 중 무엇이 더 큰지 분리하기
3. shadow correction loop에서 첫 `accept` 또는 `reject`를 만들기
4. post-promotion audit completed result 1건 이상 쌓기
5. 다음 canonical promotion candidate를 validated pool에서 고르는 기준 강화

### 지금 하지 말아야 할 것

- preview shadow를 live에 바로 올리기
- manual truth를 training/live seed로 바로 섞기
- entry/exit 확장으로 focus 분산하기
- divergence가 없는 상태에서 automation 퍼센트만 더 밀기

---

## 8. 추가 조언을 받고 싶은 질문

1. 지금 프로젝트를 `construction phase`보다 `calibration + shadow preview phase`로 보는 해석이 맞는가?
2. manual truth를 standalone answer key로 유지하는 현재 판단은 계속 맞는가?
3. 현재 병목을 `automation 부족`이 아니라 `shadow가 baseline과 충분히 다르게 행동하지 못하는 문제`로 보는 해석이 맞는가?
4. 다음 우선순위는 무엇이 가장 적절한가?
   - threshold tuning
   - target label 재설계
   - dataset bias 완화
   - preview bundle retrain
   - more shadow evidence accumulation
5. SA5 / SA6 결과가 `hold_for_more_shadow_data -> HOLD`인 현재 상태에서 live promotion 보류는 계속 맞는가?
6. 지금 가장 먼저 깨야 할 것은 무엇인가?
   - `baseline_action == shadow_action`
   - `value_diff = 0`
   - `manual_alignment_improvement = 0`
   - `HOLD only` correction state

---

## 9. 한 줄 요약

이 프로젝트는 이전 조언을 바탕으로:

- manual truth를 answer key로 고정했고
- calibration system을 운영 가능한 수준까지 끌어올렸고
- 그 위에 preview shadow automation까지 실제로 구현했다

하지만 현재 상태는:

> `live 승격`이 아니라 `preview 유지 + 추가 edge 증거 필요`

이다.

즉 지금은

> calibration system은 거의 닫혔고
> shadow는 실제로 돌아가지만
> baseline과 충분히 다르게 행동하지 못해 edge가 없는 상태

라고 보는 것이 맞다.
