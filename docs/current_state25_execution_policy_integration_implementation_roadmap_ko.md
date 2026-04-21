# State25 Execution Policy Integration Implementation Roadmap

## 목표

이 문서는 `AI5`를 작업 순서로 자른 구현 로드맵이다.

쉽게 말하면:

- 무엇부터 만들고
- 어디까지 검증하면
- 실제 execution binding 직전까지 갈 수 있는지

를 적는다.

## AI5 단계 분해

### EP1. Gate Bind

할 일:

- latest gate report 읽기
- gate stage에 따라 integration stage를 정하기

완료 기준:

- `hold / read_only / log_only_ready / rollback_hold` 중 어디인지 자동으로 보인다

### EP2. Task Readiness Bind

할 일:

- compare report에서 `group / pattern / economic / wait_quality` readiness 읽기

완료 기준:

- 어떤 실행 축을 열 수 있고 어떤 축은 아직 못 여는지 자동으로 보인다

### EP3. Runtime Surface Snapshot

할 일:

- runtime status에서 현재 threshold / semantic live mode / symbol allowlist / stage allowlist 읽기

완료 기준:

- 추천안이 현재 운영 설정과 나란히 비교된다

### EP4. Surface Recommendation

할 일:

- threshold surface 추천
- size surface 추천
- wait surface 추천
- risk surface 추천

완료 기준:

- 각 surface마다 `enabled / mode / reason`이 나온다

### EP5. Rollout Plan

할 일:

- read-only recommendation
- log-only comparison
- narrow canary
- bounded live action

순서를 candidate stage와 함께 요약한다

완료 기준:

- 지금 후보가 어느 rollout 단계까지 갈 수 있는지 보인다

### EP6. Human Summary

할 일:

- md summary를 생성해서 사람이 바로 읽게 한다

완료 기준:

- json을 열지 않아도 현재 execution integration 상태를 이해할 수 있다

## 이번 구현 파일

- `backend/services/teacher_pattern_execution_policy_integration.py`
- `scripts/teacher_pattern_execution_policy_integration_report.py`
- `docs/current_state25_execution_policy_integration_design_ko.md`
- `docs/current_state25_execution_policy_integration_implementation_roadmap_ko.md`

## 실행 명령

기본 실행:

```powershell
python scripts/teacher_pattern_execution_policy_integration_report.py
```

이 명령은 아래 순서로 동작한다.

1. latest gate report 읽기
2. compare report 읽기
3. runtime status 읽기
4. integration stage 판단
5. surface recommendation 생성
6. md/json 결과 저장

## 출력 위치

candidate 폴더:

- `teacher_pattern_execution_policy_integration_report.json`
- `teacher_pattern_execution_policy_integration_report.md`

candidate root:

- `latest_execution_policy_integration_report.json`

## 해석 방법

### 지금은 아무것도 열면 안 됨

- `integration_stage = disabled_hold`
- 또는 `disabled_rollback_hold`

### 아직 recommendation만

- `integration_stage = read_only_recommendation`

### log-only까지 갈 수 있음

- `integration_stage = log_only_candidate_bind_ready`

이 경우에도 바로 live binding이 아니라:

- threshold / size만 우선
- wait는 readiness 있을 때만
- risk는 더 뒤로

## AI5 1차 완료 기준

아래가 되면 AI5 1차는 완료다.

1. latest gate 기준 execution integration report가 자동 생성된다
2. threshold / size / wait / risk surface 추천이 분리된다
3. task readiness에 따라 어떤 축을 묶을 수 있는지 보인다
4. rollout stage가 `read_only / log_only_ready`까지 구분된다
5. md summary로 사람이 바로 읽을 수 있다

## 다음 단계

AI5 2차는 여기서 시작한다.

- threshold surface의 실제 log-only binding
- size surface의 bounded canary binding
- wait surface의 readiness 충족 후 delayed log-only binding

즉 이번 문서의 역할은:

`실행을 바로 바꾸는 것`이 아니라
`무엇을 어떤 순서로 바꿔야 안전한지 고정하는 것`

이다.
