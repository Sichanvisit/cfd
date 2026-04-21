# Current Telegram Control Plane And Improvement Loop

## 목적

이 문서는 CFD 프로젝트에서 텔레그램을 단순 알림 채널이 아니라 `운영 승인 콘솔`로 쓰기 위한 상세 구현 방향을 고정한다.

이 문서가 답하려는 질문은 아래 4개다.

1. `manage_cfd`만 켜두면 어디까지 자동으로 돌게 할 것인가
2. 텔레그램은 무엇을 자동으로 받고, 무엇을 사람이 승인해야 하는가
3. 기존 PA/SA/상태판 구조와 텔레그램 허브를 어떤 순서로 연결할 것인가
4. 다른 스레드에서 구현을 시작할 때 어떤 문서부터 어떤 순서로 봐야 하는가

이 문서는 아래 문서의 상위 구현 전략 메모로 본다.

- [current_all_in_one_system_master_playbook_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_all_in_one_system_master_playbook_ko.md)
- [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)
- [current_pre_orchestration_build_inventory_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_build_inventory_ko.md)
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_a6_checkpoint_improvement_watch_heavy_cycle_detailed_plan_ko.md)
- [current_b1_telegram_state_store_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b1_telegram_state_store_detailed_plan_ko.md)
- [current_b2_approval_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b2_approval_loop_detailed_plan_ko.md)
- [current_b3_apply_executor_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b3_apply_executor_detailed_plan_ko.md)
- [current_b4_telegram_approval_bridge_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b4_telegram_approval_bridge_detailed_plan_ko.md)
- [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_telegram_notification_hub_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_notification_hub_design_ko.md)
- [current_telegram_ops_mvp_templates_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_templates_ko.md)
- [current_telegram_ops_mvp_refinements_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_refinements_ko.md)
- [current_telegram_setup_quickstart_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_setup_quickstart_ko.md)

권장 읽기 흐름은 아래와 같다.

1. 전체 자동매매/개선/보고 축은 [current_system_reconfirmation_and_reinforcement_framework_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_system_reconfirmation_and_reinforcement_framework_ko.md)에서 먼저 본다.
2. Telegram이 그 구조 안에서 맡는 역할과 승인 경계는 이 문서에서 본다.
3. 실제 approval/apply 세부는 `B1 ~ B4` 문서와 [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)로 내려간다.

---

## 한 줄 방향

최종 목표는 아래다.

`manage_cfd`만 켜면 시스템이 알아서 수집, 요약, 후보 발굴, bounded canary 관찰까지 수행하고, 사람은 텔레그램에서 `승인 / 보류 / 거부`만 누르는 구조를 만든다.

즉 텔레그램은 메신저가 아니라 `운영 제어판(control plane)`으로 본다.

---

## 현재 구조를 어떻게 해석할 것인가

지금 프로젝트에는 이미 아래 3종 부품이 있다.

### 1. 실시간 실행 부품

- [main.py](/Users/bhs33/Desktop/project/cfd/main.py)
- [backend/fastapi/app.py](/Users/bhs33/Desktop/project/cfd/backend/fastapi/app.py)
- [backend/services/path_checkpoint_context.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)

이 영역은 시장 데이터를 수집하고, 기본 액션을 계산하고, checkpoint row를 남긴다.

### 2. 자동 개선 부품

- [backend/services/path_checkpoint_analysis_refresh.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_analysis_refresh.py)
- [backend/services/path_checkpoint_pa7_review_processor.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa7_review_processor.py)
- [backend/services/path_checkpoint_pa8_symbol_action_canary.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa8_symbol_action_canary.py)
- [backend/services/path_checkpoint_scene_disagreement_audit.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_disagreement_audit.py)
- [backend/services/path_checkpoint_scene_bias_preview.py](/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_bias_preview.py)

이 영역은 row를 다시 읽어서 상태판, preview, canary, audit를 만든다.

### 3. 텔레그램 부품

- [adapters/telegram_notifier_adapter.py](/Users/bhs33/Desktop/project/cfd/adapters/telegram_notifier_adapter.py)
- [backend/integrations/notifier.py](/Users/bhs33/Desktop/project/cfd/backend/integrations/notifier.py)

