# Shadow Compare Trace Quality Compare Owner Audit

## 1. 목적

이 문서는 `S2 trace quality audit`의 `Step 3 compare reporting owner audit` 결과를 정리한다.

## 2. 핵심 결론

[shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)는 trace quality를 다시 계산하지 않는다.

현재 compare layer의 역할은:

- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)에 이미 기록된 `semantic_shadow_trace_quality`를 읽고
- 그 값을 `trace_quality_counts`로 집계하고
- slice별 summary로 재노출하는 것

뿐이다.

즉 `fallback_heavy only`가 current compare report에 보인다고 해서 compare layer가 잘못 판단한 것은 아니다.

## 3. 코드 기준 owner 분리

### 3-1. source owner

- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)

여기서 source row와 trace-quality scalar가 만들어진다.

### 3-2. reporting owner

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)

여기서는 아래만 수행한다.

- `semantic_shadow_trace_quality` 값 읽기
- compare 전체 summary 집계
- by-symbol / by-regime / by-setup slice 집계
- markdown/json report surface

### 3-3. interpretation owner

- 사람이 report를 읽을 때의 직접 해석 owner는 compare memo / preview audit 문서다.
- 하지만 원인 제거 owner는 compare가 아니라 runtime source contract 쪽이다.

## 4. 실질 의미

현재 `trace_quality_counts = {"fallback_heavy": ...}`는 다음 의미다.

- compare bug: 아님
- aggregation bug: 아님
- source scalar가 이미 그렇게 기록됨: 맞음

즉 compare policy를 먼저 바꿔도 `fallback_heavy only`는 사라지지 않는다.

## 5. 다음 분기

이 audit 결과 다음 분기는 아래 둘이다.

1. runtime source cleanup이 먼저라고 판단되면
   - consumer/runtime migration source 정리로 간다.
2. fallback-heavy가 현재 의도된 conservative runtime contract라고 판단되면
   - `S3 compare policy refinement`로 간다.

현재 latest casebook 기준으로는 1번 여부를 먼저 따져보는 편이 안전하다.
