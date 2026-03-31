# State / Forecast Validation SF2 Advanced Input Activation Audit Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 목적

SF2는 `advanced input`이 코드에 존재하는지보다, historical row에서 실제로 얼마나 활성화되고 있는지 확인하는 단계다.

이번 구현의 핵심 질문은 아래였다.

- `advanced_input_activation_state`가 실제 row에서 얼마나 자주 활성화되는가
- `tick_history`, `order_book`, `event_risk` collector가 실제로 살아 있는가
- 특정 collector만 default-heavy한가, 아니면 전체 advanced input이 전반적으로 약한가
- 다음 단계를 `raw 추가`가 아니라 `usage/value audit`로 넘겨도 되는가

## 2. 구현 파일

- script:
  - [state_forecast_validation_advanced_input_activation_audit.py](C:\Users\bhs33\Desktop\project\cfd\scripts\state_forecast_validation_advanced_input_activation_audit.py)
- test:
  - [test_state_forecast_validation_advanced_input_activation_audit.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state_forecast_validation_advanced_input_activation_audit.py)

## 3. 샘플링 방식

이번 SF2는 SF1과 같은 bounded audit 전략을 유지했다.

- source: `entry_decisions*.detail.jsonl`
- strategy: `detail_jsonl_per_file_head_sample`
- sampled source count: `86`
- sampled rows per file: `40`
- total sampled rows: `3440`

즉 giant history 전체를 풀스캔하지 않고, active / legacy / rotated detail source 전반에서 고르게 head sample을 읽어 collector activation을 먼저 점검했다.

## 4. 생성 산출물

- [state_forecast_validation_sf2_activation_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf2_activation_latest.json)
- [state_forecast_validation_sf2_activation_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf2_activation_latest.csv)
- [state_forecast_validation_sf2_activation_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\state_forecast_validation_sf2_activation_latest.md)

## 5. 핵심 결과

latest 기준:

- `activation_active_ratio = 0.0003`
- `activation_partial_ratio = 0.8994`
- `activation_passive_ratio = 0.0948`
- `tick_state_active_like_ratio = 0.8997`
- `order_book_state_active_like_ratio = 0.0003`
- `event_risk_state_active_like_ratio = 0.8997`
- `tick_sample_positive_ratio = 0.8997`
- `order_book_levels_positive_ratio = 0.0003`
- `event_risk_match_positive_ratio = 0.8765`

즉 이번 SF2의 1차 결론은 아래 한 줄로 요약된다.

`advanced input 전체가 죽어 있는 것이 아니라, tick/event는 대체로 살아 있고 order_book만 사실상 비활성 상태다.`

## 6. activation state 해석

실제 row에서 읽힌 activation state는 다음과 같았다.

- `ADVANCED_PARTIAL`: `3094` rows (`0.8994`)
- `ADVANCED_IDLE`: `326` rows (`0.0948`)
- `ADVANCED_ACTIVE`: `1` row (`0.0003`)
- `UNKNOWN`: `19` rows (`0.0055`)

즉 현재 advanced input은 대부분 `완전 active`라기보다 `partial activation` 상태로 유지되고 있다.

이 해석은 `tick/event collector는 대부분 metadata에 살아 있지만, 특정 collector 특히 order_book은 usable signal로 이어지지 않는다`는 SF1의 default-heavy suspicion과도 맞물린다.

## 7. collector별 해석

### tick history

- top state: `BALANCED_FLOW`
- active-like ratio: `0.8997`
- positive payload ratio: `0.8997`

tick history는 현재 collector 차원에서 크게 죽어 있지 않다.
즉 SF3 이후에 value audit을 하더라도 `tick flow collector 자체가 거의 안 켜진다`는 문제보다는 `어떤 slice에서 실제로 예측 기여를 하는가`가 중심 질문이 된다.

### order book

- top state: `UNAVAILABLE`
- active-like ratio: `0.0003`
- positive payload ratio: `0.0003`

order_book은 현재 가장 강한 suspicious collector다.
`UNAVAILABLE` 비중이 압도적으로 높고, `order_book_levels > 0` row도 사실상 없다.

즉 현재 단계에서 order_book 관련 문제는 `forecast가 활용을 못 한다`기보다, 그 전에 `collector availability 자체가 거의 없다` 쪽으로 읽는 게 더 정확하다.

### event risk

- top state: `HIGH_EVENT_RISK`
- active-like ratio: `0.8997`
- positive payload ratio: `0.8765`

event_risk는 collector surface와 numeric payload가 모두 상당히 살아 있다.
다만 `HIGH_EVENT_RISK` 비중이 높게 유지되므로, SF3/SF4에서는 이게 실제 의미 있는 분리인지, 아니면 high-risk default bias가 강한지 usage/value 관점에서 다시 봐야 한다.

## 8. symbol별 해석

collector active-like ratio는 심볼별로도 큰 틀이 비슷했다.

- `BTCUSD`
  - tick_flow `0.9487`
  - order_book `0.0000`
  - event_risk `0.9487`
- `NAS100`
  - tick_flow `0.7895`
  - order_book `0.0000`
  - event_risk `0.7895`
- `XAUUSD`
  - tick_flow `0.9106`
  - order_book `0.0012`
  - event_risk `0.9106`

즉 order_book weakness는 특정 심볼만의 문제가 아니라 전 심볼 공통 현상으로 읽는 게 맞다.

## 9. activation reason 분포

상위 activation reason은 아래와 같았다.

- `wait_noise`: `2502`
- `low_participation`: `1855`
- `wait_conflict`: `906`
- `shock_regime`: `46`
- `spread_stress`: `1`

이 결과는 advanced input이 주로 `노이즈/참기 어려움/참여도 부족` 쪽 상황에서 켜지고 있음을 보여준다.
즉 현재 advanced input activation은 market microstructure 전체를 넓게 읽기보다, `문제 상황 감지` 성격이 더 강하다고 해석할 수 있다.

## 10. 이번 SF2의 결론

이번 SF2의 가장 중요한 결론은 이렇다.

1. `state raw/advanced input surface가 비어 있는 것은 아니다`
2. `tick_history`와 `event_risk`는 activation 차원에서 충분히 살아 있다
3. `order_book`만 collector availability가 거의 없어서, 현재 단계에선 가장 강한 activation gap이다
4. 따라서 다음 질문은 `더 많은 raw를 추가할까`가 아니라, `지금 살아 있는 harvest가 forecast branch에서 실제로 얼마나 쓰이고 있는가`가 된다

즉 다음 단계는 자연스럽게 `SF3 forecast harvest usage audit`이다.

## 11. 검증

실행 결과:

- SF2 전용 테스트: `2 passed`
- SF0~SF2 state/forecast validation 묶음은 다음 단계에서 함께 재검증 예정

## 12. 다음 단계

SF2 이후 active step은 `SF3 forecast harvest usage audit`이다.

SF3에서 먼저 확인해야 할 질문은 아래다.

1. `state_harvest / belief_harvest / barrier_harvest / secondary_harvest` 중 실제 branch score에 가장 많이 쓰이는 것은 무엇인가
2. `tick_flow`, `event_risk`처럼 살아 있는 collector가 실제 usage에서도 의미를 가지는가
3. `order_book`은 availability gap이 큰 만큼, usage/value audit에서 제외 후보인지 collector 보강 후보인지 어떻게 정리할 것인가

최종 요약:

`SF2는 advanced input 전체가 약한 것이 아니라 collector 불균형이 핵심이며, 특히 order_book availability gap이 현재 가장 강한 병목이라는 점을 숫자로 고정한 단계다.`
