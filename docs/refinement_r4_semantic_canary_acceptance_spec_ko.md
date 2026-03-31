# R4 Semantic Canary Acceptance Spec

## 1. 목적

이 문서는 R4에서 `semantic canary`를

- 단순 관찰 리포트
- 또는 bounded-live 직전 acceptance gate

중 무엇으로 읽을지 고정하기 위한 spec이다.

이번 단계의 목적은 canary를 새로 만드는 것이 아니라,

- 어떤 경우를 `pass`
- 어떤 경우를 `hold`
- 어떤 경우를 `stop`

으로 읽을지 운영 언어로 고정하는 것이다.

## 2. 입력 근거

- canary report latest: [semantic_canary_rollout_BTCUSD_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_canary\semantic_canary_rollout_BTCUSD_latest.json)
- canary markdown latest: [semantic_canary_rollout_BTCUSD_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_canary\semantic_canary_rollout_BTCUSD_latest.md)
- runtime status: [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- preview audit latest: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- shadow compare healthy baseline: [semantic_shadow_compare_report_20260326_200401.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_200401.json)
- runtime reason casebook: [refinement_r4_runtime_reason_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_runtime_reason_casebook_ko.md)
- rollback / kill switch contract: [refinement_r4_rollback_kill_switch_contract_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_rollback_kill_switch_contract_ko.md)

owner:

- [check_semantic_canary_rollout.py](c:\Users\bhs33\Desktop\project\cfd\scripts\check_semantic_canary_rollout.py)
- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)

## 3. canary의 역할

semantic canary는 preview audit을 대체하지 않는다.

역할 분리는 아래와 같다.

- preview audit:
  - 모델 / split / shadow compare / promotion gate의 건강도 확인
- runtime reason casebook:
  - 현재 live recent가 왜 fallback / allowlist block / no action인지 해석
- semantic canary:
  - `최근 운영 윈도우에서 semantic threshold가 실제로 적용되고 있는가`
  - `fallback이 지나치게 높지는 않은가`
  - `semantic unavailable / compatibility block이 관측 윈도우에 재등장하는가`

즉 canary는 `preview가 healthy인데 runtime이 너무 보수적인가`를 보는 보조 acceptance gate다.

## 4. 핵심 관측 축

canary에서 직접 읽는 핵심 항목은 아래와 같다.

- `recent_rows`
- `threshold_applied_rows`
- `fallback_rows`
- `fallback_ratio`
- `threshold_applied_ratio`
- `fallback_reason_counts`
- `trace_quality_counts`
- `recommendation.value`

특히 다음 reason은 별도 owner로 본다.

- `baseline_no_action`
- `symbol_not_in_allowlist`
- `semantic_unavailable`
- `compatibility_mode_blocked`

## 5. pass / hold / stop 해석 기준

### A. Pass

아래를 모두 만족할 때만 canary `pass`로 본다.

- report freshness가 운영 윈도우 안이다
- `recent_rows`가 충분하다
- `fallback_ratio`가 높더라도 주원인이 `baseline_no_action` 또는 `symbol_not_in_allowlist`다
- `semantic_unavailable`, `compatibility_mode_blocked`가 지배적이지 않다
- preview audit는 계속 `promotion_gate.status = pass`
- shadow compare는 계속 healthy다

의미:

- semantic 구조는 건강하고
- runtime fallback도 운영 정책으로 설명 가능하다

### B. Hold

아래 중 하나면 `hold`다.

- `fallback_ratio`가 매우 높다
- `threshold_applied_ratio`가 0에 가깝다
- 그러나 preview / shadow는 healthy다
- `semantic_unavailable`, `compatibility_mode_blocked`가 소수이긴 하지만 다시 관측된다

의미:

- 지금 바로 partial live로 넘길 상태는 아니고
- threshold_only 유지 / allowlist 확장 후보 검토 단계로 보는 것이 맞다

### C. Stop

아래 중 하나면 `stop`이다.

- `semantic_unavailable`가 주요 fallback reason이 된다
- `compatibility_mode_blocked`가 반복되고 비율이 커진다
- trace quality가 `fallback_heavy` 외에 `unknown`, `incomplete`, provenance mismatch 계열로 흔들린다
- preview audit / shadow compare도 동시에 나빠진다

의미:

- bounded live 논의를 멈추고
- runtime source / compatibility contract부터 다시 봐야 한다

## 6. 현재 상태 해석

최신 [semantic_canary_rollout_BTCUSD_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_canary\semantic_canary_rollout_BTCUSD_latest.json) 기준:

- `recent_rows = 4000`
- `threshold_applied_rows = 0`
- `fallback_rows = 4000`
- `fallback_ratio = 1.0`
- `threshold_applied_ratio = 0.0`
- recommendation = `too_strict_fallback`
- fallback reasons:
  - `baseline_no_action = 3696`
  - `semantic_unavailable = 233`
  - `compatibility_mode_blocked = 71`
- trace quality:
  - `fallback_heavy = 4000`

같은 시점의 preview audit 기준:

- `promotion_gate.status = pass`
- `warning_issues = []`
- shadow compare healthy

따라서 현재 해석은 다음이 맞다.

- canary status: `hold`
- 운영 action: `stay_threshold_only`
- bounded live / partial_live: 아직 아님

핵심 이유:

- fallback 대부분은 `baseline_no_action`이라 구조 붕괴는 아니다
- 하지만 `semantic_unavailable`와 `compatibility_mode_blocked`가 0이 아니므로
  canary를 `pass`라고 말하긴 이르다

## 7. R4에서 canary가 의미하는 것

R4에서 semantic canary는 다음 둘 사이를 가르는 문턱이다.

- `확장 후보를 정리해도 되는 상태`
- `partial_live를 검토해도 되는 상태`

현재는 첫 번째 상태에는 들어가지만,
두 번째 상태까지는 아직 아니다.

즉 canary는 현재

- `allowlist expansion candidate memo`와는 양립 가능
- `enable_partial_live`의 직접 근거로는 아직 부족

하다고 정리한다.

## 8. 완료 기준

- semantic canary를 `pass / hold / stop`으로 운영 해석할 수 있다
- preview audit / shadow compare / runtime reason과 역할이 섞이지 않는다
- 현재 시점의 canary 해석이 `stay_threshold_only`와 일관되게 설명된다
