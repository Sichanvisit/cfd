# R3 Post-Step7 Slice Sparsity Refinement Spec

## 1. 목적

이 문서는 R3 Step 7 이후에도 남아 있는

- `entry_quality:split_health_warning`
- `exit_management:split_health_warning`

을 `split plumbing` 문제가 아니라 `slice sparsity` 문제로 분리해서 다루기 위한 전용 spec이다.

이번 단계의 목표는 warning을 억지로 숨기는 것이 아니라,

- 어떤 warning은 이미 구조 수리로 줄었는지
- 어떤 warning은 실제 label density 부족인지
- 어디까지를 `정상적인 희소성`, 어디부터를 `정책 보강 필요`로 볼지

를 owner 기준으로 고정하는 것이다.

## 2. 현재 기준선

이번 spec의 baseline은 아래 산출물을 따른다.

- latest preview audit: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- holdout follow-up memo: [refinement_r3_post_step7_split_warning_followup_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_post_step7_split_warning_followup_memo_ko.md)
- holdout refresh build manifest: [semantic_v1_dataset_build_20260326_204936_402557.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_build_20260326_204936_402557.json)
- holdout refresh metrics: [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_holdout_20260326\metrics.json)

현재 해석은 이렇다.

### timing

- split health `healthy`
- 후속 대상 아님

### entry_quality

- holdout health는 정리됨
- 남은 warning은 `preflight_regime:TREND` test slice single-class
- 즉 owner는 `holdout bucket`이 아니라 `target / slice policy`

### exit_management

- symbol holdout health는 정리됨
- regime holdout은 `UNKNOWN` minority 부족으로 warning
- 추가로
  - `symbol = NAS100` test slice single-class
  - `symbol = XAUUSD` minority 1
  - `setup_id = range_upper_reversal_sell` minority 1
- 즉 owner는 `slice label density / aggregation policy`

## 3. 이번 단계에서 해결하려는 것

1. `entry_quality`와 `exit_management` warning을 같은 문제로 보지 않고 분리한다.
2. 실제 문제 slice를 casebook으로 고정한다.
3. `drop / ambiguous / aggregate / unsupported slice warning 유지` 중 어떤 정책이 가장 좁고 안전한지 결정한다.
4. preview audit의 warning이 진짜 데이터 문제인지, 정책 부재 문제인지 구분 가능하게 만든다.

## 4. 이번 단계에서 일부러 하지 않을 것

- `timing` target 재정의
- `promotion_gate` threshold 변경
- bounded live rollout 확장
- chart / Stage E 미세조정 재진입
- shadow compare source/provenance 재수정

즉 이번 단계는 오직 `slice sparsity policy`만 다룬다.

## 5. 직접 owner

### 1차 owner

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)

### 간접 owner

- [train_entry_quality.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_entry_quality.py)
- [train_exit_management.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_exit_management.py)
- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)

## 6. 증상 분리 기준

### A. 구조 문제가 이미 해결된 항목

- `empty_holdout_bucket`
- `all-train holdout bucket`
- replay/source alignment mismatch
- runtime provenance mismatch

이 항목들은 이번 단계의 주 대상이 아니다.

### B. 현재 남은 실제 경고

#### entry_quality

- `preflight_regime = TREND`
- test slice rows는 있으나 label이 `0 only`

#### exit_management

- `symbol = NAS100`
- `symbol = XAUUSD`
- `setup_id = range_upper_reversal_sell`
- `regime_holdout = UNKNOWN`

위 항목은 row가 아주 없거나, minority가 1~2 수준이라 평가가 과도하게 불안정하다.

## 7. 정책 옵션

이번 단계에서 비교할 정책 옵션은 아래 순서로 좁힌다.

### Option 1. unsupported slice 유지 + 설명력 강화

- slice는 그대로 둔다
- preview audit에 `unsupported_sparse_slice`로 더 명확히 남긴다
- 가장 보수적

### Option 2. evaluation-only slice suppression

- 학습 dataset은 유지
- 특정 sparse slice는 split health warning 계산에서 `지원 불가 slice`로 별도 분류
- 수치 왜곡은 줄지만, 평가 정책이 복잡해진다

### Option 3. target-side ambiguous / censored 전환

- 극단적으로 sparse한 positive/negative만 `ambiguous`로 돌린다
- dataset 분포를 바꾸므로 owner 판단이 중요하다

### Option 4. slice aggregation

- `UNKNOWN + SHOCK`
- setup 희소 그룹 병합
- 해석력이 떨어질 수 있으므로 마지막 선택지다

기본 원칙은 `Option 1 -> Option 2 -> Option 3 -> Option 4` 순서다.

## 8. 권장 구현 순서

1. baseline snapshot 고정
2. `entry_quality` sparse slice casebook
3. `exit_management` sparse slice casebook
4. least-invasive policy 선택
5. dataset/split/evaluate 구현
6. 재학습 + preview audit 재확인

## 9. 완료 기준

- `entry_quality`와 `exit_management`의 남은 warning이 왜 남는지 row/slice 기준으로 설명 가능하다.
- 구조 문제와 데이터 희소성 문제가 문서와 코드에서 분리된다.
- preview audit의 warning이 `버그`인지 `지원 불가 slice`인지 구분 가능하다.
- 다음 단계에서 `promotion gate` 논의를 할 때 warning의 성격을 혼동하지 않는다.
