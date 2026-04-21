# Current Checkpoint Improvement Watch Remaining Roadmap

## 목적

이 문서는 현재 CFD 프로젝트에서 `PA / SA / Telegram control plane`을 어떤 순서로 이어 붙여야 하는지, 그리고 지금 시점에서 실제로 남은 일이 무엇인지 정리한 잔여 로드맵이다.

특히 아래 질문에 답하는 것이 목적이다.

1. `PA8`은 어디까지 끝났고 무엇이 아직 남았는가
2. `PA9`는 언제 시작해야 하는가
3. `SA8`은 왜 아직 보류인가
4. `checkpoint_improvement_watch`는 이들 사이를 어떻게 연결해야 하는가

이 문서는 아래 문서를 함께 읽는 것을 전제로 한다.

- [current_all_in_one_system_master_playbook_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_all_in_one_system_master_playbook_ko.md)
- [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)
- [current_pre_orchestration_build_inventory_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_build_inventory_ko.md)
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md)
- [current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md)
- [current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md)
- [current_c4_checkpoint_improvement_recovery_health_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c4_checkpoint_improvement_recovery_health_detailed_plan_ko.md)
- [current_c5_checkpoint_improvement_reconcile_rules_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c5_checkpoint_improvement_reconcile_rules_detailed_plan_ko.md)
- [current_checkpoint_improvement_orchestrator_watch_runner_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_orchestrator_watch_runner_detailed_plan_ko.md)
- [current_path_aware_checkpoint_decision_implementation_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_roadmap_ko.md)
- [current_pa789_roadmap_realignment_v1_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pa789_roadmap_realignment_v1_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)

권장 읽기 순서는 아래와 같다.

1. 전체 구조와 현재 blocker는 [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)에서 먼저 본다.
2. `PA8 / PA9 / SA` 잔여 작업은 이 문서에서 확인한다.
3. 실제 조율 원칙과 구현 세부는 [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)와 개별 `A/B/C` 문서로 내려간다.

---

## 지금 상태 한눈에 보기

현재 구현 상태를 아주 짧게 요약하면 아래다.

- `PA0 ~ PA7`
  - 구조 구축은 사실상 완료
  - review queue와 packet 재정렬도 거의 닫힘
- `PA8`
  - action-only bounded canary 체인은 구축 완료
  - `NAS100 / BTCUSD / XAUUSD` 모두 canary active state까지 올라감
  - 하지만 live first-window가 아직 없어서 closeout은 대기
- `PA9`
  - 아직 본격 시작 전
  - PA8 closeout 결과를 받아 handoff packet을 만들 단계가 남아 있음
- `SA`
  - `SA0 ~ SA5.8`까지 구조/preview/log-only 체인은 형성됨
  - 하지만 `SA8 live adoption`은 아직 아님

즉 지금은

`PA8 운영 관찰 대기 + PA9 준비 전 + SA8 보류`

상태로 보는 것이 정확하다.

---

## 현재 artifact 기준 해석

최근 상태판을 해석하면 아래와 같다.

### PA8 canary refresh board

기준:

- [checkpoint_pa8_canary_refresh_board_latest.json](/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_pa8_canary_refresh_board_latest.json)

핵심:

- `active_symbol_count = 3`
- `live_observation_ready_count = 0`
- `closeout_state_counts = {"HOLD_CLOSEOUT_PENDING_LIVE_WINDOW": 3}`

해석:

- 세 심볼 모두 action-only canary는 켜져 있다
- 하지만 세 심볼 모두 아직 post-activation live row가 없다
- 따라서 closeout은 아직 내리면 안 된다

### PA8 historical replay board

기준:

- [checkpoint_pa8_historical_replay_board_latest.json](/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_pa8_historical_replay_board_latest.json)

현재 값은 replay window가 `0`이라 supporting evidence로도 약하다.

해석:

- historical replay는 구조는 연결됐지만
- 현재 recent scope 기준으론 sample floor를 못 채웠다
- 즉 이 board는 `있으면 보조 근거`, 없다고 해서 PA8 구조가 실패한 것은 아니다

### PA7 / PA8 governance packet

기준:

- [checkpoint_pa78_review_packet_latest.json](/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_pa78_review_packet_latest.json)

핵심:

- `pa7_review_state = HOLD_REVIEW_PACKET`
- `pa8_review_state = HOLD_ACTION_BASELINE_ALIGNMENT`
- `scene_bias_review_state = HOLD_SCENE_ALIGNMENT`

해석:

- recent 400 row 기준 packet은 아직 보수적으로 HOLD를 낸다
- 이 값은 `운영 지배 packet`으로 보되, canary active state와 같은 층위로 혼동하면 안 된다
- 즉 governance packet과 canary runtime board는 서로 다른 목적의 board다

