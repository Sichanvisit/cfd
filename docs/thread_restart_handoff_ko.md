# CFD 새 스레드 재시작용 Handoff

## 1. 이 문서의 목적

이 문서는 새 스레드에서 다시 시작할 때,

- 지금까지 무엇을 구축했는지
- 최근에 무엇을 수정했는지
- 지금 실제 문제는 무엇인지
- 왜 그런 문제가 생겼는지
- 다음에 어떤 순서로 이어가야 하는지

를 한 번에 붙잡기 위한 handoff 문서다.

이 문서는 특히 다음 두 축을 같이 본다.

1. `chart / check 표시 안정화`
2. `semantic ML / promotion / runtime 운영 상태`


## 2. 큰 줄기에서 이미 구축된 것

### 2-1. chart_flow 안정화 축

기존 chart_flow는 다음 단계로 안정화했다.

- `Phase 0~6`
- 의미 고정
- 공통 policy 분리
- symbol override 분리
- strength 축 표준화
- distribution / rollout / baseline compare 계측

대표 문서:

- `docs/chart_flow_phase0_freeze_ko.md`
- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_spec_ko.md`
- `docs/chart_flow_phase6_baseline_compare_sampled_mode_spec_ko.md`

핵심 의미:

- `BUY / SELL / WAIT / PROBE / READY / ENTER / EXIT`
- 차트 표기는 임의 painter 해석이 아니라, 가능한 한 upstream 의미를 번역하는 구조로 간다.


### 2-2. refinement 축

Refinement는 R0~R4까지 내려가서 정리했다.

- `R0`: 정합성 최소셋
- `R1`: Stage E 미세조정
- `R2`: 저장 / export / replay 정합성
- `R3`: semantic ML Step 3~7 refinement
- `R4`: acceptance / promotion-ready 정리

대표 문서:

- `docs/refinement_track_execution_plan_ko.md`


### 2-3. semantic ML 축

semantic ML은 “아직 시작 전”이 아니라 이미 구조는 있었고, refinement를 진행했다.

- timing target refinement
- split health refinement
- entry_quality target refinement
- legacy feature tier refinement
- preview / audit refinement
- shadow compare quality / source alignment / runtime provenance cleanup

대표 문서:

- `docs/refinement_r3_semantic_ml_refinement_spec_ko.md`
- `docs/refinement_r3_step4_split_health_refinement_spec_ko.md`
- `docs/refinement_r3_step7_preview_audit_refinement_spec_ko.md`
- `docs/refinement_shadow_compare_quality_refinement_plan_ko.md`
- `docs/refinement_shadow_compare_runtime_source_cleanup_spec_ko.md`


## 3. 최근까지 실제로 고정된 운영/ML 상태

현재 런타임 기준:

- `semantic_live_config.mode = threshold_only`
- `semantic_live_config.symbol_allowlist = ["BTCUSD", "NAS100"]`
- `semantic shadow runtime = inactive`
- `shadow_runtime_reason = model_dir_missing`

즉 현재는:

- `semantic live`는 설정상 걸려 있지만
- `semantic shadow model dir`는 비어 있어 `shadow runtime`은 비활성
- 차트 체크 의미 owner는 여전히 ML이 아니라 rule / consumer chain

중요한 해석:

- ML이 체크 의미를 자동으로 그리는 구조는 아직 아님
- ML은 threshold / rollout / promotion 쪽 보조 레이어
- 차트 체크 의미는 아직 `rule -> consumer -> painter` 체인에서 결정됨


## 4. 최근에 새로 구축한 핵심 구조

### 4-1. Consumer-coupled check/entry alignment

이전의 `check_first_display_gate` 초안은 폐기했다.

폐기 문서:

- `docs/check_first_display_gate_spec_ko.md`
- `docs/check_first_display_gate_implementation_checklist_ko.md`

현재 유효한 축:

- `docs/consumer_coupled_check_entry_alignment_baseline_snapshot_ko.md`
- `docs/consumer_coupled_check_entry_alignment_spec_ko.md`
- `docs/consumer_coupled_check_entry_alignment_implementation_checklist_ko.md`
- `docs/consumer_coupled_check_entry_alignment_reconfirm_memo_ko.md`
- `docs/consumer_coupled_check_entry_runtime_propagation_followup_ko.md`
- `docs/consumer_coupled_check_entry_visual_binding_followup_ko.md`

핵심 아이디어:

- 체크 표기를 painter가 독자 판단으로 만들지 않는다
- `Consumer`가 만든 pre-entry state를 chart와 entry가 같이 쓴다
- 즉 `check`와 `entry`를 가능한 한 같은 체인에 묶는다


### 4-2. consumer_check_state_v1

`backend/services/entry_service.py` 에서 `consumer_check_state_v1`를 만든다.

주요 필드:

- `check_candidate`
- `check_display_ready`
- `entry_ready`
- `check_side`
- `check_stage`
- `check_reason`
- `entry_block_reason`
- `blocked_display_reason`
- `display_strength_level`

이 payload는 이후:

- `backend/services/entry_try_open_entry.py`
- `backend/trading/chart_painter.py`

로 전파된다.


### 4-3. chart_painter가 consumer_check_state_v1를 우선 사용

`backend/trading/chart_painter.py`는 이제

- raw observe 이유 문자열만 보지 않고
- `consumer_check_state_v1`

를 우선 번역한다.

즉:

- `PROBE`
- `OBSERVE`
- `READY`
- `BLOCKED`

를 `BUY_PROBE / BUY_WAIT / BUY_READY / SELL_PROBE / SELL_WAIT ...` 쪽으로 번역한다.


### 4-4. visual binding 보강

다음도 최근에 같이 손봤다.

- probe/watch 색 binding 통일
- line width 전체 상향
- marker size 약 50% 축소
- probe/watch 도형 납작함 완화

의도:

- 심볼별로 제각각 보이는 느낌을 줄이고
- 같은 strength / 같은 event family면 비슷한 시각 규칙을 타게 만든다


## 5. 최근까지 실제로 드러난 문제

가장 중요한 문제는 다음이었다.

### 문제 A. 차트에 `BUY READY`처럼 보이는데 실제론 뒤에서 계속 막힘

예:

- BTC 하락 중인데 buy가 시도때도 없이 강하게 보임
- NAS도 들어가면 안 되는 자리인데 READY처럼 보이거나 실제 진입이 붙는 장면이 있었음

최근 관찰에서 실제로 보인 패턴:

- `blocked_by`가 비어 있지 않음
- `quick_trace_state = BLOCKED`
- 그런데 `consumer_check_stage = READY`
- `consumer_check_entry_ready = True`

즉:

- 실제로는 막힌 상태인데
- 차트와 일부 runtime row는 “진입 강한 체크”처럼 보였음


### 문제 B. 같은 시그니처가 너무 자주 반복 표기됨

특히:

- BTC lower rebound buy
- NAS lower rebound buy

에서 비슷한 reason / 같은 scene이 몇 봉 간격으로 반복 표기되면서,

- “진짜 새로운 자리”
- “같은 논리의 반복 알림”

이 구분이 잘 안 되는 상태였다.


### 문제 C. XAU / BTC / NAS의 체감이 너무 다름

예전엔:

- XAU는 sell surface가 과다
- BTC는 PROBE/WATCH가 납작하게 보여서 어색
- NAS는 middle / lower observe가 너무 눌림

지금은 일부 개선됐지만, 여전히

- `must-show scene`
- `generic observe`
- `late blocked scene`

의 균형이 완전히 잠긴 상태는 아니다.


## 6. 왜 이런 문제가 생겼는가

핵심 원인은 `write order`와 `owner 분리`에 있었다.

### 6-1. consumer_check_state는 먼저 계산됨

`entry_service.py`에서 먼저:

- `check_stage`
- `display_ready`
- `entry_ready`

가 정해진다.


### 6-2. 그런데 try_open_entry에서 late guard가 나중에 붙음

`entry_try_open_entry.py`에서는 그 뒤에:

- `range_lower_buy_requires_lower_edge`
- `range_lower_buy_conflict_blocked`
- `clustered_entry_price_zone`
- `pyramid_not_progressed`
- `pyramid_not_in_drawdown`
- `forecast_guard`
- `energy_soft_block`

같은 late block가 붙는다.

즉 순서가:

1. check state 계산
2. 나중에 blocked_by 추가

여서,

- 차트/row에는 READY가 남고
- 실제론 뒤에서 skip / block 되는

어긋남이 생겼다.


### 6-3. 반복 표기 억제도 짧았다

`chart_painter.py`의 repeated signature minimum이 짧아서,

- 같은 장면이 3분 정도만 지나도 다시 표기될 수 있었다.

이게 BTC/NAS에서 체감상 “시도때도 없이 뜬다”로 보였다.


## 7. 최근에 실제로 고친 것

### 7-1. weak structural observe 복구

너무 세게 줄이면서 사라졌던:

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `*_watch`

같은 구조적 약한 체크는 다시 살렸다.

의도:

- “없으면 안 되는 약한 체크”는 보이게 하고
- generic spam observe는 계속 막는다


### 7-2. BTC upper sell weak display relief

BTC 상단 sell 장면은:

- 찾고도
- `probe_against_default_side`

때문에 아예 숨겨지는 케이스가 있었다.

이건:

- entry는 계속 막더라도
- chart에는 약한 체크로는 남길 수 있게

좁게 완화했다.


### 7-3. late block와 consumer check를 다시 맞춤

최근 가장 중요한 수정.

`backend/services/entry_try_open_entry.py`에

- late blocked reason이 붙으면
- 기존 `consumer_check_state_v1`

를 다시 정리하는 `effective consumer check state` 재계산 로직을 넣었다.

현재 의도:

- late block가 붙으면 `entry_ready = false`
- guard 종류에 따라
  - `READY -> PROBE`
  - `READY -> OBSERVE`
  - `READY -> BLOCKED`
  - 또는 `display_ready = false`

로 내려간다.

특히 다음 guard는 더 강하게 숨김 대상으로 봤다.

- `clustered_entry_price_zone`
- `pyramid_not_progressed`
- `pyramid_not_in_drawdown`
- `range_lower_buy_requires_lower_edge`
- `range_lower_buy_conflict_blocked`
- `max_positions_reached`


### 7-4. repeated signature 간격 확대

`backend/trading/chart_painter.py`

- `_FLOW_SIGNATURE_REPEAT_MIN_SEC`

를 `3분 -> 6분`으로 늘렸다.

의도:

- 같은 scene의 연속 표기를 줄인다
- 진짜 새로운 자리와 반복 알림을 더 잘 구분한다


## 8. 지금 시점의 실제 최근 상태

`2026-03-27 18시대 KST` 기준, 최근 재시작 후 runtime / recent row에서 확인된 상태:

### BTCUSD

- 최근 row 다수:
  - `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `consumer_check_stage = BLOCKED`
