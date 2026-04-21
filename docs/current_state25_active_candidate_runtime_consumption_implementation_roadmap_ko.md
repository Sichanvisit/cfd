# State25 Active Candidate Runtime Consumption Implementation Roadmap

## 목표

이 문서는 `AI6 2차`를 실제 작업 순서로 나눠서 구현하기 위한 로드맵이다.

쉽게 말하면 아래 4가지를 어떤 순서로 붙일지 정리한다.

1. runtime consume
2. auto-promote apply
3. auto-rollback apply
4. canary / bounded live

## 전체 방향

이번 구현은 아래 순서를 지킨다.

1. `읽기`
2. `표시`
3. `log_only 소비`
4. `실제 apply`
5. `rollback`
6. `canary`
7. `bounded_live`

즉 `실제 바꾸기`보다 먼저 `읽고 보이기`를 끝내야 한다.

## RC1. Active State Input Contract Freeze

할 일:

- [active_candidate_state.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/active_candidate_state.json) 최소 필드 확정
- file missing / invalid fallback 규칙 확정
- `desired_runtime_patch`에서 phase2가 읽는 키 범위 확정

대상 파일:

- [teacher_pattern_auto_promote_live_actuator.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_auto_promote_live_actuator.py)
- 새 AI6 2차 설계 문서

완료 기준:

- runtime이 읽어야 하는 키와 무시해야 하는 키가 문서로 고정된다
- `파일 없음 = baseline disabled`가 명시된다

## RC2. Runtime Reader / Fingerprint Layer

할 일:

- runtime loop에서 active state 읽기
- `candidate_state_fingerprint` 계산
- 이전 loop와 달라졌을 때만 apply 경로 호출
- malformed state면 `invalid_fallback`로 baseline 유지

대상 파일:

- [trading_application_runner.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)

권장 구현 포인트:

- loop 초반 또는 policy refresh 직전
- `policy_service`와 `runtime_status` 둘 다 접근 가능한 위치

완료 기준:

- runtime이 active state를 읽는다
- 파일이 없어도 예외 없이 baseline 유지
- fingerprint 변화가 없으면 중복 apply를 하지 않는다

## RC3. Runtime Status Export

할 일:

- `state25_candidate_runtime_v1` block 추가
- `threshold_surface_v1`, `size_surface_v1` block 추가
- `state_source_status`, `last_apply_reason`, `last_rollback_reason` export

대상 파일:

- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

완료 기준:

- [runtime_status.json](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)만 봐도
  `runtime이 active candidate를 읽었는지`, `읽기만 하는지`, `실제로 반영 중인지`
  구분할 수 있다

## RC4. Threshold Log-Only Consumer

할 일:

- candidate patch에서 threshold 관련 값 읽기
- 실제 live threshold는 바꾸지 않고 shadow threshold만 계산
- symbol / entry stage scope hit 여부 계산
- trace / status에 baseline vs candidate hypothetical delta 남기기

대상 파일:

- [policy_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/policy_service.py)
- [trading_application_runner.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)
- 필요 시 entry trace surface를 만드는 runtime 서비스

완료 기준:

- `log_only`일 때 실제 진입 threshold는 baseline 그대로다
- 하지만 candidate threshold가 얼마였는지는 관찰 가능하다

## RC5. Size Log-Only Consumer

할 일:

- candidate size multiplier patch 읽기
- 실제 주문 size는 바꾸지 않고 hypothetical multiplier만 계산
- symbol scope hit 여부와 clamp 결과 export

대상 파일:

- [policy_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/policy_service.py)
- 실제 size 계산 surface가 있다면 그 지점

완료 기준:

- `log_only`에서 실제 주문 size는 baseline 유지
- candidate size multiplier는 status / trace에서 확인 가능

## RC6. AI6 Promote Apply Wiring

할 일:

- `promote_log_only_ready`일 때 실제로 active state를 쓰는 apply 경로 연결
- `apply_requested`와 `applied_action` 기록 강화
- candidate watch에서 선택적으로 apply 사용 가능하게 유지

대상 파일:

- [teacher_pattern_auto_promote_live_actuator.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_auto_promote_live_actuator.py)
- [state25_candidate_watch.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/state25_candidate_watch.py)

완료 기준:

- AI6가 `--apply` 또는 제한된 운영 플래그에서 active state를 실제로 쓸 수 있다
- runtime은 그 state를 읽고 `log_only`로 소비한다

## RC7. AI6 Rollback Apply Wiring

할 일:

- `rollback_recommended`일 때 baseline state patch write
- runtime이 이를 읽고 overlay clear
- rollback history와 runtime status 양쪽에 흔적 남기기

대상 파일:

- [teacher_pattern_auto_promote_live_actuator.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_auto_promote_live_actuator.py)
- [policy_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/policy_service.py)
- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

완료 기준:

- rollback state가 써지면 runtime은 즉시 baseline 상태로 복귀한다
- candidate overlay가 남아 있지 않다

## RC8. Canary Runtime Phase

할 일:

- `current_rollout_phase = canary` 해석 추가
- `symbol_allowlist` + `entry_stage_allowlist` 둘 다 맞는 범위에서만 실제 threshold / size 반영
- canary evidence 수집 block 추가

대상 파일:

- [policy_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/policy_service.py)
- [trading_application_runner.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)
- [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)

완료 기준:

- 지정된 symbol / stage 안에서만 실제 candidate threshold / size가 적용된다
- 나머지 범위는 baseline 유지

## RC9. Bounded Live Phase

할 일:

- `current_rollout_phase = bounded_live` 해석 추가
- canary를 통과한 candidate만 bounded live로 승격
- rollback trigger를 더 엄격하게 연결

완료 기준:

- bounded scope 안에서는 실제 candidate threshold / size가 적용된다
- canary 또는 utility 악화 시 baseline으로 복귀 가능하다

## RC10. Ops / Monitoring / Tests

할 일:

- runtime consumption 전용 unit test 추가
- active state missing / malformed / stale test 추가
- log_only / canary / rollback transition test 추가
- 사람이 읽기 쉬운 latest md 보고서 또는 runtime status block 확인 루틴 추가

권장 테스트 축:

- `policy_service` overlay 동작
- `trading_application_runner` reader / fingerprint
- `trading_application` status export
- `teacher_pattern_auto_promote_live_actuator` apply / rollback

완료 기준:

- candidate state 변화가 runtime에서 재현 가능하게 테스트된다
- rollback이 promote보다 먼저 안정적으로 검증된다

## 우선순위

지금 바로 손으로 밀 우선순위는 아래 순서가 맞다.

1. `RC2 Runtime Reader / Fingerprint`
2. `RC3 Runtime Status Export`
3. `RC4 Threshold Log-Only Consumer`
4. `RC5 Size Log-Only Consumer`
5. `RC6 Promote Apply`
6. `RC7 Rollback Apply`
7. `RC8 Canary`
8. `RC9 Bounded Live`

즉 지금의 메인 1순위는
`runtime이 active_candidate_state를 실제로 읽고 status에 보이게 만드는 것`이다.

## 이번 단계에서 지켜야 할 금지선

아래는 RC2~RC5가 끝나기 전까지 하지 않는다.

- wait policy 실제 bind
- full live threshold 교체
- full live size 교체
- canary evidence 없이 bounded live 열기

이 금지선을 지켜야 `읽기/관찰`과 `실제 반영`이 섞이지 않는다.

## 완료 판단

AI6 2차를 1차 완료로 보는 기준은 아래와 같다.

1. runtime이 active state를 baseline-safe하게 읽는다
2. runtime_status에 candidate runtime block이 보인다
3. threshold / size는 `log_only`에서 hypothetical 값으로만 소비된다
4. promote apply를 해도 실제 live는 아직 baseline 유지다
5. rollback apply를 하면 overlay가 즉시 사라진다

이 5개가 되면 그다음에만 canary와 bounded live로 넘어간다.

## 한 줄 정리

이 로드맵의 핵심은 아래 한 문장이다.

`먼저 runtime consume과 observability를 끝내고, 그 다음 promote/rollback 실제 apply를 붙이며, canary와 bounded_live는 그 이후에만 연다.`