### SA disagreement / preview

기준:

- [checkpoint_scene_disagreement_audit_latest.json](/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_scene_disagreement_audit_latest.json)
- [checkpoint_trend_exhaustion_scene_bias_preview_latest.json](/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_trend_exhaustion_scene_bias_preview_latest.json)

핵심:

- `high_conf_scene_disagreement_count = 119`
- `expected_action_alignment_rate = 0.882353`
- `preview_changed_row_count = 2`
- `improved_row_count = 1`
- `worsened_row_count = 1`

해석:

- scene candidate는 아직 log-only가 맞다
- `trend_exhaustion` preview는 아직 sample이 너무 얇고 한 건은 worsened다
- 따라서 SA는 아직 자동 adoption 대상으로 올리면 안 된다

---

## 남은 로드맵

## PA8 남은 것

### 1. live first-window accumulation

해야 하는 일:

- 장이 열리고 post-activation live row가 쌓이는지 감시
- 심볼별 first-window observation refresh
- seed reference가 아니라 실제 live window 기준 수치 확보

완료 조건:

- 각 active symbol에 대해 `live_observation_ready = true`
- `observed_window_row_count`가 최소 floor를 넘음

### 2. closeout decision

해야 하는 일:

- `hold_precision`
- `runtime_proxy_match_rate`
- `partial_then_hold_quality`
- `new worsened rows`

를 live window 기준으로 다시 계산

완료 조건:

- 각 symbol에 대해 `continue / rollback / narrow / promote-ready` 중 하나 결정

### 3. rollback packet 검증

해야 하는 일:

- rollback trigger가 live window에서도 예상대로 작동하는지 확인
- seed-only 상태에서 과잉 rollback이 일어나지 않는지 검증

완료 조건:

- false rollback 없음
- rollback trigger 설명 가능

---

## PA9 남은 것

PA9은 아직 착수 전이지만, 이제 무엇을 만들지 명확히 정리할 시점이다.

### PA9의 역할

- PA8 closeout이 끝난 action-only baseline을 운영 handoff 형태로 정리
- canary 결과를 요약하여 `이 scope를 계속 유지할지`, `확대할지`, `종료할지` 결정
- scene bias는 아직 포함하지 않는다

### PA9에서 만들어야 할 것

- `pa9_action_baseline_handoff_packet`
- `pa9_canary_result_summary`
- `pa9_rollout_scope_registry`
- `pa9_manual_review_gate`

### PA9 시작 조건

아래가 모두 Yes일 때 시작한다.

1. 최소 1개 symbol에서 live first-window closeout이 완료되었는가
2. rollback false positive가 없는가
3. scope가 아주 좁은 bounded canary로 유지되었는가
4. scene bias와 분리된 action-only handoff로 설명 가능한가

---

## SA 남은 것

### 지금 당장 하지 말아야 하는 것

- `SA8` live adoption
- scene bias automatic promotion
- trend_exhaustion live bias activation

### 지금 계속 해야 하는 것

- log-only bridge 유지
- disagreement audit 주기 갱신
- trend_exhaustion preview-only 유지
- overpull label patch 후보 관찰

### SA8 시작 조건

아래가 모두 Yes일 때만 고려한다.

1. `high_conf_scene_disagreement_count`가 안정적으로 더 낮아지는가
2. `expected_action_alignment_rate`가 action-only review 기준을 충족하는가
3. preview changed sample이 수 건이 아니라 지속적 표본으로 쌓였는가
4. worsened row 없이 설명 가능한 narrow scope가 존재하는가

즉 SA는 현재도

`preview-only / log-only / no live adoption`

이 canonical 상태다.

---

## checkpoint_improvement_watch가 맡아야 하는 일

이제 남은 로드맵을 실제로 굴리려면 `checkpoint_improvement_watch`가 아래 4계층을 조율해야 한다.

단, orchestration 관점의 상세 책임 분해와 `watch != executor` 경계는 [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)를 canonical 기준으로 본다.

### 1. row observer

역할:

- raw row 증가 감지
- recent window 기준 delta 계산
- fast refresh 필요 여부 결정

### 2. light refresh scheduler

권장 주기:

- `3~5분` 또는 `25~50 row`

역할:

- action eval refresh
- live runner watch refresh
- management snapshot refresh
- PA8 canary refresh board refresh
- master board 요약 갱신

### 3. heavy review scheduler

권장 주기:

- `15~30분` 또는 `100~300 row`

역할:

- PA7 review processor refresh
- PA78 review packet refresh
- scene disagreement audit refresh
- scene bias preview refresh