이 영역은 아직 단일 채팅 발송기 성격이 강하다. 앞으로는 이걸 `허브 + 승인 상태 저장 + callback poller` 구조로 승격해야 한다.

---

## 최종 역할 분리

구현은 반드시 아래 4개 레이어로 나눠야 한다.

### Layer 1. Hot Path

역할:

- 실시간 수집
- 기본 액션 계산
- checkpoint row 기록

원칙:

- 가장 가벼워야 한다
- Telegram API 호출을 직접 하지 않는다
- 개선 로직 전체를 여기서 돌리지 않는다

### Layer 2. Telegram Notification Hub

역할:

- 이벤트를 받아서 목적지 분기
- 체크방, 보고방, PnL 포럼방으로 라우팅
- 카드 포맷터 호출
- 신규 메시지와 edit 메시지 결정

원칙:

- 기존 로직은 문자열을 직접 보내지 않는다
- 항상 typed event를 허브로 넘긴다

### Layer 3. Approval Loop

역할:

- callback update 수신
- 승인 사용자 검증
- 체크 상태 전이
- 승인 결과 기록
- bounded apply 트리거

원칙:

- 버튼은 함수 직접 실행이 아니라 `상태 전이 트리거`다
- `approved / held / rejected / expired / applied`가 DB에 남아야 한다

### Layer 4. Improvement Loop

역할:

- fast refresh
- PA7 review queue 정리
- PA8 canary 상태판 갱신
- rollback trigger 감시
- heavy scene review 주기 실행

원칙:

- 실시간 루프와 분리된 백그라운드 watch로 돈다
- 텔레그램은 이 watch의 승인 게이트 역할을 한다
- watch는 approval-needed candidate를 만들 뿐, bounded apply 자체를 직접 수행하지 않는다

---

## manage_cfd가 최종적으로 하게 될 일

최종 그림은 아래와 같다.

```text
manage_cfd
  -> main.py / runtime
  -> API / UI
  -> state25 candidate watch
  -> manual truth calibration watch
  -> checkpoint improvement watch
     -> fast refresh
     -> PA7 / PA8 packet refresh
     -> canary monitor / rollback
     -> Telegram approval request dispatch
```

즉 `manage_cfd`는 여러 프로세스를 띄우는 런처이고, 텔레그램은 그 위에서 사람 승인만 받는 외부 손잡이가 된다.

---

## 자동과 사람 승인의 경계

이 경계는 초반부터 잠가야 한다.

### 자동으로 해도 되는 것

- checkpoint row 수집
- fast report refresh
- 보고방 알림 전송
- PnL 포럼 대표 메시지 갱신
- 학습/운영개선용 review 카드 생성
- pending 재알림
- PA7 review packet 재분류
- PA8 canary 상태판 갱신
- rollback trigger 감시

### 사람 승인 필요

- `PA8 bounded action-only canary activation`
- `PA8 closeout approval`
- `PA9 handoff approval`

주의:
- 실시간 `entry / wait / exit` 실행은 텔레그램 승인 대상이 아니다.
- 텔레그램 승인은 학습 결과 반영, bounded canary activation, closeout, handoff 같은 개선/승격 단계에만 사용한다.
- `tgops` live execution approval route는 기본 비활성이고, `tgbridge` improvement approval route만 운영 기본값으로 본다.

### 아직 자동 금지

- `SA8` scene bias live adoption
- 새 family의 첫 unrestricted rollout
- 여러 symbol로 한 번에 확대 적용
- 텔레그램 승인 없이 wide-scope rule patch live 반영

---

## 텔레그램이 실제로 처리할 카드 종류

초기 구현은 아래 4가지만 처리하면 충분하다.

### 1. 체크 카드

- `check_entry`
- `check_exit`
- `check_risk`

이 카드는 사람이 지금 판단해야 하는 것만 보낸다.

### 2. 보고 카드

- `report_entry`
- `report_exit`

이 카드는 정보성이고, 승인 버튼이 없다.

### 3. PnL 포럼 카드

- `pnl_update`
- `pnl_close`

이 카드는 토픽별 대표 메시지 edit 중심이다.

### 4. 운영 승인 카드

- `pa8_canary_activation_review`
- `pa8_canary_closeout_review`
- 나중에 `pa9_handoff_review`

