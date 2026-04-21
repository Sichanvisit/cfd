# Semantic Rollout Non-Apply Audit 상세 계획

## 목표

semantic rollout이 왜 실제 적용으로 이어지지 못했는지를 `promotion lane`과 `activation lane`으로 분리해서 읽을 수 있게 만든다.

## 왜 지금 필요한가

현재 semantic 계열은 한쪽에선:

- `log_only`
- `recent_row_count` 충분
- `shadow_available` 일부 존재

인데도 `eligible_count = 0`으로 promotion이 막히고,

다른 한쪽에선:

- bounded candidate stage 완료
- approval 완료

인데도 `runtime not idle` 때문에 activation이 막히고 있다.

즉 단순히 “semantic이 안 된다”가 아니라,

- 새 candidate 승격이 안 되는 이유
- 이미 승인된 candidate activation이 안 되는 이유

를 분리해서 봐야 한다.

## 입력 아티팩트

- `semantic_live_rollout_observation_latest.json`
- `semantic_shadow_active_runtime_readiness_latest.json`
- `semantic_shadow_bounded_candidate_stage_latest.json`
- `semantic_shadow_bounded_candidate_approval_latest.json`
- `semantic_shadow_active_runtime_activation_latest.json`

## 핵심 규칙

lane를 5개로 나눈다.

1. `promotion_counterfactual`
2. `runtime_readiness`
3. `candidate_stage`
4. `approval`
5. `runtime_activation`

특히 summary에서는 아래 두 축을 반드시 분리한다.

- `promotion_non_apply_reason_*`
- `activation_non_apply_reason_*`

promotion 우선 reason 예:

- `rollout_disabled`
- `shadow_runtime_unavailable`
- `baseline_no_action_dominant`
- `semantic_unavailable_dominant`
- `symbol_not_in_allowlist_dominant`
- `no_eligible_rows`

activation 우선 reason 예:

- `approval_pending`
- `runtime_not_idle_pending_activation`
- `approved_bundle_missing`
- `activation_not_started`

## 이번 단계에서 하지 않는 것

- semantic allowlist 변경
- rollout threshold 변경
- runtime 강제 activation
- promotion policy 변경

이번 단계는 `왜 아직 적용 안 됐는지`를 lane별로 설명하는 audit이다.

## 산출물

- `semantic_rollout_non_apply_audit_latest.json`
- `semantic_rollout_non_apply_audit_latest.md`

## 완료 조건

- promotion blocker와 activation blocker가 분리되어 보인다
- 최근 fallback reason이 무엇인지 한눈에 보인다
- “지금은 eligible row 문제인지, runtime idle 문제인지”를 바로 구분할 수 있다
