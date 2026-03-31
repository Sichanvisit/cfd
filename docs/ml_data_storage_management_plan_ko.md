# ML Data Storage Management Plan

## 1. 목적

이 문서는 현재 프로젝트의 로그, 거래 기록, 리플레이 중간 산출물, ML 학습 데이터가 어떤 경로로 생성되고 소비되는지 다시 감사한 뒤,
파일 용량을 줄이면서도 아까운 데이터가 버려지지 않도록 관리 계획을 정리한 문서다.

이번 계획의 핵심 목표는 아래 5가지다.

- hot 파일은 작고 단순하게 유지한다.
- warm archive는 리플레이와 검증에 충분하도록 남긴다.
- ML은 raw giant CSV가 아니라 compact dataset만 보게 만든다.
- 지금 거의 안 쓰이는 값도 바로 삭제하지 않고 warm or cold tier로 재배치한다.
- rollover, archive, retention, export 이력을 manifest로 남긴다.

## 2. 감사 범위와 전제

### 2.1 범위

2026-03-18 기준으로 아래 범위를 중심으로 점검했다.

- `backend/app`, `backend/services`, `backend/trading`, `backend/fastapi`
- `ml`, `scripts`, `adapters`
- `data` 아래 실제 산출물 크기
- `tests` 일부 참조 경로

코드베이스 내 Python 파일 수는 총 260개였다.

### 2.2 전제

이번 문서는 "모든 Python 파일을 동일한 깊이로 수작업 리뷰한 최종 확정판"은 아니다.
대신 데이터 저장과 소비에 닿는 경로를 넓게 스캔해서,
실제로 용량 문제를 일으키는 파일과 그 파일을 읽는 소비자들을 기준으로 계획을 재구성한 감사형 계획이다.

즉, 방향성 초안이 아니라 근거를 보강한 실무형 초안으로 보는 것이 맞다.

## 3. 현재 데이터 지형

### 3.1 디렉터리별 크기

`data` 하위 실제 크기는 대략 아래와 같았다.

- `data/trades`: 약 49.2GB
- `data/datasets`: 약 282MB
- `data/logs`: 약 20.3MB
- `data/observability`: 약 15.6MB
- `data/analysis`: 약 1.8MB
- `data/reports`: 약 60KB

병목은 거의 전부 `data/trades`에 몰려 있다.

### 3.2 가장 큰 파일

확인된 상위 파일은 아래와 같았다.

- `data/trades/entry_decisions.csv`: 약 40.8GB
- `data/trades/entry_decisions.tail_5000.csv`: 약 2.99GB
- `data/trades/entry_decisions.tail_3000.csv`: 약 1.82GB
- `data/trades/entry_decisions.tail_2000_runtime.csv`: 약 1.25GB
- `data/trades/entry_decisions.legacy_20260311_175516.csv`: 약 1.17GB
- `data/datasets/replay_intermediate/replay_dataset_rows_20260316_190905.jsonl`: 약 252MB
- `data/runtime_status.json`: 약 13.1MB
- `data/logs/bot.log`: 약 12.8MB
- `data/observability/events.jsonl`: 약 12.1MB

여기서 중요한 포인트는 단순히 `entry_decisions.csv` 하나만 큰 것이 아니라,
그 주변에 붙은 `tail_*`, `legacy_*`, 중간 산출물까지 합쳐져 용량이 누적되고 있다는 점이다.

## 4. 생성자와 소비자 요약

### 4.1 거래 로그 계열