이 카드는 텔레그램을 운영 콘솔처럼 쓰기 위한 핵심이다.

---

## 권장 데이터 흐름

권장 흐름은 아래와 같다.

```text
Trading / Exit / PA / SA / Runtime event
  -> Telegram event envelope
  -> TelegramNotificationHub
  -> Formatter
  -> TelegramClient
  -> Telegram chat / topic

Telegram callback
  -> TelegramUpdatePoller
  -> TelegramStateStore
  -> CheckQueueService
  -> bounded apply / hold / reject
  -> message edit + callback ack
```

핵심은 `보내는 쪽`과 `받는 쪽`을 분리하는 것이다.

---

## 구현 시 반드시 지켜야 하는 원칙

### 1. 이벤트 envelope를 먼저 고정한다

로직에서 텔레그램 문자열을 조합하지 않는다.

항상:

- `event_type`
- `route_key`
- `symbol`
- `reason_summary`
- `recommended_action`
- `payload`

를 가진 envelope를 허브로 넘긴다.

추가 원칙:

- integrated build에서는 contract freeze를 `soft / hard`로 나눈다
- enum 중심의 `soft contract`는 먼저 잠그고,
  `trace_id / scope_note / decision_deadline_ts / apply_job_key` 같은 세부 shape는
  watch와 approval/apply 흐름이 한 번 돈 뒤 hard freeze하는 편이 안전하다

### 2. 버튼은 DB 상태 전이여야 한다

버튼 클릭 후 동작은 아래 순서를 지킨다.

1. callback 수신
2. 허용 사용자 검증
3. `check_actions` 기록
4. `check_groups.status` 변경
5. bounded apply 또는 hold/reject 후속 처리
6. 카드 edit
7. callback ack

### 3. Hot Path를 무겁게 만들지 않는다

`main.py` 안에서 아래를 직접 하지 않는다.

- heavy scene review
- full PA7 rebuild
- 텔레그램 poller
- 장시간 승인 대기 로직

이런 것은 별도 loop로 분리한다.

### 4. 초기에는 action-only bounded canary까지만 연결한다

PA8은 연결 가능하다.

하지만 SA8은 아직 preview-only를 유지한다.

즉 텔레그램 1차 구현은 `action-only control plane`으로 본다.

---

## 권장 구현 순서

다른 스레드에서 바로 구현할 때는 아래 순서를 권장한다.

### Step 0. 문서 고정

아래 문서부터 읽는다.