주의:

- heavy review는 hot path와 완전히 분리한다
- timeout/중복 실행 방지를 위해 lock이 필요하다

### 4. apply / governance scheduler

권장 주기:

- `1~3분`

역할:

- PA8 canary state refresh
- first-window observation refresh
- rollback trigger refresh
- closeout candidate 생성
- Telegram approval queue 반영

---

## master board는 어떻게 설계해야 하는가

추천 산출물:

- `data/analysis/shadow_auto/checkpoint_improvement_master_board_latest.json`
- `data/analysis/shadow_auto/checkpoint_improvement_master_board_latest.md`

여기엔 최소 아래가 들어가야 한다.

### Fast state

- raw row latest ts
- row delta
- light refresh last run
- heavy refresh last run

### PA state

- `pa7_review_state`
- `pa8_review_state`
- symbol별 canary closeout state
- rollback pending 여부

### SA state

- `scene_bias_review_state`
- disagreement count
- preview changed / improved / worsened

### Telegram state

- pending approval count
- latest activation review request
- latest rollback review request
- latest closeout review request

### 추가 필수 필드

최소한 아래는 같이 보여야 운영상 막히지 않는다.

- `blocking_reason`
- `next_required_action`
- `oldest_pending_approval_age_sec`
- `last_successful_apply_ts`
- `degraded_components`
- `reconcile_backlog_count`

---

## Telegram과 어떻게 연결해야 하는가

`checkpoint_improvement_watch`는 텔레그램을 직접 구현 세부와 섞지 말고, 승인 요청 이벤트만 발행해야 한다.

즉 구조는 아래처럼 간다.

```text
checkpoint_improvement_watch
  -> review needed 판단
  -> approval event 생성
  -> TelegramNotificationHub로 전달
  -> operator approves / holds / rejects
  -> TelegramUpdatePoller callback 수신
  -> state store 갱신
  -> watch가 다음 루프에서 반영
```

이 방식이 좋은 이유는 아래와 같다.

- watch가 Telegram API에 직접 묶이지 않는다
- approval과 apply가 분리된다
- 재시도/중복 클릭/timeout 처리가 쉬워진다

---

## 다른 스레드에서 바로 구현할 때 우선순위

다음 구현 스레드에선 아래 `A/B/C` 순서를 권장한다.

### T0. foundation v2 정렬

먼저 문서 기준을 아래처럼 다시 읽는다.

- `watch first tick`을 최대한 빨리 돌린다
- `ApprovalLoop / ApplyExecutor`는 병렬로 붙인다
- `Master Board / Reconcile`은 합류 후 안정화로 미룬다

상세 순서는 [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)를 따른다.

### T1. Track A 시작

먼저 구축:

- `SystemStateManager v0`
- `EventBus v0`
- `cycle definition`

### T2. checkpoint_improvement_watch first tick

만들 파일:

- [backend/services/checkpoint_improvement_watch.py](/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_watch.py)
- [scripts/checkpoint_improvement_watch.py](/Users/bhs33/Desktop/project/cfd/scripts/checkpoint_improvement_watch.py)

해야 하는 일:

- row observer
- `light_cycle`
- fast refresh 호출
- state update

### T3. Track B 병렬 연결

해야 하는 일:

- `TelegramStateStore` contract 정렬
- activation review request
- rollback review request
- closeout review request
- `ApprovalLoop`
- `ApplyExecutor`

주의:

- 기존 `PA8 Governance Contract`는 이 단계에 흡수해서 읽는 것이 맞다

### T4. governance + live closeout support

해야 하는 일:

- `governance_cycle`
- PA8 canary refresh 호출
- live first-window ready 감지
- closeout candidate 자동 생성
- approval queue에 publish

### T5. 합류 후 안정화

해야 하는 일:

- `Master Board`
- `heavy_cycle`
- `reconcile_cycle` 자리 확보
- `OrchestratorLoop`

### T6. PA9 handoff packet 설계

해야 하는 일:

- action-only baseline handoff packet
- rollout scope registry
- manual review gate

---

## 지금 시점의 한 줄 권장안

지금 가장 좋은 다음 행동은 아래다.

1. `checkpoint_improvement_watch`를 먼저 만든다
2. 이 watch가 `light / heavy / apply`를 분리해서 조율하게 한다
3. PA8은 live window가 생길 때까지 `canary active + closeout pending`으로 유지한다
4. PA9는 PA8 closeout 이후에 시작한다
5. SA8은 계속 preview-only로 둔다

즉 다음 스레드의 중심축은

`Telegram card 구현`만이 아니라
`checkpoint_improvement_watch + Telegram approval control plane`

이라고 보는 게 맞다.
