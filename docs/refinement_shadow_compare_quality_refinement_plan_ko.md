# Shadow Compare Quality Refinement Plan

## 1. 목적

이 문서는 `preview / audit 연결` 이후 남은 실제 후속 과제인
`shadow compare 품질 개선` 전용 상세 계획서다.

지금 상태에서 문제는

- shadow compare report가 생성되지 않는 것이 아니라
- 생성은 되지만 scorable quality가 낮아서
- promotion / rollout 판단 근거로 쓰기엔 아직 약하다는 점이다.

즉 이 문서의 목적은

- 현재 shadow compare가 왜 약한지
- 어느 owner를 먼저 봐야 하는지
- 어떤 순서로 정제해야 하는지

를 코드와 산출물 기준으로 고정하는 것이다.

## 2. 현재 상태

현재 기준 산출물:

- preview audit latest
  - [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- shadow compare latest
  - [semantic_shadow_compare_report_20260326_165911.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_165911.json)

현재 읽히는 핵심 상태:

- `promotion_gate.status = pass`
- `promotion_gate.shadow_compare_ready = true`
- `promotion_gate.shadow_compare_status = warning`
- warning 사유:
  - `shadow_compare:shadow_compare_scorable_rows_below_gate`

shadow compare report 기준 핵심 수치:

- `rows_total = 21898`
- `shadow_available_rows = 21898`
- `baseline_entered_rows = 46`
- `semantic_enter_rows = 21898`
- `scorable_shadow_rows = 0`
- `trace_quality_counts = fallback_heavy only`
- `compare_label_counts = semantic_earlier_enter overwhelmingly dominant`

해석:

- plumbing은 연결됐다
- report도 잘 나온다
- 하지만 compare의 질이 낮아서 실제 판단 근거는 약하다

## 3. 왜 지금 별도 트랙으로 빼야 하나

이 문제는 이미 Step 7에서 해결한 문제와 다르다.

Step 7이 해결한 것:

- preview audit 한 장에서
  - join coverage
  - split health
  - feature tier
  - shadow compare
  - promotion gate
  를 함께 읽게 만든 것

지금 남은 것:

- shadow compare가 실제로 비교 가능한 row를 충분히 갖고 있는가
- fallback-heavy가 왜 과도한가
- semantic enter가 왜 거의 전부 earlier-enter로만 찍히는가

즉 다음 작업은 UI/문서 문제가 아니라
`compare quality`와 `label / runtime alignment quality` 문제다.

## 4. 직접 owner

### 1차 owner

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)

### 2차 owner

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py)
- [runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\runtime_adapter.py)

### 간접 owner

- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)
- [promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\scripts\promote_semantic_preview_to_shadow.py)

## 5. 현재 의심되는 핵심 원인

### 가설 A. replay label과 shadow compare join은 되지만 실제 scorable label이 거의 없다

증상:

- `scorable_shadow_rows = 0`
- precision / false positive rate가 전부 `null`

의미:

- join key는 이어졌더라도
- `actual_positive`를 만들 수 있는 replay row가 거의 없거나
- label status가 `VALID`가 아니거나
- ambiguous / censored 비중이 너무 높다는 뜻일 수 있다

### 가설 B. semantic shadow prediction이 너무 쉽게 enter로 기울어 있다

증상:

- `semantic_enter_rows = 21898`
- `semantic_earlier_enter = 21852`

의미:

- threshold 해석이 너무 공격적이거나
- unavailable / fallback-heavy row도 사실상 enter처럼 읽히고 있거나
- `should_enter` contract가 너무 느슨할 수 있다

### 가설 C. trace quality가 사실상 전부 fallback-heavy로 떨어진다

증상:

- `trace_quality_counts = fallback_heavy only`

의미:

- runtime feature row가 shadow compare input으로 들어갈 때
  trace quality 관련 scalar가 비어 있거나
- feature tier와 runtime shadow input contract가 안 맞을 수 있다

### 가설 D. baseline action과 semantic action의 비교 단위가 너무 넓다

증상:

- baseline entered는 46건인데 semantic enter는 전 row

