# R2 Join Coverage Casebook

## 1. 목적

이 문서는 R2 `Step 3. Join Coverage Casebook` 전용 메모다.

핵심 질문은 아래다.

- runtime row가 hot decision row, export parquet, replay intermediate, semantic dataset까지 실제로 이어지는가
- 어떤 케이스에서 `trade_link_key`가 비어 있어도 정상이고, 어떤 케이스에서는 반드시 있어야 하는가
- join health 문제와 label quality 문제를 서로 혼동하지 않도록 어떻게 분리해서 볼 것인가


## 2. 사용한 샘플 산출물

### wait / non-entry chain 샘플

- export:
  - [entry_decisions.r2_audit.replay.parquet](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit.replay.parquet)
  - [entry_decisions.r2_audit.replay.parquet.summary.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit.replay.parquet.summary.json)
  - [entry_decisions.r2_audit.replay.parquet.key_integrity.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit.replay.parquet.key_integrity.json)
- replay:
  - [replay_dataset_rows_r2_audit.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate\replay_dataset_rows_r2_audit.jsonl)
  - [replay_dataset_key_integrity_manifest_20260326_135344.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\replay_dataset_key_integrity_manifest_20260326_135344.json)
  - [replay_dataset_build_manifest_20260326_135344.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\replay_dataset_build_manifest_20260326_135344.json)
- semantic dataset:
  - [semantic_v1_dataset_join_health_20260326_135404_051547.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_join_health_20260326_135404_051547.json)

### entered / execution chain 샘플

- export:
  - [entry_decisions.r2_audit_entered.replay.parquet](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit_entered.replay.parquet)
  - [entry_decisions.r2_audit_entered.replay.parquet.summary.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit_entered.replay.parquet.summary.json)
  - [entry_decisions.r2_audit_entered.replay.parquet.key_integrity.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit_entered.replay.parquet.key_integrity.json)
- replay:
  - [replay_dataset_rows_r2_audit_entered.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate\replay_dataset_rows_r2_audit_entered.jsonl)
  - [replay_dataset_key_integrity_manifest_20260326_135443.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\replay_dataset_key_integrity_manifest_20260326_135443.json)


## 3. Join Chain 기준

R2에서 실제로 보는 기본 chain은 아래다.

```text
runtime snapshot row
-> hot entry decision row
-> export parquet row
-> replay intermediate row
-> semantic dataset joined row
```

핵심 key는 아래처럼 해석한다.

| key | 역할 |
| --- | --- |
| `decision_row_key` | runtime decision row identity |
| `runtime_snapshot_key` | runtime signal linkage |
| `trade_link_key` | execution linkage |
| `replay_row_key` | replay / semantic dataset join key |


## 4. Case A. wait / non-entry chain

### 관측 요약

wait/non-entry sample은 1000-row export와 300-row replay, 300-row semantic join으로 확인했다.

핵심 수치:

- export key integrity
  - `decision_row_key` missing = 0
  - `runtime_snapshot_key` missing = 0
  - `replay_row_key` missing = 0
  - `trade_link_key` missing = 1000
  - `decision_replay_mismatch_rows` = 0
- replay key integrity
  - `rows_total` = 300
  - `decision_row_key` missing = 0
  - `runtime_snapshot_key` missing = 0
  - `replay_row_key` missing = 0
  - `trade_link_key` missing = 300
  - `detail_row_key_present_rows` = 300
- semantic join health
  - `feature_rows` = 1000
  - `label_rows` = 300
  - `joined_rows` = 300
  - `feature_only_join_keys_count` = 700
  - `label_only_join_keys_count` = 0
  - `joined_key_mismatch_rows` 전부 0

### 해석

- wait/non-entry row에서는 `trade_link_key`가 비어 있어도 정상이다.
- 이 케이스에서 핵심은 `decision_row_key`, `runtime_snapshot_key`, `replay_row_key`가 안정적으로 유지되는지다.
- semantic join에서 `feature_only_join_keys_count = 700`이 나온 건
  join bug가 아니라 feature export를 1000 rows, replay sample을 300 rows로 다르게 뽑았기 때문이다.
