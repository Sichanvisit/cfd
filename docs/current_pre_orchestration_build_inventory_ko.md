# Current Pre-Orchestration Build Inventory

## 목적

이 문서는 `checkpoint_improvement_watch`와 `OrchestratorLoop`를 올리기 전에,
무엇이 이미 있고, 무엇은 조금만 보강하면 되고, 무엇은 실제로 새로 만들어야 하는지를
지금 코드 기준으로 다시 나눈 inventory다.

핵심 목적은 아래 세 가지다.

1. 이미 있는 것을 다시 만들지 않기
2. `조금만 보강할 것`과 `진짜 비어 있는 것`을 구분하기
3. `watch first tick`을 늦추지 않는 순서로 착수점 정리하기

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_a1_system_state_manager_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a1_system_state_manager_v0_detailed_plan_ko.md)
- [current_a2_event_bus_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a2_event_bus_v0_detailed_plan_ko.md)
- [current_a3_cycle_definition_v0_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a3_cycle_definition_v0_detailed_plan_ko.md)
- [current_a4_checkpoint_improvement_watch_light_cycle_first_tick_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a4_checkpoint_improvement_watch_light_cycle_first_tick_detailed_plan_ko.md)
- [current_a5_checkpoint_improvement_watch_governance_cycle_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a5_checkpoint_improvement_watch_governance_cycle_detailed_plan_ko.md)
- [current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md)
- [current_b1_telegram_state_store_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b1_telegram_state_store_detailed_plan_ko.md)
- [current_b2_approval_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b2_approval_loop_detailed_plan_ko.md)
- [current_b3_apply_executor_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b3_apply_executor_detailed_plan_ko.md)
- [current_b4_telegram_approval_bridge_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b4_telegram_approval_bridge_detailed_plan_ko.md)
- [current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c1_checkpoint_improvement_master_board_detailed_plan_ko.md)
- [current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c2_checkpoint_improvement_reconcile_placeholder_detailed_plan_ko.md)
- [current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_c3_checkpoint_improvement_orchestrator_loop_detailed_plan_ko.md)
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)

---

## 한 줄 요약

지금은 `오케스트레이션을 위한 새 분석 로직`을 더 만드는 단계가 아니다.

먼저 아래를 준비해야 한다.

- 상위 상태를 들고 있을 것
- approval/apply를 기록하고 집행할 것
- watch가 첫 tick을 돌 수 있을 것
- 실제 운영 데이터가 나온 뒤 board와 reconcile을 안정화할 것

즉

`반장을 앉히기 전에 출석부와 최소 도구함을 먼저 준비하되, 반장 첫 수업은 최대한 빨리 시작하게 하는 단계`

로 보면 된다.

---

## 1. 이미 있는 것

이 항목들은 새로 크게 만들 필요가 없는 재료다.
재사용이 기본이다.

## 1-1. Hot Path

- [main.py](/Users/bhs33/Desktop/project/cfd/main.py)
- [backend/services/path_checkpoint_context.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)

이미 하는 일:

- 실시간 수집
- 기본 action 수행
- checkpoint row 기록

판단:

- `HotPath` 자체는 이미 있다
- 오케스트레이션 이전 단계에서 다시 설계할 대상이 아니다

## 1-2. Fast refresh 재료

- [backend/services/path_checkpoint_analysis_refresh.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_analysis_refresh.py)
- [scripts/build_checkpoint_analysis_refresh_chain.py](/Users/bhs33/Desktop/project/cfd/scripts/build_checkpoint_analysis_refresh_chain.py)

이미 하는 일:

- recent row 기준 fast refresh
- throttle
- lock
- recent-limit 기반 재빌드

판단:

- `light_cycle`의 핵심 재료는 이미 있다
- 부족한 것은 `언제 / 무엇을 / 어떤 skip 조건으로 돌릴지`라는 scheduler 계약이다

## 1-3. PA7 / PA8 review / canary 재료

- [backend/services/path_checkpoint_pa7_review_processor.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa7_review_processor.py)
- [backend/services/path_checkpoint_pa78_review_packet.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa78_review_packet.py)
- [backend/services/path_checkpoint_pa8_symbol_action_canary.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa8_symbol_action_canary.py)
- [backend/services/path_checkpoint_pa8_canary_refresh.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa8_canary_refresh.py)
- [backend/services/path_checkpoint_pa8_action_canary_activation_apply.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa8_action_canary_activation_apply.py)
- [backend/services/path_checkpoint_pa8_action_canary_closeout_decision.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa8_action_canary_closeout_decision.py)

이미 하는 일:

- review queue
- action-only canary
- refresh board
- activation / closeout 판단

판단:

- `PA8 governance 판단 로직`은 이미 많이 있다
- 부족한 것은 `누가 승인하고 누가 적용하는가`의 흐름이다

