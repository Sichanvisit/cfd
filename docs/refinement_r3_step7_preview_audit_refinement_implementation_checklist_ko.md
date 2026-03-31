# R3 Step 7 Preview / Audit Refinement Implementation Checklist

## 1. 목적

이 문서는 [refinement_r3_step7_preview_audit_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step7_preview_audit_refinement_spec_ko.md) 실행 checklist다.

목표는 preview audit을

- join coverage
- split health
- feature tier
- shadow compare
- promotion gate

를 한 번에 읽을 수 있는 gate 문서로 만들고, 그 연결을 테스트로 잠그는 것이다.

## 2. 이번 단계에서 할 것 / 하지 않을 것

### 할 것

- preview audit baseline snapshot 고정
- feature tier compact summary 추가
- shadow compare compact summary 추가
- promotion gate blocker / warning 연결 정리
- markdown surface 개선
- Step 7 회귀 테스트 추가
- preview + shadow compare 재확인
- 문서 동기화

### 하지 않을 것

- target fold 변경
- split health 수치 정책 변경
- promotion threshold 재설계
- live rollout mode 변경

## 3. 입력 기준

기준 문서:

- [refinement_r3_step7_preview_audit_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step7_preview_audit_refinement_spec_ko.md)
- [refinement_r3_step6_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step6_preview_evaluate_reconfirm_memo_ko.md)
- [semantic_ml_v1_promotion_gates_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_promotion_gates_ko.md)

중요 파일:

- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)
- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- [promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\scripts\promote_semantic_preview_to_shadow.py)

## 4. 현재 상태

현재 audit baseline은:

- join coverage는 잘 보인다
- target metrics와 split health도 보인다
- feature tier는 metrics 내부엔 있으나 audit surface는 약하다
- shadow compare는 별도 report로만 존재한다
- promotion gate는 shadow compare가 실제로 있었는지 충분히 설명하지 못한다

현재 상태 메모:

- Step 7 구현 완료
- 관련 메모:
  - [refinement_r3_step7_preview_audit_refinement_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step7_preview_audit_refinement_memo_ko.md)
  - [refinement_r3_step7_preview_shadow_compare_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step7_preview_shadow_compare_reconfirm_memo_ko.md)

## 5. 구현 순서

### Step 1. Preview Audit Baseline Snapshot 고정

목표:

- 현재 audit JSON / markdown에서 무엇이 보이고 무엇이 안 보이는지 고정한다.

완료 기준:

- Step 7 시작 baseline이 문장으로 정리된다.

### Step 2. Feature Tier Summary Surface 추가

목표:

- per-target feature tier compact summary를 audit payload에 넣는다.

해야 할 일:

- `dataset_source_generation`
- `dataset_feature_tier_policy`
- `dataset_feature_tier_summary`
- `dataset_observed_only_dropped_feature_columns`

를 compact summary로 정리한다.

완료 기준:

- audit JSON과 markdown에서 target별 feature tier가 읽힌다.

### Step 3. Shadow Compare Summary 연결

목표:

- preview audit이 shadow compare report를 읽어 compact summary를 담는다.

해야 할 일:

- optional report path 인자 추가
- latest shadow compare report fallback 탐색
- summary / compare labels / trace quality / top candidate 추출
- missing / warning / healthy 상태 표준화

완료 기준:

- audit JSON 안에 `shadow_compare` 섹션이 생기고, report 부재도 설명 가능하다.

### Step 4. Promotion Gate Summary 정리

목표:

- shadow compare 부재/상태를 blocker / warning에 반영한다.

해야 할 일:

- `shadow_compare_report_missing` blocker
- shadow compare warning issue 전달
- `shadow_compare_ready` compatibility 유지

완료 기준:

- promotion gate가 왜 ready / blocked 인지 더 정확히 설명한다.

### Step 5. Markdown Surface 개선

목표:

- JSON만 보지 않아도 핵심 판단이 읽히게 한다.

해야 할 일:

- feature tier 섹션 추가
- shadow compare 섹션 추가
- promotion gate 섹션 보강

완료 기준:

- markdown report만 봐도 핵심 축이 한눈에 들어온다.

### Step 6. 테스트 추가

최소 대상:

- 새 preview audit test
- shadow compare 연결 회귀
- promotion script compatibility 확인

완료 기준:

- Step 7 계약이 테스트로 고정된다.

### Step 7. Preview / Shadow Compare 재확인

목표:

- explicit preview pair 기준으로 실제 report를 다시 만들고 확인한다.

완료 기준:

- Step 7 결과가 실제 산출물로 남는다.

### Step 8. 문서 동기화

목표:

- Step 7 spec / checklist / 결과 메모를 현재 상태에 맞춘다.

## 6. Done Definition

아래를 만족하면 Step 7을 닫는다.

- preview audit이 feature tier와 shadow compare를 함께 surface 한다.
- missing shadow compare가 blocker로 읽힌다.
- shadow compare가 있으면 warning / healthy 상태가 읽힌다.
- promotion script compatibility가 유지된다.
- 테스트와 실제 report가 함께 남는다.

## 7. 다음 단계

Step 7이 끝나면 R3 preview / audit refinement는 닫고,
promotion gate 운영 검토 또는 다음 refinement/R4 acceptance 단계로 넘어간다.