의미:

- compare window 자체가 너무 넓거나
- baseline non-entry row가 과도하게 포함되고 있을 수 있다

## 6. 이번 트랙에서 봐야 할 관측 축

### 6-1. Label Quality

- `transition_label_status`
- `label_is_ambiguous`
- `is_censored`
- `label_source_descriptor`
- `actual_positive` 생성 가능 row 수

### 6-2. Compare Quality

- `semantic_enter_rows / baseline_entered_rows`
- `semantic_earlier_enter_rows`
- `semantic_later_block_rows`
- `scorable_shadow_rows`
- precision
- false positive rate

### 6-3. Trace Quality

- `semantic_shadow_trace_quality`
- `fallback_heavy`
- `clean`
- `degraded`

### 6-4. Join / Coverage

- replay row 존재 여부
- `decision_row_key / replay_row_key` coverage
- symbol / regime / setup slice별 compare 가능 row 수

## 7. 권장 실행 순서

### Phase S0. Baseline Snapshot

목표:

- 지금 shadow compare가 왜 warning인지 숫자와 샘플로 고정한다

해야 할 일:

- latest report snapshot memo
- symbol / regime / setup별 top issue 정리
- fallback-heavy dominant 원인 분리

완료 기준:

- "현재 무엇이 문제인지"가 문장과 수치로 고정된다

### Phase S1. Scorable Row Audit

목표:

- `scorable_shadow_rows = 0`의 직접 원인을 찾는다

해야 할 일:

- replay label frame에서 `actual_positive`가 `None`이 되는 대표 사유 분류
- `VALID` / ambiguous / censored 비율 확인
- join 이후 drop되는 row 분해

완료 기준:

- scorable row가 왜 0인지 reason taxonomy가 나온다

### Phase S2. Trace Quality Audit

목표:

- 왜 전부 `fallback_heavy`로 읽히는지 찾는다

해야 할 일:

- runtime shadow row에 들어가는 trace quality source 확인
- runtime adapter와 compare input 간 contract 점검
- clean / degraded / fallback_heavy 분포가 정상인지 확인

완료 기준:

- fallback-heavy only가 정상인지, 버그인지, conservative policy인지 구분 가능하다

### Phase S3. Compare Policy Refinement

목표:

- semantic enter가 과도하게 넓게 잡히는 경우를 줄인다

해야 할 일:

- shadow compare의 enter 판단 기준 재점검
- unavailable / fallback-heavy / low-confidence row를 compare candidate에서 더 보수적으로 제외할지 검토
- threshold candidate table 해석 보강

완료 기준:

- `semantic_earlier_enter` 과대 현상이 완화되거나, 최소한 원인이 설명된다

### Phase S4. Promotion Gate Rebind

목표:

- shadow compare quality 개선 결과를 promotion gate 해석에 반영한다

해야 할 일:

- warning / blocker 기준 재확인
- `shadow_compare_ready`가 너무 느슨하거나 너무 빡빡하지 않은지 확인

완료 기준:

- promotion gate가 shadow compare 품질을 더 정확히 반영한다

## 8. 이번 트랙에서 하지 않을 것

- timing / entry_quality / exit_management target 재정의
- split health 수치 재조정
- chart signal / execution owner 변경
- bounded live rollout 자체 시작

## 9. 완료 기준

아래를 만족하면 이 트랙을 닫는다.

- shadow compare warning 원인이 taxonomy로 정리된다
- `scorable_shadow_rows`가 왜 0인지 명확히 설명 가능하다
- fallback-heavy only 상태가 원인과 함께 설명되거나 개선된다
- `semantic_earlier_enter` 과대 현상이 완화되거나 계약상 설명된다
- promotion gate가 shadow compare 품질을 더 신뢰 가능하게 읽는다

## 10. 다음 액션

가장 먼저 할 일은 `Phase S0 baseline snapshot + Phase S1 scorable row audit`이다.

즉 다음 실무 단계는:

1. latest shadow compare snapshot memo
2. scorable row casebook
3. trace quality casebook

순으로 가는 것이 가장 안전하다.
