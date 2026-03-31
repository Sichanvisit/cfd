# Semantic ML Key 전략 정리

## 1. 목적

이 문서는 `Step 2. key 전략 정리`의 산출물이다.

핵심 목표는 세 가지다.

- 현재 key 생성의 기준 함수가 어디인지 고정
- `join_ordinal`이 왜 필요한지 설명
- 지금 당장 새 key를 만드는 대신 무엇을 유지하고 무엇을 나중에 바꿀지 결정

상위 기준 문서:

- `docs/semantic_ml_structure_change_plan_ko.md`
- `docs/semantic_ml_structure_audit_baseline_ko.md`
- `data/analysis/semantic_v1_audit_20260321_ko.md`

---

## 2. 현재 canonical key owner

현재 key 생성의 canonical owner는 [`backend/services/storage_compaction.py`](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)다.

여기에서 아래 3개 helper가 기준 규칙을 제공한다.

- `resolve_entry_decision_row_key()`
- `resolve_runtime_signal_row_key()`
- `resolve_trade_link_key()`

현재 판단은 이렇다.

- runtime, export, replay가 이 helper를 재사용하고 있으므로
- 지금 단계에서 새로운 key 규칙을 따로 만들 필요는 없다
- 먼저 이 helper를 기준선으로 못 박는 것이 맞다

---

## 3. key별 역할

| key | 의미 | 주 용도 | 현재 기준 |
| --- | --- | --- | --- |
| `decision_row_key` | 진입 판단 row의 기준 key | hot row, detail row, export, replay 연결 | `resolve_entry_decision_row_key()` |
| `runtime_snapshot_key` | runtime snapshot 기준 key | runtime 상태와 decision row 연결 | `resolve_runtime_signal_row_key()` |
| `trade_link_key` | 실제 trade와 decision 연결 key | trade history / closed trade / replay 연결 | `resolve_trade_link_key()` |
| `replay_row_key` | replay/dataset 조인용 key | replay intermediate와 compact export 연결 | 현재는 기본적으로 `decision_row_key` 계열을 따른다 |

---

## 4. 실제 사용 흐름 확인

## 4-1. Runtime / Logging

- [`backend/app/trading_application_runner.py`](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)는 `resolve_runtime_signal_row_key()`를 사용한다.
- [`backend/services/entry_engines.py`](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)는 `resolve_entry_decision_row_key()`와 `resolve_runtime_signal_row_key()`를 사용한다.

즉 runtime과 decision logging은 같은 helper 계열을 기준으로 움직인다.

## 4-2. Compact Export

- [`scripts/export_entry_decisions_ml.py`](/C:/Users/bhs33/Desktop/project/cfd/scripts/export_entry_decisions_ml.py)는 old CSV에서도
  - `decision_row_key`
  - `runtime_snapshot_key`
  - `replay_row_key`
  를 같은 helper 규칙으로 다시 계산한다.

즉 export는 "새 규칙"이 아니라 "기존 기준 helper 재사용"이다.

## 4-3. Replay

- [`backend/trading/engine/offline/replay_dataset_builder.py`](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/offline/replay_dataset_builder.py)는 `resolve_entry_decision_row_key()`를 기준으로 replay row key를 만든다.

즉 replay도 decision key 규칙과 따로 놀지 않는다.

## 4-4. Dataset Join

- [`ml/semantic_v1/dataset_builder.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_builder.py)는 feature 쪽과 label 쪽 모두에서
  - `join_key`
  - `join_ordinal`
  를 만든 뒤
  - `on=["join_key", "join_ordinal"]`
  로 merge한다.

즉 dataset 단계에서만 `조인 보정용 보조 키`가 추가된다.

---

## 5. `join_ordinal`이 왜 필요한가

`join_ordinal`은 새 canonical key가 아니다.

역할은 이것 하나다.

```text
같은 coarse key가 같은 시점에 여러 번 반복될 때
행이 사라지지 않게 feature 쪽과 replay 쪽 발생 순서를 맞추는 보조 장치
```

현재 구조에서 `join_ordinal`이 필요한 이유:

- old source에는 row-level unique key가 충분히 정밀하지 않은 경우가 있었다
- 같은 `decision_row_key` 또는 `replay_row_key`가 반복되는 구간이 있었다
- 이 상태에서 단순 `join_key`만으로 merge하면 다대일/일대다 문제로 행 손실이 생긴다

그래서 현재는:

- feature parquet에서 `join_key`별 `cumcount()`
- replay label frame에서도 `join_key`별 `cumcount()`
- 이후 `join_key + join_ordinal`로 inner join

이 방식을 쓴다.

---

## 6. `join_ordinal`의 현재 위치 평가

현재 평가는 다음과 같다.

### 좋은 점

- old coarse key 중복이 있어도 dataset build를 살릴 수 있다
- 실제로 join coverage를 `0 -> 복구`시키는 데 도움이 됐다
- 지금 단계에서는 가장 안전한 bridge다

### 한계

- row-level semantic identity를 설명하는 key는 아니다
- feature와 replay의 정렬 순서가 다르면 취약해질 수 있다
- 장기적으로는 canonical key를 대신할 수 없다

결론:

- `join_ordinal`은 유지한다
- 하지만 canonical key로 승격하지 않는다
- 문서상 역할을 `dataset join bridge`로만 제한한다

---

## 7. row-level unique key가 지금 당장 필요한가

현재 결론은 `당장 필수는 아니지만, 장기적으로는 필요하다`이다.

판단 근거:

- export chunk bug 수정 이후 join coverage는 복구됐다
- 현재 canonical helper 규칙도 runtime/export/replay에서 일관되게 쓰이고 있다
- 즉 지금 병목은 key 체계보다 `target 정의`와 `split 건강도`다

따라서 지금은:

- `row-level unique key v2`를 바로 도입하지 않는다
- 대신 아래 경우에만 다시 검토한다

재검토 조건:

- 같은 source에서 다시 join coverage 손실이 발생할 때
- `join_ordinal`에 지나치게 의존하는 소스가 계속 늘어날 때
- 동일 key 반복 row가 설명 불가능한 수준으로 많아질 때

---

## 8. Step 2 기준 결론

Step 2의 결론은 아래처럼 고정한다.

### 유지할 것

- canonical key owner는 [`storage_compaction.py`](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- runtime/export/replay는 이 helper 규칙을 계속 재사용
- dataset 단계의 `join_ordinal` bridge 유지

### 지금 하지 않을 것

- 새 row-level unique key v2 즉시 도입
- key 규칙을 runtime/export/replay별로 따로 나누기
- `join_ordinal`을 canonical key처럼 취급하기

### 다음으로 넘길 것

- target 재설계
- split 기준 보강
- legacy source feature tier 정리

---

## 9. 완료 기준 판정

Step 2 완료 기준은 아래다.

- key 생성 함수의 canonical owner가 문서로 고정됨
- runtime/export/replay가 같은 규칙을 쓴다는 점이 확인됨
- `join_ordinal` 역할이 `dataset join bridge`로 문서화됨
- 현재 기준으로 join coverage 손실이 없는 상태라는 판단이 연결됨

현재 판정:

- 위 기준을 충족하므로 `Step 2는 완료`로 본다

---

## 10. 다음 작업 연결

Step 2 다음 작업은 그대로 `P0 timing target 재설계`다.

중심 파일:

- [`ml/semantic_v1/dataset_builder.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_builder.py)
- [`ml/semantic_v1/dataset_splits.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/dataset_splits.py)
- [`ml/semantic_v1/evaluate.py`](/C:/Users/bhs33/Desktop/project/cfd/ml/semantic_v1/evaluate.py)
