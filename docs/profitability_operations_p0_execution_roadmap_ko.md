# Profitability / Operations P0 Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P0`를 실제 실행 가능한 순서로 쪼개기 위한 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [profitability_operations_p0_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p0_detailed_reference_ko.md)

## 2. P0 전체 순서

```text
P0-A. decision trace surface helper
-> P0-B. hot/detail log integration
-> P0-C. ownership/coverage field stabilization
-> P0-D. contract and test freeze
-> P0-E. P1 handoff
```

## 3. 현재 상태

현재는 `P0-A ~ P0-D`의 첫 버전이 들어간 상태다.

이미 구현된 것:

- `p0_decision_trace.py` helper
- hot/detail log 컬럼 연결
- ownership / coverage / dominant reason 기본 surface
- unit test 추가

즉 지금 P0는 `초기 v1 구현 완료`로 보는 것이 맞다.

## 4. P0-A. Decision Trace Surface Helper

### 목표

- row 하나를 운영 해석 가능한 trace payload로 바꾼다.

### 구현 파일

- [p0_decision_trace.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\p0_decision_trace.py)

### 완료 기준

- ownership relation
- coverage state
- dominant reason
- guard failures

를 하나의 payload로 만들 수 있다.

## 5. P0-B. Hot / Detail Log Integration

### 목표

- P0 trace를 downstream observability가 바로 읽을 수 있게 hot/detail log에 남긴다.

### 구현 파일

- [entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)

### 현재 연결된 필드

- `p0_identity_owner`
- `p0_execution_gate_owner`
- `p0_decision_owner_relation`
- `p0_coverage_state`
- `p0_coverage_source`
- `p0_decision_trace_v1`
- `p0_decision_trace_contract_v1`

### 완료 기준

- hot csv에서 바로 group / filter 가능
- detail payload에서도 같은 정보를 읽을 수 있음

## 6. P0-C. Ownership / Coverage Stabilization

### 목표

- P0 field meaning을 흔들리지 않게 고정한다.

### 해야 할 일

- ownership relation 명칭 freeze
- coverage state 명칭 freeze
- outside_coverage와 runtime in-scope를 혼동하지 않도록 규칙 고정

### 다음 보강 후보

- consumer contract 문서와 relation enum 연결
- report layer에서 coverage-aware separation 강제

## 7. P0-D. Contract / Test Freeze

### 목표

- 이후 P1/P2에서 믿고 사용할 수 있게 테스트와 문서 기준선을 잠근다.

### 현재 구현

- [test_p0_decision_trace.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_p0_decision_trace.py)
- [test_entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_engines.py)

### 완료 기준

- ownership / coverage / guard trace가 회귀 없이 유지된다

## 8. P0-E. P1 Handoff

### 목표

- P1 lifecycle summary가 이 surface를 바로 읽도록 넘긴다.

### handoff 조건

- `p0_decision_trace_v1`가 latest entry log에 남아 있다
- `p0_decision_owner_relation`로 semantic/legacy 관계를 바로 group할 수 있다
- `p0_coverage_state`로 coverage-aware separation이 가능하다

## 9. 지금 바로 다음 작업

P0 다음 즉시 작업은 아래가 가장 자연스럽다.

1. `P1 lifecycle correlation summary shape` 설계
2. P0 trace를 lifecycle summary input으로 연결
3. coverage-aware separation 규칙을 lifecycle report에 반영

## 10. 한 줄 결론

P0는 이미 첫 구현이 들어간 상태이고, 지금 남은 가장 자연스러운 다음 단계는 `P0를 더 키우는 것`보다 `이 surface를 바로 P1 lifecycle report에 연결하는 것`이다.
