# R3 Step 7 Preview Audit Refinement Memo

## 1. 이번 변경의 목적

Step 7의 목적은 preview audit을 단순 metric dump가 아니라,

- join coverage
- split health
- feature tier
- shadow compare
- promotion gate

를 한 번에 설명하는 gate 문서로 만드는 것이었다.

## 2. 실제 코드 변경

### [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)

이번 변경에서 아래를 추가했다.

- `semantic_preview_audit_v2`
- per-target `feature_tier` compact summary
- optional `--shadow-compare-path`
- analysis dir 내 latest `semantic_shadow_compare_report_*.json` 자동 탐색
- `shadow_compare` 섹션 추가
- promotion gate에 `shadow_compare_status`, `shadow_compare_report_path` 추가
- markdown report에 feature tier / shadow compare 섹션 추가

핵심 해석 규칙은 아래와 같다.

- shadow compare report가 없으면 `shadow_compare_report_missing` blocker
- shadow compare report는 있지만 row/threshold candidate가 약하면 warning
- promotion script가 읽는 `shadow_compare_ready`는 그대로 유지하되,
  이제는 왜 ready / blocked 인지 더 직접 설명한다.

### [promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\scripts\promote_semantic_preview_to_shadow.py)

promotion manifest에도 아래를 같이 싣게 했다.

- `shadow_compare_status`
- `shadow_compare_report_path`

즉 승격 manifest만 봐도 preview audit이 어떤 shadow compare 상태를 봤는지 추적 가능해졌다.

## 3. 테스트 고정

새 테스트:

- [test_run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_run_semantic_v1_preview_audit.py)

이번 테스트는 두 가지를 잠근다.

1. shadow compare가 있으면
   - feature tier summary가 audit에 붙는다
   - shadow compare summary가 audit에 붙는다
   - promotion gate가 `shadow_compare_status`를 surface 한다

2. shadow compare가 없으면
   - `shadow_compare_report_missing` blocker가 생긴다
   - `shadow_compare_ready = false`가 된다

호환성 회귀도 같이 확인했다.

- [test_semantic_v1_shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_shadow_compare.py)
- [test_promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_promote_semantic_preview_to_shadow.py)

## 4. 검증 결과

실행한 테스트:

- `pytest tests/unit/test_run_semantic_v1_preview_audit.py tests/unit/test_semantic_v1_shadow_compare.py tests/unit/test_promote_semantic_preview_to_shadow.py`
  - `5 passed`
- `pytest tests/unit/test_semantic_v1_dataset_builder.py tests/unit/test_semantic_v1_dataset_splits.py tests/unit/test_semantic_v1_training.py tests/unit/test_semantic_v1_promotion_guard.py tests/unit/test_semantic_v1_runtime_adapter.py tests/unit/test_check_semantic_canary_rollout.py`
  - `28 passed`

즉 Step 7 변경은 preview audit / shadow compare / promotion compatibility를 깨지 않았다.

## 5. 이번 단계의 의미

Step 7 이후에는

- preview audit 한 장으로 gate 설명력이 올라갔고
- feature tier와 shadow compare가 더 이상 별도 추적 항목이 아니게 되었으며
- promotion-ready 해석이 더 직접적이 되었다.

다만 이것이 곧바로 "shadow compare 품질이 충분히 좋다"는 뜻은 아니다.
그 평가는 실제 shadow compare 재확인 memo에서 따로 본다.
