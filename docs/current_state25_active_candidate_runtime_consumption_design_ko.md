# State25 Active Candidate Runtime Consumption Design

## 목적

이 문서는 `AI6 2차`에서 다룰 핵심 질문을 정리한다.

- runtime이 [active_candidate_state.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/active_candidate_state.json)을 어떻게 읽어야 하는가
- `log_only`, `canary`, `bounded_live`를 어떤 순서와 안전장치로 열어야 하는가
- `auto-promote / auto-rollback`의 계산 결과를 runtime이 어떤 방식으로 실제 소비해야 하는가

쉽게 말하면 이 문서는 `AI6 dry-run controller`와 `실제 runtime 반영` 사이의 마지막 빈칸을 메우는 설계 문서다.

## 왜 지금 이 문서가 필요한가

지금까지 이미 된 것은 아래와 같다.

- AI3가 candidate를 다시 만든다
- AI4가 `hold / log_only_ready / promote_ready / rollback_recommended`를 판정한다
- AI5가 `threshold / size / wait / risk` 추천 surface를 만든다
- AI6가 `promote_log_only_ready / rollback_ready`를 계산하고 active-state patch를 제안한다

하지만 아직 runtime은 그 결과를 직접 소비하지 않는다.

즉 지금 상태는 아래와 같다.

- candidate watch는 돌아간다
- gate / integration / actuator report도 나온다
- 그런데 실제 runtime은 여전히 `current_baseline`만 쓴다

그래서 `AI6 2차`가 필요하다.

## 이 단계의 핵심 원칙

### 1. 계산과 적용은 분리한다

AI3~AI6이 계산한 결과가 좋아 보여도 바로 live 정책을 바꾸면 안 된다.

그래서 순서는 아래처럼 간다.

1. 계산
2. active state 기록
3. runtime read
4. `log_only` 소비
5. `canary`
6. `bounded_live`

즉 `좋아 보인다 -> 곧바로 실매매 변경`이 아니라,
`좋아 보인다 -> runtime이 읽는다 -> log_only로 먼저 확인한다 -> 일부만 실제 반영한다` 순서다.

### 2. file missing은 오류가 아니라 baseline fallback이다

[active_candidate_state.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/active_candidate_state.json)이 아직 없을 수 있다.

이 경우 runtime은 아래처럼 해석해야 한다.

- `active_candidate_id = ""`
- `active_policy_source = current_baseline`
- `current_rollout_phase = disabled`
- `current_binding_mode = disabled`

즉 `파일 없음 = baseline 유지`이지, 예외로 런타임을 흔들면 안 된다.

### 3. phase2는 threshold / size만 다룬다

이번 단계에서 실제 runtime 소비 대상으로 보는 것은 아래 2개뿐이다.

- `threshold`
- `size`

아래 항목은 아직 phase2 범위 밖이다.

- wait policy 실제 반영
- risk policy 실제 반영
- symbol universe 자체 교체
- execution engine 구조 변경

이유는 간단하다.

- threshold / size는 비교적 국소적이다
- wait policy는 잘못 열면 진입 수와 품질을 동시에 크게 흔든다
- bounded live 전에는 `wait`를 건드리지 않는 편이 안전하다

## 현재 입력 계약

AI6 2차에서 runtime이 신뢰하는 입력은 아래 4개다.

1. [latest_gate_report.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/latest_gate_report.json)
2. [latest_execution_policy_integration_report.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/latest_execution_policy_integration_report.json)
3. [latest_execution_policy_log_only_binding_report.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/latest_execution_policy_log_only_binding_report.json)
4. [active_candidate_state.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/active_candidate_state.json)

다만 runtime이 직접 읽는 주 입력은 4번이다.

앞의 1~3번은 candidate watch와 AI6 report가 만드는 근거 문서고,
runtime은 그 계산 결과가 요약된 `active state`만 직접 소비한다.

## active_candidate_state contract

runtime은 최소 아래 필드만 읽으면 된다.

- `contract_version`
- `active_candidate_id`
- `active_policy_source`
- `current_rollout_phase`
- `current_binding_mode`
- `activated_at`
- `last_event`
- `desired_runtime_patch`

`desired_runtime_patch`에서 phase2 기준으로 읽는 키는 아래와 같다.

