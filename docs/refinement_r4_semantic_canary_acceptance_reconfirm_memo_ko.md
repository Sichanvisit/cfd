# R4 Semantic Canary Acceptance Reconfirm Memo

## 1. 요약

최신 canary 기준으로 현재 semantic canary 상태는 `pass`가 아니라 `hold`다.

즉:

- preview / shadow는 healthy
- promotion gate는 pass
- 하지만 canary는 여전히 `too_strict_fallback`

이므로 R4 운영 action은 계속 `stay_threshold_only`가 맞다.

## 2. 최신 근거

기준 리포트:

- [semantic_canary_rollout_BTCUSD_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_canary\semantic_canary_rollout_BTCUSD_latest.json)
- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

canary 최신 값:

- `generated_at = 2026-03-26T22:10:51+09:00`
- `recent_rows = 4000`
- `threshold_applied_rows = 0`
- `fallback_rows = 4000`
- `fallback_ratio = 1.0`
- `threshold_applied_ratio = 0.0`
- `recommendation = too_strict_fallback`

fallback reason:

- `baseline_no_action = 3696`
- `semantic_unavailable = 233`
- `compatibility_mode_blocked = 71`

trace quality:

- `fallback_heavy = 4000`

preview / shadow:

- `promotion_gate.status = pass`
- `warning_issues = []`
- `shadow_compare.status = healthy`

## 3. 해석

이번 canary는 구조 붕괴를 말하진 않는다.

왜냐하면:

- preview / shadow가 healthy이고
- fallback의 대다수는 `baseline_no_action`이기 때문이다.

하지만 `semantic_unavailable`와 `compatibility_mode_blocked`가 0이 아니므로,
canary를 `pass`라고 읽어서는 안 된다.

따라서 현재 해석은 아래가 맞다.

- canary status: `hold`
- bounded live readiness: `not yet`
- allowlist expansion candidate review: `possible`
- immediate rollback: `not required`

## 4. 현재 운영 결론

R4에서 semantic canary는 지금

- `expand_allowlist candidate memo`와는 양립 가능
- `enable_partial_live` 근거로는 아직 부족

하다고 정리한다.

즉 현재 운영 결론은:

- `stay_threshold_only`
- `allowlist expansion 후보는 NAS100 -> XAUUSD 순으로 검토`
- `partial_live는 canary가 pass로 올라오기 전까지 보류`

로 잠그는 것이 맞다.
