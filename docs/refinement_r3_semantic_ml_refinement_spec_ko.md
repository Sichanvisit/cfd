# R3 Semantic ML Step 3~7 Refinement Spec

## 1. 목적

이 문서는 refinement track의 `R3. Semantic ML Step 3~7 refinement` 전용 spec이다.

R2에서 `runtime row -> export -> replay -> semantic dataset` 정합성을 닫았으므로,
R3에서는 이제 semantic ML v1을

- `구조가 있음`
- `dataset이 만들어짐`
- `preview와 split 숫자를 해석할 수 있음`

수준에서

- `target 정의를 신뢰할 수 있음`
- `split health를 설명할 수 있음`
- `preview / shadow / gate 판단의 근거로 쓸 수 있음`

수준으로 올리는 것을 목표로 한다.


## 2. 이 문서의 역할

이 문서는 아래를 고정한다.

- R3의 범위와 제외 범위
- Step 3~7의 owner와 순서
- 각 step이 무엇을 산출해야 하는지
- 어떤 변경은 R3에서 허용되고 어떤 변경은 허용되지 않는지

이 문서는 세부 구현 checklist가 아니라,
R3 전체를 어떤 틀로 진행할지 정하는 `상위 설계 문서`다.


## 3. 기준 문서

R3는 아래 문서를 source set으로 삼는다.

- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)
- [semantic_ml_structure_change_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_structure_change_plan_ko.md)
- [semantic_ml_v1_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_execution_plan_ko.md)
- [semantic_ml_v1_promotion_gates_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_promotion_gates_ko.md)
- [storage_semantic_flow_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\storage_semantic_flow_handoff_ko.md)


## 4. 현재 위치

현재 기준선은 아래와 같다.

- Step 1 구조 감사: 완료
- Step 2 key 전략 정리: 완료
- R2 storage / export / replay 정합성: 완료
- 다음 착수점: `Step 3. timing target refinement`

현재 semantic ML 계층 검증 기준은 아래다.

- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md) 기준 semantic ML 테스트 묶음 `26 passed`

즉 지금은 promotion을 더 넓히는 단계가 아니라,
`target 계약`과 `split 기준`을 다시 잠그는 단계다.


## 5. 범위

### 포함 범위

- `timing_now_vs_wait` target 정의 refinement
- split health 기준 refinement
- `entry_quality` target 정의 refinement
- legacy / mixed / modern source tier policy refinement
- preview / evaluate / shadow compare 기준 재정렬

### 제외 범위

- rule engine이 owner인 `side / setup / invalidation / management_profile` 의미 변경
- chart flow policy / Stage E 추가 미세조정
- promotion gate 숫자 자체의 live 확대 결정
- bounded live rollout 활성화


## 6. Owner 원칙

R3의 핵심 원칙은 아래와 같다.

### rule owner로 남길 것

- 방향 결정
- setup 의미
- invalidation 의미
- execution owner

즉 semantic ML은 의미 creator가 아니라,
`timing`, `entry_quality`, `exit_management`, `preview calibration`의 보정층으로만 다룬다.

### R3의 직접 owner

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- 필요 시 train scripts
  - [train_timing.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_timing.py)
  - [train_entry_quality.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_entry_quality.py)
  - [train_exit_management.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_exit_management.py)


## 7. 진행 방식

R3는 `한 번에 세부 구현 전부 확정` 방식으로 가지 않는다.

권장 방식은 아래와 같다.

1. `R3 전체 spec`과 `전체 checklist`를 먼저 고정한다.
2. 실제 구현은 `현재 active step`만 전용 spec / checklist로 더 세분화한다.
3. 한 step이 끝나면 다음 step을 세분화한다.

이 방식이 필요한 이유는,
Step 3 결과가 Step 4의 split health 기준에 영향을 주고,
Step 4 결과가 Step 5와 Step 7 preview 해석을 다시 바꾸기 때문이다.


## 8. 세부 단계

### Step 3. Timing Target Refinement

#### 목표

`timing_now_vs_wait` target이 실제 의미와 같은 방향으로 접히는지 다시 고정한다.

#### 핵심 질문