1. [current_checkpoint_improvement_watch_remaining_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_remaining_roadmap_ko.md)
2. [current_pre_orchestration_build_inventory_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_build_inventory_ko.md)
3. [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
4. [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
5. [current_telegram_notification_hub_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_notification_hub_design_ko.md)
6. [current_telegram_ops_mvp_templates_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_templates_ko.md)
7. [current_telegram_ops_mvp_refinements_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_refinements_ko.md)
8. [current_telegram_setup_quickstart_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_setup_quickstart_ko.md)

통합 구현 기준으로는 아래 해석이 중요하다.

- `Track A`: watch first tick에 필요한 최소 기반
- `Track B`: TelegramStateStore / ApprovalLoop / ApplyExecutor 병렬 구축
- 텔레그램 control plane은 `Track B`의 승인 콘솔 역할이다

### Step 1. 설정 확장

아래 키부터 추가한다.

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHECK_CHAT_ID`
- `TELEGRAM_REPORT_CHAT_ID`
- `TELEGRAM_PNL_FORUM_CHAT_ID`
- `TELEGRAM_PNL_TOPIC_1H_ID`
- `TELEGRAM_PNL_TOPIC_4H_ID`
- `TELEGRAM_PNL_TOPIC_1D_ID`
- `TELEGRAM_PNL_TOPIC_1W_ID`
- `TELEGRAM_PNL_TOPIC_1M_ID`
- `TELEGRAM_ALLOWED_USER_IDS`
- `TELEGRAM_CHECK_MERGE_WINDOW_MINUTES`
- `TELEGRAM_CHECK_RENOTIFY_MINUTES`
- `TELEGRAM_CHECK_EXPIRE_MINUTES`
- `TELEGRAM_POLL_INTERVAL_SEC`
- `TELEGRAM_LONG_POLL_TIMEOUT_SEC`

### Step 2. TelegramClient

반드시 아래 메서드부터 만든다.

- `send_message`
- `edit_message_text`
- `edit_message_reply_markup`
- `answer_callback_query`
- `get_updates`

### Step 3. Formatter

아래 포맷터를 먼저 만든다.

- `TelegramCheckCardFormatter`
- `TelegramReportFormatter`
- `TelegramPnlFormatter`

### Step 4. TelegramNotificationHub

역할:

- route 분기
- formatter 호출
- chat/topic 선택
- 신규 전송 vs edit 전송 선택

### Step 5. TelegramStateStore

권장 저장 항목:

- `check_groups`
- `check_events`
- `check_actions`
- `telegram_messages`
- `poller_offsets`

### Step 6. CheckQueueService

역할:

- 그룹 생성
- 병합
- 만료
- 재알림
- 승인/거부/보류 상태 전이

### Step 7. TelegramUpdatePoller

역할:

- callback update polling
- offset 저장
- 멱등 처리
- 허용 사용자 검증

### Step 8. PnL Digest

권장 순서:

1. `1D`
2. `1H`
3. `4H`
4. `1W`
5. `1M`

### Step 9. 운영 승인 카드

아래 카드부터 텔레그램으로 올린다.

- `PA8 canary activation`
- `PA8 first window monitoring summary`
- `PA8 rollback review`
- `PA8 closeout review`

### Step 10. Improvement Watch

별도 watch를 추가한다.

권장 파일:

- [scripts/checkpoint_improvement_watch.py](/Users/bhs33/Desktop/project/cfd/scripts/checkpoint_improvement_watch.py)
- [backend/services/checkpoint_improvement_watch.py](/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_watch.py)

이 watch는 아래를 조율한다.

- row delta 감지
- fast refresh
- heavy review 주기 실행
- PA8 canary 상태 갱신
- rollback trigger 감시
- 텔레그램 승인 요청 발송

실제 orchestration 세부 구조는 [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)를 따른다.

주의:

- integrated build에선 `Improvement Watch`를 모든 기반 공사 뒤에 미루지 않는다
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md) 기준
  `watch light_cycle first tick`은 가능한 한 빨리 시작하고,
  Telegram approval 기반은 병렬로 붙이는 것이 맞다

---

## 첫 구현 범위와 보류 범위

### 첫 구현 범위

- 보고방 라우팅
- 체크방 카드 전송
- 승인/거부/보류 버튼
- check queue 병합
- `1D` PnL 대표 메시지
- `PA8 canary activation` 텔레그램 승인 카드

### 바로 넣지 않는 것

- 텔레그램 Mini App
- webhook
- 복잡한 조건부 승인 UI
- scene bias live adoption
- 다심볼 동시 대규모 rollout

---

## 다른 스레드에서 바로 착수할 때 체크할 것

아래가 Yes면 구현을 시작해도 된다.

1. 방 3개와 포럼 토픽 5개가 준비되었는가
2. `chat_id`와 `topic_id`를 모두 확보했는가
3. `recommended_action`, `recommended_action_note`, `trigger_summary`, `decision_deadline_ts`를 canonical field로 잠갔는가
4. approval 카드에 `scope_note`와 `deadline`이 들어가는가
5. 승인과 자동 적용의 경계를 문서로 잠갔는가
6. `PA8 action-only`, `SA preview-only` 경계를 지키는가

---

## 최종 권장안

현재 프로젝트에 가장 맞는 방식은 아래다.

1. 텔레그램은 단순 알림이 아니라 운영 승인 콘솔로 쓴다.
2. `manage_cfd`는 여러 런타임과 improvement loop를 띄우는 반장으로 유지한다.
3. 텔레그램 1차 구현은 `허브 + 상태 저장 + callback poller`를 먼저 닫는다.
4. `PA8`은 action-only bounded canary 승인까지 연결한다.
5. `SA8`은 아직 preview-only를 유지한다.

이렇게 가면 과한 자동화로 흔들리지 않으면서도, 실제 운영에서 `보고 -> 승인 -> 적용 -> 관찰 -> 롤백`까지 자연스럽게 이어지는 control plane을 만들 수 있다.
