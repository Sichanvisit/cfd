# F10. bounded candidate shadow apply

## 1. 목적

F10의 목적은 F9에서 생성된 `bounded calibration candidate`를
전체 시스템에 바로 반영하지 않고,

**아주 좁은 symbol / state / window 범위에서만 shadow-only로 시험 적용**

하는 것이다.

즉 F10은 threshold patch를 live judgment에 곧바로 태우는 층이 아니다.
F10은 candidate를

- apply session으로 전환하고
- before / after를 같은 조건에서 비교 가능하게 만들고
- 부작용 없이 시험 가능한 운영 범위를 강제하는

**controlled experiment layer**

다.

---

## 2. 왜 필요한가

F9까지 오면 우리는 이미 안다.

- 무엇을 바꿔볼지
- 왜 그 key가 후보가 되었는지
- 얼마나 작게 움직여야 하는지

하지만 candidate를 만들었다고 해서
바로 값을 바꾸면 아래 문제가 생긴다.

### 2-1. local optimization trap

특정 BTC row에서는 ambiguity threshold를 조금 완화하면 좋아 보일 수 있다.
그러나 다른 BTC window나 다른 state bucket에서는
오히려 false widening이 늘 수 있다.

### 2-2. 구조 침범 위험

candidate는 tunable control만 다뤄야 하는데,
적용 범위가 넓어지면 실제로는 해석 구조 전체를 흔들 수 있다.

### 2-3. 평가 불가능 문제

candidate를 곧바로 전체 반영하면
"이 변화가 실제로 후보 개선에 도움이 됐는지"를
분리해서 보기 어렵다.

따라서 F10은

**좋은 아이디어를 작은 범위에서만 시험해,
후속 평가가 가능한 before / after 실험 세션으로 바꾸는 층**

이어야 한다.

---

## 3. 상위 원칙

### 3-1. F10은 운영층이지 해석층이 아니다

F10은 새로운 해석 권한을 만들지 않는다.
F10은 F1~F9가 이미 만든 구조 위에서만 작동한다.

즉 F10은

- `dominant_side`
- `dominance_gap` 계산 구조
- rejection split
- structure gate 권한

을 바꾸지 못한다.

### 3-2. 기본 apply mode는 `SHADOW_ONLY`

첫 운영에서는 candidate를 live 판단에 직접 반영하지 않는다.

기본 모드는 아래처럼 둔다.

- `SHADOW_ONLY`
- `LOG_ONLY`
- `LIMITED_APPLY`는 이후 단계

즉 처음에는

- 현재 live 판단은 그대로 두고
- 병렬로 candidate patch를 재계산하고
- before / after 차이만 surface

하는 것이 원칙이다.

### 3-3. apply scope는 좁을수록 좋다

첫 bounded apply는 가능한 한 아래 순서로 좁게 시작한다.

- symbol 1개
- learning key 1개
- state bucket 제한
- recent validation window 제한
- apply duration 제한

### 3-4. delta는 항상 bounded

F10은 candidate 안의 `max_allowed_delta`를 넘지 못한다.

또한 아래를 같이 지킨다.

- same key 연속 RELAX는 관찰 기간 없이 허용하지 않음
- safety가 낮은 candidate는 delta를 더 줄임
- shared/common parameter는 local parameter보다 더 작은 delta에서 시작

### 3-5. conflict candidate는 동시에 활성화하지 않는다

서로 반대 방향 효과를 가지는 candidate는
같은 scope 안에서 동시에 켜지면 안 된다.

예:

- `flow.ambiguity_threshold` relax
- `flow.conviction_building_floor` tighten

가 같은 symbol / same state bucket / 같은 validation window에서
동시에 활성화되면 결과가 섞인다.

따라서 conflict rule은 아래처럼 둔다.

- 겹치는 scope 안에서 반대 효과면 conflict
- conflict가 있으면 higher priority candidate만 유지
- 나머지는 `HOLD`

### 3-6. candidate drift memory를 가진다

같은 key를 계속 같은 방향으로 밀다 보면
bounded calibration이 아니라 silent drift가 된다.

따라서 F10에는 최소 아래 보호가 필요하다.

- `symbol × learning_key` 기준 cumulative delta 추적
- shared/common parameter는 별도 global drift 추적
- cumulative shift가 기준 범위를 넘으면 추가 relax/tighten 차단

즉 F10은

**개별 candidate의 delta뿐 아니라,
같은 key가 시간이 지나며 얼마나 멀리 이동했는지도 봐야 한다.**

---

## 4. 입력 층

F10은 기본적으로 F9 candidate catalog를 입력으로 받는다.