- `consumer_check_display_ready = false`가 많음
- `consumer_check_entry_ready = false`
- `quick_trace_state = PROBE_READY`

해석:

- 예전처럼 `blocked인데 READY`로 남는 패턴은 최근 기준 거의 내려옴
- 지금 BTC는 lower buy/probe 후보가 남더라도, `energy_soft_block`가 붙으면 chart 표기까지 같이 내려가는 쪽으로 붙어 있음


### NAS100

최근 NAS는 크게 두 갈래가 같이 보인다.

- late block row:
  - `lower_rebound_confirm` 또는 `lower_rebound_probe_observe`
  - `blocked_by = energy_soft_block`
  - `consumer_check_stage = BLOCKED`
  - `consumer_check_entry_ready = false`
  - `consumer_check_display_ready`는 `true/false`가 둘 다 나옴
- clean ready row:
  - `blocked_by = ""`
  - `observe_reason = lower_rebound_probe_observe`
  - `consumer_check_stage = READY`
  - `consumer_check_entry_ready = true`
  - `quick_trace_state = PROBE_READY`

해석:

- 예전의 `blocked_by != ""`인데 `READY + entry_ready=true`이던 wrong READY 패턴은 최근 window에선 거의 안 보임
- 대신 clean READY와 late-blocked `BLOCKED`가 섞여 보여서, 여전히 buy 방향 표시가 잦게 느껴질 수 있음


