# Current Continuous Learning / Runtime Rollout External Review Request

## How This Connects To The Existing Roadmap

이 문서는 완전히 새로운 로드맵을 시작하는 것이 아니라,
기존 `market-family multi-surface` 로드맵의 다음 단계가 왜 `continuous operating layer`여야 하는지를 설명하기 위한 문서다.

중요한 전제 하나가 있다.

- `CL`은 현재 runtime 판단이 최소한 bounded하게 안전하다는 전제 위에서 붙는 운영층이다
- 따라서 최근 확인된 `wrong-side active-action conflict`는 `CL`보다 먼저 `P0 hotfix`로 정리해야 한다
- 이 P0 문제를 외부에 상세히 물어볼 때는 별도 문서인
  [current_wrong_side_active_action_conflict_external_review_request_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wrong_side_active_action_conflict_external_review_request_ko.md)
  를 기준으로 본다
- 또한 `follow_through / continuation_hold / protective_exit`를
  실제 차트 경로와 체크포인트 단위로 어떻게 읽게 할지는 별도 문서인
  [current_path_aware_checkpoint_decision_external_review_request_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_external_review_request_ko.md)
  를 기준으로 본다

현재까지의 큰 진행 상황은 아래와 같다.

- `PF0` 성능 baseline hold: 완료
- `MF1 ~ MF16`: 구현 완료
- `MF17`: candidate gate, review manifest, signoff criteria, signoff packet, activation contract까지 구현 완료
- `BTCUSD / NAS100 / XAUUSD initial_entry_surface` 3개는 모두 공통 signoff packet과 공통 activation contract에 올라와 있음
- 아직 live activation은 열지 않았고, 현재 상태는 `READY_FOR_MANUAL_SIGNOFF -> PENDING_MANUAL_SIGNOFF`

즉 기존에 하던 일의 본질은:

- market-family 분리
- multi-surface 분리
- preview dataset / evaluation
- bounded rollout signoff gate

를 실제로 구축하는 것이었다.

반대로 아직 남아 있는 "기존 로드맵의 마지막 일"은 아래다.

- `BTCUSD / NAS100 / XAUUSD initial_entry_surface` manual signoff
- bounded activation
- `follow_through` 음성 샘플 보강
- `continuation_hold / protective_exit` 데이터 보강

따라서 다음 질문은 더 이상
"어떤 전략 로직을 하나 더 붙일까"가 아니라,
"이미 구축한 후보/평가/승인 구조를 어떻게 지속 운영 루프로 닫을까"가 된다.

## New Direction To Review

현재 판단은 이렇다.

- `PF0 ~ MF17`까지로 `market-family + multi-surface + bounded rollout gate`의 부품은 대부분 구축했다.
- `BTCUSD / NAS100 / XAUUSD initial_entry_surface`는 모두 공통 signoff packet과 공통 activation contract에 올라와 있다.
- 따라서 다음 핵심은 새 전략 아이디어를 더 붙이는 것이 아니라,
  `continuous harvest -> rebuild -> eval -> candidate package -> signoff queue -> canary -> rollback -> observability`
  운영 루프를 닫는 것이다.

외부 리뷰에서 특히 듣고 싶은 것은 아래 세 가지다.

1. `continuous_learning_orchestrator`를 어떤 계층으로 두는 것이 가장 안정적인가
2. `symbol + surface + version` candidate package를 어떤 schema로 표준화하는 것이 좋은가
3. signoff, canary, rollback, symbol-specific observability를 어떤 lifecycle/status machine으로 묶는 것이 가장 운영 친화적인가

## Suggested Next Operating-Layer Roadmap

현재 내부 제안은 아래 순서다.

1. `CL1 Continuous Learning Orchestrator`
2. `CL2 Candidate Package Schema Standardization`
3. `CL3 Signoff Queue / Lifecycle Status`
4. `CL4 Symbol-Specific Observability Registries`
5. `CL5 Surface KPI Collector`
6. `CL6 Canary Runtime Guard / Rollback Engine`
7. `CL7 Auto-Apply / Manual-Exception / Diagnostic Policy`
8. `CL8 LLM Summary Layer`
9. `CL9 Operating Mode System`

핵심 가정은 아래와 같다.