## 1-4. SA preview / audit 재료

- [backend/services/path_checkpoint_scene_disagreement_audit.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_disagreement_audit.py)
- [backend/services/path_checkpoint_scene_bias_preview.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_bias_preview.py)

이미 하는 일:

- disagreement audit
- preview-only 검증

판단:

- `heavy_cycle`에 실릴 재료는 이미 있다
- 지금 단계에서 SA live adoption 로직을 새로 만드는 것은 아니다

## 1-5. Telegram 발송 바닥층

- [adapters/telegram_notifier_adapter.py](/Users/bhs33/Desktop/project/cfd/adapters/telegram_notifier_adapter.py)
- [backend/integrations/notifier.py](/Users/bhs33/Desktop/project/cfd/backend/integrations/notifier.py)

판단:

- 완성된 control plane은 아니지만, 저수준 전송 기반은 이미 있다
- 따라서 내부 기반 공사 문서에서는 Telegram 자체보다 `approval/apply 경계`를 더 중시하면 된다

---

## 2. 조금만 보강하면 되는 것

이 항목들은 완전 신설이 아니라,
이미 있는 재료를 `운영 계약` 수준으로 묶어주면 된다.

v2 기준에서는 일부 항목을 `watch first tick 이후`로 미루는 것이 더 현실적이다.

## 2-1. Master Board Contract

기존 재료:

- `checkpoint_pa78_review_packet_latest.json`
- `checkpoint_pa8_canary_refresh_board_latest.json`
- `checkpoint_scene_disagreement_audit_latest.json`
- `checkpoint_analysis_refresh_latest.json`

부족한 점:

- 한 군데서 통합해서 읽는 canonical shape가 없다

필요한 보강:

- `checkpoint_improvement_master_board_latest.json`
- `checkpoint_improvement_master_board_latest.md`
- 섹션 shape 고정
- 최소 필드:
  - `blocking_reason`
  - `next_required_action`
  - `oldest_pending_approval_age_sec`
  - `last_successful_apply_ts`
  - `degraded_components`
  - `reconcile_backlog_count`

판단:

- 완전 신설보다는 `artifact aggregator contract`에 가깝다
- 다만 `watch first tick`과 approval/apply가 실제로 한 번 돈 뒤에 붙이는 것이 더 맞다

## 2-2. TelegramStateStore contract / PA8 Governance 연결 규약

기존 재료:

- Telegram low-level notifier / callback 설계 문서
- activation review packet
- monitoring packet
- rollback review packet
- closeout decision

부족한 점:

- `TelegramStateStore`와 `SystemStateManager`의 계층 관계가 문서상 더 강하게 고정되어 있지 않다
- approval request / apply / closeout을 같은 승인 흐름으로 묶는 contract가 약하다

필요한 보강:

- `TelegramStateStore`는 하위 승인/메시지 저장소,
  `SystemStateManager`는 상위 운영 상태 진실 소스라는 경계 고정
- `activation / rollback / closeout` 공통 review type enum
- `approval_id / scope_key / apply_job_key / supersedes_approval_id` 규약
- approval -> apply 연결 규약

판단:

- 별도 거대한 새 판단 로직보다는 `ApprovalLoop + ApplyExecutor`에 흡수되어야 하는 계약에 가깝다

## 2-3. Reconcile Rules

기존 재료:

- false rollback patch 경험
- pending/approval 상태 전이에 대한 문서 초안

부족한 점:

- stale pending
- approved-but-not-applied
- message mapping repair
- late callback invalidation
- same-scope duplicate / superseded approval 정리

이 한 곳에 묶인 운영 규칙이 아직 없다.

판단:

- v2에서는 이것을 `미리 완성하는 규칙집`으로 보지 않는다
- `reconcile_cycle 자리 + 운영 중 발견 규칙 추가 지점`으로 먼저 두는 것이 맞다

## 2-4. light / heavy / apply cycle definition

기존 재료:

- fast refresh
- PA7 processor
- PA8 canary refresh
- SA audit / preview

부족한 점:

- 어느 주기에서 무엇을 돌릴지
- skip / timeout / lock 기준
- 어떤 cycle이 어떤 산출물을 책임지는지

이 아직 canonical contract로 고정되지 않았다.

v2 기준 핵심:

- `light_cycle`은 watch 첫 tick을 위해 가장 먼저 잠근다
- `governance_cycle`은 PA8 candidate를 만드는 데 우선 필요하다
- `heavy_cycle`과 `reconcile_cycle`은 뒤에 붙여도 된다

---

## 3. 새로 만들어야 하는 것

이 항목들은 실제로 아직 비어 있는 기반 부품이다.