### XAUUSD

- 최근엔 `conflict_box_upper_bb20_lower_*_observe` 류 conflict observe 위주
- `action_none_reason = observe_state_wait`
- `consumer_check_stage = BLOCKED`
- `consumer_check_display_ready = true`
- `consumer_check_entry_ready = false`

해석:

- 예전처럼 XAU만 과도하게 도배되는 상태는 많이 줄었음
- 다만 display는 남아 있기 때문에, conflict/upper-heavy 장면에서는 여전히 sell 쪽 bias가 체감될 수 있음


## 9. 지금 남아 있는 문제

아직 끝나지 않은 건 다음이다.

### 9-1. `BLOCKED`도 여전히 체감상 “buy 가능성 높음”처럼 보일 수 있음

지금은 READY는 많이 내려왔지만,

- `BLOCKED`
- `PROBE`
- `OBSERVE`

가 전부 방향성 체크로는 남아 있기 때문에,

사용자 체감상:

- “계속 buy가 강하다고 말하는 것 같다”

로 보일 수 있다.


### 9-2. must-show scene 정의가 아직 완전히 잠기지 않음

아직도 일부 표기는 이유 문자열 기반이 강하다.

즉:

- “진짜 있어야 하는 자리”
- “있어도 되는 약한 자리”
- “스팸이라 숨겨야 하는 자리”

