# Profitability / Operations P0 Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P0`가 무엇인지, 왜 먼저 필요한지, 이번 `P0 v1` 구현에서 어디까지 들어갔는지를 고정하기 위한 상세 기준 문서다.

핵심 질문은 이것이다.

`P1 lifecycle, P2 expectancy로 올라가기 전에 어떤 trace / ownership / coverage-aware 표면을 먼저 고정해야 하는가?`

## 2. P0가 필요한 이유

P1과 P2는 결국 최근 거래를 읽는 단계다.

그런데 그 전에 아래 질문이 먼저 해결되어야 한다.

- 이 row는 왜 들어갔는가
- semantic이 identity owner였는가
- legacy gate가 execution에 어떻게 끼는가
- 어떤 guard가 마지막으로 막았는가
- 이 표본은 coverage 안쪽인가 바깥인가

이 질문이 먼저 정리되지 않으면,

- lifecycle 해석이 흔들리고
- expectancy가 오염되며
- anomaly를 잡아도 원인 설명이 어려워진다

그래서 P0는 “작은 바닥 정리”지만 실제론 P 전체의 해석 신뢰도를 결정하는 단계다.

## 3. P0의 범위

이번 P0는 아래 세 가지를 목표로 한다.

1. `decision ownership` 명시
2. `guard / non-action trace` 명시
3. `coverage-aware state` 명시

이번 P0는 아직 아래를 하지 않는다.

- lifecycle summary 자체
- expectancy 계산 자체
- anomaly threshold 자체
- counterfactual / adaptation

즉 P0는 `운영 해석용 공통 surface`를 먼저 심는 단계다.

## 4. P0 v1 현재 구현 범위

이번 v1 구현은 아래까지 들어갔다.

### 새 helper

- [p0_decision_trace.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\p0_decision_trace.py)

핵심 기능:

- `build_p0_decision_trace_v1`
- `resolve_p0_decision_ownership`
- `resolve_p0_coverage_state`

### hot / detail logging 연결

- [entry_engines.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)

새 hot/detail 표면:

- `p0_identity_owner`
- `p0_execution_gate_owner`
- `p0_decision_owner_relation`
- `p0_coverage_state`
- `p0_coverage_source`
- `p0_decision_trace_v1`
- `p0_decision_trace_contract_v1`

## 5. 현재 P0 v1이 실제로 말해주는 것

현재 P0 trace는 row 기준으로 최소한 아래를 말해준다.

- semantic identity가 있었는가
- legacy execution gate가 있었는가
- 둘의 관계가 `semantic_identity_with_legacy_execution_gate` 같은 어떤 형태였는가
- 마지막 dominant reason이 blocked_by / action_none_reason / quick_trace_reason 중 어디였는가
- consumer / probe / entry blocked guard 중 무엇이 실패했는가
- coverage state를 `in_scope_runtime / outside_coverage / unknown` 중 무엇으로 읽어야 하는가

즉 P0는 “이 row를 앞으로 어떻게 읽어야 하는지”의 최소 운영 언어를 만든다.

## 6. 현재 해석 규칙

### ownership

- semantic identity surface가 있고 legacy threshold / rule 흔적도 있으면
  `semantic_identity_with_legacy_execution_gate`
- semantic만 강하면
  `semantic_primary`
- legacy만 남아 있으면
  `legacy_primary`

### coverage

- `r0_non_action_family == decision_log_coverage_gap`이면 `outside_coverage`
- runtime snapshot key가 있으면 기본은 `in_scope_runtime`
- 둘 다 아니면 `unknown`

### dominant reason

우선순위는 아래 순서다.

1. failing guard
2. `blocked_by`
3. `action_none_reason`
4. `quick_trace_reason`
5. `observe_reason`

## 7. 현재 한계

이번 P0 v1은 의도적으로 얇다.

아직 남아 있는 것은 아래다.

- entry / wait / exit 전 구간을 아우르는 통합 trace는 아님
- consumer contract 문서 수준 ownership enum까지는 아직 아님
- lifecycle summary나 compare report와 직접 연결되진 않음
- coverage state를 analysis layer 전체에 퍼뜨리진 않았음

즉 지금은 `P1/P2 시작을 위한 첫 trace surface`가 들어간 상태로 보는 게 맞다.

## 8. 다음 확장 포인트

가장 자연스러운 다음 확장은 아래다.

1. entry surface trace를 lifecycle summary에서 직접 읽게 만들기
2. legacy ↔ semantic owner relation을 설정/로그 contract로 더 명시화
3. coverage-aware state를 report layer까지 확장

## 9. 한 줄 결론

P0 v1은 `의사결정을 더 똑똑하게 만드는 작업`이 아니라 `의사결정을 더 읽을 수 있게 만드는 작업`이다. 지금 구현은 hot/detail log에 ownership, guard, coverage-aware trace를 심는 첫 단계다.
