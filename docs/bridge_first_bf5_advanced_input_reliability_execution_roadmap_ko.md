# BF5 Advanced Input Reliability Execution Roadmap

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `BF5 advanced_input_reliability_v1`를 실제로 구현하고 검증하는 순서를 정리한 실행 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [bridge_first_bf5_advanced_input_reliability_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_bf5_advanced_input_reliability_detailed_reference_ko.md)

## 2. 구현 순서

```text
BF5-A. contract freeze
-> BF5-B. summary shape 구현
-> BF5-C. transition wiring
-> BF5-D. management wiring
-> BF5-E. usage trace / audit fixture 갱신
-> BF5-F. close-out
```

## 3. BF5-A. contract freeze

1. `advanced_input_activation_state`, `tick_flow_state`, `order_book_state`, `event_risk_state`를 BF5 입력으로 고정한다.
2. BF5는 `secondary raw expansion`이 아니라 `reliability summary`라는 점을 계약으로 고정한다.

## 4. BF5-B. summary shape 구현

1. `advanced_reliability`, `order_book_reliable`, `event_context_reliable`를 구현한다.
2. activation score와 collector availability를 component score로 남긴다.

대상 파일:

- `backend/trading/engine/core/forecast_features.py`

## 5. BF5-C. transition wiring

1. BF1 false-break pressure에 BF5 reliability를 soft-scale로 연결한다.
2. transition metadata reason trace에 BF5 값을 남긴다.
3. transition usage trace에 `secondary_harvest` direct use를 남긴다.

대상 파일:

- `backend/trading/engine/core/forecast_engine.py`

## 6. BF5-D. management wiring

1. BF3/BF4 effective scale에 BF5 reliability를 연결한다.
2. `order_book`은 collision 성분만 따로 약하게 다룬다.
3. management metadata version을 올리고 BF5 trace를 남긴다.

대상 파일:

- `backend/trading/engine/core/forecast_engine.py`

## 7. BF5-E. usage trace / audit fixture 갱신

1. forecast contract test에 BF5 summary / metadata 계약을 추가한다.
2. SF3 usage audit fixture를 새 usage trace 기준으로 갱신한다.

대상 파일:

- `tests/unit/test_forecast_contract.py`
- `tests/unit/test_state_forecast_validation_forecast_harvest_usage_audit.py`

## 8. BF5-F. close-out

1. BF5 구현 메모를 남긴다.
2. 메인 BF 로드맵 active step을 `BF6`로 넘긴다.
