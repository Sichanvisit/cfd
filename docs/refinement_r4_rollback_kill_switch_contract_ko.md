# R4 Rollback / Kill Switch Contract

## 1. 목적

이 문서는 semantic rollout을 운영하는 동안
언제 `유지`, `보류`, `즉시 중단`, `롤백`을 해야 하는지
kill switch owner와 함께 고정하는 계약 문서다.

핵심은
`kill switch가 있다는 사실`
보다
`어떤 신호를 stop 사유로 볼지`
를 운영 언어로 잠그는 것이다.

## 2. 직접 owner

- config owner: [config.py](c:\Users\bhs33\Desktop\project\cfd\backend\core\config.py)
- promotion owner: [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)
- runtime surface owner: [trading_application.py](c:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

## 3. 현재 코드 surface

### config

[config.py](c:\Users\bhs33\Desktop\project\cfd\backend\core\config.py)에 현재 semantic live 운영 스위치가 있다.

핵심 필드:

- `SEMANTIC_LIVE_ROLLOUT_MODE`
- `SEMANTIC_LIVE_KILL_SWITCH`
- `SEMANTIC_LIVE_REQUIRE_CLEAN_TRACE`
- `SEMANTIC_LIVE_ALLOW_FALLBACK_HEAVY`
- `SEMANTIC_LIVE_SYMBOL_ALLOWLIST`
- `SEMANTIC_LIVE_ENTRY_STAGE_ALLOWLIST`
- `SEMANTIC_LIVE_MIN_TIMING_PROB`
- `SEMANTIC_LIVE_MIN_ENTRY_QUALITY_PROB`

### promotion guard

[promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)에서
entry rollout의 fallback reason과 threshold/partial-live 적용 여부를 결정한다.

중요한 stop 관련 분기:

- `kill_switch_enabled`
- `rollout_disabled`
- `symbol_not_in_allowlist`
- `entry_stage_not_in_allowlist`
- `baseline_no_action`
- `semantic_unavailable`
- `timing_probability_too_low`
- `entry_quality_probability_too_low`
- `missing_feature_count_high`
- `compatibility_mode_blocked`
- `trace_quality_*`

### runtime surface

[trading_application.py](c:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)는
현재 semantic live config와 recent rollout state를 [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)에 써준다.

즉 운영 중 rollback 판단은
이 파일과 runtime status 산출물 기준으로도 설명 가능해야 한다.

## 4. 등급 분류

이번 계약에서는 신호를 네 등급으로 나눈다.

### A. `관측만`

의미:

- 지금 당장 운영 action을 바꾸지는 않음
- 추세만 본다

예:

- `baseline_no_action`
- `symbol_not_in_allowlist`

### B. `hold`

의미:

- 즉시 stop은 아니지만 확장/승격은 보류한다

예:

- `trace_quality_fallback_heavy`
- `timing_probability_too_low`
- `entry_quality_probability_too_low`

### C. `stop`

의미:

- semantic live 영향도를 더 키우는 모든 작업을 중단한다
- 필요하면 mode를 낮추거나 allowlist 확장을 멈춘다

예:

- preview audit fail 재발
- shadow compare unhealthy 재발
- runtime provenance mismatch 재발
- `compatibility_mode_blocked`
- `trace_quality_unknown`
- `trace_quality_incomplete`

### D. `kill_switch / rollback`

의미:

- semantic live 적용을 즉시 끈다
- 최소한 `disabled` 또는 baseline-only에 가깝게 되돌린다

예:

- `SEMANTIC_LIVE_KILL_SWITCH = true`
- rollout 결과가 예측 불가능한 방향으로 흔들리고 원인 설명이 불가능할 때
- preview/shadow/runtime 기준이 동시에 어긋날 때

## 5. 현재 recommended contract

현재 상태를 기준으로 추천 계약은 아래와 같다.

### 5-1. 즉시 kill switch 사유

아래는 지금 바로 kill switch 또는 사실상 동일한 stop으로 본다.

1. preview audit `promotion_gate.status != pass`
2. `shadow_compare_status != healthy`
3. runtime source/provenance mismatch 재발
4. `compatibility_mode_blocked`가 live recent에 반복 발생
5. `trace_quality_unknown` 또는 `trace_quality_incomplete`가 최근 윈도우에서 의미 있게 증가

### 5-2. hold 사유

아래는 즉시 kill switch는 아니지만 확장/partial_live를 멈추는 사유다.

1. `trace_quality_fallback_heavy`가 recent 대부분을 차지함
2. `timing_probability_too_low`, `entry_quality_probability_too_low`가 symbol별로 반복됨
3. allowlist 밖 symbol에서 semantic score는 높지만 운영 근거가 아직 약함

### 5-3. 관측만 사유

아래는 현재 구조상 정상 동작으로 본다.

1. `baseline_no_action`
2. `symbol_not_in_allowlist`

이 둘은 운영 policy의 결과이지 즉시 오류가 아니다.

## 6. 현재 시점의 실제 판정

현재 [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json) recent 40건 기준:

- `threshold_only = 40`
- `fallback_heavy = 40`
- `baseline_no_action = 14`
- `symbol_not_in_allowlist = 26`

해석:

- kill switch를 써야 할 즉시 stop 신호는 보이지 않는다
- 다만 `fallback_heavy`가 전량이므로 partial_live로 바로 가기엔 아직 이르다
- 즉 현재 추천은
  - `stay_threshold_only`
  - allowlist 확장 전 review
  - partial_live 보류

## 7. rollback action 계층

실제 운영 action은 아래 순서로 보수적으로 내린다.

1. `partial_live -> threshold_only`
2. `threshold_only -> alert_only`
3. `alert_only -> log_only`
4. `log_only -> disabled`
5. 필요 시 `SEMANTIC_LIVE_KILL_SWITCH = true`

즉 rollback은 항상 한 번에 “완전 종료”만 뜻하지 않는다.
상황에 따라 semantic 영향도를 단계적으로 낮추는 것도 rollback으로 본다.

## 8. 실행 원칙

1. `kill switch`는 마지막 수단이다.
2. preview/shadow가 healthy면 먼저 mode downgrade를 검토한다.
3. runtime provenance/source mismatch는 preview pass보다 우선해서 본다.
4. allowlist 확장은 stop 사유가 없을 때만 논의한다.
5. partial_live는 hold 사유가 하나라도 크면 보류한다.

## 9. 현재 결론

현재 기준으로는

- `kill_switch`를 바로 켤 이유는 없다
- `threshold_only 유지`가 맞다
- 다음 확장 전에 rollback contract를 문서로 고정한 상태라고 볼 수 있다

즉 이번 문서의 역할은
`확장할 때 브레이크가 어디인지`를 먼저 정해두는 것이다.
