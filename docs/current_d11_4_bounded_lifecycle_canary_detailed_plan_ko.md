# D11-4. Bounded Lifecycle Canary 상세 계획

## 목적

- shadow audit을 통과한 lifecycle policy 중에서도 아주 좁은 범위만 bounded canary 후보로 read-only 선정한다.

## 핵심 원칙

- bounded canary는 아직 실행하지 않는다
- `BOUNDED_READY`는 recommendation일 뿐이다
- 우선은 `XAU single symbol`, `single policy slice` 같은 매우 좁은 범위만 허용한다

## 예상 row-level field

- `bounded_lifecycle_canary_profile_v1`
- `lifecycle_canary_candidate_state_v1`
- `lifecycle_canary_scope_v1`
- `lifecycle_canary_policy_slice_v1`
- `lifecycle_canary_eligibility_v1`
- `lifecycle_canary_reason_summary_v1`

## 후보 상태

- `BLOCKED`
- `OBSERVE_ONLY`
- `BOUNDED_READY`

## 완료 기준

- 세 심볼 모두 canary 후보 상태가 surface된다
- 아주 좁은 scope/slice 기준으로만 bounded ready가 나올 수 있다
