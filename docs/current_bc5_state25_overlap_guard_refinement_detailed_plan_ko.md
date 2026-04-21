# BC5 State25 Overlap Guard Refinement 상세 계획

## 목적

`BC5`의 목적은 `state25_context_bridge_v1`의 overlap guard를 완전히 끄는 것이 아니라,
`forecast / belief / barrier`가 **같은 runtime hint를 포맷만 바꿔 반복 탑재한 경우**와
정말로 별도 위험 신호가 겹친 경우를 구분하는 것이다.

즉 이번 단계는 다음을 분리하는 작업이다.

- 같은 `state25_runtime_hint_v1`가 여러 bridge에 반복된 경우
- 실제로 서로 다른 힌트나 countertrend 신호가 같이 존재하는 경우

핵심 원칙:

- `BC5`는 `BC2 weight-only`에만 적용한다.
- `threshold / size` bridge에는 아직 적용하지 않는다.
- `countertrend_continuation_signal_v1`가 있으면 완화하지 않는다.
- 같은 runtime hint의 중복만 `review-friendly`하게 통과시킨다.

## 현재 문제

기존 overlap guard는 아래 source 중 하나만 있어도 바로 `double_counting_guard_active = true`로 처리했다.

- `forecast_state25_runtime_bridge_v1`
- `belief_state25_runtime_bridge_v1`
- `barrier_state25_runtime_bridge_v1`
- `countertrend_continuation_signal_v1`

이 방식의 문제는, 실제로는 `forecast / belief / barrier`가 모두 **같은 hint payload**를 읽고 있어도
세 개를 모두 별도 중복으로 보고 `effective = 0`까지 눌러버린다는 점이다.

특히 `XAUUSD` 같은 케이스에서:

- `requested_weight_count = 2`
- `effective_weight_count = 0`
- `suppressed_weight_count = 2`

가 되어, low-confidence review relief로 살린 후보가 다시 blanket guard에 눌리는 현상이 있었다.

## BC5 설계

### 1. overlap source는 그대로 수집

기존처럼 overlap source는 계속 수집한다.

- `forecast_state25_runtime_bridge_v1`
- `belief_state25_runtime_bridge_v1`
- `barrier_state25_runtime_bridge_v1`
- `countertrend_continuation_signal_v1`

### 2. runtime hint signature 비교 추가

아래 3개 source에 대해 `state25_runtime_hint_v1`의 signature를 추출한다.

- `scene_pattern_id`
- `entry_bias_hint`
- `wait_bias_hint`
- `exit_bias_hint`
- `transition_risk_hint`
- `reason_summary`

이 signature가 2개 이상 존재하고 서로 완전히 같으면:

- `same_runtime_hint_duplicate = true`

로 본다.

### 3. source-sensitive guard decision

`overlap_guard_decision`을 새로 둔다.

- `NO_OVERLAP`
- `BLOCKED_OVERLAP_DUPLICATE`
- `RELAXED_SAME_RUNTIME_HINT_DUPLICATE`

규칙:

- overlap source가 없으면 `NO_OVERLAP`
- `countertrend_continuation_signal_v1`가 있으면 무조건 `BLOCKED_OVERLAP_DUPLICATE`
- `RISK_DUPLICATE`이면서 `forecast / belief / barrier`가 같은 runtime hint를 반복하면
  - `RELAXED_SAME_RUNTIME_HINT_DUPLICATE`
  - `double_counting_guard_active = false`
- 그 외는 `BLOCKED_OVERLAP_DUPLICATE`

### 4. trace 보강

아래 trace를 남긴다.

- `overlap_same_runtime_hint_duplicate`
- `overlap_guard_decision`
- `OVERLAP_GUARD_RELAXED_SAME_RUNTIME_HINT`

그리고 한국어 trace에도 아래 뜻이 남아야 한다.

- 같은 runtime hint가 bridge 여러 개에 반복된 경우라서
- `BC5`에서는 weight-only review를 위해 suppression을 완화했다

## 기대 효과

### 개선되는 것

- 같은 runtime hint 중복 때문에 `requested -> effective 0`이 되는 blanket suppression 감소
- `BC4 weight-only log-only review lane`에서 실제 review 후보가 더 자연스럽게 surface
- low-confidence review relief와 BC4 review lane이 끊기지 않음

### 여전히 유지되는 것

- 진짜 별도 신호 overlap 차단
- countertrend signal overlap 차단
- threshold / size에는 아직 미적용
- hard override 없음

## 적용 범위

이번 단계는 아래에만 적용한다.

- [state25_context_bridge.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_context_bridge.py)
- [test_state25_context_bridge.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state25_context_bridge.py)
- [test_state25_weight_patch_review.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state25_weight_patch_review.py)

그리고 검증용 audit는 아래를 사용한다.

- [state25_context_bridge_overlap_guard_audit.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_context_bridge_overlap_guard_audit.py)

## 이번 단계에서 의도적으로 하지 않는 것

- overlap source별 상세 score 비교
- threshold / size bridge까지 동일 rule 확장
- `RELAX` threshold 계약 도입
- countertrend signal 완화
- live apply

이번 `BC5`는 오직 **weight-only review lane에서 blanket overlap suppression을 source-sensitive하게 줄이는 단계**다.
