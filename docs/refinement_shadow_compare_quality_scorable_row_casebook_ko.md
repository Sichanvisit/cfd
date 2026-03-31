# Shadow Compare Scorable Row Casebook

## 1. 목적

이 문서는 shadow compare에서 `actual_positive`가 왜 만들어지지 않는지,
즉 왜 row가 scorable하지 않은지를 reason taxonomy로 정리한 casebook이다.

## 2. 현재 taxonomy

현재 [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)에 들어간 taxonomy는 아래다.

- `missing_replay_join`
- `transition_status_not_valid`
- `label_ambiguous`
- `is_censored`
- `no_transition_counts`
- `scorable`

이 taxonomy는 최신 report의

- `summary.matched_replay_rows`
- `summary.missing_replay_join_rows`
- `scorable_exclusion_reason_counts`
- `transition_label_status_counts`

로 surface 된다.

## 3. 최신 full report 기준 dominant reason

기준 report:

- [semantic_shadow_compare_report_20260326_175602.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_175602.json)

dominant reason:

- `missing_replay_join = 22349`
- `transition_status_not_valid = 310`
- `label_ambiguous = 0`
- `is_censored = 0`
- `no_transition_counts = 0`
- `scorable = 0`

즉 현재는 ambiguous/censored보다 훨씬 앞단에서
`replay join 자체가 대부분 성립하지 않는 상태`다.

## 4. symbol별 분해

### BTCUSD

- rows: `7550`
- `missing_replay_join = 7446`
- `transition_status_not_valid = 104`

### NAS100

- rows: `7555`
- `missing_replay_join = 7455`
- `transition_status_not_valid = 100`

### XAUUSD

- rows: `7554`
- `missing_replay_join = 7448`
- `transition_status_not_valid = 106`

해석:

- 특정 심볼 하나의 문제라기보다
- 전 심볼 공통으로 replay join이 먼저 비고 있다

## 5. transition_status_not_valid 해석

최신 report 기준 `transition_label_status_counts`는:

- `UNKNOWN = 22349`
- `INSUFFICIENT_FUTURE_BARS = 310`

즉 join이 붙은 소수 케이스도
대부분 `VALID`가 아니라 `INSUFFICIENT_FUTURE_BARS`라서 scorable로 못 간다.

이건 다음을 뜻한다.

- replay row는 일부 있지만
- label horizon이 아직 닫히지 않았거나
- compare 시점이 너무 이른 row가 포함되어 있다

## 6. 표본 확인

최근 200개 shadow-available row를 기준으로,
최신 replay 파일 2개만 본 빠른 표본 점검에서도 아래가 나왔다.

- `matched_keys = 0`
- `trace_quality_counts = fallback_heavy only`
- `compare_label_counts = semantic_earlier_enter dominant`
- `reason_counts = missing_replay_join only`

즉 quick sample과 full report가 같은 방향을 가리킨다.

## 7. 결론

현재 S1의 결론은 명확하다.

- 문제의 1순위는 `missing_replay_join`
- 문제의 2순위는 `transition_status_not_valid`
- ambiguous / censored / no-count는 아직 주 원인이 아니다

따라서 다음 구현 우선순위는

1. replay source scope / alignment audit
2. label horizon timing audit
3. 그 다음 trace quality audit

순서가 더 맞다.