- `apply_now`
- `state25_execution_bind_mode`
- `state25_execution_symbol_allowlist`
- `state25_execution_entry_stage_allowlist`
- `state25_threshold_log_only_enabled`
- `state25_threshold_log_only_max_adjustment_abs`
- `state25_size_log_only_enabled`
- `state25_size_log_only_min_multiplier`
- `state25_size_log_only_max_multiplier`

### 해석 원칙

- 키가 없으면 보수적 기본값을 쓴다
- 타입이 이상하면 그 키만 무시한다
- `state25_execution_bind_mode != current_binding_mode`이면 `current_binding_mode`를 우선한다
- `current_rollout_phase = disabled`면 patch가 있어도 적용하지 않는다

## rollout phase 의미

### `disabled`

- baseline만 사용
- candidate threshold / size overlay 전부 비활성
- runtime status에는 `candidate disabled`만 남긴다

### `log_only`

- runtime이 candidate patch를 읽는다
- 하지만 실제 진입 기준과 실제 size는 baseline 그대로 둔다
- 대신 `candidate였으면 threshold가 얼마였는지`, `candidate였으면 size multiplier가 얼마였는지`를 trace와 status에 남긴다

즉 `consume`은 하지만 `live apply`는 하지 않는다.

### `canary`

- 실제 반영을 아주 좁은 범위에만 연다
- `symbol_allowlist`와 `entry_stage_allowlist` 둘 다 걸어서 제한한다
- threshold / size만 실제로 바뀔 수 있다

### `bounded_live`

- canary evidence가 통과된 뒤에만 연다
- 그래도 전면 live가 아니라 bounded scope 안에서만 연다

## log_only를 먼저 여는 이유

`log_only`는 아래 두 문제를 동시에 해결한다.

1. runtime이 active candidate를 제대로 읽는지 확인
2. 실제 live 의사결정은 아직 건드리지 않고 candidate patch가 어떤 방향으로 작동할지 관찰

즉 `phase2`에서 가장 중요한 것은
`실제 반영보다 먼저 runtime consumption과 observability를 완성하는 것`이다.

## runtime 쪽 책임 분리

### 1. reader 책임

대상 파일:

- [trading_application_runner.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)

역할:

- `active_candidate_state.json` 읽기
- 파일이 없거나 깨졌으면 baseline fallback
- `candidate_state_fingerprint` 계산
- 이전 loop와 달라졌을 때만 재적용

### 2. policy overlay 책임

대상 파일:

- [policy_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/policy_service.py)

역할:

- baseline policy snapshot 유지
- candidate log-only overlay 저장
- canary / bounded live용 실제 overlay 저장
- overlay clear / rollback 지원

중요한 점:

`PolicyService.entry_threshold` 같은 실제 live 값과
`candidate log_only threshold` 같은 shadow 값을 분리해서 들고 있어야 한다.

### 3. runtime status export 책임

대상 파일:

- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

역할:

- 현재 active candidate 정보 export
- rollout phase export
- threshold / size patch가 `disabled / log_only / canary / bounded_live` 중 어디인지 export
- last apply / last rollback reason export

## phase2에서 runtime이 실제로 해야 하는 일

### A. active candidate read

매 loop마다 또는 짧은 poll interval마다 active state를 읽는다.

필요 output:

- `candidate_id`
- `rollout_phase`
- `binding_mode`
- `patch_fingerprint`
- `state_source_status` (`loaded`, `missing_fallback`, `invalid_fallback`)

### B. threshold log-only consume

`log_only`일 때는 실제 entry threshold를 바꾸지 않는다.

대신 아래 값을 계산해 남긴다.

- baseline threshold
- candidate hypothetical threshold
- delta
- symbol / stage scope에 들어오는지 여부

즉 진입 trace에는 아래가 같이 보여야 한다.

- `baseline_entry_threshold`
- `candidate_log_only_entry_threshold`
- `candidate_log_only_threshold_delta`
- `candidate_log_only_scope_hit`

### C. size log-only consume

`log_only`일 때는 실제 주문 size를 바꾸지 않는다.

대신 아래를 계산해 남긴다.

- baseline size multiplier
- candidate hypothetical size multiplier
- min / max clamp
- symbol scope hit

### D. rollback consume

AI6가 baseline 복귀 state를 썼다면 runtime은 즉시 아래를 해야 한다.

