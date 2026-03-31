# State / Forecast Validation SF6 Close-Out / Next-Action Decision Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

SF6에서는 SF5까지 쌓인 validation 결과를 다시 raw 수준으로 재계산하지 않고,
이미 잠긴 gap matrix와 bridge candidate를 기준으로
`지금 하지 말아야 할 것`, `지금 바로 해야 할 것`, `단일 next action`을 공식적으로 닫았다.

구현 파일:

- [state_forecast_validation_close_out_next_action_decision.py](C:\Users\bhs33\Desktop\project\cfd\scripts\state_forecast_validation_close_out_next_action_decision.py)
- [test_state_forecast_validation_close_out_next_action_decision.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_state_forecast_validation_close_out_next_action_decision.py)

산출물:

- `data/analysis/state_forecast_validation/state_forecast_validation_sf6_close_out_latest.json`
- `data/analysis/state_forecast_validation/state_forecast_validation_sf6_close_out_latest.csv`
- `data/analysis/state_forecast_validation/state_forecast_validation_sf6_close_out_latest.md`

## 2. SF6에서 공식으로 닫은 결론

이번 close-out의 핵심 결론은 아래 한 줄이다.

```text
지금은 broad raw 확장보다 bridge-first가 맞고,
단일 next action은 BF1 act_vs_wait_bias_v1 이다.
```

정리하면:

- `state raw surface`는 이미 충분히 존재한다.
- `order_book`은 collector 전반 문제가 아니라 targeted availability gap이다.
- `secondary_harvest`는 activation이 일부 살아 있어도 direct-use/value path가 없다.
- `transition false-break`는 separation이 flat하다.
- `management hold/fail`도 separation이 약하거나 flat하다.

즉 병목은 `raw 부족`보다는
`usage/value path 부족 + bridge summary 부족`으로 보는 게 맞다.

## 3. 그래서 왜 BF1 act_vs_wait_bias_v1이 먼저인가

P1 bridge 후보는 3개가 있었지만,
SF6에서는 `act_vs_wait_bias_v1`을 단일 active step으로 고정했다.

이유는 아래와 같다.

1. `p_false_break`가 가장 직접적으로 flat하다.
   - `separation_gap = -0.0147`
   - `high_low_rate_gap = -0.0039`

2. 이 문제는 forecast 내부 branch refinement에만 머무르지 않는다.
   - chart wait awareness
   - product acceptance의 `W / awareness`
   - transition scene interpretation
   로 바로 연결된다.

3. 새 raw field를 크게 더하지 않아도 된다.
   - 이미 있는 `state + evidence + belief + barrier`를 bridge로 요약해도 시작할 수 있다.

4. management bridge 두 개보다 선행 가치가 높다.
   - `hold_reward_hint`
   - `fast_cut_risk`
   는 이후에도 중요하지만,
   먼저 act/wait discrimination을 정리해야 상위 scene 해석과 product acceptance가 덜 흔들린다.

## 4. 지금 하지 말아야 하는 것

SF6 기준으로 아래는 지금 active step으로 올리지 않는다.

### 4-1. broad raw add

- 이유: state raw surface는 이미 충분히 존재한다.
- 판단: `defer`

### 4-2. broad secondary raw expansion

- 이유: secondary raw를 더 넣어도 direct-use/value path가 비어 있으면 효과가 약하다.
- 판단: `defer`

### 4-3. broad collector rebuild

- 이유: collector 전반이 죽은 게 아니라 `order_book`만 유난히 비활성이다.
- 판단: `defer`

### 4-4. threshold tuning first

- 이유: bridge/value path가 약한 상태에서 threshold부터 만지면 신호를 고치는 대신 부족한 구조를 우회하게 된다.
- 판단: `defer`

## 5. 지금 바로 해야 하는 것

### 5-1. active now

- `BF1 act_vs_wait_bias_v1`

목표:

- `act_vs_wait_bias`
- `false_break_risk`
- `awareness_keep_allowed`

를 `state + evidence + belief + barrier`에서 bridge summary로 만든다.

이 bridge는:

- transition forecast branch
- chart wait awareness
- product acceptance의 `WAIT / awareness` 재조정

을 같이 도울 수 있어야 한다.

### 5-2. queue next

- `BF2 management_hold_reward_hint_v1`
- `BF3 management_fast_cut_risk_v1`

이 둘은 act/wait bridge 다음 우선순위다.

## 6. 그 다음 follow-up

SF6가 닫은 뒤 follow-up 후보는 아래 순서다.

- `trend_continuation_maturity_v1`
- `advanced_input_reliability_v1`
- `detail_to_csv_activation_projection_v1`

즉 지금 immediately 필요한 건
`공통 summary bridge`이고,
그 다음에야 trend-specific, reliability, analysis projection을 손보는 게 맞다.

## 7. product acceptance와의 연결

이번 close-out은 validation 트랙으로 끝나는 게 아니라,
지금 진행 중인 chart/product acceptance 조정과도 직접 연결된다.

특히 `BF1 act_vs_wait_bias_v1`은

- NAS의 상단 혼잡 awareness
- XAU의 chop soft-cap
- BTC의 reclaim/continuation distinction

같은 장면에서
`왜 1개로 남겨야 하는지`, `왜 W로 눌러야 하는지`
를 더 일관되게 설명하는 공통 modifier가 될 수 있다.

즉 SF6의 handoff는 단순 forecast 개선이 아니라
`forecast refinement + product acceptance chart/wait refinement`
를 묶는 첫 bridge step으로 이해하는 게 맞다.

## 8. 다음 active step

SF6 close-out 이후 다음 active step은 아래로 고정한다.

```text
BF1. act_vs_wait_bias_v1 bridge 설계 및 구현
```

관련 follow-up 문서:

- [bridge_first_refinement_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_refinement_detailed_reference_ko.md)
- [bridge_first_refinement_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_refinement_execution_roadmap_ko.md)

한 줄 요약:

```text
SF6의 공식 결론은
지금은 raw 확장이 아니라 bridge-first가 맞고,
그 첫 번째 bridge는 act_vs_wait_bias_v1 이라는 것이다.
```
