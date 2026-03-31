# Bridge-First Refinement Execution Roadmap

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `BF (bridge-first refinement)`를 실제로 실행 가능한 순서로 쪼갠 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [bridge_first_refinement_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_refinement_detailed_reference_ko.md)

## 2. 전체 순서

```text
BF1. act_vs_wait_bias_v1
-> BF2. management_hold_reward_hint_v1
-> BF3. management_fast_cut_risk_v1
-> BF4. trend_continuation_maturity_v1
-> BF5. advanced_input_reliability_v1
-> BF6. detail_to_csv_activation_projection_v1
-> BF7. close-out and handoff
```

현재 BF 트랙은 close-out까지 완료됐고, 다음 handoff는 아래다.

```text
product_acceptance_common_state_aware_display_modifier_v1
```

## 3. BF1. act_vs_wait_bias_v1

### 목표

`WAIT / observe / directional act`를 더 잘 구분하는 공통 bridge를 만든다.

### 구현 순서

#### BF1-A. input contract freeze

해야 할 일:

1. 현재 사용 가능한 입력을 freeze한다.
   - `state`
   - `evidence`
   - `belief`
   - `barrier`
2. raw를 직접 노출하지 말고 bridge 입력 묶음을 고정한다.
3. `consumer_contract` 위반 없이 chart/product 쪽이 읽을 수 있는 표면을 정한다.

주 대상 파일:

- `backend/services/consumer_contract.py`
- `backend/services/context_classifier.py`
- `backend/services/entry_service.py`

완료 기준:

- BF1 입력 표면이 문서/코드에서 흔들리지 않는다.

#### BF1-B. bridge summary shape 정의

해야 할 일:

1. 아래 summary shape를 고정한다.
   - `act_vs_wait_bias`
   - `false_break_risk`
   - `awareness_keep_allowed`
2. metadata에 `why` surface를 남길 수 있게 reason shape를 같이 정한다.

주 대상 파일:

- `backend/trading/engine/core/forecast_features.py`
- `backend/trading/engine/core/models.py`

완료 기준:

- BF1 bridge summary shape가 하나로 잠긴다.

#### BF1-C. forecast feature wiring

해야 할 일:

1. transition forecast가 BF1 bridge를 읽도록 연결한다.
2. usage trace에 BF1 사용 여부가 남게 한다.
3. 기존 branch math와 충돌하지 않게 additive wiring으로 넣는다.

주 대상 파일:

- `backend/trading/engine/core/forecast_features.py`
- `backend/trading/engine/core/forecast_engine.py`

완료 기준:

- transition forecast path에서 BF1 bridge가 실제로 생성/전달된다.

#### BF1-D. product acceptance wiring

해야 할 일:

1. `consumer_check_state`가 BF1 bridge를 awareness/wait 보정에 활용하도록 연결한다.
2. NAS/XAU/BTC acceptance 트랙에서 같은 bridge 언어를 재사용할 수 있게 한다.
3. `display_importance_adjustment_reason`과 분리되는 BF1 reason surface를 남긴다.

주 대상 파일:

- `backend/services/consumer_check_state.py`
- `backend/services/entry_wait_state_bias_policy.py`

완료 기준:

- chart/product acceptance 쪽에서도 BF1 bridge를 실제로 읽는다.

#### BF1-E. audit / report

해야 할 일:

1. BF1 사용 trace와 latest audit 산출물을 만든다.
2. `WAIT vs act` separation이 이전보다 나아졌는지 재확인한다.
3. 필요하면 false-break 관련 slice를 따로 분리한다.

주 대상 파일:

- `scripts/` 아래 BF1 audit report
- `tests/unit/` BF1 contract / audit tests

완료 기준:

- BF1 latest report가 생기고, before/after 판단이 가능하다.

#### BF1-F. close-out

해야 할 일:

1. BF1 결과를 close-out memo로 정리한다.
2. 다음 active step을 `BF6`으로 넘긴다.

완료 기준:

- BF1 close-out memo와 next step 결정이 있다.

## 4. BF2. management_hold_reward_hint_v1

### 목표

hold를 유지해야 할 근거를 trade management forecast에 bridge로 넣는다.

### 순서

1. 입력 contract freeze
2. summary shape 정의
3. management forecast wiring
4. hold/exit acceptance review 연결
5. audit / close-out

## 5. BF3. management_fast_cut_risk_v1

### 목표

빠른 손실/충돌 위험을 bridge로 만들어 cut-now / exit caution 판단을 강화한다.

### 순서

1. event/friction/collision 입력 고정
2. summary shape 정의
3. management forecast wiring
4. exit caution / cut-now review 연결
5. audit / close-out

## 6. BF4. trend_continuation_maturity_v1

### 목표

trend slice에서 왜 hold value가 약한지 보완하는 maturity/exhaustion bridge를 만든다.

### 순서

1. trend slice gap 재확인
2. maturity / exhaustion summary shape 정의
3. management trend path 연결
4. slice value 재감사

## 7. BF5. advanced_input_reliability_v1

### 목표

secondary input을 raw로 과신하지 않도록 collector availability를 reliability summary로 바꾼다.

### 순서

1. tick/event/order_book activation rule 정리
2. reliability shape 정의
3. product display / forecast guard 쪽 연결
4. targeted order_book follow-up 필요 여부 판단

## 8. BF6. detail_to_csv_activation_projection_v1

### 목표

detail usage trace와 CSV value rows를 이어서 review surface를 더 정확히 만든다.

### 순서

1. projection contract 정의
2. detail-to-csv mapping 구현
3. activation/value slice audit 보강
4. SF validation 보조 surface 갱신

## 9. BF7. Close-Out and Handoff

### 목표

BF1~BF6 결과를 공식적으로 닫고, product acceptance와 forecast refinement의 공통 bridge 체계를 handoff한다.

### 해야 할 일

1. BF 전체 close-out memo 작성
2. `어떤 bridge가 실제 가치가 있었는지` 정리
3. `추가 raw가 여전히 필요한지` 재판단
4. product acceptance / forecast / management follow-up으로 handoff

## 10. 지금 가장 자연스러운 시작

지금 바로 시작해야 하는 건 아래다.

1. `BF1-A input contract freeze`
2. `BF1-B bridge summary shape 정의`
3. `BF1-C forecast feature wiring`

즉 BF는 큰 계획을 먼저 다 만드는 것이 아니라,
`BF1을 먼저 작은 공통 bridge로 완성`하고 나서
그 다음 `BF2/BF3`로 내려가는 구조가 맞다.

## 11. 최종 한 줄 요약

```text
BF의 시작은 BF1 act_vs_wait_bias_v1이고,
이 bridge를 transition forecast와 chart/product acceptance가 함께 쓰게 만드는 것이 현재 가장 중요한 구현 순서다.
```
