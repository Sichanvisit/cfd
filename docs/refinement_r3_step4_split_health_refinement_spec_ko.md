# R3 Step 4 Split Health Refinement Spec

## 1. 목적

이 문서는 `R3. Semantic ML Step 3~7 refinement` 중
`Step 4. split health refinement` 전용 spec이다.

Step 3에서 `timing_now_vs_wait` target을 다시 고정했고
preview / evaluate 재확인까지 끝냈으므로,
다음 단계에서는 train / validation / test / holdout 구성이
실제로 믿을 수 있는 분리인지 문서와 코드 기준으로 함께 고정해야 한다.

이 단계의 목적은:

- split이 단순히 "나뉘어 있다"가 아니라
- promotion gate에 써도 되는 품질인지
- failure / warning / pass를 어떤 기준으로 판단할지

를 설명 가능한 상태로 만드는 것이다.

## 2. 이 문서의 역할

이 문서는 아래를 고정한다.

- Step 4의 범위와 비범위
- split health를 보는 관측 축
- 어떤 owner가 무엇을 책임지는지
- 어떤 경우를 failure로 보고 어떤 경우를 warning으로 볼지
- 구현 전에 필요한 산출물과 완료 기준

이 문서는 구현 checklist가 아니라
Step 4 구현을 위한 상위 기준 문서다.

## 3. 기준 문서

Step 4는 아래 문서를 source set으로 읽는다.

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md)
- [refinement_r3_step3_timing_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_refinement_spec_ko.md)
- [refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md)
- [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)
- [semantic_ml_v1_promotion_gates_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_promotion_gates_ko.md)

## 4. 현재 위치

현재 기준선은 아래와 같다.

- R2 `storage / export / replay integrity`: 완료
- R3 Step 3 `timing target refinement`: 1차 완료
- Step 3 preview / evaluate 재확인: 완료
- timing preview AUC: `0.610649 -> 0.633218`
- 현재 다음 active step: `Step 4 split health refinement`

즉 지금 Step 4는
target 정의 자체를 다시 바꾸는 단계가 아니라,
이미 손본 target을 어떤 split에서 어떻게 믿을지 정리하는 단계다.

## 5. 포함 범위

### 포함

- time split health
- symbol holdout health
- regime holdout health
- minority class / positive-negative balance health
- join health와 split health의 연결 해석
- split 기준 경고 / 실패 / 통과 규칙
- split health report와 preview / audit report 연결

### 제외

- `timing_now_vs_wait` target 자체 재정의
- `entry_quality` target 정의 변경
- legacy feature tier policy 변경
- chart / Stage E calibration 재조정
- promotion gate 수치 자체를 여기서 곧바로 확장 결정

## 6. owner

Step 4의 직접 owner는 아래 파일들이다.

- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)

간접 owner / 연계:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- [promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\promotion_guard.py)

owner 원칙:

- split health는 target owner를 침범하지 않는다.
- split health는 "이 target을 어떤 분리에서 어떻게 평가해야 하는가"만 책임진다.
- promotion 여부는 Step 4가 직접 결정하지 않고,
  Step 4는 promotion gate가 읽을 수 있는 split health 근거를 만든다.

## 7. split health 관측 축

Step 4에서는 최소 아래 축을 본다.

### 7-1. Time Window Health

- train / validation / test가 시간상 지나치게 겹치지 않는가
- latest regime가 특정 split에만 몰리지 않는가
- evaluation이 stale window에 과도하게 의존하지 않는가

### 7-2. Symbol Coverage Health

- `BTCUSD`, `NAS100`, `XAUUSD`가 split별로 지나치게 한쪽에 몰리지 않는가
- 특정 symbol이 validation / test / holdout에서 너무 적지 않은가
- symbol holdout이 "형식적 존재" 수준으로 축소되지 않았는가

### 7-3. Regime Coverage Health

- range / trend / mixed / expanding / contracting 같은 주요 regime가
  split별로 완전히 깨지지 않았는가
- regime holdout이 설명 가능한 수준인지
- 특정 regime이 전부 train에만 남는지

### 7-4. Label Balance Health

- positive / negative / ambiguous / censored row가 split별로 너무 왜곡되지 않는가
- minority label이 validation / test에서 0 또는 거의 0에 가깝지 않은가
- class imbalance가 preview 해석을 왜곡할 정도인지

### 7-5. Join + Split Combined Health

- join health가 정상이라도 split health가 망가지면 evaluate 해석이 흔들린다
- split health는 반드시 R2 join health와 같이 읽는다
- "joined_rows는 충분한데 특정 split minority가 사라지는" 상황을 따로 surface한다

## 8. 판단 규칙

### failure

아래는 failure 후보다.

- validation 또는 test에서 핵심 label minority가 사실상 0
- symbol holdout이 promotion gate 근거로 쓸 수 없을 정도로 너무 희소
- regime holdout이 특정 regime를 사실상 잃어버림
- split leakage 의심이 설명되지 않음

### warning

아래는 warning 후보다.

- minority count가 너무 낮지만 아직 완전 0은 아님
- 특정 symbol coverage가 약함
- latest regime coverage가 한 split으로 치우침
- preview metric이 유지되더라도 split 해석상 신뢰도가 낮음

### pass

아래 조건을 만족하면 pass다.

- split별 label / symbol / regime coverage가 설명 가능
- leakage 의심이 없음
- join health와 합쳐 읽어도 구조적 결함이 없음
- preview / audit 결과를 split health 관점에서 해석할 수 있음

## 9. 산출물

Step 4에서 최소 아래 산출물을 만든다.

- split health spec
- split health implementation checklist
- split health casebook / audit memo
- split health report 또는 report snapshot
- preview / evaluate 해석 메모

## 10. 구현 순서

권장 순서는 아래와 같다.

1. 현재 split baseline snapshot 고정
2. split health 축별 casebook 작성
3. [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py) refinement
4. [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py) report / surface refinement
5. 테스트 보강
6. preview / audit 재확인
7. 문서 동기화

## 11. 완료 기준

아래를 만족하면 Step 4를 닫을 수 있다.

- split health를 문장과 수치로 설명 가능하다.
- validation / test / holdout 품질 문제를 warning/failure로 분리해 말할 수 있다.
- join health와 split health를 함께 읽는 기준이 고정된다.
- preview / audit 결과를 split 품질 관점에서 다시 해석할 수 있다.
- Step 5 `entry_quality target refinement`로 넘어갈 준비가 된다.

## 12. 다음 단계

이 spec 다음에는
[refinement_r3_step4_split_health_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_refinement_implementation_checklist_ko.md)
를 기준으로 실제 구현에 들어간다.
