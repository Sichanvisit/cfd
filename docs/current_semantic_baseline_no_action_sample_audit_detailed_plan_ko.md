# Semantic Baseline No-Action Sample Audit 상세 계획

## 목표

최근 semantic rollout recent 200행에서 `baseline_no_action`이 어떤 장면들에 의해 지배되는지 샘플 수준으로 읽을 수 있게 만든다.

## 왜 지금 필요한가

semantic non-apply audit에서 `baseline_no_action_dominant`가 promotion blocker로 보였지만, 이 말만으로는

- 어떤 symbol인지
- 어떤 observe_reason인지
- 어떤 blocked_by인지
- 어떤 action_none_reason인지

를 알기 어렵다.

즉 이번 단계는 최근 200행에서 `baseline_no_action` 샘플을 직접 뽑아, dominant cluster를 읽는 audit이다.

## 입력

- `data/trades/entry_decisions.csv`

## 핵심 산출물

- `recent_row_count`
- `baseline_no_action_count`
- `symbol_counts`
- `observe_reason_counts`
- `blocked_by_counts`
- `action_none_reason_counts`
- `semantic_shadow_trace_quality_counts`
- `dominant_cluster`
- sample rows

cluster key는 아래 4개를 붙여 만든다.

- `symbol`
- `observe_reason`
- `blocked_by`
- `action_none_reason`

## 이번 단계에서 하지 않는 것

- semantic allowlist 수정
- baseline action policy 수정
- semantic threshold 수정

즉 이번 단계는 “어떤 장면군이 baseline_no_action을 반복 생산하는지”를 먼저 보는 audit이다.