를 scene contract로 완전히 고정한 상태는 아님.


### 9-3. unified score ladder는 아직 미구현

최근 논의:

- sell 3단
- wait 1단
- buy 3단
- 총 7단 시각 체계

아이디어는 괜찮지만,

- 현재 score 분포
- blocked scene 처리
- must-show scene whitelist

가 아직 먼저 더 잠겨야 한다.

즉 지금은

- `0.45/0.65/0.90`
- `0.60/0.75/0.90`

같은 단순 수치만 박아서 끝낼 단계는 아니다.


## 10. 다음 스레드에서 먼저 볼 것

새 스레드에서 시작하면 이 순서가 가장 좋다.

### Step 1. late blocked row가 실제로 얼마나 줄었는지 다시 본다

먼저 확인할 파일:

- `data/trades/entry_decisions.csv`
- `data/runtime_status.json`
  - `latest_signal_by_symbol`
- 필요하면 `data/runtime_status.detail.json`

확인 포인트:

- `entry_decisions.csv`는 최근 `200~300행` 위주로 먼저 본다
  - 과거 CSV에는 수정 전 wrong READY row가 그대로 남아 있을 수 있다
- `blocked_by != ""` 인데 `consumer_check_stage = READY` 가 최근 재시작 이후에도 남아 있는가
- `blocked_by != ""` 인데 `consumer_check_entry_ready = true`가 최근 재시작 이후에도 남아 있는가
- `BLOCKED + display_ready=true`가 어떤 guard에서 주로 남는가
  - `energy_soft_block`
  - `order_send_failed`
  - `observe_state_wait`

추가로 이제는 `runtime_status.detail.json`에서 최근 `wait-energy` 패턴을 바로 볼 수 있다.

- 경로:
  - `recent_runtime_diagnostics.windows.last_200.wait_energy_trace_summary`
  - 또는 slim 쪽 `recent_runtime_summary.windows.last_200.wait_energy_trace_summary`
- 구조:
  - `entry_wait_state_trace`
  - `entry_wait_decision_trace`
- 읽는 법:
  - `trace_present_rows`: 최근 row 중 trace payload 자체가 있던 row 수
  - `trace_branch_rows`: 그중 실제 branch record가 들어 있던 row 수
  - `usage_source_counts`: `recorded / inferred` 비율
  - `usage_mode_counts`: `wait_state_branch_applied / wait_decision_branch_applied / not_consumed` 비율
  - `branch_counts`: 최근에 실제로 많이 소비된 wait-energy branch
