# BF6 Detail-to-CSV Activation Projection Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

BF6의 목적은 `detail usage trace`와 `CSV value row`를 다시 붙여서,
지금까지 SF3/SF4가 따로 보던 두 surface를 한 번에 읽을 수 있게 만드는 것이다.

즉 BF6은 아래 한 줄로 이해하면 된다.

```text
detail에는 activation/usage trace가 있고,
CSV에는 value coverage가 있으니,
둘을 decision row 기준으로 다시 붙여 activation/value review surface를 복원한다.
```

## 2. 왜 필요한가

SF4/SF5까지의 공식 gap은 이랬다.

- full CSV는 `value coverage`는 좋다.
- 하지만 per-row `activation / grouped usage trace`는 얇아진다.
- detail JSONL은 `usage trace`는 풍부하다.
- 하지만 value audit은 CSV full-scan 쪽이 더 안정적이다.

즉 부족한 건 raw가 아니라 `projection bridge`였다.

## 3. 입력

BF6은 아래 surface를 같이 읽는다.

- `entry_decisions.csv`
- `entry_decisions.legacy_*.csv`
- `entry_decisions.detail.jsonl`
- `entry_decisions.legacy_*.detail.jsonl`
- `entry_decisions.detail.rotate_*.jsonl`

## 4. projection contract

### 4-1. value owner

value owner는 계속 `CSV normalized row`다.

- transition value proxy
- management actual/proxy
- regime/value slices

이 값은 BF6에서도 CSV 기준으로 유지한다.

### 4-2. activation / section usage owner

activation / usage owner는 `detail trace`다.

- `advanced_input_activation_state`
- `order_book_state`
- `semantic_forecast_inputs_v2_usage_v1.grouped_usage`

즉 BF6은 owner를 뒤섞지 않고,
`CSV value row + detail usage trace`를 projection한다.

### 4-3. match order

BF6의 기본 match 순서는 아래다.

1. `decision_row_key`
2. `replay_row_key`
3. `(symbol, signal_timeframe, time)` exact tuple fallback

현재 latest 기준 실제 match 대부분은 `decision_row_key` exact다.

## 5. 현재 latest 결과

기준 산출물:

- [state_forecast_validation_bf6_projection_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_bf6_projection_latest.json)
- [state_forecast_validation_bf6_projection_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_bf6_projection_latest.md)

현재 핵심 수치는 아래다.

- `sampled_detail_rows = 3695`
- `matched_projection_rows = 3664`
- `projection_match_ratio = 0.9916`
- `exact_decision_row_key_matches = 3664`
- `unmatched_projection_rows = 31`
- `activation_slice_projection_row_count = 6`
- `section_value_projection_row_count = 8`

즉 BF6의 1차 결론은 분명하다.

```text
detail-to-csv projection 자체는 잘 붙는다.
지금 병목은 projection 실패가 아니라,
붙인 뒤 어떤 section/activation이 실제 value path를 가지는지 해석하는 문제다.
```

## 6. 현재 해석

BF6 latest가 보여주는 가장 중요한 점은 두 가지다.

### 6-1. projection bridge는 성공

- detail sample을 넓게 잡아도 CSV row와 거의 다 붙는다.
- 즉 `activation slice projection gap`은 구현적으로는 닫혔다.

### 6-2. secondary_harvest value path는 아직 약하다

projection 후에도 `secondary_harvest` section used ratio가 약하거나 `0`으로 남는 구간이 있다.

이건 BF6 실패가 아니라,

- historical row가 BF5 이전 metadata를 가지고 있거나
- secondary direct-use/value path가 아직 약한 것

을 뜻한다.

즉 BF6은 `projection bridge`를 닫았고,
이제 남은 문제는 `bridge-first value path` 자체다.

## 7. BF6 이후 의미

BF6이 닫히면 이제 다음이 가능해진다.

- activation state 기준 value slice를 본다
- detail usage section 기준 separation delta를 본다
- SF validation에서 “CSV엔 없어서 못 본다”는 말을 줄인다

즉 BF6은 BF 전체에서 `review surface restoration` 역할을 한다.

## 8. 완료 기준

BF6 완료는 아래 상태를 뜻한다.

- detail trace와 CSV row가 높은 coverage로 붙는다
- activation slice projection latest가 생성된다
- section value projection latest가 생성된다
- 다음 단계가 `BF7 close-out`으로 선명해진다
