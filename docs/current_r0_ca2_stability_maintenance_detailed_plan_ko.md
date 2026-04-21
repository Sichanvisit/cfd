# R0 CA2 안정 유지 상세 계획

## 1. 목적

이 문서는 `CA2` 검증 축의 가장 첫 단계인 `R0. CA2 안정 유지`를 별도 운영 단계로 정의한다.

지금 이 단계의 목표는 새 판단 규칙을 더 붙이는 것이 아니다.
이미 붙어 있는 아래 축이 **계속 살아서 누적되는지**를 확인하는 것이다.

- `execution_diff`
- `continuation_accuracy`
- `guard / promotion`의 기반 trace
- `row ↔ flow history` 동기화

즉 `R0`는 기능 개선 단계가 아니라, **검증 체계를 지키는 단계**다.

## 2. 왜 R0가 따로 필요한가

현재 시스템은 이미 많은 축이 연결되어 있다.

- `current-cycle overlay -> execution`
- `execution_diff_*` live surface
- `flow history`와 row surface 동기화
- `continuation_accuracy` 누적
- `runtime_signal_wiring_audit_summary_v1`

하지만 이 상태에서 세션-aware annotation이나 state25 확장을 얹기 전에, 아래 질문이 먼저 닫혀야 한다.

1. `execution_diff`가 계속 live row에 남는가
2. `flow history`가 canonical row와 계속 맞는가
3. `continuation_accuracy`가 계속 누적되는가
4. 이 세 가지가 주기적으로 비거나 깨지지 않는가

이게 닫히지 않으면 이후 `R1~R6`는 숫자로 검증할 수 없다.

## 3. R0에서 실제로 보는 핵심 지표

### 3-1. 배선/표면화

- `execution_diff_surface_count`
- `flow_sync_match_count`
- `symbol_count`

이 세 값으로 지금 사이클에서 배선과 동기화가 살아 있는지 본다.

### 3-2. 누적

- `primary_measured_count`
- `primary_correct_rate`
- `resolved_observation_count`

여기서 중요한 것은 `correct_rate` 절대값만이 아니다.
`measured_count`가 계속 쌓이고 있는지가 먼저다.

### 3-3. 보조 상태

- `ai_entry_trace_count`
- `ai_entry_trace_execution_diff_count`
- detail payload 생성 여부
- artifact 생성 여부

## 4. 현재 이미 있는 재료

R0를 위해 새 재료를 만들 필요는 거의 없다. 아래가 이미 있다.

- [runtime_signal_wiring_audit.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/runtime_signal_wiring_audit.py)
- [directional_continuation_accuracy_tracker.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/directional_continuation_accuracy_tracker.py)
- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

즉 R0 구현의 핵심은 새 분석 축을 만드는 게 아니라, **기존 두 summary를 묶어서 R0 상태를 판정하는 것**이다.

## 5. 아직 부족한 구조

현재는 아래 문제가 남아 있다.

1. `wiring audit`와 `accuracy summary`는 있지만, `R0 READY/HOLD/BLOCKED`를 한 번에 읽는 상태 판정이 없다.
2. 직전 사이클과 비교해 `누적이 계속되고 있는지`를 한눈에 볼 수 없다.
3. 문서상 `R0` 기준이 코드 artifact로 직접 연결되지 않는다.

즉 지금 필요한 건 새 규칙이 아니라 **운영 판정기**다.

## 6. R0 상태 판정 원칙

### 6-1. READY

아래가 동시에 만족되면 `READY`로 본다.

- `symbol_count > 0`
- `execution_diff_surface_count == symbol_count`
- `flow_sync_match_count == symbol_count`
- `primary_measured_count > 0`
- 직전 snapshot 대비 `primary_measured_count`가 감소하지 않음

### 6-2. HOLD

아래 같은 경우는 `HOLD`다.

- detail/trace가 간헐적으로 비는 경우
- `execution_diff_surface_count < symbol_count`
- `flow_sync_match_count < symbol_count`
- 첫 snapshot이라 누적 추세를 아직 판단하기 어려운 경우
- `primary_measured_count`는 있으나 이번 관측에서 증가 여부가 확실하지 않은 경우

### 6-3. BLOCKED

아래는 `BLOCKED`다.

- `symbol_count == 0`
- `primary_measured_count == 0`이 지속됨
- `execution_diff_surface_count == 0`
- `flow_sync_match_count == 0`
- 직전 대비 `primary_measured_count`가 뒤로 감
- artifact/detail 생성 자체가 실패함

## 7. 구현 원칙

### 7-1. 기존 집계는 건드리지 않는다

R0 구현은 아래를 다시 계산하지 않는다.

- continuation accuracy core logic
- execution diff core logic
- wiring audit core logic

대신 이미 만들어진 summary를 읽어서 **상태만 판정**한다.

### 7-2. 이전 snapshot과 비교한다

`R0`의 핵심은 “지금 값이 있다”보다 “계속 살아 있다”다.
따라서 이전 artifact를 읽어 변화량(`delta`)을 같이 본다.

### 7-3. 상태 판정은 보수적으로 한다

세 값이 조금만 빈다고 바로 `BLOCKED`로 가지 않는다.
간헐적 누락은 `HOLD`, 기반 축이 실제로 깨진 경우만 `BLOCKED`로 둔다.

## 8. 산출물

R0 구현의 출력은 아래 두 가지다.

- `runtime_status.detail.json` 안의
  - `ca2_r0_stability_summary_v1`
  - `ca2_r0_stability_artifact_paths`
- 별도 artifact
  - `data/analysis/shadow_auto/ca2_r0_stability_latest.json`
  - `data/analysis/shadow_auto/ca2_r0_stability_latest.md`

## 9. R0가 닫혔는지의 의미

R0가 닫혔다는 건 “정확도가 충분히 높다”는 뜻이 아니다.
의미는 이렇다.

- live 검증 계측 체계가 안정적으로 계속 돈다
- 이후 `R1` 세션 분해를 해도 기준이 흔들리지 않는다
- `R2~R3` annotation 축을 얹어도 원래 CA2가 깨지지 않는다

즉 R0의 성공은 성능 개선이 아니라 **검증 기반 확보**다.
