# BF7 Close-Out and Handoff Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

BF7의 목적은 BF1~BF6 구현 결과를 공식적으로 닫고,
다음 단계가 무엇인지 흔들리지 않게 handoff하는 것이다.

즉 BF7은 아래 한 줄로 이해하면 된다.

```text
bridge-first 본선은 닫고,
다음은 broad raw add가 아니라
product acceptance 공통 state-aware modifier와
fresh-row 기반 forecast re-review로 넘긴다.
```

## 2. BF7이 닫는 것

BF7은 아래를 공식적으로 닫는다.

- BF1 `act_vs_wait_bias_v1`
- BF2 `management_hold_reward_hint_v1`
- BF3 `management_fast_cut_risk_v1`
- BF4 `trend_continuation_maturity_v1`
- BF5 `advanced_input_reliability_v1`
- BF6 `detail_to_csv_activation_projection_v1`

## 3. 현재 공식 결론

기준 산출물:

- [bridge_first_bf7_close_out_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\bridge_first_bf7_close_out_latest.json)
- [bridge_first_bf7_close_out_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\bridge_first_bf7_close_out_latest.md)

현재 BF7의 main call은 아래다.

```text
BF1~BF6는 구현 완료 상태로 닫고,
다음 leverage는 product acceptance 공통 state-aware display modifier다.
```

## 4. 왜 broad raw add가 아닌가

SF0~SF6와 BF1~BF6를 합치면 결론은 계속 같다.

- raw surface는 이미 넓다
- order_book만 targeted collector outlier다
- bridge/value path가 더 큰 병목이다
- BF6 projection도 높은 coverage로 붙는다

즉 BF7 이후에 다시 `raw를 더 넣자`로 돌아가는 건 지금 순서가 아니다.

## 5. BF7 이후 handoff

BF7 이후 handoff는 세 갈래로 나눈다.

추가 handoff 기준 문서:

- [state_forecast_product_acceptance_handoff_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\state_forecast_product_acceptance_handoff_ko.md)

### 5-1. product acceptance handoff

다음 1순위는 `common_state_aware_display_modifier_v1` 이다.

이유:

- 지금까지는 XAU/NAS/BTC를 부분적으로 따로 조정했다
- BF bridge가 생겼으니
  이제 모든 심볼이 같은 `scene owner + bridge modifier` 구조를 타야 한다
- chart acceptance와 wait awareness를 더 일관되게 맞출 수 있다

active 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_implementation_checklist_ko.md)

### 5-2. forecast validation handoff

다음 1순위는 `fresh BF5/BF6 row`가 조금 더 쌓인 뒤
SF3/SF4를 다시 보는 것이다.

이유:

- BF5의 secondary direct-use trace는 fresh row에서 더 정확히 드러난다
- BF6 projection은 이미 붙었으므로 fresh row가 쌓일수록 section value path 해석이 더 선명해진다

### 5-3. collector handoff

collector 쪽은 broad rebuild가 아니라
`order_book availability`만 좁게 follow-up 한다.

## 6. 완료 기준

BF7 완료는 아래를 뜻한다.

- BF1~BF6 구현 inventory가 공식적으로 남는다
- BF6 projection evidence가 close-out에 포함된다
- broad raw add를 지금 하지 않는다는 판단이 고정된다
- 다음 active step이 product acceptance 공통 modifier로 선명해진다
