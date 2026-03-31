# BF5 Advanced Input Reliability Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 패스에서 한 일

- `forecast_features`에 `advanced_input_reliability_v1` bridge를 추가했다.
- `transition_forecast`에서 BF1 false-break pressure에 BF5 reliability를 soft-scale로 연결했다.
- `trade_management_forecast`에서 BF3/BF4 effective scale에 BF5 reliability를 연결했다.
- `secondary_harvest`의 `advanced_input_activation_state`, `tick_flow_state`, `order_book_state`를 branch usage trace에 direct-use로 표시했다.
- management branch metadata version을 `fc9`로 올렸다.

## 2. 구현 파일

- `backend/trading/engine/core/forecast_features.py`
- `backend/trading/engine/core/forecast_engine.py`
- `tests/unit/test_forecast_contract.py`
- `tests/unit/test_state_forecast_validation_forecast_harvest_usage_audit.py`

## 3. BF5 해석

이번 BF5는 `secondary input를 더 많이 쓰자`가 아니다.

핵심은 아래다.

- tick/event가 살아 있으면 advanced context 전체를 0으로 보지 않는다
- order book이 거의 비어 있으므로 collision 성분은 별도 scale로 보수적으로 본다
- 즉 `collector availability 불균형`을 bridge로 흡수한다

## 4. 테스트 기준

- forecast contract targeted: 통과
- SF3 usage audit test: 통과

## 5. 구현 후 주의점

실데이터 SF3 latest는 아직 옛 row 기준이라 `secondary_harvest_direct_use_field_count = 0`으로 남을 수 있다.

이건 BF5 구현 실패라기보다:

- 기존 historical detail row는 이전 metadata를 담고 있고
- BF5 trace는 새로 생성되는 row부터 반영되기 때문

즉 BF5의 real latest coverage는 새 runtime row가 더 쌓인 뒤 다시 봐야 한다.

## 6. 다음 단계

다음 active step은 `BF6 detail_to_csv_activation_projection_v1`이다.