최소 입력 필드:

- `candidate_id`
- `symbol`
- `learning_key`
- `current_value`
- `proposed_value`
- `delta`
- `max_allowed_delta`
- `confidence`
- `candidate_priority_score_v1`
- `scope`
- `rollback.auto_rollback_if`
- `status`

보조 해석 입력:

- `flow_support_state_v1`
- `flow_structure_gate_v1`
- `aggregate_conviction_v1`
- `flow_persistence_v1`
- `flow_threshold_profile_v1`

---

## 5. apply session 개념

F10에서는 candidate 자체와 apply session을 분리하는 편이 좋다.

candidate는
"무엇을 바꿀까"를 말하고,
apply session은
"그 candidate를 언제 어디에 어떻게 시험 중인가"를 말한다.

### 5-1. apply session 예시

```json
{
  "apply_session_id": "F10-BTCUSD-flow.ambiguity_threshold-20260415-01",
  "candidate_id": "BTCUSD:flow.ambiguity_threshold",
  "apply_mode": "SHADOW_ONLY",
  "symbol": "BTCUSD",
  "learning_key": "flow.ambiguity_threshold",
  "status": "ACTIVE",
  "scope": {
    "apply_states": ["FLOW_BUILDING", "FLOW_UNCONFIRMED"],
    "validation_windows": ["recent_live", "retained_symbol_windows"],
    "apply_duration_hours": 48
  },
  "candidate_patch": {
    "current_value": 0.40,
    "proposed_value": 0.35,
    "delta": -0.05
  },
  "started_at": "2026-04-15T10:00:00+09:00",
  "scheduled_review_at": "2026-04-17T10:00:00+09:00"
}
```

---

## 6. row-level before / after surface

F11이 나중에 판정하려면,
F10은 row 수준 차이를 일관되게 남겨야 한다.

### 6-1. apply fields

- `bounded_apply_session_id_v1`
- `bounded_apply_candidate_id_v1`
- `bounded_apply_mode_v1`
- `bounded_apply_scope_match_v1`

### 6-2. before / after fields

- `flow_support_state_before_v1`
- `flow_support_state_after_v1`
- `flow_structure_gate_before_v1`
- `flow_structure_gate_after_v1`
- `aggregate_conviction_before_v1`
- `aggregate_conviction_after_v1`
- `flow_persistence_before_v1`
- `flow_persistence_after_v1`

### 6-3. diff fields

- `flow_state_changed_v1`
- `flow_state_change_type_v1`
- `conviction_delta_v1`
- `persistence_delta_v1`
- `candidate_effect_direction_v1`

### 6-4. guard fields

- `bounded_apply_conflict_flag_v1`
- `bounded_apply_conflict_reason_v1`
- `bounded_apply_block_reason_v1`
- `bounded_apply_drift_guard_state_v1`

---

## 7. apply session 상태

F10 apply session 상태는 최소 아래처럼 두는 편이 좋다.

- `PROPOSED`
- `ACTIVE`
- `HOLD`
- `BLOCKED`
- `COMPLETED`
- `ROLLED_BACK`

### 7-1. `HOLD`

conflict candidate가 생겼거나,
더 높은 priority candidate가 같은 scope를 점유하는 경우

### 7-2. `BLOCKED`

- immutable rule 침범 위험
- drift limit 초과
- scope 불일치
- invalid patch

### 7-3. `COMPLETED`

정해진 shadow 관찰 기간을 마치고
F11 evaluation으로 넘길 준비가 된 상태

---

## 8. session-level summary

F10 summary와 artifact에는 최소 아래가 필요하다.

- `active_apply_session_count`
- `apply_mode_count_summary`
- `apply_status_count_summary`
- `apply_symbol_count_summary`
- `apply_learning_key_count_summary`
- `conflict_session_count`
- `drift_guard_block_count`

이 summary는
"현재 어떤 candidate가 시험 중인가"를 보여주는 운영 표면이다.

---

## 9. 완료 기준

- candidate별 apply session이 추적 가능하다
- before / after diff가 row 수준에서 남는다
- scope 밖 row에는 영향이 없다
- conflict candidate가 동시에 활성화되지 않는다
- drift memory가 누적 이동을 제한한다
- live 판단은 기본적으로 바뀌지 않는다

---

## 10. 다음 단계 연결

F10이 끝나면 다음은 F11이다.

F11은 F10의 before / after 결과를 candidate 단위로 집계해,

- `PROMOTE`
- `KEEP_OBSERVING`
- `EXPIRE_WITHOUT_PROMOTION`
- `ROLLBACK`

중 하나로 판정하는 evaluation / governance 층이다.