- [`backend/services/entry_engines.py`](C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
  - `entry_decisions.csv` 작성
  - `ENTRY_DECISION_LOG_COLUMNS` 수: 191개
- [`backend/trading/trade_logger.py`](C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py)
  - `trade_history.csv`
  - `trade_closed_history.csv`
  - `trade_shock_events.csv`
  - `trades.db` SQLite mirror
- [`backend/services/trade_sqlite_store.py`](C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_sqlite_store.py)
  - CSV는 append/log source
  - SQLite는 read/query acceleration

### 4.2 런타임 상태와 관측 계열

- [`backend/app/trading_application.py`](C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py)
  - `data/runtime_status.json`
  - `data/runtime_loop_debug.json`
  - `latest_signal_by_symbol`
  - `ai_entry_traces`
  - `loop_debug_state`
- [`adapters/file_observability_adapter.py`](C:/Users/bhs33/Desktop/project/cfd/adapters/file_observability_adapter.py)
  - `data/observability/counters.json`
  - `data/observability/events.jsonl`
- [`backend/app/trading_application_runner.py`](C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)
  - `data/logs/bot.log`

### 4.3 ML과 리플레이 계열

- [`ml/dataset_builder.py`](C:/Users/bhs33/Desktop/project/cfd/ml/dataset_builder.py)
  - `trade_history.csv`, `trade_closed_history.csv` 기반
  - `entry_dataset.csv`, `exit_dataset.csv` 생성
- [`ml/train.py`](C:/Users/bhs33/Desktop/project/cfd/ml/train.py)
  - `ai_models.joblib` 생성
- [`scripts/export_entry_decisions_ml.py`](C:/Users/bhs33/Desktop/project/cfd/scripts/export_entry_decisions_ml.py)
  - `entry_decisions.csv`에서 slim parquet export
- [`backend/trading/engine/offline/outcome_labeler.py`](C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/offline/outcome_labeler.py)
  - analysis shadow output 생성
- [`backend/trading/engine/offline/replay_dataset_builder.py`](C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/offline/replay_dataset_builder.py)
  - `data/datasets/replay_intermediate/*.jsonl`
  - `data/analysis/*`

## 5. 현재 구조가 잘한 점

### 5.1 거래 이력은 이미 비교적 건강하다

`trade_history.csv`, `trade_closed_history.csv` 경로는 이미 `CSV + SQLite mirror` 구조를 갖고 있다.
즉 write source와 query path가 어느 정도 분리되어 있고,
현재 운영 중인 단순 tabular AI도 이 작은 거래 이력 쪽을 잘 활용하고 있다.

이 구조는 유지하는 것이 맞다.

### 5.2 semantic or replay로 이어질 중간 계층도 이미 있다

`OutcomeLabeler`, `ReplayDatasetBuilder`, `forecast_shadow_compare_readiness` 계열 덕분에
무거운 원본 로그를 그대로 모델에 넣지 않고 중간 계층을 거쳐 compact dataset으로 갈 수 있는 뼈대가 이미 있다.

즉 "ML을 위한 데이터 관리 체계가 전혀 없는 상태"는 아니다.

## 6. 지금 아쉽게 낭비되고 있는 부분

### 6.1 `entry_decisions.csv`가 너무 많은 역할을 동시에 맡고 있다

현재 `entry_decisions.csv`는 아래 역할을 한 파일에 모두 떠안고 있다.

- live append source
- semantic replay source
- forecast validation source
- shadow compare source
- ad-hoc debugging source
- ML export source

이 파일은 단순한 진입 로그가 아니라 191개 컬럼의 JSON-heavy 원본이다.
문제는 이 파일이 "쓸모없어서 큰 것"이 아니라 "유용하지만 hot tier에 두기에는 너무 크고 무거운 것"이라는 점이다.

따라서 방향은 삭제가 아니라 분리다.

### 6.2 `tail_*`와 `legacy_*`가 디버그 산출물에서 사실상 준영구 파일이 되고 있다

`entry_decisions.tail_*`와 `entry_decisions.legacy_*`는 원래는 조사와 복구를 돕는 파일인데,
현재는 수 GB 단위로 남아 메인 원본만큼 부담을 키우고 있다.

이 파일들은 가치가 있지만 hot 파일과 동일한 보존 정책을 주면 안 된다.

### 6.3 `runtime_status.json`이 hot status 역할을 넘어서고 있다

`runtime_status.json`은 최신 상태 파일이어야 하는데,
실제로는 `latest_signal_by_symbol` 전체와 각종 상세 payload가 함께 들어가 커지고 있다.

이 파일은 여러 스크립트와 UI에서 읽히고 있어서 없앨 수는 없지만,
"빠른 최신 상태"와 "상세 진단 payload"를 분리하지 않으면 계속 불어난다.

### 6.4 `events.jsonl`과 `bot.log`는 크기는 아직 작아도 정책이 비어 있다

- `bot.log`는 `FileHandler`로 쓰이고 있어 회전 정책이 없다.
- `events.jsonl`은 append-only인데 rollover or retention이 없다.

지금은 10MB대이지만, `entry_decisions`와 같은 실수를 반복하기 쉬운 경로다.

### 6.5 replay intermediate는 무겁지만 버리기 아깝다

`data/datasets/replay_intermediate/replay_dataset_rows_*.jsonl`은 이미 252MB 수준의 파일이 생기고 있다.
이건 크기만 보면 정리 대상처럼 보이지만,
차세대 semantic or forecast ML로 가는 중간 산출물이라는 점에서 그냥 날리면 아깝다.

이 계층은 없애는 대신 manifest와 retention을 붙여 관리하는 쪽이 맞다.

## 7. "버리면 아쉬운 것"과 "hot에서 빼야 하는 것" 구분

### 7.1 hot에서 빼야 하는 것

아래 값들은 완전히 무가치한 것이 아니라,
현재 append hot file에 항상 함께 실을 필요가 적은 값들이다.

- 대형 semantic snapshot JSON
- forecast snapshot and contract JSON
- observe-confirm 세부 진단 payload
- energy helper 세부 payload
- shadow compare only fields
- tail or legacy raw duplicates

즉 이 값들은 warm archive나 compact sidecar로 이동할 후보지,
즉시 삭제 후보가 아니다.

### 7.2 계속 남겨야 하는 것

아래 경로는 이미 사용처가 명확하므로 성급히 줄이면 안 된다.

- `trade_history.csv`
- `trade_closed_history.csv`
- `trades.db`
- `entry_dataset.csv`
- `exit_dataset.csv`
- `ml_exports/*.parquet`
- `replay_intermediate/*.jsonl`
- labeling validation report

### 7.3 low-read but still useful

문자열 기준 참조 수를 넓게 스캔해보면,
`entry_decisions` 컬럼 중 일부는 외부 소비가 매우 적다.
예를 들어 `last_order_comment`, `entry_wait_hard`, `entry_wait_value`, `utility_stats_ready`,
`order_block_remaining_sec` 같은 값은 주로 특정 서비스나 export script에서만 보인다.

하지만 이것이 곧바로 삭제 사유는 아니다.
오히려 "hot raw에서 분리하고 warm or ML export에서 필요한 경우만 다시 쓰는 것"이 적절하다.

## 8. 권장 데이터 계층

### 8.1 Hot Tier

목적은 live append와 빠른 최신 조회다.

권장 대상:

- `data/trades/entry_decisions.csv`
- `data/trades/trade_history.csv`
- `data/trades/trade_closed_history.csv`
- `data/trades/trades.db`
- `data/runtime_status.json`
- `data/logs/bot.log`
- `data/observability/counters.json`
- `data/observability/events.jsonl`

원칙:

- active 파일은 각 종류별로 1개만 유지
- size or day 기준 자동 rollover
- status 파일은 slim version 우선
- debug detail은 별도 sidecar or archive로 분리

### 8.2 Warm Tier

목적은 리플레이, 검증, 포렌식, shadow compare다.

권장 대상:

- archived `entry_decisions` parquet
- archived `trade_history` parquet snapshot
- archived `trade_closed_history` parquet snapshot
- `replay_intermediate/*.jsonl`
- labeling validation report
- `analysis/*.jsonl`
- selected debug sidecar

원칙:

- columnar format 우선
- compression은 `zstd`
- 날짜 파티션 사용
- manifest 필수

### 8.3 ML Tier

목적은 학습, 검증, 배포 입력이다.

권장 대상:

- `data/datasets/entry_dataset.csv`
- `data/datasets/exit_dataset.csv`
- `data/datasets/ml_exports/runtime/*.parquet`
- `data/datasets/ml_exports/forecast/*.parquet`
- `data/datasets/ml_exports/replay/*.parquet`

원칙:

- raw giant CSV 직접 사용 금지
- 학습 목적별 export 분리
- source row count, selected columns, filtering rule 기록

### 8.4 Cold Tier

목적은 규제, 복구, 월간 checkpoint, 릴리즈 기준선 보존이다.

권장 대상:

- 월간 archive checkpoint
- 릴리즈 acceptance baseline
- manifest snapshot
- 소수의 복구용 legacy checkpoint

원칙:

- 많이 읽지 않으므로 용량 효율 우선
- 보존 기간과 삭제 시점 명시

## 9. 파일별 권장 정책

### 9.1 `entry_decisions.csv`

판정:

- 가장 큰 용량 문제의 중심
- 하지만 semantic or forecast 재활용 가치도 가장 큼

정책:

- hot raw는 최대 512MB~1GB or 1일 단위로 rollover
- rollover 직후 `parquet + zstd` archive 생성
- archive 성공 후 raw legacy는 제한 보존
- `tail_*`는 debug artifact로 분류하고 7일 retention
- `legacy_*`는 최근 3개 or 7일 retention
- 장기 분석은 archive parquet만 사용

추가 권고:

- 향후에는 `entry_decisions.hot.csv`와 `entry_decisions.detail.parquet` 같은 split도 고려

### 9.2 `trade_history.csv`, `trade_closed_history.csv`

판정:

- 현재 구조가 비교적 안정적
- ML과 운영 둘 다 이미 잘 연결됨

정책:

- 현재 CSV + SQLite mirror 유지
- 주 or 월 단위 parquet snapshot 추가
- 운영 read path는 계속 SQLite 우선

### 9.3 `trade_shock_events.csv`

판정:

- 크기는 아직 작을 가능성이 높지만 이벤트성 포렌식 가치가 있다

정책:

- hot CSV 유지
- 월 단위 archive 가능
- 직접 삭제보다는 trade archive에 포함

### 9.4 `runtime_status.json`

판정:

- 최신 상태 파일로는 너무 무겁다
- 소비자는 적지 않지만 대체로 latest view 목적이다

정책:

- `runtime_status.slim.json`과 `runtime_status.detail.json`으로 분리 검토
- slim에는 symbol별 핵심 요약만 남김
- detail은 최근 N개 snapshot만 warm tier 보존
- 기존 `runtime_status.json`을 유지해야 한다면 slim 구조를 우선으로 하고 detail은 외부 파일 참조

### 9.5 `events.jsonl`

판정:

- 아직 소비자는 많지 않다
- append-only라 방치 시 누적 위험이 높다

정책:

- 일 or size 기준 rollover
- 30일 hot, 90일 warm 보존
- event type summary는 별도 집계

### 9.6 `bot.log`

판정:

- 이미 FastAPI 쪽은 rotate하는데 bot log만 무방비 상태다

정책:

- `RotatingFileHandler` 적용
- 5MB~20MB 범위에서 backup count 설정
- 장기 보존은 summary report만 남김

### 9.7 `replay_intermediate/*.jsonl`

판정:

- 크기는 중간 이상이지만 차세대 ML 준비물로 가치가 높다

정책:

- 삭제보다 retention과 manifest 부착
- generation rule, source range, schema version 기록
- 일정 기간 이후 parquet re-pack 고려

### 9.8 `analysis/*`, `reports/*`

판정:

- 대부분은 크기보다 난립이 문제다

정책:

- 30일 기본 retention
- baseline, readiness, release evidence는 180일 이상
- probe or temporary validation 결과는 짧게 정리

## 10. ML 데이터 관리 원칙

### 10.1 현재 운영 AI는 계속 작은 거래 이력 기반으로 간다

현 운영 entry or exit AI는 `trade_history.csv`, `trade_closed_history.csv`,
`entry_dataset.csv`, `exit_dataset.csv` 기반이므로 이 경로는 계속 유지하는 편이 맞다.

즉 현재 운영 AI를 위해 40GB 원본 로그를 통째로 들고 갈 이유는 없다.

### 10.2 차세대 semantic or forecast ML은 중간 계층을 거친다

문서상 목표였던 semantic or forecast ML은 아래처럼 가는 것이 맞다.

- raw `entry_decisions.csv`
- `OutcomeLabeler`
- `ReplayDatasetBuilder`
- compact replay export
- training or shadow compare

따라서 `entry_decisions.csv`는 "학습 파일"이 아니라 "원천 로그"로 다뤄야 한다.

### 10.3 ML export는 3갈래로 나눈다

`ml_exports`는 아래처럼 분리하는 것이 좋다.

- `runtime`
  - 현 운영 AI 보조 feature
- `forecast`
  - forecast gap, shadow compare, calibration용
- `replay`
  - outcome labeled replay training용

이렇게 나누면 같은 원본에서 출발해도 사용 목적과 retention을 다르게 줄 수 있다.

## 11. manifest 규격

모든 rollover, archive, export, cleanup 작업은 manifest를 남긴다.

최소 필드는 아래를 권장한다.

- `created_at`
- `job_name`
- `source_path`
- `output_path`
- `schema_version`
- `row_count`
- `file_size_bytes`
- `compression`
- `symbols`
- `time_range_start`
- `time_range_end`
- `retention_policy`
- `delete_after`
- `notes`

권장 저장 위치:

- `data/manifests/baseline`
- `data/manifests/rollover`
- `data/manifests/archive`
- `data/manifests/export`
- `data/manifests/retention`

## 12. 단계별 실행 계획

### Phase 1. Stop The Bleed

목표:

- 더 이상 40GB 단일 hot CSV가 계속 커지지 않게 막는다

작업:

- `entry_decisions.csv` 자동 rollover
- `tail_*`, `legacy_*` retention 스크립트 추가
- `entry_decisions` archive parquet 생성
- `bot.log` rotate 적용
- `events.jsonl` rollover 추가

### Phase 2. Hot and Detail Split

목표:

- hot latest view와 상세 디버그 payload를 분리한다

작업:

- `runtime_status` slim or detail 분리
- `entry_decisions` hot fields와 detail fields 분리 설계
- debug sidecar 위치와 schema 결정

### Phase 3. ML Tier Separation

목표:

- raw source와 training-ready dataset을 완전히 분리한다

작업:

- `ml_exports/runtime`
- `ml_exports/forecast`
- `ml_exports/replay`
- export naming and version 규칙 확정
- compact export manifest 작성

### Phase 4. Warm Archive Discipline

목표:

- 아까운 데이터를 지우지 않으면서도 보관비용을 제어한다

작업:

- replay intermediate retention
- analysis and report retention
- monthly checkpoint 정책 수립
- archive parquet 재압축 or 재정리 정책 추가

### Phase 5. Data Audit Dashboard

목표:

- 파일이 다시 커질 때 늦게 알지 않도록 한다

작업:

- active file size summary
- last rollover time
- export success or fail
- retention cleanup result
- largest files top N report

## 13. 바로 착수할 1순위

지금 가장 효과가 큰 작업은 아래 7가지다.

1. `entry_decisions.csv` 자동 rollover
2. rollover 직후 parquet archive
3. `legacy_*`, `tail_*` retention cleanup
4. `runtime_status` slim or detail 분리 설계
5. `bot.log` rotation 적용
6. `events.jsonl` rollover and retention 적용
7. `data/manifests` 표준화

## 14. 성공 기준

- active `entry_decisions.csv`가 1GB 이하로 유지된다
- raw archive는 CSV가 아니라 parquet 중심이 된다
- ML 학습은 compact dataset만 사용한다
- `tail_*`, `legacy_*`, `events.jsonl`, `bot.log`에 retention이 붙는다
- `runtime_status.json`이 latest status 역할에 맞는 크기로 돌아온다
- source log, replay artifact, training dataset이 서로 다른 계층으로 분리된다

## 15. 결론

초안의 큰 방향은 맞았다.
다만 이번 감사로 보니 문제는 단순히 `entry_decisions.csv` 하나가 아니라,
"hot file에 너무 많은 역할이 몰려 있고, debug와 archive에도 retention이 약하다"는 구조적 문제였다.

그래서 최종 방향은 아래 한 줄로 정리된다.

hot은 작게, warm은 풍부하게, ML은 compact하게, 그리고 버리기 아까운 데이터는 삭제 대신 계층 이동으로 관리한다.

## 16. Step 1 Baseline Freeze

Step 1 기준선 산출물은 아래 경로를 단일 기준으로 본다.

- `data/manifests/baseline/ml_storage_baseline_latest.json`
- `data/manifests/baseline/ml_storage_baseline_latest.md`

Step 1에서 고정한 active 관리 대상 파일은 아래와 같다.

- `data/trades/entry_decisions.csv`
- `data/trades/trade_history.csv`
- `data/trades/trade_closed_history.csv`
- `data/trades/trade_shock_events.csv`
- `data/trades/trades.db`
- `data/trades/trades.db-wal`
- `data/runtime_status.json`
- `data/runtime_loop_debug.json`
- `data/observability/events.jsonl`
- `data/observability/counters.json`
- `data/logs/bot.log`

Step 1 warning 기준은 아래처럼 고정한다.

- `entry_decisions.csv`: warning `512MB`, critical `1GB`
- `trade_history.csv`: warning `64MB`, critical `256MB`
- `trade_closed_history.csv`: warning `128MB`, critical `512MB`
- `trade_shock_events.csv`: warning `32MB`, critical `128MB`
- `trades.db`: warning `256MB`, critical `1GB`
- `trades.db-wal`: warning `64MB`, critical `256MB`
- `runtime_status.json`: warning `5MB`, critical `10MB`
- `runtime_loop_debug.json`: warning `1MB`, critical `5MB`
- `events.jsonl`: warning `10MB`, critical `25MB`
- `counters.json`: warning `1MB`, critical `5MB`
- `bot.log`: warning `10MB`, critical `20MB`

Step 1 field pack baseline은 아래 네 묶음을 기준으로 고정한다.

- `Hot Keep Pack`
- `Warm Metadata Pack`
- `Current ML Promotion Pack`
- `Semantic Compact Promotion Pack`

이 기준선은 [`ml_data_storage_roadmap_ko.md`](C:/Users/bhs33/Desktop/project/cfd/docs/ml_data_storage_roadmap_ko.md)의 `4. 필드 계층을 먼저 고정한다`와 동일한 기준을 따른다.

## 17. Step 6 Trace and Quality 적용 메모

2026-03-18 기준으로 Step 6의 핵심 목적은 "조금 더 빨리 샀어야 했다" 같은 질문을 감이 아니라 row 단위 trace로 되짚을 수 있게 만드는 것이다.

이번 단계에서 실제로 붙은 값은 아래와 같다.

- join and provenance
  - `decision_row_key`
  - `runtime_snapshot_key`
  - `trade_link_key`
  - `replay_row_key`
- freshness and latency
  - `signal_age_sec`
  - `bar_age_sec`
  - `decision_latency_ms`
  - `order_submit_latency_ms`
- data quality
  - `missing_feature_count`
  - `data_completeness_ratio`
  - `used_fallback_count`
  - `compatibility_mode`
- storage health
  - `detail_blob_bytes`
  - `snapshot_payload_bytes`
  - `row_payload_bytes`

이 값들은 아래 계층에 퍼지도록 맞췄다.

- `entry_decisions.csv` hot row
- `entry_decisions.detail.jsonl` sidecar detail row
- `runtime_status.json`
- `runtime_status.detail.json`
- `trade_history.csv`
- `trade_closed_history.csv`
- `scripts/export_entry_decisions_ml.py` compact parquet export

운영 관점에서 이 단계가 중요한 이유는 아래 3가지다.

- 늦은 진입이 freshness 문제인지 decision latency 문제인지 분리해서 볼 수 있다.
- fallback이 잦은 row와 native row를 학습 및 검증에서 분리할 수 있다.
- 저장 구조가 다시 무거워질 때 hot row, snapshot, detail 중 어디서 커지는지 바로 볼 수 있다.

## 18. Step 8 Warm Archive and 운영 가시화 메모

Step 8은 "정리"보다 "질서 있게 남기기"와 "늦게 알지 않기"에 초점을 둔다.

이번 단계에서 추가한 운영 도구는 [`run_ml_storage_maintenance.py`](C:/Users/bhs33/Desktop/project/cfd/scripts/run_ml_storage_maintenance.py) 하나로, 아래 기능을 같이 수행한다.

- warm retention cleanup
  - `data/datasets/replay_intermediate`
  - `data/analysis`
  - `data/reports`
- size audit and tier summary
  - largest files top N
  - `hot`, `warm`, `ml`, `cold` tier totals
  - active hot file health
- latest manifest summary
  - baseline
  - rollover
  - archive
  - export
  - retention
- monthly checkpoint

2026-03-18 기준 dry-run 산출물은 아래 경로에 있다.

- [`ml_storage_retention_20260318_190548.json`](C:/Users/bhs33/Desktop/project/cfd/data/manifests/retention/ml_storage_retention_20260318_190548.json)
- [`ml_storage_health_latest.json`](C:/Users/bhs33/Desktop/project/cfd/data/reports/ml_storage/ml_storage_health_latest.json)
- [`ml_storage_health_latest.md`](C:/Users/bhs33/Desktop/project/cfd/data/reports/ml_storage/ml_storage_health_latest.md)
- [`ml_storage_checkpoint_2026_03.json`](C:/Users/bhs33/Desktop/project/cfd/data/reports/ml_storage/checkpoints/ml_storage_checkpoint_2026_03.json)

이번 dry-run에서 드러난 핵심은 아래와 같다.

- hot critical은 사실상 [`entry_decisions.csv`](C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv) 하나에 집중돼 있다.
- warm 대형 파일은 `tail_*`, `legacy_*`, `replay_intermediate`가 중심이다.
- 현재 retention 기본값 안에서는 즉시 삭제 대상이 없었다.
- 즉 Step 8은 이미 "감지와 보고" 단계까지는 들어갔고, 실제 대용량 완화는 Step 2 rollover 실적용과 함께 봐야 한다.
