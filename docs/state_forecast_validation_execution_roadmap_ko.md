# State / Forecast Validation Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `state / forecast validation` subtrack을
실행 가능한 순서로 쪼갠 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [state_forecast_validation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\state_forecast_validation_detailed_reference_ko.md)

## 2. 전체 순서

```text
SF0. baseline inventory freeze
-> SF1. state coverage audit
-> SF2. advanced input activation audit
-> SF3. forecast harvest usage audit
-> SF4. forecast feature value / slice audit
-> SF5. gap matrix and bridge candidate review
-> SF6. close-out and next-action decision
```

## 3. SF0. Baseline Inventory Freeze

### 목표

현재 state / forecast 입력과 테스트 기준선을 먼저 고정한다.

### 해야 할 일

1. 현재 state builder가 실어주는 field inventory를 고정한다.
2. advanced input inventory를 고정한다.
3. forecast semantic harvest inventory를 고정한다.
4. 관련 테스트 baseline을 고정한다.

### 주요 파일

- [builder.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\builder.py)
- [advanced_inputs.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\advanced_inputs.py)
- [forecast_features.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\forecast_features.py)
- [test_forecast_contract.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_forecast_contract.py)

### 완료 기준

- 현재 inventory를 문서/산출물로 바로 읽을 수 있다.

## 4. SF1. State Coverage Audit

### 목표

state raw와 state_vector_v2가 실제 row에서 얼마나 살아 있는지 본다.

### 해야 할 일

1. symbol별 coverage
2. timeframe별 coverage
3. regime별 coverage
4. default/zero-heavy field 점검
5. field sparsity / suspicious fill-rate 리포트

### 질문

- 어떤 field는 거의 항상 0인가
- 어떤 field는 특정 심볼에서만 살아 있나
- 어떤 field는 latest rows에만 있고 historical엔 비는가

### 완료 기준

- state coverage latest report가 있다.

## 5. SF2. Advanced Input Activation Audit

### 목표

advanced input이 `코드상 존재`가 아니라 `실제로 활성화`되고 있는지 본다.

### 해야 할 일

1. `advanced_input_activation_state` 빈도 점검
2. tick_history activation 비율
3. order_book activation 비율
4. event_risk activation 비율
5. activation reason 분포 점검

### 질문

- activation이 너무 드문가
- 심볼별 편차가 큰가
- collector unavailable/default가 너무 많은가

### 완료 기준

- advanced input activation audit latest report가 있다.

### 현재 상태

- SF2 구현 완료
- latest 기준 `tick_history`와 `event_risk`는 대체로 활성화되어 있음
- `order_book`은 `UNAVAILABLE` 비중이 압도적으로 높아 가장 강한 activation gap으로 확인됨
- 다음 active step은 `SF3. Forecast Harvest Usage Audit`

## 6. SF3. Forecast Harvest Usage Audit

### 목표

forecast가 harvest한 값을 실제로 branch 계산에서 얼마나 쓰는지 usage 기준으로 본다.

### 해야 할 일

1. state_harvest usage 집계
2. belief_harvest usage 집계
3. barrier_harvest usage 집계
4. secondary_harvest usage 집계
5. branch role별 usage 차이 확인

### 질문

- 담고만 있고 거의 안 쓰는 harvest는 무엇인가
- 특정 branch에서만 중요한 harvest는 무엇인가

### 완료 기준

- usage summary와 unused/low-value candidate 목록이 있다.

## 7. SF4. Forecast Feature Value / Slice Audit

### 목표

usage를 넘어서, 실제 예측 품질에 어떤 입력이 기여하는지 본다.

### 해야 할 일

1. preview/shadow 기준 metric 집계
2. symbol별 metric
3. regime별 metric
4. slice별 heavy-default / sparse / unstable bucket 확인
5. 가능하면 ablation 또는 proxy importance 분석

### 질문

- 어떤 harvest는 정확도/분리도를 실제로 올리는가
- 어떤 harvest는 특정 slice에서만 유효한가
- 어떤 심볼은 bridge 요약이 더 필요하고 어떤 심볼은 raw가 더 필요한가

### 완료 기준

- feature value / slice audit latest report가 있다.

## 8. SF5. Gap Matrix and Bridge Candidate Review

### 목표

이제 부족한 것이 `raw`, `activation`, `usage`, `bridge` 중 무엇인지 분리해서 정리한다.

### 해야 할 일

1. gap matrix 작성
2. 심볼별 상태 정리
3. chart acceptance에 바로 연결 가능한 bridge 후보 정리
4. forecast refinement에 필요한 bridge 후보 정리

### 예시 bridge 후보

- chop_pressure
- directional_pressure
- exhaustion_pressure
- awareness_keep_allowed
- act_vs_wait_bias
- fast_cut_risk
- hold_reward_hint

### 완료 기준

- 다음 단계 후보가 raw 추가 / bridge 추가 / 무변경 유지 중 어디인지 정리된다.

## 9. SF6. Close-Out and Next-Action Decision

### 목표

validation 결과를 실제 다음 작업으로 연결한다.

### 가능한 결론

1. raw 추가는 보류, bridge만 추가
2. advanced input activation부터 개선
3. 특정 심볼만 raw/collector 보강
4. forecast feature weighting / threshold 조정
5. product acceptance chart modifier로 일부 결과 연결

### 완료 기준

- close-out memo가 있고,
- 다음 active step이 명확히 하나로 좁혀진다.

## 10. 지금 가장 자연스러운 시작점

지금은 아래 순서가 가장 자연스럽다.

1. `SF0 baseline inventory freeze`
2. `SF1 state coverage audit`
3. `SF2 advanced input activation audit`

이 세 단계를 먼저 해야
`데이터가 부족하다`는 가설이 맞는지,
아니면 `활성화/커버리지가 약하다`는 쪽이 맞는지 판정할 수 있다.

## 11. 한 줄 결론

```text
state / forecast validation의 첫 목표는 더 넣는 것이 아니라,
지금 이미 있는 입력이 얼마나 살아 있고 얼마나 실제 가치가 있는지 확인하는 것이다.
```
