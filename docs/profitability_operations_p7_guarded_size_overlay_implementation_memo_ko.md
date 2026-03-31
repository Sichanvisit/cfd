# Profitability / Operations P7 Guarded Size Overlay Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 구현 목적

이번 구현의 목적은 `P7 guarded apply candidate` 중 실제 live 실험 가능한 유일 후보였던
`size_overlay_guarded_apply`를 안전한 실험 표면으로 내리는 것이었다.

핵심 원칙은 아래와 같다.

- semantic core / setup logic / timing rule은 건드리지 않는다.
- overlay는 execution layer에서만 읽는다.
- 기본값은 `disabled`라서 현재 live 동작은 바뀌지 않는다.
- `dry_run -> apply` 순으로만 쓸 수 있게 만든다.
- apply 모드에서도 `max step` cap으로 한 번에 크게 줄이지 않는다.

## 2. 구현 범위

### 2-1. Materialization

P7 latest에서 guarded size candidate만 추려 별도 overlay latest를 생성하는 스크립트를 추가했다.

- [profitability_operations_p7_guarded_size_overlay_materialize.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/profitability_operations_p7_guarded_size_overlay_materialize.py)

생성 산출물:

- [profitability_operations_p7_guarded_size_overlay_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/profitability_operations/profitability_operations_p7_guarded_size_overlay_latest.json)
- [profitability_operations_p7_guarded_size_overlay_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/profitability_operations/profitability_operations_p7_guarded_size_overlay_latest.csv)
- [profitability_operations_p7_guarded_size_overlay_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/profitability_operations/profitability_operations_p7_guarded_size_overlay_latest.md)

현재 latest 기준 후보는 3개다.

- `XAUUSD -> 0.25`
- `NAS100 -> 0.43`
- `BTCUSD -> 0.57`

### 2-2. Runtime Resolver

entry execution 직전에 overlay source를 읽고, 현재 모드에 따라 `candidate multiplier`와
`effective multiplier`를 계산하는 resolver를 추가했다.

- [p7_guarded_size_overlay.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/p7_guarded_size_overlay.py)

지원 모드:

- `disabled`
- `dry_run`
- `apply`

핵심 규칙:

- target이 현재 multiplier보다 작을 때만 reduction 후보가 된다.
- `P7_GUARDED_SIZE_OVERLAY_MAX_STEP` 만큼만 한 번에 줄인다.
- `dry_run`에서는 lot을 바꾸지 않고 trace만 남긴다.
- `apply`에서만 실제 lot을 줄인다.

### 2-3. Entry Hook

overlay는 `probe_execution_v1 -> order_lot` 계산 이후에만 붙였다.

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)

즉 semantic decision과 setup naming은 그대로 두고, execution lot만 보수적으로 조정한다.

### 2-4. Logging Surface

entry decision log에 P7 overlay trace를 남기도록 확장했다.

- [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)

추가된 주요 필드:

- `p7_guarded_size_overlay_v1`
- `p7_size_overlay_enabled`
- `p7_size_overlay_mode`
- `p7_size_overlay_matched`
- `p7_size_overlay_target_multiplier`
- `p7_size_overlay_effective_multiplier`
- `p7_size_overlay_apply_allowed`
- `p7_size_overlay_applied`
- `p7_size_overlay_gate_reason`
- `p7_size_overlay_source`

### 2-5. Config Surface

새 env/config surface를 추가했다.

- [config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

핵심 설정:

- `ENABLE_P7_GUARDED_SIZE_OVERLAY`
- `P7_GUARDED_SIZE_OVERLAY_MODE`
- `P7_GUARDED_SIZE_OVERLAY_SOURCE_PATH`
- `P7_GUARDED_SIZE_OVERLAY_MAX_STEP`
- `P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST`

## 3. 현재 해석

이번 구현은 `자동 적응`이 아니다.

정확히는:

- P7 proposal을 materialize한다.
- entry 실행 직전에 overlay candidate를 읽는다.
- disabled/dry_run/apply 모드를 구분한다.
- trace를 hot log에 남긴다.

즉 지금 상태는 `운영 가능한 guarded experiment surface`가 열린 것이다.

## 4. 테스트

추가/보강 테스트:

- [test_p7_guarded_size_overlay.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_p7_guarded_size_overlay.py)
- [test_profitability_operations_p7_guarded_size_overlay_materialize.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_profitability_operations_p7_guarded_size_overlay_materialize.py)
- [test_entry_service_guards.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_service_guards.py)
- [test_entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_engines.py)

검증 결과:

- targeted tests: 통과
- full unit: `1142 passed, 127 warnings`

## 5. 다음 단계

다음 실제 운영 단계는 아주 좁게 가는 게 맞다.

1. 기본은 `disabled` 유지
2. 먼저 `dry_run`으로 실제 log 누적
3. 그 다음 symbol allowlist를 좁혀 `apply`
4. rerun 기준은 `P4/P5/P6/P7` delta로 다시 본다

아직 하지 않는 것:

- XAU timing rule 수정
- legacy identity gap scene live apply
- full self-tuning / auto-adaptation

## 6. 현재 운영 모드

현재 `.env` 기준 운영 모드는 아래처럼 고정했다.

- `ENABLE_P7_GUARDED_SIZE_OVERLAY=true`
- `P7_GUARDED_SIZE_OVERLAY_MODE=dry_run`
- `P7_GUARDED_SIZE_OVERLAY_SYMBOL_ALLOWLIST=` (비워둠, dry-run에서는 전체 candidate 관측)

즉 지금부터는 live lot은 바뀌지 않고, entry log에 `p7_guarded_size_overlay_v1`와
관련 trace가 누적된다. 실제 lot reduction 적용은 아직 열지 않았다.

주의:

- 이미 떠 있는 `main.py` / `uvicorn` 프로세스는 기존 env를 들고 있을 수 있다.
- 따라서 현재 세션에서 dry-run 설정이 실제 runtime에 적용되려면 프로세스 재시작이 필요하다.
- 다만 `main.py` 재시작은 live loop를 끊을 수 있으므로 자동으로 수행하지 않았다.

## 7. 첫 Dry-Run Review 결과

첫 dry-run review 산출물:

- [profitability_operations_p7_guarded_size_overlay_dry_run_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/profitability_operations/profitability_operations_p7_guarded_size_overlay_dry_run_latest.json)
- [profitability_operations_p7_guarded_size_overlay_dry_run_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/profitability_operations/profitability_operations_p7_guarded_size_overlay_dry_run_latest.csv)
- [profitability_operations_p7_guarded_size_overlay_dry_run_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/profitability_operations/profitability_operations_p7_guarded_size_overlay_dry_run_latest.md)

현재 결과는 아래처럼 읽는다.

- `p7_schema_present=false`
- `p7_trace_row_count=0`
- `review_state=pre_p7_schema_header`
- `recommended_next_step=restart_runtime_and_wait_for_new_entry_rows`

즉 설정과 코드 준비는 끝났지만, 실제 dry-run 누적은 아직 시작되지 않았다.
다음 실제 운영 액션은 runtime 재시작 후 새 entry row를 받는 것이다.