- 지금 진입이 유리한가
- 1~2 bar 기다리는 것이 유리한가
- fallback-heavy row를 timing positive로 볼 수 있는가
- ambiguous / censored row는 positive/negative가 아니라 제외해야 하는가

#### 주 owner

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

#### 완료 기준

- timing target 정의를 사람이 row 단위로 설명 가능하다.
- preview가 최소 무작위보다 의미 있게 동작한다.


### Step 4. Split Health Refinement

#### 목표

train / validation / test / holdout 건강도를 문서와 코드 기준으로 같이 고정한다.

#### 핵심 질문

- time split이 왜곡되지 않았는가
- symbol holdout이 너무 빈약하지 않은가
- regime holdout이 promotion block을 설명 가능한가
- validation / test minority row health를 failure로 볼 것인가 warning으로 볼 것인가

#### 주 owner

- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)

#### 완료 기준

- split 건강도 기준이 문서와 코드에 같이 반영된다.
- validation/test 단일 클래스 문제를 조기 경고하거나 실패로 surface할 수 있다.


### Step 5. Entry Quality Target Refinement

#### 목표

`entry_quality`가 실제 “좋은 진입”을 설명하도록 target 정의를 다시 고정한다.

#### 핵심 질문

- 좋은 진입은 단순 수익이 아닌가
- timing과 entry_quality는 무엇이 다른가
- hold가 더 좋았던 진입은 positive인가 ambiguous인가
- leakage 없이 이 정의를 preview까지 가져갈 수 있는가

#### 주 owner

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

#### 완료 기준

- 사람이 봐도 납득 가능한 positive / negative / ambiguous 기준이 정해진다.
- direct leakage 없이 preview 재학습이 가능하다.


### Step 6. Legacy Feature Tier Refinement

#### 목표

legacy / mixed / modern source tier를 builder와 summary 기준으로 설명 가능하게 만든다.

#### 핵심 질문

- 어떤 feature tier는 `enabled`
- 어떤 tier는 `observed_only`
- all-missing legacy feature를 warning으로 볼지 drop으로 볼지
- mixed source를 legacy로 취급할지 modern으로 취급할지

#### 주 owner

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

#### 완료 기준

- source tier별 허용 범위가 문서와 코드로 고정된다.
- useless missing warning과 silent drop의 경계가 설명 가능하다.


### Step 7. Preview / Audit Refinement

#### 목표

Step 3~6을 반영한 뒤 preview / evaluate / shadow compare를 다시 돌려,
다음 gate로 넘길 수 있는지 판단 근거를 만든다.

#### 핵심 질문

- 세 target preview가 설명 가능한가
- join health / split health / leakage audit가 동시에 해석 가능한가
- shadow compare와 promotion gate 입력으로 넘길 수 있는가

#### 주 owner

- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- train scripts

#### 완료 기준

- preview train / evaluate 결과를 문서와 숫자로 설명할 수 있다.
- join / split / leakage / calibration 재점검 결과가 promotion gate 판단에 연결된다.


## 9. 단계별 우선순위

- `P0`
  - Step 3 timing target refinement
  - Step 4 split health refinement
- `P1`
  - Step 5 entry_quality target refinement
  - Step 6 legacy feature tier refinement
- `P2`
  - Step 7 preview / audit refinement

즉 지금 첫 착수는 `Step 3`이다.


## 10. 단계별 산출물

R3 전체에서 기대하는 산출물은 아래와 같다.

- R3 전체 spec
- R3 전체 implementation checklist
- Step 3 casebook / target memo
- Step 4 split health memo
- Step 5 entry quality target memo
- Step 6 feature tier memo
- Step 7 preview / audit memo
- 관련 테스트 보강


## 11. 완료 기준

R3는 아래 조건을 만족하면 닫을 수 있다.

- `timing / entry_quality / exit_management` target 정의가 문서와 코드로 설명 가능하다.
- split health가 promotion block 사유 없이 해석 가능하다.
- preview / shadow compare 결과를 다음 gate 기준으로 읽을 수 있다.
- R4 acceptance / promotion-ready 정리로 자연스럽게 넘어갈 수 있다.


## 12. 다음 단계

R3 전체 spec과 checklist를 고정한 뒤,
실제 구현은 `Step 3 timing target refinement`부터 시작한다.
