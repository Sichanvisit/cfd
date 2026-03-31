# R3 Post-Step7 Slice Sparsity Refinement Implementation Checklist

## 1. 목적

이 문서는 [refinement_r3_post_step7_slice_sparsity_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_slice_sparsity_refinement_spec_ko.md)의 실행 checklist다.

이번 단계는 `split plumbing`을 더 만지는 단계가 아니라,
남아 있는 `entry_quality / exit_management` warning을
`slice sparsity policy`로 분리해서 다루는 단계다.

## 2. 입력 기준

- latest preview audit: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- latest holdout follow-up memo: [refinement_r3_post_step7_split_warning_followup_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_split_warning_followup_memo_ko.md)
- current holdout preview model dir: [semantic_v1_preview_r3_holdout_20260326](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_holdout_20260326)
- current holdout dataset dir: [semantic_v1_r3_holdout_20260326](c:\Users\bhs33\Desktop\project\cfd\data\datasets\semantic_v1_r3_holdout_20260326)

대상 owner:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)

## 3. Step 1. Sparse Slice Baseline Snapshot

목표:

- 현재 warning을 숫자로 다시 고정한다.

확인 항목:

- `entry_quality` warning slice
- `exit_management` warning slice
- 각 slice의 rows / class_balance / minority_rows
- holdout health 현황

완료 기준:

- 이후 구현 전후 비교표가 생긴다.

## 4. Step 2. Entry Quality Sparse Slice Casebook

목표:

- `entry_quality`의 `preflight_regime:TREND` warning을 실제 row 특성으로 고정한다.

해야 할 일:

1. `TREND` slice의 train / validation / test label 분포를 기록한다.
2. 왜 test에서 single-class가 되는지 확인한다.
3. `unsupported slice 유지`, `ambiguous 처리`, `slice 병합` 중 어떤 정책이 가장 좁은지 판단한다.

완료 기준:

- `entry_quality` sparse slice owner와 정책 후보가 문서화된다.

## 5. Step 3. Exit Management Sparse Slice Casebook

목표:

- `exit_management` warning의 실제 owner를 slice별로 분리한다.

해야 할 일:

1. `symbol = NAS100`
2. `symbol = XAUUSD`
3. `setup_id = range_upper_reversal_sell`
4. `regime_holdout = UNKNOWN`

각각에 대해 rows / class_balance / minority_rows / bucket 위치를 기록한다.

완료 기준:

- `symbol/setup/regime` warning이 하나로 뭉개지지 않고 분리된다.

## 6. Step 4. Least-Invasive Policy 선택

목표:

- 가장 보수적이고 설명 가능한 정책을 먼저 고른다.

우선순위:

1. `unsupported_sparse_slice` 표면화
2. evaluation-only suppression
3. target-side ambiguous 전환
4. slice aggregation

완료 기준:

- 어떤 policy를 이번 라운드에 구현할지 하나로 좁힌다.

## 7. Step 5. Dataset / Split / Evaluate 구현

목표:

- 선택한 sparse slice policy를 코드에 반영한다.

가능한 구현 포인트:

- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
  - sparse slice health classification
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
  - preview surface / warning taxonomy
- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
  - target-side ambiguous 처리 필요 시

완료 기준:

- 정책이 테스트와 audit에 모두 반영된다.

## 8. Step 6. 테스트

최소 테스트:

- [test_semantic_v1_dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_splits.py)
- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)
- 관련 preview / audit 테스트

완료 기준:

- sparse slice policy가 회귀 없이 고정된다.

## 9. Step 7. 재생성 / 재학습 / 재감사

목표:

- 변경 후 warning이 어떻게 바뀌는지 다시 본다.

해야 할 일:

1. dataset rebuild
2. timing / entry_quality / exit_management 재학습
3. preview audit 재생성

완료 기준:

- warning이 줄었는지, 혹은 그대로여도 더 설명 가능해졌는지 확인된다.

## 10. Step 8. 문서 동기화

목표:

- post-Step7 follow-up 상태를 이후에 안 헷갈리게 맞춘다.

동기화 문서:

- [refinement_r3_post_step7_split_warning_followup_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_split_warning_followup_memo_ko.md)
- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)

## 11. Done Definition

- sparse slice warning의 owner가 `구조`가 아니라 `데이터 희소성`임을 코드와 문서로 설명 가능하다.
- 필요한 경우 warning이 줄고, 줄지 않더라도 `unsupported_sparse_slice` 같은 더 정확한 이름으로 surface 된다.
- 다음 `promotion / bounded live` 논의에서 warning 해석이 흔들리지 않는다.
