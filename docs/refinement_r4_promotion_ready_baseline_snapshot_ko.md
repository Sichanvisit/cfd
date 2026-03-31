# R4 Promotion-Ready Baseline Snapshot

## 1. 목적

이 문서는 R4 착수 시점의 현재 상태를
`preview/shadow 기준`과 `runtime 기준`으로 나눠 고정한다.

이번 snapshot의 목적은
지금 상태가 왜 `promotion-ready pass`이면서도
동시에 `운영상 아직 threshold_only`인지 설명 가능하게 만드는 것이다.

## 2. preview / shadow 기준

기준 산출물:

- audit latest: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- audit json: [semantic_preview_audit_20260326_211339.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_211339.json)
- shadow compare: [semantic_shadow_compare_report_20260326_200401.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_200401.json)

현재 판정:

- `promotion_gate.status = pass`
- `promotion_gate.warning_issues = []`
- `shadow_compare_status = healthy`
- `join_coverage.status = healthy`

해석:

- preview / dataset / shadow compare 기준으론 R3 후속까지 한 번 닫힌 상태다.
- 즉 문서상 `promotion-ready`는 성립한다.

## 3. runtime 기준

기준 산출물:

- runtime status: [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)

현재 상태:

- `semantic_live_config.mode = threshold_only`
- `semantic_live_config.kill_switch = false`
- `semantic_live_config.symbol_allowlist = ["BTCUSD"]`
- `semantic_live_config.allowed_compatibility_modes = ["observe_confirm_v1_fallback"]`
- `semantic_rollout_state.entry.threshold_applied_total = 0`
- `semantic_rollout_state.entry.fallback_total = 2391`
- recent reason에는 `baseline_no_action`, `symbol_not_in_allowlist`, `trace_quality_state = fallback_heavy`가 반복 surface 된다

해석:

- semantic runtime은 살아 있고 shadow도 active다.
- 하지만 운영 적용은 아직 매우 보수적이다.
- 현재는 `threshold_only + single symbol allowlist + alert 중심` 상태로 보는 것이 맞다.

## 4. 현재 위치 해석

현재 위치는 아래처럼 읽는 것이 정확하다.

### 문서상 상태

- pass

### 운영상 상태

- bounded live 직전
- 아직 확장 실행 단계는 아님

즉 지금은
`preview/shadow 건강성 확인은 끝났고, 이제 실제 운영 승격 기준을 문서와 runbook으로 잠글 차례`
라고 보는 것이 맞다.

## 5. 현재 리스크

### 리스크 1. runtime recent fallback-heavy

- preview/shadow/source cleanup 기준으론 구조 bug가 정리됐어도
- runtime recent에는 여전히 `fallback_heavy`가 많이 surface 된다

현재 해석:

- 즉시 stop 사유는 아니다
- 하지만 bounded live 확장 전에는 운영상 이유를 명시적으로 분류해야 한다

### 리스크 2. allowlist 확장 부재

- 현재 `BTCUSD`만 allowlist에 있다
- `NAS100`, `XAUUSD`는 quality가 좋아도 runtime에선 `symbol_not_in_allowlist`로 남는다

현재 해석:

- 모델 품질 문제와 운영 확장 정책 문제를 분리해서 봐야 한다

### 리스크 3. threshold applied total = 0

- 현재 rollout state는 shadow/alert 중심이고
- threshold adjustment가 실제 runtime 행동에 거의 개입하지 않았다

현재 해석:

- 다음 단계는 바로 partial_live보다
  먼저 `threshold_only operational criteria`를 더 명확히 하는 것이 안전하다

## 6. 현재 추천 action

이번 snapshot 기준 추천은 아래와 같다.

1. `threshold_only 유지`
2. R4 문서/체크리스트로 bounded-live 승격 기준 고정
3. 그 다음에만 `allowlist 확장` 여부 판단

즉 지금 시점의 추천 action은
`바로 partial_live로 가기`가 아니라
`promotion-ready 기준을 운영 runbook으로 확정`하는 것이다.
