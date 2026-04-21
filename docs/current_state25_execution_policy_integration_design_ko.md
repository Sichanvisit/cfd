# State25 Execution Policy Integration Design

## 목적

이 문서는 `AI5 execution policy integration`을 어떻게 시작할지 정리한다.

핵심은 간단하다.

- 후보 모델이 좋아 보여도 바로 주문 로직을 바꾸지 않는다
- 먼저 `어떤 실행 축에만` 닿게 할지 정한다
- 그 축을 `read-only -> log-only -> narrow canary -> bounded live` 순서로 연다

## 지금 AI5를 왜 분리해야 하나

AI3는 후보를 만들고 비교한다.
AI4는 올릴지 말지를 판단한다.

하지만 실제 수익에 닿으려면 결국 실행 정책이 바뀌어야 한다.

그런데 여기서 바로 전체 진입 로직을 건드리면 위험하다.

그래서 AI5는 아래 질문에 답하는 층이다.

- 지금 후보가 threshold를 건드려도 되는가
- 지금 후보가 size를 건드려도 되는가
- 지금 후보가 wait policy를 건드려도 되는가
- 아직 건드리면 안 되는 축은 무엇인가

## AI5 1차 범위

이번 구현은 실제 live binding이 아니라 `실행 정책 추천기`다.

즉 이번 단계는:

1. AI4 gate 결과 읽기
2. compare report에서 task readiness 읽기
3. runtime status에서 현재 execution surface 읽기
4. threshold / size / wait / risk 축별 추천 상태 만들기
5. 사람이 읽는 md/json 보고서 생성

중요한 점:

- 아직 `.env`를 바꾸지 않는다
- 아직 runtime entry threshold를 자동으로 바꾸지 않는다
- 아직 wait policy multiplier를 live에 직접 넣지 않는다

이번 단계는 `무엇을 열 수 있는지`를 안전하게 정리하는 단계다.

## 입력

### 1. AI4 gate report

- `models/teacher_pattern_state25_candidates/latest_gate_report.json`

여기서 읽는 핵심 값:

- `gate_stage`
- `recommended_action`
- `compare_report_path`

### 2. AI3 compare report

여기서 읽는 핵심 값:

- `group_task` ready 여부
- `pattern_task` ready 여부
- `economic_total_task` ready 여부
- `wait_quality_task` ready 여부

핵심 해석:

- `economic_total_task`가 열려야 threshold / size에 의미를 줄 수 있다
- `wait_quality_task`가 열려야 wait policy에 의미를 줄 수 있다

### 3. runtime status

- `data/runtime_status.json`

여기서 읽는 핵심 값:

- `entry_threshold`
- `exit_threshold`
- `semantic_live_config.mode`
- `symbol_allowlist`
- `entry_stage_allowlist`

## AI5 1차 권장 연결 축

### 1. threshold surface

가장 먼저 열기 좋은 축이다.

이유:

- 영향 범위가 명확하다
- log-only 비교가 쉽다
- candidate가 좋지 않으면 곧바로 0 point adjustment로 되돌릴 수 있다

1차 원칙:

- `promote_ready` 전에는 열지 않는다
- `economic_total_task_ready`일 때만 본다
- 첫 단계는 `log_only`
- 조정 범위는 좁게 `±4 pts`

### 2. size surface

threshold 다음으로 열기 좋다.

이유:

- bounded canary에서 위험을 줄이기 쉽다
- 수익 개선보다 먼저 손실 확대를 막는 안전장치로 쓸 수 있다

1차 원칙:

- `promote_ready` 전에는 열지 않는다
- `economic_total_task_ready`일 때만 본다
- 첫 단계는 `log_only`
- multiplier 범위는 좁게 `0.75 ~ 1.00`

### 3. wait surface

가장 늦게 열어야 한다.

이유:

- 지금도 wait는 민감한 층이다
- `wait_quality_task`가 아직 sparse하면 잘못된 방향으로 굳을 수 있다

1차 원칙:

- `wait_quality_task_ready` 전에는 무조건 `observe_only`
- readiness가 생겨도 바로 live 적용하지 않고 `log_only`

### 4. risk surface

이번 1차에선 실제 bind를 미룬다.

이유:

- spread / slippage / noise 가중은 실제로 돈과 가깝지만 해석도 까다롭다
- threshold / size / wait보다 늦게 여는 게 안전하다

## integration stage 해석

### `disabled_hold`

- candidate가 아직 실행에 닿으면 안 된다
- current baseline 유지

### `read_only_recommendation`

- candidate는 보기엔 쓸 만할 수 있다
- 하지만 아직 shadow / canary 이전이다
- recommendation report만 본다

### `log_only_candidate_bind_ready`

- gate는 통과했다
- threshold / size 중심으로 log-only 비교를 시작할 수 있다

### `disabled_rollback_hold`

- canary나 gate에서 위험 신호가 나왔다
- candidate-linked execution surface를 끈다

## 이번 AI5의 출력

candidate 폴더마다 아래 파일이 생긴다.

- `teacher_pattern_execution_policy_integration_report.json`
- `teacher_pattern_execution_policy_integration_report.md`

루트 latest 포인터:

- `models/teacher_pattern_state25_candidates/latest_execution_policy_integration_report.json`

## 현재 상태 해석

현재 latest gate는 `hold_offline`이다.

따라서 지금 AI5를 실제로 돌리면 자연스러운 결과는:

- `integration_stage = disabled_hold`
- threshold / size / wait / risk 모두 live bind 금지

이건 아무것도 못 하는 상태가 아니라,

`실행 정책을 아무 때나 건드리지 않게 막는 안전한 기본값`

이 생긴 것이다.
