# State / Forecast Validation SF4 Forecast Feature Value / Slice Audit Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

SF4에서는 `forecast input이 실제로 value를 만드는지`를 보기 위해
기존 sampled detail 기반이 아니라 `entry_decisions CSV 전체 + trade_closed_history` 기준으로
value / slice audit surface를 새로 열었다.

구현 파일:

- [state_forecast_validation_forecast_feature_value_slice_audit.py](C:\Users\bhs33\Desktop\project\cfd\scripts\state_forecast_validation_forecast_feature_value_slice_audit.py)
- [test_state_forecast_validation_forecast_feature_value_slice_audit.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state_forecast_validation_forecast_feature_value_slice_audit.py)

산출물:

- `data/analysis/state_forecast_validation/state_forecast_validation_sf4_value_latest.json`
- `data/analysis/state_forecast_validation/state_forecast_validation_sf4_value_latest.csv`
- `data/analysis/state_forecast_validation/state_forecast_validation_sf4_value_latest.md`

## 2. 왜 sampled detail이 아니라 full CSV로 갔는가

SF1~SF3는 coverage / activation / usage trace를 보기 때문에 sampled detail head scan으로 충분했다.

하지만 SF4는 `실제 outcome label`이 중요하다.
sampled detail 3480 row 기준으로 `ENTERED = 17` row밖에 없어서 management actual value audit에는 너무 얇았다.

반면 `entry_decisions.csv + legacy csv` 전체를 보면:

- total decision rows: 약 `34k`
- `ENTERED` rows: `160`

이라서 management actual value를 보기 위한 최소 커버리지가 확보된다.

즉 SF4는 `value audit` 특성상 intentionally source strategy를 바꿨다.

## 3. 이번 SF4에서 본 value의 정의

### 3-1. transition branch

transition 쪽은 아직 직접 future outcome label이 붙은 구조가 아니므로
다음 proxy로 separation을 본다.

- `p_buy_confirm` vs `BUY path`
- `p_sell_confirm` vs `SELL path`
- `p_false_break` vs `WAIT / observe path`

여기서 label은 주로 `observe_confirm_v1.action/state`를 쓰고,
빈 경우만 `consumer_check_side / consumer_check_stage` fallback을 쓴다.

### 3-2. trade management branch

management 쪽은 `outcome = ENTERED` row를
`symbol + direction + decision time` 기준으로
`trade_closed_history.csv`의 실제 closed trade에 매칭해서 actual label을 만든다.

이번 proxy는 다음 두 개다.

- `p_continue_favor` vs `profit > 0`
- `p_fail_now` vs `profit < 0`

즉 SF4 management value는 `decision proxy`가 아니라 `matched trade actual`이다.

## 4. slice / harvest value proxy를 어떻게 읽는가

### 4-1. slice

현재 slice는 다음 세 축으로 본다.

- `symbol`
- `regime_key`
- `advanced_input_activation_state`

각 slice마다 metric separation이 평평한지, useful한지, strong한지를 본다.

### 4-2. harvest section value proxy

진짜 ablation은 아직 하지 않았고,
usage trace 기준 `section used rows`와 `unused rows`를 나눠
branch separation이 얼마나 달라지는지 proxy로 본다.

즉 이 단계는

- causal proof
- model feature attribution

이 아니라

- `어느 section은 value path가 열려 있고`
- `어느 section은 아예 direct value path가 비어 있는지`

를 operational하게 확인하는 단계다.

## 5. 이번 단계에서 특히 중요하게 보는 것

이번 SF4에서 특히 중요한 질문은 아래다.

1. transition score는 실제 decision proxy를 어느 정도 분리하는가
2. management score는 실제 matched trade actual을 어느 정도 분리하는가
3. symbol / regime / activation slice 중 separation이 유독 평평한 곳은 어디인가
4. `secondary_harvest`는 usage trace는 있어도 value path가 실제로 열려 있는가

## 6. 현재 해석 포인트

이번 단계의 핵심 해석은 아래 중 하나로 귀결된다.

- raw가 부족한 게 아니라 existing harvest도 already useful하다
- 특정 slice에서만 useful하고 나머지는 bridge가 더 필요하다
- `secondary_harvest`처럼 activation은 살아 있어도 direct-use/value path가 비어 있다
- management actual coverage는 붙지만 아직 더 넓은 sample이 필요하다

## 7. 다음 단계

이번 SF4 다음 active step은 `SF5 gap matrix + bridge candidate review`다.

즉 이제는 다음 중 무엇이 부족한지 분리해 말할 수 있어야 한다.

- `raw 부족`
- `activation 부족`
- `usage 부족`
- `value path 부족`
- `bridge summary 부족`