- 중요한 건 `label_only_join_keys_count = 0`이고,
  실제 joined row의 key mismatch가 0이라는 점이다.

### 대표 row 예시

대표 wait row에서는 아래가 유지된다.

- `decision_row_key == replay_row_key`
- `runtime_snapshot_key`는 존재
- `trade_link_key`는 비어 있음
- `observe_reason / blocked_by / action_none_reason`는 replay row의 `decision_row`에 유지됨

즉 wait row는 `execution linkage 없이도 replay/dataset으로 이어지는 chain`이 정상 작동한다.


## 5. Case B. entered / execution chain

### 관측 요약

entered-only sample은 실제 action row만 대상으로 확인했다.

핵심 수치:

- export key integrity
  - rows = 10
  - `decision_row_key` missing = 0
  - `runtime_snapshot_key` missing = 0
  - `trade_link_key` missing = 0
  - `replay_row_key` missing = 0
  - `decision_replay_mismatch_rows` = 0
- replay key integrity
  - `rows_total` = 10
  - `decision_row_key` missing = 0
  - `runtime_snapshot_key` missing = 0
  - `trade_link_key` missing = 0
  - `replay_row_key` missing = 0
  - `detail_row_key_present_rows` = 10

### 해석

- entered row에서는 `trade_link_key`가 실제 execution linkage key로 잘 전달된다.
- export -> replay 경로에서도 `trade_link_key`는 그대로 유지된다.
- 즉 execution chain 자체는 `trade_link_key` 기준으로 이어지고 있다.

### 주의사항

이 sample에는 historical duplicate row가 포함돼 있다.

예:

- `XAUUSD`
- `action=SELL`
- `setup_id=range_upper_reversal_sell`
- 동일 `decision_row_key`
- 서로 다른 `trade_link_key`

즉 entered row join coverage는 살아 있지만,
historical CSV에는 old key rule로 생성된 duplicate `decision_row_key`가 아직 남아 있다.

이건 join coverage 문제라기보다
이미 [refinement_r2_decision_row_key_uniqueness_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_decision_row_key_uniqueness_audit_ko.md)
에서 다룬 uniqueness 문제다.


## 6. Join과 Label Quality는 별도다

wait sample replay에서 validation report는 `INSUFFICIENT_FUTURE_BARS`가 많이 나왔다.

하지만 이건 R2 join coverage failure가 아니다.

분리해서 보면:

- join coverage:
  - key가 이어졌는가
  - orphan / mismatch가 있는가
- label quality:
  - future bars가 충분한가
  - scorable rows가 충분한가

즉 `joined_rows = 300`, `joined_key_mismatch_rows = 0`이어도
label report는 unknown-heavy일 수 있다.
그건 R3/R4 해석 영역이다.


## 7. 현재 판정

현재 join coverage 판정은 아래와 같다.

### 통과

- wait/non-entry chain에서 `decision_row_key`, `runtime_snapshot_key`, `replay_row_key` 유지
- entered/action chain에서 `trade_link_key` 유지
- replay -> semantic dataset join에서 `label_only_join_keys_count = 0`
- joined row key mismatch = 0

### 아직 남아 있는 caveat

- historical entered row의 duplicate `decision_row_key`
- feature export sample과 replay sample 크기가 다를 때 발생하는 `feature_only_join_keys`
- label unknown-heavy 현상을 join 문제와 혼동하지 않도록 구분 필요


## 8. 다음 액션

R2 Step 3 이후 바로 이어질 작업은 아래다.

1. hot/detail -> export/replay propagation table 작성
2. semantic dataset builder compatibility memo 작성
3. historical duplicate row 처리 정책을 R2 후반 또는 R3 진입 전에 결정

