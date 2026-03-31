# R3 Step 7 Preview / Audit Refinement Spec

## 1. 목적

이 문서는 `R3. Semantic ML Step 3~7 refinement` 중 `Step 7. preview / audit refinement` 전용 spec이다.

Step 3~6에서 아래를 정리했다.

- `timing` target fold
- `split_health` payload
- `entry_quality` ambiguity contract
- `legacy / mixed / modern` feature tier policy

이제 Step 7에서는 위 결과가 실제 preview / audit 산출물에서 한 번에 읽히게 만드는 것이 목표다.

즉:

- preview audit 한 장에서
  - join coverage
  - split health
  - feature tier
  - shadow compare
  - promotion-ready 판단
  를 같이 설명할 수 있어야 한다.

## 2. 이 문서가 하는 일

이 문서는 아래를 고정한다.

- Step 7의 포함 범위와 제외 범위
- preview audit이 반드시 surface 해야 하는 정보
- shadow compare와 preview audit의 연결 방식
- promotion gate summary가 무엇을 blocker / warning 으로 볼지
- 구현 산출물과 완료 기준

## 3. 기준 문서

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_step4_split_health_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_reconfirm_memo_ko.md)
- [refinement_r3_step5_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step5_preview_evaluate_reconfirm_memo_ko.md)
- [refinement_r3_step6_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step6_preview_evaluate_reconfirm_memo_ko.md)
- [semantic_ml_v1_promotion_gates_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_promotion_gates_ko.md)

## 4. 현재 위치

현재 baseline은 아래와 같다.

- preview audit은 `join coverage + per-target metrics + promotion gate` 중심이다.
- shadow compare report는 별도 파일로 존재하고, preview audit 안에는 직접 합쳐져 있지 않다.
- feature tier summary는 `metrics.json` 안에는 있으나, preview audit markdown/json에서 한 눈에 읽기 어렵다.
- promotion script는 `semantic_preview_audit_latest.json`의 `promotion_gate.shadow_compare_ready`만 본다.

즉 지금 문제는:

- 정보가 없어서가 아니라
- 정보가 여러 파일에 흩어져 있어
- "왜 지금 pass / warning / blocked 인가"를 한 번에 읽기 어렵다는 점이다.

현재 상태 메모:

- Step 7 1차 구현과 재확인은 완료
- 구현 메모: [refinement_r3_step7_preview_audit_refinement_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step7_preview_audit_refinement_memo_ko.md)
- 재확인 메모: [refinement_r3_step7_preview_shadow_compare_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step7_preview_shadow_compare_reconfirm_memo_ko.md)

## 5. 포함 범위

### 포함

- preview audit에 `feature_tier` 요약 반영
- preview audit에 `shadow_compare` 요약 반영
- promotion gate summary에 `shadow_compare` 기반 blocker / warning 반영
- preview audit markdown 가독성 개선
- Step 7 회귀 테스트 추가
- explicit preview + shadow compare 재확인

### 제외

- target fold 자체 변경
- split cutoff 자체 변경
- promotion threshold 수치 정책 재설계
- live rollout mode 변경
- runtime adapter / entry owner 변경

## 6. 직접 owner

- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)

간접 owner:

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- [promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\scripts\promote_semantic_preview_to_shadow.py)

## 7. 해석 원칙

### 7-1. preview audit은 "요약 집계"가 아니라 "설명 가능한 gate 문서"여야 한다

Step 7의 preview audit은 단순 metric dump가 아니라:

- 왜 join은 괜찮은지
- 왜 split은 healthy / warning 인지
- feature tier가 어떤 generation에서 어떻게 동작했는지
- shadow compare가 실제로 있었는지
- 그래서 promotion-ready가 왜 pass / warning / blocked 인지

를 같이 말해줘야 한다.

### 7-2. feature tier 정보는 per-target 단위로 surface 한다

각 target마다 아래가 바로 보여야 한다.

- `dataset_source_generation`
- `dataset_feature_tier_policy`
- `dataset_feature_tier_summary`
- `dataset_observed_only_dropped_feature_columns`

단, preview audit에는 full payload를 그대로 덤프하지 않고
읽기 좋은 compact summary와 dropped count / sample 위주로 surface 한다.

### 7-3. shadow compare는 "있으면 참고"가 아니라 "Gate C 근거"다

따라서 preview audit은 shadow compare report를 optional note로만 두지 않고,
현재 audit readiness의 일부로 요약해야 한다.

권장 계약:

- report가 없으면 `shadow_compare_report_missing` blocker
- report는 있는데 row가 적거나 candidate table이 비면 warning
- compare label / precision / false positive rate는 summary로 함께 노출

### 7-4. promotion script를 깨지 않게 compatibility를 유지한다

`promote_semantic_preview_to_shadow.py`는 여전히
`promotion_gate.shadow_compare_ready`를 읽는다.

Step 7에서 바꾸는 것은:

- 그 bool이 무엇을 뜻하는지 더 정확히 만들고
- 추가 summary field를 넣어 manifest 설명력을 높이는 것

이지, promotion script 인터페이스를 깨는 것은 아니다.

## 8. Step 7에서 반드시 surface 할 축

### 8-1. Join Coverage

- joined rows
- feature joinable rows
- replay joinable rows
- coverage ratio

### 8-2. Split Health

- `overall_status`
- `bucket_coverage`
- `holdout_health`
- target별 warning / fail 여부

### 8-3. Feature Tier

- source generation
- tier policy
- tier summary
- observed-only dropped feature count / sample

### 8-4. Shadow Compare

- report path
- report status
- summary
- compare label counts
- trace quality counts
- top threshold candidate

### 8-5. Promotion Gate

- blocker list
- warning list
- `shadow_compare_ready`
- `status`

## 9. 권장 gate 방향

### blocker

- join coverage fail
- forbidden feature leakage
- split health fail
- required shadow compare report missing
- target AUC가 random 이하

### warning

- split health warning
- shadow compare report는 있으나 row가 적음
- shadow compare candidate threshold table 비어 있음
- feature tier에서 observed-only drop이 과도함

## 10. 산출물

Step 7에서 최소 아래 산출물을 만든다.

- Step 7 spec
- Step 7 implementation checklist
- preview audit refinement memo
- preview / shadow compare reconfirm memo

## 11. 구현 순서

1. Step 7 spec / checklist 고정
2. preview audit baseline snapshot 확인
3. audit script에 feature tier summary 추가
4. audit script에 shadow compare summary 추가
5. promotion gate summary 연결 정리
6. 테스트 추가
7. preview audit + shadow compare 재실행
8. 문서 동기화

## 12. 완료 기준

아래를 만족하면 Step 7을 닫는다.

- preview audit 한 파일만 봐도 `join / split / feature tier / shadow compare / promotion`를 함께 설명할 수 있다.
- shadow compare가 없으면 이유가 blocker로 드러난다.
- shadow compare가 있으면 summary가 audit 안에 같이 남는다.
- feature tier summary가 target별로 읽힌다.
- promotion script compatibility가 유지된다.
- Step 7 결과를 문서와 테스트로 설명할 수 있다.

## 13. 다음 단계

Step 7이 끝나면 R3의 preview / audit 쪽은 일단 닫고,
다음은 promotion gate 운영 검토 또는 R4 acceptance / bounded live readiness 쪽으로 넘어간다.
