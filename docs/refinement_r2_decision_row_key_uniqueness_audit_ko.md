# R2 Decision Row Key Uniqueness Audit

## 1. 목적

이 문서는 R2 `Step 2. decision_row_key uniqueness audit`의
첫 live sample 결과를 정리한 메모다.

핵심 질문은 두 가지다.

- 현재 `entry_decisions.csv`에서 `decision_row_key` 중복이 실제로 존재하는가
- 존재한다면 그 원인이 key 설계 문제인지, 정상적인 sparse/wait 구조인지


## 2. 점검 기준

점검 소스:

- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)

점검 시각:

- 2026-03-26 KST

보조 확인 코드:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [export_entry_decisions_ml.py](c:\Users\bhs33\Desktop\project\cfd\scripts\export_entry_decisions_ml.py)


## 3. 전체 집계

live sample 집계 결과는 아래와 같다.

| 항목 | 값 |
| --- | --- |
| 전체 row 수 | 18,861 |
| `decision_row_key` 누락 | 0 |
| `runtime_snapshot_key` 누락 | 0 |
| `trade_link_key` 누락 | 18,834 |
| `replay_row_key` 누락 | 0 |
| `decision_row_key` 중복 그룹 수 | 3 |
| 중복 row 합계 | 8 |

보조 해석:

- `trade_link_key` 누락은 대부분 wait / non-entry row에서 발생한다.
- 실제 action row 수는 94건이었고,
  `trade_link_key`가 있는 row는 10건,
  그 10건은 모두 action row였다.
- 따라서 `trade_link_key`가 대부분 비어 있는 것 자체는
  현재 구조에서 곧바로 bug로 보면 안 된다.


## 4. 실제 중복 그룹

발견된 중복 그룹은 아래 3개였다.

| key | count |
| --- | --- |
| `BTCUSD / 1774509300 / BUY / range_lower_reversal_buy / ticket=0` | 3 |
| `XAUUSD / 1774448100 / SELL / range_upper_reversal_sell / ticket=0` | 3 |
| `XAUUSD / 1774449900 / SELL / range_upper_reversal_sell / ticket=0` | 2 |

실제 row 특징:

- 모두 `action=BUY` 또는 `action=SELL`
- 모두 `outcome=entered`
- `decision_time` 비어 있음
- `ticket`, `position_id` 비어 있음
- 대신 `trade_link_key`에는 실제 ticket이 들어 있음

즉 중복은 wait/sparse row suffix 부족이 아니라,
entered row인데 base key가 `ticket=0`으로 고정된 케이스에서 생겼다.


## 5. 원인 분석

중복 원인은 [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L1064) 의
`_position_key()`와
[storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L1193) 의
`resolve_entry_decision_row_key()` 조합에 있었다.

이전 구조:

- `ticket`, `position_id`만 position identity로 봄
- entered row라도 위 두 필드가 비어 있으면 `ticket=0`
- action row는 `_needs_sparse_decision_suffix()`가 꺼져 있으므로
  `decision_time`, `observe_reason` 같은 suffix가 붙지 않음
- 결과적으로
  `same symbol + same signal_bar_ts + same action + same setup_id + ticket=0`
  row가 서로 충돌 가능


## 6. 적용한 보강

이번 audit에서 future fix를 같이 넣었다.

변경 파일:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)

변경 내용:

- `_ticket_from_trade_link_key()` 추가
- `_position_key()`가 `ticket`, `position_id`가 비어 있을 때
  `trade_link_key` 안의 ticket도 fallback으로 사용

의미:

- entered row인데 explicit `ticket` 컬럼이 비어 있어도
  `trade_link_key`가 있으면 `decision_row_key` base key가 달라진다
- 따라서 앞으로 새로 생성되는 같은 유형 row의
  `decision_row_key` 중복 가능성이 줄어든다

제한:

- 이미 기록된 historical CSV row의 key는 자동으로 바뀌지 않는다
- 즉 이 보강은 `future write path`를 고치는 성격이다


## 7. 회귀 테스트

추가 / 재확인한 테스트:

- [test_storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_storage_compaction.py)

핵심 회귀:

- `trade_link_key`만 다른 두 entered row가
  서로 다른 `decision_row_key`를 가져야 한다

검증 결과:

- `pytest tests/unit/test_storage_compaction.py`
  - `12 passed`
- `pytest tests/unit/test_export_entry_decisions_ml.py tests/unit/test_replay_dataset_builder.py tests/unit/test_semantic_v1_dataset_builder.py`
  - `19 passed`


## 8. export sample 재생성 확인

기존 `ml_exports` 산출물은 R2 코드 반영 전 파일이어서
`key_integrity_report_path`가 비어 있는 summary가 남아 있었다.

그래서 현재 코드 기준으로 아래 sample export를 새로 생성했다.

- [entry_decisions.r2_audit.replay.parquet.summary.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit.replay.parquet.summary.json)
- [entry_decisions.r2_audit.replay.parquet.key_integrity.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit.replay.parquet.key_integrity.json)
- [entry_decisions.r2_audit.forecast.parquet.summary.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\forecast\entry_decisions.r2_audit.forecast.parquet.summary.json)
- [entry_decisions.r2_audit.forecast.parquet.key_integrity.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\forecast\entry_decisions.r2_audit.forecast.parquet.key_integrity.json)

sample export 결과:

- rows = 1000
- `decision_row_key` missing = 0
- `runtime_snapshot_key` missing = 0
- `replay_row_key` missing = 0
- `trade_link_key` missing = 1000
- `decision_replay_mismatch_rows` = 0

해석:

- 최근 sample은 전부 wait/non-entry 중심이라 `trade_link_key`가 전부 비어 있었다
- 대신 export summary / manifest가 현재는 `key_integrity_report_path`를 정상 기록한다는 점은 확인됐다


## 9. 현재 판정

현재 판정은 아래와 같다.

- `decision_row_key` missing 문제: 없음
- `decision_row_key` historical duplicate 문제: 있음
- duplicate root cause: entered row의 `ticket=0` base key 충돌
- future write-path fix: 반영 완료
- historical row 정리: 아직 안 함

즉 R2 `Step 2`는
“문제가 없었다”가 아니라
“historical duplicate를 발견했고, future path fix는 반영했다” 상태다.


## 10. 다음 액션

R2에서 다음으로 이어질 자연스러운 액션은 아래다.

1. `runtime_snapshot_key / trade_link_key / replay_row_key` join coverage casebook 작성
2. hot/detail -> export/replay propagation table 작성
3. historical duplicate row를 replay/export에서 어떻게 다룰지 정책 결정

