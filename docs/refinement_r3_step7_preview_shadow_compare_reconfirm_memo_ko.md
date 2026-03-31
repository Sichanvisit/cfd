# R3 Step 7 Preview / Shadow Compare Reconfirm Memo

## 1. 재확인 기준

이번 Step 7 재확인은 아래 조합으로 다시 실행했다.

- preview metrics:
  - [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_step6_20260326\metrics.json)
- dataset build manifest:
  - [semantic_v1_dataset_build_20260326_163015_945811.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_build_20260326_163015_945811.json)
- shadow compare report:
  - [semantic_shadow_compare_report_20260326_165911.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_165911.json)

최종 preview audit:

- [semantic_preview_audit_20260326_170014.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_170014.json)
- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

## 2. 결과 요약

### preview audit

- `report_version = semantic_preview_audit_v2`
- `join_coverage.status = healthy`
- `promotion_gate.status = pass`
- `promotion_gate.shadow_compare_ready = true`
- `promotion_gate.shadow_compare_status = warning`

warning은 아래 세 가지였다.

- `entry_quality:split_health_warning`
- `exit_management:split_health_warning`
- `shadow_compare:shadow_compare_scorable_rows_below_gate`

즉 현재 상태는:

- join과 metrics baseline은 괜찮고
- promotion-ready는 유지되지만
- shadow compare 품질은 아직 warning을 품고 있다

로 해석하는 것이 맞다.

### shadow compare

현재 shadow compare report는 아래 상태를 보였다.

- `rows_total = 21898`
- `shadow_available_rows = 21898`
- `baseline_entered_rows = 46`
- `semantic_enter_rows = 21898`
- `scorable_shadow_rows = 0`
- `trace_quality_counts = fallback_heavy only`

이 의미는 매우 중요하다.

- shadow compare report는 생성 자체는 잘 되었고
- compare label과 threshold table도 surface 됐지만
- 실제로는 scorable label이 거의 없어
- Step 7 audit 기준에서 `warning`으로 읽히는 것이 맞다

즉 Step 7이 해결한 것은 "shadow compare를 audit에 연결하는 문제"이고,
다음에 남는 것은 "shadow compare의 scorable quality를 어떻게 높일 것인가"에 가깝다.

## 3. feature tier 가시성

Step 7 preview audit에서는 target마다 아래가 이제 같이 읽힌다.

- `dataset_source_generation`
- `dataset_feature_tier_policy`
- `dataset_feature_tier_summary`
- `dataset_observed_only_dropped_feature_columns`

이 덕분에 Step 6에서 넣은 legacy/mixed/modern tier 정책이
preview audit에서도 직접 보이게 됐다.

## 4. 해석

이번 Step 7은 성공이다.

이유:

- preview audit이 실제로 `feature_tier + shadow_compare + promotion gate`를 함께 surface 한다
- missing shadow compare는 blocker로 읽힌다
- real shadow compare를 연결했을 때도 audit가 정상적으로 warning/pass를 분리해준다

다만 이번 재확인은 동시에 다음 숙제도 보여준다.

- shadow compare report는 생성되지만 scorable rows가 0이라 품질이 아직 낮다
- 따라서 이후 promotion gate 고도화나 bounded live readiness로 갈 때는
  `shadow compare label quality / replay label availability`를 다시 보는 작업이 필요하다

## 5. 결론

Step 7은 `preview / audit refinement` 관점에서는 닫아도 된다.

남는 follow-up은 Step 7 미완성이 아니라,

- shadow compare 품질 개선
- promotion gate 운영 기준 정제

쪽의 다음 트랙으로 보는 것이 더 정확하다.
