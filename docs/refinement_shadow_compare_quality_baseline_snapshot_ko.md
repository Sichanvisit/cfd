# Shadow Compare Quality Baseline Snapshot

## 1. 기준 산출물

이번 baseline snapshot은 아래 최신 산출물을 기준으로 정리한다.

- shadow compare latest
  - [semantic_shadow_compare_report_20260326_175602.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_175602.json)
- preview audit latest
  - [semantic_preview_audit_20260326_175709.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_175709.json)

## 2. 핵심 요약

### preview audit

- `promotion_gate.status = pass`
- `promotion_gate.shadow_compare_ready = true`
- `promotion_gate.shadow_compare_status = warning`

warning은 여전히 아래 세 가지다.

- `entry_quality:split_health_warning`
- `exit_management:split_health_warning`
- `shadow_compare:shadow_compare_scorable_rows_below_gate`

### shadow compare

최신 shadow compare에서 중요한 값은 아래다.

- `rows_total = 22659`
- `shadow_available_rows = 22659`
- `matched_replay_rows = 310`
- `missing_replay_join_rows = 22349`
- `baseline_entered_rows = 60`
- `semantic_enter_rows = 22659`
- `scorable_shadow_rows = 0`
- `unscorable_shadow_rows = 22659`
- `trace_quality_counts = fallback_heavy only`
- `compare_label_counts = semantic_earlier_enter dominant`

## 3. baseline 해석

이 snapshot에서 보이는 결론은 단순하다.

1. `shadow compare plumbing 자체는 동작한다`
   - report 생성 성공
   - preview audit과 연결 성공

2. `품질 병목은 compare 가능한 row 부족이다`
   - `scorable_shadow_rows = 0`

3. `가장 큰 직접 원인은 replay join 부재다`
   - `missing_replay_join_rows = 22349`

4. `남는 소수 케이스는 label status 자체가 유효하지 않다`
   - `transition_status_not_valid = 310`
   - 최신 report 기준 status는 `INSUFFICIENT_FUTURE_BARS`

즉 지금 병목은:

- threshold 미세조정
- compare label wording
- preview 렌더링

이 아니라

- replay source alignment
- label availability timing

쪽에 더 가깝다.

## 4. 왜 이 snapshot이 중요한가

이 snapshot 덕분에 다음 작업 우선순위가 분명해진다.

- `S2 trace quality audit`보다 먼저
- 사실상 `replay join alignment`를 먼저 확인해야 한다

왜냐하면 trace quality가 전부 fallback-heavy인 것도 문제지만,
현재는 그보다 먼저 `join 자체가 거의 안 붙는 상태`이기 때문이다.

## 5. 다음 단계

다음 active step은 `S1 scorable row audit`을 조금 더 명확히 casebook으로 정리하고,
곧바로 `S2 trace quality audit`보다는
`replay join alignment / source scope audit`까지 같이 보는 쪽이 더 맞다.
