# CFD 새 스레드 첫 점검 체크리스트

이 문서는 `thread_restart_handoff_ko.md`에서
새 스레드 시작 직후 실제로 바로 확인해야 하는 부분만 짧게 뽑아낸 실행용 체크리스트다.


## 1. 먼저 열 파일

- `docs/thread_restart_handoff_ko.md`
- `docs/current_wait_runtime_read_guide_ko.md`
- `docs/current_exit_runtime_read_guide_ko.md`
- `docs/current_entry_wait_exit_lifecycle_summary_ko.md`
- `data/runtime_status.json`
- `data/runtime_status.detail.json`
- `data/trades/entry_decisions.csv`


## 2. 5분 빠른 점검

### Step 1. `runtime_status.json`에서 현재 심볼 상태를 본다

- `latest_signal_by_symbol`
- 심볼별로 우선 볼 필드:
  - `action`
  - `observe_reason`
  - `blocked_by`
  - `consumer_check_stage`
  - `entry_wait_state`
  - `entry_wait_decision`
  - `quick_trace_state`

질문:

- 지금 막히는 축이 `observe / consumer / wait / execution` 중 어디인가
- `BLOCKED`가 많은지, `WAIT`가 많은지, 아니면 clean `READY`가 보이는지


### Step 2. `runtime_status.detail.json`에서 recent window 요약을 본다

우선 경로:

- `recent_runtime_diagnostics.windows.last_200`

핵심 필드:

- `stage_counts`
- `blocked_reason_counts`
- `wrong_ready_count`
- `display_ready_summary`
- `wait_energy_trace_summary`
- `wait_state_semantic_summary`
- `wait_decision_summary`
- `wait_state_decision_bridge_summary`

의미:

- `wrong_ready_count`
  - `blocked_by != ""`인데 `READY`처럼 남은 recent row 개수
- `wait_energy_trace_summary.entry_wait_state_trace`
  - wait state를 만들 때 energy hint가 실제로 얼마나 소비됐는지
- `wait_energy_trace_summary.entry_wait_decision_trace`
  - 최종 wait decision까지 energy hint가 얼마나 영향을 줬는지
- `wait_state_semantic_summary.wait_state_counts`
  - 최근 wait state가 어떤 이름으로 가장 많이 잡히는지
- `wait_state_semantic_summary.hard_wait_state_counts`
  - 최근 wait state 중 실제 hard wait로 굳는 쪽이 어디인지
- `wait_decision_summary.wait_selected_rate`
  - recent row 중 실제 `wait`가 선택된 비율
- `wait_state_decision_bridge_summary.state_to_decision_counts`
  - 특정 wait state가 실제로 어떤 decision으로 이어졌는지


### Step 3. 최근 row를 CSV로 직접 확인한다

- `entry_decisions.csv` 최근 `200~300행`

먼저 찾을 것:

- `blocked_by != ""` 인데 `consumer_check_stage = READY`
- `blocked_by != ""` 인데 `consumer_check_entry_ready = true`
- `BLOCKED + display_ready=true`

주로 같이 볼 필드:

- `blocked_by`
- `action_none_reason`
- `consumer_check_stage`
- `consumer_check_display_ready`
- `consumer_check_entry_ready`
- `entry_wait_state`
- `entry_wait_decision`
- `entry_wait_energy_usage_trace_v1`
- `entry_wait_decision_energy_usage_trace_v1`


## 3. `wait_energy_trace_summary` 읽는 법

경로:

- 전체 요약:
  - `recent_runtime_diagnostics.windows.last_200.wait_energy_trace_summary`
- 심볼별 요약:
  - `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_energy_trace_summary`

핵심 필드:

- `trace_present_rows`
  - trace payload가 존재한 row 수
- `trace_branch_rows`
  - 실제 branch record까지 남은 row 수
- `usage_source_counts`
  - `recorded / inferred / not_yet_consumed`
- `usage_mode_counts`
  - `wait_state_branch_applied / wait_decision_branch_applied / not_consumed`
