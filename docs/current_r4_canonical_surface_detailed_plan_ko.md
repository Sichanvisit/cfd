# R4 Canonical Surface 상세 계획

## 1. 목적

R4의 목적은 chart, runtime, execution, hindsight가 같은 장면을 같은 이름으로 부르게 만드는 것이다.

지금 시스템에는 이미 많은 surface가 있다.

- `directional_continuation_overlay_event_kind_hint`
- `entry_candidate_surface_family/state`
- `breakout_candidate_surface_family/state`
- `execution_diff_final_action_side`
- `should_have_done expected_surface`

하지만 이 값들은 아직 소비자마다 다른 이름과 다른 층위로 흩어져 있다.

R4는 이걸 최소 공용 표면 언어로 묶는다.

## 2. R4 v1에서 하는 일

R4 첫 버전은 execution을 바꾸지 않는다.

대신 아래를 만든다.

- `canonical_runtime_surface_name_v1`
- `canonical_execution_surface_name_v1`
- `canonical_direction_annotation_v1`
- `canonical_continuation_annotation_v1`
- `canonical_phase_v1`
- `canonical_runtime_execution_alignment_v1`

즉 지금 단계에서는 `공용 이름`을 먼저 만들고,
실제 차트나 실행이 모두 이 이름을 직접 쓰도록 바꾸는 것은 다음 단계에서 한다.

## 3. 왜 지금 필요한가

R3 should-have-done이 생기면 이제 실제 출력과 정답 후보를 비교해야 한다.

그런데 현재는

- chart는 `BUY_WATCH`
- execution은 `BUY`
- hindsight는 `expected_surface`

처럼 다른 말로 같은 장면을 부를 수 있다.

이 상태에선 이후 accuracy와 state25 연결이 흔들린다.

그래서 R4는 `같은 장면을 같은 언어로 비교할 수 있게 만드는 중간층`이다.

## 4. v1 공용 규칙

### 4-1. runtime surface

우선순위:

- `directional_continuation_overlay_event_kind_hint`
- overlay direction fallback
- 없으면 `WAIT`

### 4-2. execution surface

매핑:

- final `BUY` -> `BUY_EXECUTION`
- final `SELL` -> `SELL_EXECUTION`
- 그 외 -> `WAIT`

### 4-3. annotation mapping

- runtime surface가 `BUY*`면 `UP`
- runtime surface가 `SELL*`면 `DOWN`
- `WAIT`면 `NEUTRAL`

### 4-4. phase

첫 버전은 보수적으로 간다.

- `LOW_ALIGNMENT`, `DIRECTION_TIE` -> `BOUNDARY`
- countertrend signal 활성 -> `REVERSAL`
- 그 외 directional surface -> `CONTINUATION`

## 5. priority rule

R4는 아래 우선순위를 계약으로 고정한다.

- `phase > continuation > direction`

즉 surface를 해석할 때 phase가 가장 상위 문맥이다.

## 6. 상태 기준

### READY

- canonical contract가 고정됨
- row-level canonical fields가 붙음
- summary/artifact가 생성됨

### HOLD

- contract는 있으나 row와 summary가 같은 언어를 공유하지 못함

### BLOCKED

- chart/runtime/execution이 서로 다른 canonical 이름 체계를 씀

## 7. 산출물

- `canonical_surface_contract_v1`
- `canonical_surface_summary_v1`
- `canonical_surface_artifact_paths`
- `data/analysis/shadow_auto/canonical_surface_summary_latest.json`
- `data/analysis/shadow_auto/canonical_surface_summary_latest.md`

## 8. R4가 닫혔다는 뜻

R4가 닫혔다는 것은 공용 이름이 생겼다는 뜻이다.

정확한 의미는 이렇다.

- runtime row가 canonical surface를 가진다
- execution 결과도 같은 canonical 비교 축으로 볼 수 있다
- should-have-done의 `expected_surface`와 실제 runtime surface를 같은 말로 비교할 준비가 된다

즉 R4는 `언어 통합` 단계다.
