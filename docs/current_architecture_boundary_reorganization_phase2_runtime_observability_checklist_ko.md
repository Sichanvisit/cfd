# CFD 현재 아키텍처 정리 Phase 2 체크리스트

부제: Runtime Recent Diagnostics + Semantic Shadow Diagnostics Export

작성일: 2026-03-27 (KST)

## 1. Phase 목표

Phase 2의 목표는 운영 표면을 정직하게 만드는 것이다.

핵심은 아래 두 가지다.

- `latest snapshot` 중심 runtime status를 `recent-window diagnostics`까지 포함한 운영 표면으로 확장한다
- semantic shadow runtime의 상세 진단을 요약이 아니라 운영 계약으로도 노출한다


## 2. 현재 문제 요약

현재 runtime status는 아래 구간에서 작성된다.

- `backend/app/trading_application.py:416-444`
- `backend/app/trading_application.py:1216-1232`

현재는 유용한 요약이 있지만, 아래 질문에 바로 답하기 어렵다.

- 최근에도 wrong READY가 남는가
- 최근 blocked reason top-N은 무엇인가
- symbol별로 blocked/probe/observe/ready 비율이 어떻게 변했는가
- shadow runtime이 inactive인 이유가 상세하게 무엇인가


## 3. 대상 파일

- `backend/app/trading_application.py`
- 필요 시 runtime exporter/helper
- `tests/unit/test_trading_application_runtime_status.py`
- 필요 시 관련 runtime serialization tests


## 4. 권장 구현 방향

### 4-1. slim vs detail 분리 유지

현재 `runtime_status.json`과 `runtime_status.detail.json` 분리가 있으므로, 이 구조는 유지하는 편이 좋다.

권장 방향:

- slim 파일에는 핵심 요약
- detail 파일에는 recent diagnostics와 shadow diagnostics 상세

### 4-2. recent diagnostics는 top-level 운영 계약으로 추가

권장 필드 예시:

- `recent_stage_counts`
- `recent_blocked_reason_counts`
- `recent_symbol_summary`
- `recent_wrong_ready_count`
- `recent_display_ready_summary`

window 예시:

- `last_50`
- `last_200`
- `last_300`

### 4-3. semantic shadow diagnostics raw/detail export

현재 `semantic_live_config`는 요약만 담는다.

여기에 더해 아래가 있으면 좋다.

- `semantic_shadow_runtime_diagnostics`
- `semantic_shadow_runtime_checked_at`
- `semantic_shadow_runtime_model_dir`
- `semantic_shadow_runtime_load_error`


## 5. 체크리스트

### 5-1. recent-window 지표 정의

- 어떤 window를 공식 운영 기준으로 볼지 고정한다
- stage count 스키마를 고정한다
- blocked reason top-N 스키마를 고정한다
- symbol summary 스키마를 고정한다

### 5-2. 데이터 소스 결정

- recent diagnostics를 어디서 집계할지 정한다
- 가능하면 truth source를 하나로 고정한다
- csv recent read를 쓸지, in-memory buffer를 쓸지 결정한다
- slim/detail 쓰기 비용이 과도하지 않은지 확인한다

### 5-3. runtime payload 확장

- `runtime_status.json`에 핵심 recent summary를 넣는다
- `runtime_status.detail.json`에는 더 자세한 diagnostics를 넣는다
- 기존 필드와의 호환성을 해치지 않도록 한다

### 5-4. shadow diagnostics 확장

- 현재 내부 `semantic_shadow_runtime_diagnostics` 객체를 구조적으로 export한다
- `shadow_runtime_reason` 요약과 detail payload가 서로 모순되지 않게 한다

### 5-5. 테스트 보강

- slim/detail 파일 모두 새 필드를 보존하는지
- recent diagnostics가 비어 있을 때 fallback 동작이 괜찮은지
- 최신 signal만 있는 경우에도 serialization이 깨지지 않는지
- shadow diagnostics가 inactive/active 모두에서 안정적으로 직렬화되는지


## 6. 완료 기준

- 새 스레드에서 `runtime_status.json`만 봐도 최근 상태를 1차 파악할 수 있다
- `runtime_status.detail.json`에서 semantic shadow inactive 이유를 더 깊게 읽을 수 있다
- csv를 열지 않고도 최근 blocked 흐름을 설명할 수 있다
- 기존 runtime status 테스트가 깨지지 않는다


## 7. 건드리면 안 되는 것

- runtime 파일을 너무 비대하게 만들어 쓰기 비용을 과도하게 늘리지 말 것
- recent summary가 original truth를 대체하게 만들지 말 것
- slim 파일에 detail 수준 정보를 무분별하게 넣지 말 것


## 8. 권장 테스트 명령

- `pytest tests/unit/test_trading_application_runtime_status.py -q`
- 필요 시 `pytest tests/unit/test_entry_service_guards.py -q`
- 필요 시 recent diagnostics aggregation용 신규 테스트


## 9. Phase 종료 후 확인 포인트

- `runtime_status.json`에 recent summary가 들어갔는지
- `runtime_status.detail.json`에 shadow diagnostics raw/detail이 들어갔는지
- 현재 기준 `mode=threshold_only`, `symbol_allowlist`, `shadow_runtime_reason=model_dir_missing`가 detail과 모순되지 않는지