- `branch_counts`
  - 최근 window에서 실제로 많이 소비된 branch

branch 해석:

- `helper_soft_block_state`
  - state 단계에서 soft block이 자주 걸림
- `helper_soft_block_hard_wait`
  - soft block 강도가 높아서 hard wait 성격으로 잠김
- `helper_wait_bias_state`
  - low-readiness + prefer-wait 성향이 state 단계에서 누적됨
- `wait_soft_helper_block_decision`
  - decision 단계에서 실제 wait 선택까지 이어짐
- `wait_soft_helper_bias_decision`
  - soft block보다는 bias/readiness 쪽으로 wait가 선택됨


## 4. `wait semantic summary` 읽는 법

경로:

- 전체 요약:
  - `recent_runtime_diagnostics.windows.last_200.wait_state_semantic_summary`
  - `recent_runtime_diagnostics.windows.last_200.wait_decision_summary`
  - `recent_runtime_diagnostics.windows.last_200.wait_state_decision_bridge_summary`
- 심볼별 요약:
  - `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_state_semantic_summary`
  - `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_decision_summary`
  - `recent_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.wait_state_decision_bridge_summary`

핵심 필드:

- `wait_state_counts`
  - 최근 window에서 어떤 wait state가 자주 등장했는지
- `hard_wait_state_counts`
  - 최근 window에서 어떤 wait state가 실제 hard wait로 많이 굳었는지
- `wait_decision_counts`
  - `skip / wait_*` decision이 어떻게 나뉘는지
- `wait_selected_rate`
  - recent row 중 실제 wait가 선택된 비율
- `state_to_decision_counts`
  - 특정 wait state가 어떤 decision 결과로 이어졌는지

wait state taxonomy 빠른 해석:

- `POLICY_BLOCK / POLICY_SUPPRESSED / AGAINST_MODE`
  - policy/layer mode나 허용 방향 mismatch 성격
- `HELPER_SOFT_BLOCK / HELPER_WAIT`
  - energy/helper가 wait를 강하게 만든 상태
- `EDGE_APPROACH / NEED_RETEST / PROBE_CANDIDATE`
  - 구조적 접근/재테스트/probe 장면 대기
- `CENTER / CONFLICT / NOISE`
  - 중립/충돌/잡음 계열로, state는 많아도 decision 단계에선 `skip`으로 잘 풀릴 수 있음
- `ACTIVE`
  - 일반 보류처럼 보이지만 scene-specific observe/hold가 섞일 수 있어 `state_to_decision_counts`를 같이 봐야 함

hard wait / soft wait 바로 읽기:

- `hard_wait_state_counts`가 높다
  - 해당 state가 단순 관찰이 아니라 실제 강한 대기/차단 성격으로 굳는 편
- `wait_state_counts`는 높은데 `wait_selected_rate`가 낮다
  - state는 자주 보이지만 decision 단계에서 많이 풀리는 패턴
- `hard_wait_state_counts`와 `wait_selected_rate`가 같이 높다
  - 최근 window에서 실제 wait가 강하게 주도되는 패턴

심볼별로 볼 때는 이 순서가 가장 빠르다:

1. `symbol_summary.<SYMBOL>.wait_state_semantic_summary`
2. `symbol_summary.<SYMBOL>.wait_decision_summary`
3. `symbol_summary.<SYMBOL>.wait_state_decision_bridge_summary`
4. `symbol_summary.<SYMBOL>.wait_energy_trace_summary`

바로 읽는 법:

- `HELPER_SOFT_BLOCK`가 높고 `hard_wait_state_counts`도 같이 높다
  - helper soft block이 wait를 강하게 주도하는 상태
- `CENTER -> skip`이 높다
  - 중앙/중립 상태는 자주 보이지만 실제 wait 선택까지는 잘 이어지지 않음
- `PROBE_CANDIDATE -> wait_*`가 높다
  - probe 장면이나 scene-specific wait가 최근 wait 흐름을 주도 중