- 해석:
  - `helper_soft_block_state`가 많으면 state 단계에서 soft block이 많이 걸린 것
  - `helper_wait_bias_state`가 많으면 low-readiness + prefer-wait 성향이 state 쪽에서 누적된 것
  - `wait_soft_helper_block_decision`이 많으면 decision 단계에서 실제 wait 선택까지 이어진 것
  - 즉, `WAIT/BLOCKED가 많다`를 넘어서 `어느 단계에서 왜 멈췄는지`를 recent window 기준으로 바로 볼 수 있다
- 심볼별로 보고 싶으면:
  - `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_energy_trace_summary`
  - 예: `BTCUSD`, `NAS100`, `XAUUSD`

추가로 W3 이후에는 같은 recent window에서 `wait semantic summary`도 같이 본다.

- 경로:
  - `recent_runtime_diagnostics.windows.last_200.wait_state_semantic_summary`
  - `recent_runtime_diagnostics.windows.last_200.wait_decision_summary`
  - `recent_runtime_diagnostics.windows.last_200.wait_state_decision_bridge_summary`
  - 또는 심볼별 `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.*`
- 읽는 법:
  - `wait_state_counts`: 최근에 어떤 wait state가 자주 잡히는지
  - `hard_wait_state_counts`: 그중 실제 hard wait로 굳은 state가 무엇인지
  - `wait_decision_counts`: 최근 `skip / wait_*` decision 분포
  - `wait_selected_rate`: recent row 중 실제 wait 선택 비율
  - `state_to_decision_counts`: 특정 wait state가 어떤 decision으로 이어졌는지
- 해석:
  - `HELPER_SOFT_BLOCK`와 `hard_wait_state_counts`가 같이 높으면 helper soft block이 wait를 주도 중
  - `CENTER -> skip`이 높으면 state는 자주 보이지만 decision 단계에서는 풀리는 경우가 많음
  - `PROBE_CANDIDATE -> wait_*`가 높으면 probe 장면이나 scene-specific wait가 최근 흐름을 주도 중

추가로 wait state 이름은 아래처럼 크게 묶어서 보면 읽기 속도가 훨씬 빨라진다.

- 정책/허용 방향 계열:
  - `POLICY_BLOCK`
  - `POLICY_SUPPRESSED`
  - `AGAINST_MODE`
  - policy/layer mode나 허용 방향 mismatch를 먼저 의심한다
- helper 주도 계열:
  - `HELPER_SOFT_BLOCK`
  - `HELPER_WAIT`
  - energy/helper hint가 wait를 만든 경우다
- 구조적 관찰 계열:
  - `EDGE_APPROACH`
  - `NEED_RETEST`
  - `PROBE_CANDIDATE`
  - edge 접근, retest 필요, probe 장면 대기 같은 구조적 이유를 뜻한다
- 중립/충돌 계열:
  - `CENTER`
  - `CONFLICT`
  - `NOISE`
  - state는 자주 잡혀도 decision 단계에서 `skip`으로 많이 풀릴 수 있다
- 일반 보류/scene hold 계열:
  - `ACTIVE`
  - generic hold처럼 보이지만 scene-specific observe/hold가 섞여 있을 수 있으니 `state_to_decision_counts`를 같이 본다

`hard_wait_state_counts`가 높으면

- 단순 관찰이 아니라 실제 강한 대기/차단 성격이 굳는 쪽이고
- 같은 window에서 `wait_selected_rate`와 `state_to_decision_counts`를 같이 봐야 한다

심볼별로 읽을 때는 이 순서가 좋다.

1. `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_state_semantic_summary`
2. `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_decision_summary`
3. `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_state_decision_bridge_summary`
4. `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_energy_trace_summary`