- 사람은 모든 row를 검토하지 않고, 예외와 승인만 본다
- shared surface는 유지하되, 관측과 drift는 symbol별로 분리한다
- candidate는 룰 조각이 아니라 `symbol + surface + version` 패키지로 관리한다
- rollback은 on/off가 아니라 downgrade를 포함한 단계형이어야 한다

## 목적

이 문서는 외부 LLM 또는 리뷰어에게

- 지금까지 어떤 구조를 실제로 구축했는지
- 왜 이런 구조를 만들었는지
- 현재 어디까지 구현되었는지
- 다음에는 어떤 형태로 접근하는 것이 맞는지

를 한 번에 설명하기 위한 상세 요청서다.

핵심 질문은 단순하다.

> 우리는 이미 `시장별/상황별 surface + bounded rollout gate`까지 만들었다.
> 이제 이 구조를 `계속 쌓이는 자동매매 데이터`를 먹으면서
> `더 좋은 entry / wait / hold / exit` 판단으로 계속 업데이트되는
> **continuous learning loop**로 어떻게 안전하게 진화시키는 것이 맞는가?

---

## 한 줄 현재 상태

현재 시스템은 이미

- `NAS100 / BTCUSD / XAUUSD` 시장별 분리,
- `initial_entry / follow_through / continuation_hold / protective_exit` surface 분리,
- failure label harvest,
- preview dataset export,
- preview evaluation,
- bounded rollout candidate gate,
- signoff packet,
- activation contract

까지 닫혀 있다.

특히 `initial_entry_surface`는 지금

- `BTCUSD`
- `NAS100`
- `XAUUSD`

세 symbol 모두 **같은 공통 signoff packet -> 같은 공통 activation contract**
구조 안에 올라와 있다.

다만 아직 실제 live activation은 열지 않았고,
현재는 **manual signoff 직전 상태**다.

---

## 왜 이런 구조를 만들었는가

원래 문제는 단순한 “좋은 진입 점수 하나”가 아니었다.

최근 runtime을 보면:

- `NAS100`은 conflict/observe 계열이 과하게 많고
- `BTCUSD`는 middle-anchor observe가 많고
- `XAUUSD`는 follow-through와 runner 보존을 과하게 막는 경향이 있었다

즉 같은 시장이 아니고,
같은 종류의 판단도 아니었다.

그래서 다음 원칙으로 재설계했다.

1. 시장별 family를 따로 본다
2. action 종류를 surface로 분리한다
3. 실패 케이스도 라벨로 수집한다
4. live에는 바로 붙이지 않고 preview -> gate -> signoff -> bounded activation 순으로 간다
5. 모델을 종목별로 완전히 분리하지 않고 `shared surface + market adapter`로 간다

---

## 현재 프로젝트 구성

### 1. Runtime / Execution Layer