- `wait_selected_rate`가 높지 않은데 `wait_state_counts`만 높다
  - state는 자주 잡히지만 decision 단계에서는 풀리는 경우가 많음


## 5. 증상별 바로 해석

- `wrong_ready_count > 0`
  - late blocked rewrite 또는 consumer-check propagation을 먼저 의심
- `helper_soft_block_state`는 많은데 `wait_soft_helper_block_decision`은 적다
  - state에서는 압력이 있는데 decision까지는 덜 이어짐
  - `wait_engine` decision margin이나 다른 wait branch가 섞였는지 확인
- `wait_soft_helper_block_decision`이 높다
  - energy hint가 실제 wait 선택의 주 원인일 가능성이 큼
- wait가 많은데 wait-energy trace는 거의 없다
  - energy가 아니라 `observe / policy / core / threshold` 쪽 원인일 가능성이 큼
- `POLICY_BLOCK / POLICY_SUPPRESSED`가 높다
  - policy/layer mode와 허용 방향 제약을 먼저 본다
- `EDGE_APPROACH / NEED_RETEST`는 많은데 `wait_selected_rate`는 낮다
  - 구조적 관찰 state는 자주 뜨지만 decision 단계에서 release가 많이 나는 패턴
- `ACTIVE`가 많은데 `state_to_decision_counts`가 넓게 퍼진다
  - generic hold가 아니라 scene-specific wait와 일반 observe가 섞여 있을 가능성이 크다


## 6. 첫 점검 메모 템플릿

- 시각:
- 본 window:
- 심볼별 현재 상태:
- `wrong_ready_count`:
- top `blocked_reason_counts`:
- top `wait_energy` branch:
- top `wait_state_counts`:
- top `wait_decision_counts`:
- 제일 먼저 다시 볼 파일/함수:


## 7. 다음 행동 가이드

- wrong READY류가 보이면:
  - `consumer_check_state_v1`
  - late blocked rewrite
  - chart/state propagation
- wait-energy branch가 과도하게 높으면:
  - `wait_engine`
  - `energy_helper_v2`
  - `entry_wait_*_trace`
- wait state는 많은데 실제 `wait_selected_rate`는 낮으면:
  - `entry_wait_state_policy_v1`
  - `entry_wait_decision_policy_v1`
  - `entry_wait_state_policy_input_v1`
- 특정 state에서 특정 decision으로만 과도하게 쏠리면:
  - `entry_wait_context_v1`
  - `entry_wait_bias_bundle_v1`
  - `wait_state_decision_bridge_summary`
- policy 계열 state가 높으면:
  - `entry_wait_state_policy_input_v1`
  - `consumer_layer_mode_*`
  - `consumer_policy_block_*`
- probe/edge 계열 state가 높으면:
  - `entry_probe_plan_v1`
  - `entry_wait_context_v1`
  - `wait_state_decision_bridge_summary`
- 최근 흐름은 멀쩡한데 시각 표현만 이상하면:
  - `chart_painter`
- `chart_flow_policy`


## 8. exit quick read

먼저 보는 경로:

- `runtime_status.json`
  - `recent_exit_summary_window`
  - `recent_exit_status_counts`
  - `recent_exit_state_semantic_summary`
  - `recent_exit_decision_summary`
  - `recent_exit_state_decision_bridge_summary`
- `runtime_status.detail.json`
  - `recent_exit_runtime_diagnostics.windows.last_200.exit_state_semantic_summary`
  - `recent_exit_runtime_diagnostics.windows.last_200.exit_decision_summary`
  - `recent_exit_runtime_diagnostics.windows.last_200.exit_state_decision_bridge_summary`
  - `recent_exit_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>.*`

읽는 순서:

1. state
2. decision
3. bridge

즉
`최근 청산 state가 어떤 계열로 많나 -> 실제로 어디로 기울었나 -> 둘이 어떻게 이어졌나`
순서로 보면 된다.

전용 가이드는 아래 문서에 있다.

- `docs/current_exit_runtime_read_guide_ko.md`