즉 `state 분포 -> decision 분포 -> state→decision 연결 -> energy trace` 순으로 보면
`무슨 wait가 많나 -> 실제 wait로 이어지나 -> 어느 이유가 주도하나`
를 한 번에 묶어 볼 수 있다.

wait surface를 따로 읽는 빠른 가이드는 아래 문서에 정리돼 있다.

- `docs/current_wait_runtime_read_guide_ko.md`

exit 축도 이제 같은 방식으로 runtime surface에서 먼저 읽을 수 있다.

- slim:
  - `recent_exit_summary_window`
  - `recent_exit_status_counts`
  - `recent_exit_state_semantic_summary`
  - `recent_exit_decision_summary`
  - `recent_exit_state_decision_bridge_summary`
- detail:
  - `recent_exit_runtime_diagnostics.windows.last_200.exit_state_semantic_summary`
  - `recent_exit_runtime_diagnostics.windows.last_200.exit_decision_summary`
  - `recent_exit_runtime_diagnostics.windows.last_200.exit_state_decision_bridge_summary`
  - `recent_exit_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.*`

읽는 순서는 `state -> decision -> bridge`가 가장 빠르다.

즉
`최근 청산 state가 어떤 계열로 많나 -> 실제로 어디로 갔나 -> 둘이 어떻게 이어졌나`
순서로 보면 된다.

빠른 전용 가이드는 아래 문서에 따로 정리돼 있다.

- `docs/current_exit_runtime_read_guide_ko.md`
- `docs/current_entry_wait_exit_lifecycle_summary_ko.md`


### Step 2. BLOCKED의 시각 처리 방침을 정한다

선택지는 대략 두 가지다.

1. `BLOCKED`는 계속 보이되 더 작고 더 연하게
2. 특정 late suppress guard는 `BLOCKED`도 아예 숨김

현재 사용자 체감상으론

- `BLOCKED`를 더 약하게
- 또는 일부는 숨기는 쪽

이 더 맞을 가능성이 크다.


### Step 3. must-show scene casebook을 만든다

특히 심볼별로:

- `BTC`
  - lower rebound buy
  - upper reject sell
- `NAS`
  - clean confirm lower buy
  - middle/lower must-show observe
- `XAU`
  - upper sell repeat spam 억제
  - 진짜 구조적 watch/probe만 살리기

를 분리해야 한다.


### Step 4. 그 다음 unified ladder로 들어간다

즉 순서는:

1. wrong READY 제거
2. repeated spam 줄이기
3. must-show scene 정리
4. 그 다음 7단계 시각 ladder 정리

가 맞다.


## 11. 새 스레드에서 참고할 우선 문서

읽는 순서 추천:

1. `docs/thread_restart_handoff_ko.md`
2. `docs/thread_restart_first_checklist_ko.md`
3. `docs/current_wait_runtime_read_guide_ko.md`
4. `docs/current_wait_architecture_reorganization_phase_w5_completion_summary_ko.md`
5. `docs/refinement_track_execution_plan_ko.md`
6. `docs/consumer_coupled_check_entry_alignment_spec_ko.md`
7. `docs/consumer_coupled_check_entry_alignment_reconfirm_memo_ko.md`
8. `docs/consumer_coupled_check_entry_runtime_propagation_followup_ko.md`
9. `docs/consumer_coupled_check_entry_visual_binding_followup_ko.md`

참고:

- `check_first_display_gate_*` 계열은 현재 기준선이 아님
- `consumer_coupled_check_entry_alignment_*` 쪽이 현재 유효한 축이다


## 12. 한 줄 결론

지금까지 한 건 헛수고가 아니라,

- chart 의미 체계를 안정화하고
- check와 entry를 consumer chain으로 묶고
- semantic ML / rollout / shadow compare 축도 정리한 뒤
- 최근엔 `late blocked row가 chart READY로 보이던 구조적 어긋남`

을 고치고 있는 단계다.

즉 현재는:

- 큰 구조를 새로 만드는 단계가 아니라
- 이미 구축한 체계 위에서
- `거짓 READY`, `반복 표기`, `scene 선별`을 정렬하는 단계

라고 보면 된다.
