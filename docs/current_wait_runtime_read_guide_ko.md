# 현재 wait runtime 읽기 가이드

부제: recent wait 흐름을 CSV 없이 먼저 읽기 위한 실전 가이드

작성일: 2026-03-29 (KST)

## 1. 이 문서의 목적

이 문서는 현재 wait 축을 운영 관점에서 읽는 가장 짧은 경로를 정리한 가이드다.

목표는 단순하다.

- `runtime_status.json`
- `runtime_status.detail.json`

만으로 먼저

- 최근 wait가 왜 많은지
- 어떤 state가 주도 중인지
- 실제 wait 선택까지 이어지는지
- energy/helper가 원인인지
- policy/observe/probe가 원인인지

를 5분 안에 1차 해석하는 것이다.


## 2. 먼저 보는 순서

추천 순서는 아래와 같다.

1. `runtime_status.json`의 `latest_signal_by_symbol`
2. `runtime_status.detail.json`의 `recent_runtime_diagnostics.windows.last_200`
3. 같은 window의 `symbol_summary.<SYMBOL>`
4. 필요할 때만 `entry_decisions.csv` 최근 200~300행
5. 그래도 안 풀리면 관련 policy/helper 코드

핵심은
`latest current state -> recent distribution -> symbol-specific pattern -> row truth`
순서로 내려가는 것이다.


## 3. Step 1. latest row에서 현재 축을 본다

먼저 심볼별 latest row에서 아래를 본다.

- `action`
- `observe_reason`
- `blocked_by`
- `consumer_check_stage`
- `entry_wait_state`
- `entry_wait_decision`

여기서 먼저 답할 질문은 이것이다.

- 지금 막힌 축이 observe 쪽인가
- consumer blocked인가
- wait 쪽인가
- execution 쪽인가

즉 latest row는 “지금 현재 어떤 레이어에서 멈추는가”를 보는 용도다.


## 4. Step 2. recent summary에서 패턴을 본다

그다음 `recent_runtime_diagnostics.windows.last_200`에서 아래를 본다.

- `wrong_ready_count`
- `blocked_reason_counts`
- `wait_energy_trace_summary`
- `wait_state_semantic_summary`
- `wait_decision_summary`
- `wait_state_decision_bridge_summary`

여기서는 한 건이 아니라
최근 흐름 전체가 어떤 방향으로 쏠리는지 본다.


## 5. wait state taxonomy 빠른 해석

wait state는 아래 다섯 묶음으로 먼저 보면 해석이 빨라진다.

### 5-1. 정책/허용 방향 계열

- `POLICY_BLOCK`
- `POLICY_SUPPRESSED`
- `AGAINST_MODE`

이 계열이 높으면
energy보다 policy/layer mode, 허용 방향, consumer gate를 먼저 본다.

### 5-2. helper 주도 계열

- `HELPER_SOFT_BLOCK`
- `HELPER_WAIT`

이 계열이 높으면
energy/helper hint가 wait를 만든 경우가 많다.

### 5-3. 구조적 관찰 계열

- `EDGE_APPROACH`
- `NEED_RETEST`
- `PROBE_CANDIDATE`

이 계열은 방향 가장자리 접근, retest 필요, probe 장면 대기처럼
구조적 이유로 wait가 생긴 경우다.

### 5-4. 중립/충돌 계열

- `CENTER`
- `CONFLICT`
- `NOISE`

이 계열은 state는 자주 보이지만
decision 단계에서는 `skip`으로 풀릴 수 있는 경우가 많다.

### 5-5. 일반 보류/scene hold 계열

- `ACTIVE`

`ACTIVE`는 단순 generic hold처럼 보이지만
scene-specific observe/hold가 섞일 수 있어서
반드시 `state_to_decision_counts`를 같이 본다.


## 6. hard wait / soft wait 읽는 법

이 구분은 최근 흐름을 해석할 때 중요하다.

- `hard_wait_state_counts`가 높다
  - 단순 관찰이 아니라 실제 강한 대기/차단 쪽으로 굳는 패턴
- `wait_state_counts`는 높은데 `wait_selected_rate`는 낮다
  - state는 보이지만 decision 단계에서 release가 많이 나는 패턴
- `hard_wait_state_counts`와 `wait_selected_rate`가 같이 높다
  - 최근 window에서 실제 wait가 강하게 주도되는 패턴


## 7. energy trace와 semantic summary를 함께 읽는 법

둘은 역할이 다르다.

- `wait_energy_trace_summary`
  - energy/helper가 실제 얼마나 소비되었는지
- `wait_state_semantic_summary`
  - 최근 wait state가 무엇으로 잡히는지
- `wait_decision_summary`
  - 최종적으로 어떤 decision이 나오는지
- `wait_state_decision_bridge_summary`
  - 그 state가 어떤 decision으로 이어지는지

즉 energy trace는 “원인 후보”를 보여주고,
semantic summary는 “표면 의미와 결과”를 보여준다.


## 8. 심볼별로 읽을 때의 표준 순서

심볼 하나를 깊게 볼 때는 이 순서가 가장 좋다.

1. `symbol_summary.<SYMBOL>.wait_state_semantic_summary`
2. `symbol_summary.<SYMBOL>.wait_decision_summary`
3. `symbol_summary.<SYMBOL>.wait_state_decision_bridge_summary`
4. `symbol_summary.<SYMBOL>.wait_energy_trace_summary`

이 순서를 쓰면

- 어떤 state가 많은가
- 실제 어떤 decision으로 이어지나
- 그 뒤에 energy/helper가 있나

를 자연스럽게 이어 볼 수 있다.


## 9. 자주 나오는 해석 패턴

- `HELPER_SOFT_BLOCK`가 높고 `hard_wait_state_counts`도 높다
  - helper soft block이 wait를 강하게 주도하는 패턴
- `CENTER -> skip`이 높다
  - 중립/중앙 상태는 자주 보이지만 실제 wait 선택까지는 덜 이어진다
- `PROBE_CANDIDATE -> wait_*`가 높다
  - probe 장면이나 scene-specific wait가 최근 흐름을 주도한다
- `wait_selected_rate`는 낮은데 `wait_state_counts`만 높다
  - state는 많지만 decision 단계에서 release가 많다
- `wait_soft_helper_block_decision`이 높다
  - energy/helper가 실제 wait 선택의 주 원인일 가능성이 크다
- wait가 많은데 energy trace는 약하다
  - energy보다 policy, observe, threshold, structural wait 쪽 원인을 먼저 본다


## 10. 언제 CSV로 내려가야 하나

아래 경우에는 `entry_decisions.csv` 최근 200~300행으로 내려가는 것이 좋다.

- `wrong_ready_count > 0`
- 특정 state와 decision 연결이 예상과 다르게 보일 때
- symbol summary와 전체 summary가 서로 다른 말을 할 때
- wait trace는 높은데 latest row 해석이 잘 안 붙을 때

즉 CSV는 1차 진단 도구가 아니라
runtime summary가 가설을 세운 뒤 truth row를 확인하는 마지막 단계로 쓰는 편이 좋다.


## 11. 함께 보면 좋은 문서

- `docs/thread_restart_handoff_ko.md`
- `docs/thread_restart_first_checklist_ko.md`
- `docs/current_wait_architecture_reorganization_phase_w5_completion_summary_ko.md`