- candidate overlay clear
- last active candidate id 기록
- `runtime_status`에 rollback event 기록

즉 rollback은 `실패한 후보를 baseline으로 되돌리는 실제 소비 동작`까지 포함한다.

## 추천 runtime 상태 계약

runtime status에는 최소 아래 block이 새로 필요하다.

### `state25_candidate_runtime_v1`

- `available`
- `state_source_status`
- `active_candidate_id`
- `active_policy_source`
- `rollout_phase`
- `binding_mode`
- `patch_fingerprint`
- `last_applied_fingerprint`
- `last_apply_at`
- `last_apply_reason`
- `last_rollback_at`
- `last_rollback_reason`

### `state25_candidate_threshold_surface_v1`

- `enabled`
- `mode`
- `scope_hit_symbols`
- `max_adjustment_abs`
- `baseline_entry_threshold`
- `candidate_log_only_entry_threshold`
- `actual_live_entry_threshold`

### `state25_candidate_size_surface_v1`

- `enabled`
- `mode`
- `symbol_scope`
- `baseline_min_multiplier`
- `candidate_min_multiplier`
- `candidate_max_multiplier`
- `actual_live_size_multiplier_mode`

이 block이 있어야 사람이
`지금 runtime이 읽고 있는지`, `읽기만 하는지`, `실제 반영했는지`
를 헷갈리지 않는다.

## auto-promote 실제 apply 원칙

지금 AI6 report는 `promote_log_only_ready`를 계산할 수 있다.

phase2에서 실제 apply는 아래까지만 연다.

- `promote_log_only_ready`면 active state write 허용
- runtime은 그 state를 읽고 `log_only`로만 소비

즉 phase2의 auto-promote는
`live threshold / size 실반영`이 아니라
`active candidate를 log-only runtime state로 승격`하는 것까지다.

## auto-rollback 실제 apply 원칙

`rollback_recommended`면 AI6는 active state를 baseline으로 되돌릴 수 있어야 한다.

runtime은 이 state를 읽고 아래를 해야 한다.

- candidate overlay clear
- active source를 `current_baseline`으로 재설정
- runtime status에 rollback 흔적 남기기

중요한 점:

rollback은 promote보다 더 보수적으로 동작해야 한다.

- candidate file이 이상하면 rollback
- runtime이 candidate patch를 해석 못하면 rollback
- canary evidence가 악화되면 rollback

## canary와 bounded_live는 왜 나중 단계인가

`log_only`는 계산과 관찰만 한다.
반면 `canary / bounded_live`는 실제 매매를 바꾼다.

그래서 아래 조건이 추가로 필요하다.

- AI4 gate가 `promote_ready`
- canary evidence가 존재
- rollback path가 이미 검증됨
- runtime status / logs에서 scope hit가 잘 보임

즉 canary는 `phase2 consume`이 안정화된 다음 단계다.

## phase2에서 아직 하지 않는 것

아래는 이번 문서 범위 밖이다.

- wait policy 실제 bind
- risk policy 실제 bind
- symbol allowlist 자체를 live symbol universe처럼 강제 교체
- candidate model artifact를 runtime model loader로 직접 갈아끼우기

이번 단계의 목표는
`state25 active candidate patch를 runtime이 읽고, threshold / size를 안전하게 소비하는 것`
이지, 모든 execution policy를 한 번에 바꾸는 것이 아니다.

## 왜 이렇게 구축해야 하는가

핵심 이유는 3개다.

1. `관찰 가능성`
   runtime이 무엇을 읽고 무엇을 무시하는지 보여야 한다.

2. `안전성`
   `log_only`와 실제 live apply를 분리해야 사고를 줄일 수 있다.

3. `복구 가능성`
   rollback이 promote보다 먼저 검증돼야 한다.

즉 이 구조는 느려 보일 수 있지만,
`점점 똑똑해지는 자동 구조`를 만들기 위해 필요한 최소 안전장치다.

## 한 줄 정리

AI6 2차의 핵심은 아래 한 문장으로 정리된다.

`runtime이 active_candidate_state를 baseline-safe하게 읽고, 먼저 threshold/size를 log_only로만 소비한 뒤, 그 다음에만 auto-promote apply와 canary/bounded_live로 확장한다.`
