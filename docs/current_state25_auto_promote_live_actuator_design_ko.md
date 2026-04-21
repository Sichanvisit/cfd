# State25 Auto Promote / Rollback / Live Actuator Design

## 목적

이 문서는 `AI6 auto-promote / rollback / live actuator`의 역할을 정리한다.

핵심은 간단하다.

- AI3는 후보를 다시 만든다
- AI4는 올릴지 막을지 판단한다
- AI5는 어떤 실행 정책을 열 수 있는지 추천한다
- AI6는 그 결과를 받아서 `지금 정말 올릴지`, `지금 내려야 하는지`, `실제 live actuator를 어느 단계로 둘지`를 한 곳에서 결정한다

즉 AI6는 `자동 재학습`과 `자동 실행 반영` 사이의 마지막 관제층이다.

## 왜 AI6가 따로 필요한가

AI3~AI5까지만 있으면 아직 이런 문제가 남는다.

- 후보가 좋아 보여도 누가 active candidate가 되는지 정해주는 owner가 없다
- rollback이 필요할 때 누가 기존 정책으로 되돌리는지 정해져 있지 않다
- log-only, canary, bounded live를 어떤 상태 파일로 이어서 관리할지 기준이 없다

그래서 AI6가 필요하다.

AI6는 아래 3개를 동시에 본다.

1. `gate_stage`
2. `integration_stage`
3. `binding_mode`

그리고 현재 active candidate 상태까지 같이 읽어서 다음 액션을 하나로 정리한다.

## AI6의 입력

### 1. latest gate report

- `models/teacher_pattern_state25_candidates/latest_gate_report.json`

### 2. latest execution policy integration report

- `models/teacher_pattern_state25_candidates/latest_execution_policy_integration_report.json`

### 3. latest log-only binding report

- `models/teacher_pattern_state25_candidates/latest_execution_policy_log_only_binding_report.json`

### 4. active candidate state

- `models/teacher_pattern_state25_candidates/active_candidate_state.json`

현재 active candidate가 누구인지, rollout phase가 어디인지, binding mode가 무엇인지를 여기서 읽는다.

## AI6 1차 범위

이번 1차 구현은 안전하게 `dry-run 기본`으로 둔다.

즉 지금 AI6가 하는 일은:

- 올릴 수 있는지 계산
- 내려야 하는지 계산
- 어떤 상태 파일을 써야 하는지 계산
- 사람이 읽기 쉬운 md/json으로 남김

아직 바로 안 하는 일:

- `.env`를 직접 바꾸기
- runtime threshold를 즉시 변경하기
- wait policy를 즉시 변경하기
- MT5 live 진입 조건을 즉시 바꾸기

이번 단계는 `결정을 한 곳에 모으는 단계`다.

## AI6 controller stage

### `hold_disabled`

아직 gate가 promote-ready가 아니거나 integration/binding이 live actuator를 열 수 없는 상태다.

### `promote_log_only_ready`

이 조합일 때다.

- gate는 `promote_ready`
- integration은 `log_only_candidate_bind_ready`
- binding은 `log_only`

이때는 후보를 active candidate로 올리되, rollout phase는 `log_only`까지만 허용한다.

### `already_promoted_log_only`

같은 candidate가 이미 active이고 rollout phase도 `log_only`인 상태다. 이때는 다시 promote하지 않고 canary evidence만 더 모은다.

### `rollback_ready`

gate가 `rollback_recommended`이고 현재 active candidate가 문제 candidate와 동일할 때다. 이때는 active policy source를 다시 `current_baseline`으로 되돌릴 준비가 된 상태다.

## 상태 파일 설계

### active_candidate_state.json

이 파일은 AI6의 현재 결정을 기록하는 레지스트리다.

핵심 필드:

- `active_candidate_id`
- `active_policy_source`
- `current_rollout_phase`
- `current_binding_mode`
- `desired_runtime_patch`
- `last_event`

초기값은 아래와 같다.

- `active_candidate_id = ""`
- `active_policy_source = current_baseline`
- `current_rollout_phase = disabled`
- `current_binding_mode = disabled`

### auto_promote_history.jsonl

이 파일은 승격/롤백 이력을 줄 단위로 쌓는다.

왜 필요한가:

- 언제 어떤 candidate를 올렸는지
- 왜 내렸는지
- 어떤 상태 파일을 썼는지

를 나중에 복기할 수 있어야 하기 때문이다.

## promote 동작

AI6가 promote를 허용하는 첫 단계는 `log_only`뿐이다.

즉 이번 설계의 기본 원칙은:

- 좋아 보인다고 바로 bounded live로 가지 않는다
- 먼저 active candidate를 `log_only`로 올린다
- 그 상태에서 canary evidence를 더 쌓는다

## rollback 동작

rollback은 더 보수적으로 본다.

조건:

- gate stage가 `rollback_recommended`
- 현재 active candidate가 문제 candidate와 같다

이때 AI6는:

- active candidate를 비운다
- policy source를 `current_baseline`으로 되돌린다
- threshold/size log-only patch도 disabled로 만든다

즉 rollback은 `후보 해제 + baseline 복귀`를 의미한다.

## candidate watch와의 관계

`state25_candidate_watch.py`는 15분마다 AI3~AI5를 다시 돌린다.

AI6는 여기에 붙어서 같은 cycle 안에서:

- 이번 후보를 올릴 준비가 됐는지
- 아직 보류인지
- 이미 active인지
- 되돌려야 하는지

를 같이 계산한다.

현재 기본값은 `apply_ai6 = false`다. 즉 candidate watch가 AI6까지 계산은 하지만, 아직 상태 파일을 실제로 쓰지는 않는다.

## 이번 1차 설계의 의미

AI6는 바로 돈을 벌게 만드는 마법 스위치가 아니라, 자동 승격과 자동 롤백을 안전하게 시작하기 위한 마지막 제어층이다.

지금 단계에서는 `dry-run controller`가 먼저 맞다.

그 다음에야:

1. active state 실제 적용
2. runtime consumption
3. bounded live

순서로 가는 게 안전하다.