다만 v2에서는 `전부 직렬로` 만드는 것이 아니라,
`watch 기동에 필요한 것`과 `approval/apply 병렬 기반`으로 다시 읽는 것이 맞다.

## 3-1. SystemStateManager

필요 이유:

- 전체 상태를 한 곳에서 관리해야 한다
- 서비스가 제각각 상태를 바꾸면 나중에 진실 소스가 없어진다

최소 책임:

- state snapshot
- state transition
- lock
- current phase 관리
- `last_row_ts`
- `light_last_run / heavy_last_run / governance_last_run`
- symbol별 `pa8_symbols` 상태

권장 파일:

- `backend/services/system_state_manager.py`

v2 메모:

- 처음부터 full state tree를 만들기보다 `v0 최소 상태`로 시작하는 것이 더 현실적이다

## 3-2. EventBus

필요 이유:

- watch가 TelegramHub를 직접 import해서 부르면 결합도가 너무 높아진다
- approval loop, apply executor, state manager 사이를 느슨하게 연결해야 한다

최소 책임:

- `publish`
- `subscribe`
- `drain`
- handler 오류 격리

권장 파일:

- `backend/services/event_bus.py`

v2 메모:

- 처음엔 이벤트를 많이 만들지 않는다
- `LightRefreshCompleted / GovernanceActionNeeded / ApprovalReceived / SystemPhaseChanged / WatchError`
  정도의 v0 이벤트부터 시작한다

## 3-3. ApprovalLoop

필요 이유:

- callback -> approval state transition을 담당할 운영형 상태기계가 필요하다

최소 책임:

- `approved / held / rejected / expired / applied`
- allowed user 검증
- callback idempotency
- deadline expire
- `approval_id / scope_key` 기준 전이 기록

권장 파일:

- `backend/services/approval_loop.py`

## 3-4. ApplyExecutor

필요 이유:

- 승인된 bounded action-only change를 실제로 적용할 집행기가 필요하다

최소 책임:

- activation apply
- rollback apply
- closeout apply
- apply job registry
- approval 없는 apply 거부
- 같은 job 중복 apply 차단

권장 파일:

- `backend/services/apply_executor.py`

## 3-5. checkpoint_improvement_watch

필요 이유:

- row observer / scheduler / review candidate generator가 아직 없다

최소 책임:

- `light_cycle`
- `heavy_cycle`
- `governance_cycle`
- `reconcile_cycle`

권장 파일:

- `backend/services/checkpoint_improvement_watch.py`
- `scripts/checkpoint_improvement_watch.py`

---

## 4. 제일 추천하는 착수 순서

v2 기준에선 아래처럼 `A/B/C`로 읽는 것이 가장 자연스럽다.

### Track A. watch 최소 기동

1. `SystemStateManager v0`
2. `EventBus v0`
3. `light / governance / heavy / reconcile cycle definition`
4. `checkpoint_improvement_watch light_cycle first tick`

핵심:

- 실제 row를 보고 첫 tick을 최대한 빨리 돌린다

### Track B. 승인/적용 병렬 기반

5. `TelegramStateStore contract 정렬`
6. `ApprovalLoop`
7. `ApplyExecutor`
8. `Telegram approval bridge`

핵심:

- watch가 도는 동안 approval/apply 기반을 병렬로 붙인다
- `PA8 Governance Contract`는 별도 거대한 단계보다 이 트랙에 흡수하는 것이 맞다

### Track C. 합류 후 안정화

9. `Master Board Contract`
10. `heavy_cycle` 정식 연결
11. `Reconcile Rules`
12. `OrchestratorLoop`

핵심:

- 보드와 reconcile은 실제 운영 데이터가 나온 뒤 붙인다

즉 v2에선

`반장을 끝까지 미루는 것`이 아니라,
`반장이 첫 수업은 빨리 시작하게 하고, 행정반과 집행반은 옆에서 병렬로 붙이는 구조`

가 맞다.

---

## 5. 다음 스레드에서 바로 읽는 법

다른 스레드에선 아래 문서 순서로 읽으면 된다.

1. 이 문서
2. [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
3. [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
4. [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)

그 다음에야 실제로

- `A1. SystemStateManager v0`
- `A2. EventBus v0`
- `A4. watch light_cycle first tick`
- 병렬로 `B2. ApprovalLoop`
- `B3. ApplyExecutor`

순으로 구현에 들어가는 것이 맞다.

---

## 최종 권장안

이 문서의 결론은 아래다.

`이미 있는 재료는 살리고, 진짜 비어 있는 최소 기반만 먼저 만든 뒤, watch first tick을 앞당기고, approval/apply 기반은 병렬로 붙이며, Master Board와 Reconcile은 실제 운영 데이터가 나온 뒤 안정화한다`
