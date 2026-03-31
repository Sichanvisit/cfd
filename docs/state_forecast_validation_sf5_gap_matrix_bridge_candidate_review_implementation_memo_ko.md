# State / Forecast Validation SF5 Gap Matrix / Bridge Candidate Review Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

SF5에서는 SF1~SF4 산출물을 다시 계산하지 않고,
이미 확보한 검증 결과를 `gap matrix`와 `bridge candidate review`로 공식 정리했다.

구현 파일:

- [state_forecast_validation_gap_matrix_bridge_candidate_review.py](C:\Users\bhs33\Desktop\project\cfd\scripts\state_forecast_validation_gap_matrix_bridge_candidate_review.py)
- [test_state_forecast_validation_gap_matrix_bridge_candidate_review.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state_forecast_validation_gap_matrix_bridge_candidate_review.py)

산출물:

- `data/analysis/state_forecast_validation/state_forecast_validation_sf5_gap_matrix_latest.json`
- `data/analysis/state_forecast_validation/state_forecast_validation_sf5_gap_matrix_latest.csv`
- `data/analysis/state_forecast_validation/state_forecast_validation_sf5_gap_matrix_latest.md`

## 2. 왜 SF5가 필요한가

SF1~SF4까지 오면 정보는 충분히 많아진다.
하지만 실제 다음 액션을 정하려면 아래를 분리해서 말할 수 있어야 한다.

- raw가 부족한가
- collector activation이 부족한가
- usage path가 비어 있는가
- value separation이 약한가
- 아니면 bridge summary가 부족한가

SF5는 이 질문에 답하는 분류 단계다.

## 3. 이번 SF5의 핵심 결론

이번 검토의 메인 결론은 아래 한 줄이다.

```text
지금 병목은 broad raw 부족보다 bridge + usage + value path 쪽에 더 가깝다.
```

더 구체적으로는:

- raw state surface는 이미 충분히 살아 있다
- order_book은 targeted collector gap이다
- secondary_harvest는 activation과 별개로 direct-use/value path가 비어 있다
- transition에서는 `p_false_break`가 평평하다
- management에서는 `p_continue_favor`, `p_fail_now`가 아직 약하다
- trend management slice가 range보다 약하다
- full CSV surface는 value coverage는 좋지만 activation/usage projection은 잃는다

## 4. 그래서 왜 bridge candidate가 필요한가

이번 단계에서 새 raw field를 바로 늘리는 대신 bridge candidate를 먼저 뽑은 이유는 명확하다.

1. 이미 raw는 많다
2. secondary_harvest는 collector/usage path가 비어 있다
3. transition false-break와 management hold/fail은 요약 bridge가 더 직접적인 개선 포인트다

즉 `state를 더 넣는다`보다
`기존 state/evidence/belief/barrier를 product/forecast가 쓰기 좋은 bridge로 요약한다`
가 더 맞는 단계라는 뜻이다.

## 5. 현재 우선 bridge 후보

### P1

- `act_vs_wait_bias_v1`
- `management_hold_reward_hint_v1`
- `management_fast_cut_risk_v1`

### P2

- `trend_continuation_maturity_v1`
- `advanced_input_reliability_v1`

### P3

- `detail_to_csv_activation_projection_v1`

## 6. 다음 단계

SF5 다음 active step은 `SF6 close-out + next-action decision`이다.

여기서 결정해야 하는 건 아래다.

- broad raw add를 계속 미룰지
- order_book collector를 targeted fix로 볼지
- P1 bridge 후보를 실제 product acceptance / forecast refinement로 연결할지
- analysis projection bridge를 별도 보조 과제로 둘지