실시간 거래 판단과 실행은 주로 아래 파일에서 일어난다.

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [entry_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)
- [entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)
- [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
- [trading_application_runner.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)

여기서 하는 일:

- symbol별 entry/wait/skip/enter 판단
- candidate source 결합
- follow-through / countertrend / breakout 등 보조 판단 기록
- protective exit / runner preservation 분기
- runtime row와 compact detail payload 저장

현재는 성능 병목과 main-engine crash도 1차 정리된 상태다.

관련 baseline:

- [entry_performance_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/entry_performance_baseline_latest.json)
- [entry_performance_regression_watch_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/entry_performance_regression_watch_latest.json)

운영 원칙:

- 지금 성능은 baseline으로 고정
- 다시 `elapsed_ms >= 200` 수준의 regression이 나올 때만 성능 최적화에 재진입

### 2. Breakout / Directional Candidate Layer

breakout과 countertrend continuation은 별도 후보-owner로 분리되어 있다.

관련 핵심:

- [breakout_event_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_runtime.py)
- [breakout_event_overlay.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_overlay.py)
- [countertrend_materialization_check.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/countertrend_materialization_check.py)
- [countertrend_down_bootstrap_validation.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/countertrend_down_bootstrap_validation.py)

최근 진화:

- 초기에는 `anti-buy -> SELL` bootstrap으로 시작
- 이후 `anti_long / anti_short / pro_up / pro_down`과
  `UP/DOWN WATCH -> PROBE -> ENTER` 구조로 일반화
- 현재는 direction-agnostic state machine이 live row에 materialize되는 단계

### 3. Market-Family Multi-Surface Learning Layer

이게 이번 프로젝트의 중심이다.

관련 설계/로드맵:

- [current_market_family_multi_surface_execution_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_design_ko.md)
- [current_market_family_multi_surface_execution_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_implementation_roadmap_ko.md)

핵심 아이디어:

- market family:
  - `NAS100`
  - `BTCUSD`
  - `XAUUSD`
- surface:
  - `initial_entry_surface`
  - `follow_through_surface`
  - `continuation_hold_surface`
  - `protective_exit_surface`

그리고 사람의 체크/색 구분을 formalized label로 끌어올렸다.

관련 산출물:

- [check_color_label_formalization_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/check_color_label_formalization_latest.json)
- [surface_time_axis_contract_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/surface_time_axis_contract_latest.json)
- [failure_label_harvest_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/failure_label_harvest_latest.json)
- [market_adapter_layer_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_adapter_layer_latest.json)

### 4. Preview Dataset / Evaluation Layer

학습 직전 단계의 corpus와 symbol-surface 평가가 이미 있다.

관련 산출물:

- [multi_surface_preview_dataset_export_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/multi_surface_preview_dataset_export_latest.json)
- [initial_entry_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/initial_entry_dataset.csv)
- [follow_through_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/follow_through_dataset.csv)
- [continuation_hold_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/continuation_hold_dataset.csv)
- [protective_exit_dataset.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/protective_exit_dataset.csv)
- [symbol_surface_preview_evaluation_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/symbol_surface_preview_evaluation_latest.json)

현재 요약:

- `preview_eval_ready = 3`
- 세 개 모두 `initial_entry_surface`
- 즉 지금 가장 먼저 bounded rollout gate에 올릴 수 있는 것은
  `BTC / NAS / XAU initial_entry_surface` 3개다

### 5. Label Resolution / Draft / Apply Layer

여기가 최근에 중요하게 바뀐 부분이다.

예전에는 NAS/XAU가 draft만 있고 실제 평가에는 반영되지 않았는데,
지금은 apply 단계까지 추가되어 실제 dataset에 반영된다.

관련 산출물:

- [initial_entry_label_resolution_queue_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/initial_entry_label_resolution_queue_latest.json)
- [initial_entry_label_resolution_draft_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/initial_entry_label_resolution_draft_latest.json)
- [initial_entry_label_resolution_apply_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/initial_entry_label_resolution_apply_latest.json)
- [initial_entry_dataset_resolved.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/multi_surface_preview/initial_entry_dataset_resolved.csv)

현재 apply 결과:

- `applied_row_count = 5`
- `NAS100 2`
- `XAUUSD 3`

즉 NAS/XAU도 이제 “draft-only”가 아니라
**resolved dataset를 통해 실제 MF16/MF17 평가 체인 안으로 들어간 상태**다.

### 6. Bounded Rollout Gate / Signoff / Activation Layer

이제 symbol-surface 단위로 review-canary를 열 수 있는 공통 gate가 만들어져 있다.

관련 산출물:

- [bounded_rollout_candidate_gate_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_rollout_candidate_gate_latest.json)
- [bounded_rollout_review_manifest_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_rollout_review_manifest_latest.json)
- [bounded_rollout_signoff_criteria_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_rollout_signoff_criteria_latest.json)
- [symbol_surface_canary_signoff_packet_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/symbol_surface_canary_signoff_packet_latest.json)
- [bounded_symbol_surface_activation_contract_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/bounded_symbol_surface_activation_contract_latest.json)

현재 상태:

- candidate gate:
  - `review_canary_count = 3`
- signoff criteria:
  - `READY_FOR_MANUAL_SIGNOFF = 3`
- signoff packet:
  - `BTCUSD / NAS100 / XAUUSD` 모두 `REVIEW_PACKET_READY`
- activation contract:
  - 세 개 모두 `PENDING_MANUAL_SIGNOFF`

즉 **구조적으로는 세 symbol 모두 같은 문 앞에 와 있고,
아직 manual signoff를 하지 않았기 때문에 live activation만 잠겨 있는 상태**다.

---

## 지금까지 로드맵에서 완료된 것

큰 줄기만 요약하면:

- PF0: entry performance baseline hold
- MF1: market-family audit snapshot
- MF2: surface objective / EV specification
- MF3: check/color label formalization
- MF4: time-axis contract
- MF5: initial-entry runtime split
- MF6: distribution-based promotion gate baseline
- MF7A~E: countertrend / direction-agnostic continuation 구조
- MF11: continuation hold / runner preservation split
- MF12: protective exit surface split
- MF13: failure label harvest
- MF14: market adapter layer
- MF15: multi-surface preview dataset export
- MF16: symbol-surface preview evaluation
- MF17: candidate gate / review manifest / signoff criteria / signoff packet / activation contract / label resolution apply

즉 지금은 “기초 구조를 만들고 있는 단계”는 사실상 지났고,
**bounded review-canary를 열기 직전의 운영 게이트 단계**다.

---

## 현재 남은 것

### 1. Manual signoff

현재 `initial_entry_surface`의 세 symbol:

- `BTCUSD`
- `NAS100`
- `XAUUSD`

모두 manual signoff만 남아 있다.

즉 지금 당장 필요한 운영 행동은:

- `manual_signoff_btcusd_initial_entry_surface_review_canary`
- `manual_signoff_nas100_initial_entry_surface_review_canary`
- `manual_signoff_xauusd_initial_entry_surface_review_canary`

### 2. Follow-through negative expansion

관련 산출물:

- [follow_through_negative_expansion_draft_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/follow_through_negative_expansion_draft_latest.json)

현재 요약:

- `row_count = 46`
- `BTC 34 / NAS 7 / XAU 5`

이건 follow-through가 positive-heavy라서
실패한 continuation / false breakout 음성 샘플을 더 넣으려는 draft다.

### 3. Continuation hold / protective exit augmentation

관련 산출물:

- [hold_exit_augmentation_draft_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/hold_exit_augmentation_draft_latest.json)

현재 요약:

- `row_count = 22`
- `continuation_hold_surface = 19`
- `protective_exit_surface = 3`

즉 runner preservation과 protective exit 쪽은 아직 데이터가 얇아서
보강 draft가 필요한 상태다.

---

## 지금 프로젝트가 막 도달한 구조적 전환점

이 프로젝트는 이제 “룰 몇 개 더 추가” 단계가 아니다.

현재 도달한 전환점은 다음과 같다.

1. **rule-first -> surface-first**
2. **single-score -> market-family + surface 분리**
3. **manual memo -> label formalization**
4. **one-shot tuning -> rolling preview evaluation**
5. **hard activation -> review/signoff/canary activation**

즉 이제부터는
“어떤 조건을 하나 더 넣을까”보다,
“계속 쌓이는 runtime 데이터를 어떤 루프로 학습/평가/승인까지 연결할까”
가 더 중요한 질문이다.

---

## 우리가 다음에 가고 싶은 방향

지금 생각하는 다음 방향은 아래와 같다.

### 방향 1. Continuous auto-harvest

계속 쌓이는 자동매매 데이터를 바탕으로

- failure harvest
- follow-through negative
- hold/exit augmentation

같은 고신뢰 샘플은 자동으로 더 누적한다.

### 방향 2. Manual-exception-only

사람이 모든 row를 보지 않고,
애매한 경계 케이스만 본다.

예:

- `PROBE_ENTRY vs WAIT_MORE`
- signoff 직결 row
- 새 cluster / 새 scene family

### 방향 3. Rolling preview rebuild / re-evaluation

실시간 live에서 바로 규칙을 바꾸는 게 아니라,

- 짧은 주기 배치로 dataset rebuild
- preview evaluation 재계산
- signoff packet 재계산
- activation contract 업데이트

를 반복한다.

### 방향 4. Bounded activation only

새 판단이 좋아 보여도

- symbol allowlist
- surface allowlist
- size cap
- rollback guard

가 있는 bounded canary로만 연다.

즉 “online learning”이라도
**data accumulation은 거의 실시간으로,
live rule 반영은 bounded gated rollout으로**
가고 싶다.

---

## 외부 리뷰어에게 묻고 싶은 핵심 질문

### 질문 1. Continuous learning loop를 어떻게 설계하는 것이 맞는가

현재는

- auto-harvest
- draft
- apply
- preview eval
- signoff
- bounded activation

까지는 만들어두었다.

여기서 다음 형태 중 무엇이 가장 안전하고 실용적인가?

- `hourly rolling rebuild`
- `session-end rebuild`
- `daily batch promotion`
- `hybrid: harvest는 계속, rollout 반영은 daily`

### 질문 2. 무엇을 auto-apply하고 무엇을 manual-exception으로 남겨야 하는가

현재는 NAS/XAU initial-entry는 draft를 apply해서 ready로 올렸다.

그렇다면 일반 원칙을 어떻게 두는 것이 좋은가?

- `high confidence >= auto-apply`
- `mid confidence -> review queue`
- `low confidence -> diagnostic only`

같은 구조가 맞는가?

### 질문 3. Initial-entry 이후 follow-through / hold / exit는 어떤 순서로 rollout하는 것이 좋은가

현재는 initial-entry 3개 symbol만 review-canary ready이고,
follow-through / continuation_hold / protective_exit는 아직 데이터 보강 중이다.

다음 rollout 순서를 어떻게 잡는 것이 좋은가?

- `initial_entry 3개 symbol signoff 먼저`
- `follow_through negative 확장 후 signoff`
- `continuation_hold / protective_exit는 더 뒤`

가 맞는가?

### 질문 4. Shared surface + market adapter 구조는 계속 유지하는 것이 맞는가

현재는 symbol별 완전 분리 모델 대신
공통 surface 위에 market adapter를 붙이고 있다.

이 방향이 지금 단계에서 가장 적절한가?

아니면 특정 symbol-surface부터 더 강한 전용 adapter나 전용 head가 필요한가?

### 질문 5. Manual signoff를 어떤 단위로 유지해야 하는가

현재는 `symbol + surface` 단위 signoff다.

더 세분화해야 하는가?

예:

- `symbol + surface + scene family`
- `symbol + surface + cluster`

아니면 지금처럼 `symbol + surface`만 유지하고,
나머지는 rollout 내부 monitor로 보는 것이 맞는가?

### 질문 6. 실시간 업데이트와 안전성의 균형은 어떻게 잡는 것이 좋은가

우리가 원하는 것은

- 데이터는 계속 쌓이고
- preview 판단은 계속 갱신되며
- 더 좋은 entry / wait / exit가 반영되는 구조

지만,
live에서 매번 규칙이 흔들리면 위험하다.

어떤 수준의 separation이 맞는가?

- `runtime log -> offline rebuild -> canary activation`
- `runtime log -> online score update, but gate fixed`
- `runtime log -> immediate threshold tweak`는 피해야 하는가?

---

## 내가 현재 생각하는 가장 자연스러운 다음 단계

지금 기준으로는 다음 순서가 가장 자연스럽다고 보고 있다.

1. `BTC/NAS/XAU initial_entry_surface` 3개 manual signoff
2. 세 symbol 모두 same generic activation contract 안에서 bounded canary 시작
3. `follow_through_negative_expansion_draft`를 실제 dataset 쪽으로 merge
4. `continuation_hold / protective_exit augmentation` merge
5. 이후 initial-entry와 같은 signoff/activation 문으로 follow-through / hold / exit를 순차 승격
6. 마지막에만 더 강한 rolling retrain / auto-apply 체계로 확장

---

## 매우 짧은 복붙용 질문

현재 우리는 CFD 자동매매 시스템에서 `NAS100 / BTCUSD / XAUUSD`를 `initial_entry / follow_through / continuation_hold / protective_exit` 4개 surface로 분리하고, label formalization, failure harvest, preview dataset export, preview evaluation, market adapter, signoff packet, bounded activation contract까지 구축했습니다. 최근에는 NAS/XAU initial-entry label resolution을 actual resolved dataset에 apply해서, 이제 `BTC/NAS/XAU initial_entry_surface` 3개가 모두 같은 generic signoff packet과 activation contract 안에서 `READY_FOR_MANUAL_SIGNOFF / PENDING_MANUAL_SIGNOFF` 상태입니다. 다음 단계로는 `continuous auto-harvest + manual-exception-only + rolling preview rebuild/eval + bounded activation` 루프로 가고 싶은데, 어떤 cadence와 gating 구조가 가장 안전하고 실용적인지, 그리고 initial-entry 이후 follow-through / continuation_hold / protective_exit를 어떤 순서와 기준으로 같은 gate로 올리는 것이 맞는지 조언이 필요합니다.
