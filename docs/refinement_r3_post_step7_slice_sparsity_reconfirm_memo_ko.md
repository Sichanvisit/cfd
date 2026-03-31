# R3 Post-Step7 Slice Sparsity Reconfirm Memo

## 1. 목적

이 문서는 `unsupported sparse slice` 정책을 적용한 뒤
`entry_quality / exit_management split warning`이 실제로 어떻게 바뀌었는지
재생성된 dataset, preview model, preview audit 기준으로 다시 확인한 결과를 정리한다.

관련 기준 문서:

- [refinement_r3_post_step7_slice_sparsity_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_refinement_spec_ko.md)
- [refinement_r3_post_step7_slice_sparsity_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_refinement_implementation_checklist_ko.md)
- [refinement_r3_post_step7_split_warning_followup_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_split_warning_followup_memo_ko.md)

## 2. 적용한 정책

이번 라운드에서 바꾼 핵심은 `dataset_splits.py`의 sparse slice 분류 방식이다.

- `len(class_balance) < 2` 또는 `minority_rows <= 1`인 slice는
  `warning`이 아니라 `unsupported_sparse_slice`로 분리한다.
- `minority_rows < MIN_SLICE_MINORITY_ROWS`이지만 극단적인 single-class/1-row minority는 아닌 경우만
  기존 warning으로 유지한다.
- preview audit와 metrics에는 `unsupported_issues`를 별도로 surface한다.
- `warning_issues`는 실제로 후속 보정이 필요한 slice health 문제만 남긴다.

즉 이번 변경의 목적은
`경고를 억지로 숨기기`가 아니라
`구조 경고`와 `평가 대상이 되기 어려운 초희소 slice`를 분리하는 데 있다.

## 3. 재생성 산출물

### dataset build

- build manifest: [semantic_v1_dataset_build_20260326_211158_413120.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_build_20260326_211158_413120.json)
- join health: [semantic_v1_dataset_join_health_20260326_211158_413120.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_join_health_20260326_211158_413120.json)
- dataset dir: [semantic_v1_r3_slice_sparse_20260326](c:\Users\bhs33\Desktop\project\cfd\data\datasets\semantic_v1_r3_slice_sparse_20260326)

### preview model

- model dir: [semantic_v1_preview_r3_slice_sparse_20260326](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_slice_sparse_20260326)
- metrics: [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_slice_sparse_20260326\metrics.json)

### preview audit

- audit json: [semantic_preview_audit_20260326_211339.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_211339.json)
- audit latest: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- shadow compare baseline used: [semantic_shadow_compare_report_20260326_200401.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_200401.json)

## 4. 결과 요약

### promotion gate

- `promotion_gate.status = pass`
- `promotion_gate.warning_issues = []`
- `shadow_compare_status = healthy`

즉 Post-Step7 follow-up에서 남아 있던
`entry_quality:split_health_warning`,
`exit_management:split_health_warning`
은 최신 preview audit 기준으로는 더 이상 warning으로 남아 있지 않다.

### timing

- 기존과 동일하게 `split_health_status = healthy`
- 추가 follow-up 필요 없음

### entry_quality

- `split_health_status = healthy`
- `unsupported_issues = ["preflight_regime:unsupported_slices=1/2"]`
- `preflight_regime = TREND` test slice는 여전히 single-class이지만
  이제는 actionable warning이 아니라 `unsupported sparse slice`로 분리된다.

해석:

- 이 slice는 지금 당장 split policy bug로 볼 대상이 아니다.
- 평가 표본이 극단적으로 치우친 영역이라는 뜻이므로
  이후에는 `warning`이 아니라 `coverage/unsupported memo`로 읽는 것이 맞다.

### exit_management

- `split_health_status = healthy`
- `unsupported_issues = ["symbol:unsupported_slices=2/3", "setup_id:unsupported_slices=1/2"]`
- `symbol = NAS100`, `symbol = XAUUSD`, `setup_id = range_upper_reversal_sell`은
  여전히 극단 희소 slice이지만 actionable warning은 아니다.
- regime holdout은 여전히 summary 내부에 `holdout_minority_below_minimum:2<8`가 남아 있지만,
  현재 overall split health와 promotion gate를 막는 수준으로 surface되지는 않는다.

해석:

- 기존 warning의 핵심은 plumbing 문제가 아니라 희소 slice 자체였다.
- 이번 라운드로 그 성격이 분리되었고,
  이제 남은 것은 구조 버그가 아니라 향후 data density 확보나 aggregation policy 논의다.

## 5. metric 변화

metric 자체는 크게 흔들지 않았다.

- `timing`
  - AUC: `0.633218` 유지
- `entry_quality`
  - AUC: `0.598303` 유지
- `exit_management`
  - AUC: `0.876899` 유지

즉 이번 정책은
모델 성능을 억지로 바꾸기 위한 변경이 아니라
warning taxonomy를 더 정확하게 만드는 변경으로 작동했다.

## 6. 이번 라운드의 의미

이번 결과로 확인된 것은 세 가지다.

1. 남아 있던 warning의 큰 부분은 split plumbing이 아니라 slice sparsity였다.
2. unsupported sparse slice를 warning과 분리해도 preview metric은 무너지지 않았다.
3. 최신 preview audit은 이제 `promotion gate pass + warning 없음` 기준으로 읽을 수 있다.

즉 R3 본선 이후 이어진 post-Step7 follow-up은
현재 시점 기준으로는 한 번 닫아도 되는 상태다.

## 7. 남은 관측 포인트

완전히 사라진 것이 아니라 별도 성격으로 남아 있는 항목은 아래와 같다.

- `entry_quality / preflight_regime = TREND` coverage 부족
- `exit_management / NAS100, XAUUSD, range_upper_reversal_sell` 희소 slice
- `regime_holdout minority 2<8` 같은 초소형 holdout 현상

이 항목들은 이제 `warning fix`보다는
`coverage expansion / aggregation / future data policy` 후보로 보는 것이 맞다.

## 8. 현재 판정

현재 위치는 이렇게 정리할 수 있다.

- R3 Step 3~7: 완료
- shadow compare quality / source cleanup: 완료
- post-Step7 split warning follow-up: 이번 라운드로 1차 종료 가능
- 다음 후보:
  - bounded live / promotion 운영 기준 정리
  - 희소 slice coverage 확보 전략
  - future aggregation policy 검토
