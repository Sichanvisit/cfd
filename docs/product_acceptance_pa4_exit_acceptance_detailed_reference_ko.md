# Product Acceptance PA4 Exit Acceptance Detailed Reference

## 목적

이 문서는 `PA4. exit acceptance`를 실제 구현 단계로 내리기 전에,
무엇을 `PA4` 문제로 볼지와 첫 구현축이 무엇인지 고정하기 위한 상세 기준 문서다.

## 현재 위치

최신 기준선은 아래다.

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

현재 exit 쪽 summary:

- `must_hold_candidate = 2`
- `must_release_candidate = 10`
- `bad_exit_candidate = 10`

즉 `PA3`가 아직 살아 있지만,
동시에 `final close action quality`도 이미 별도 축으로 분리해서 볼 수 있는 상태다.

## PA3와 PA4의 경계

### PA3가 먼저 보는 것

- 너무 오래 버텼는가
- 반대로 recovery를 너무 짧게 봤는가
- `adverse_wait=warmup/recovery/timeout/holding` 경계가 적절한가

### PA4가 보는 것

- 최종 `Protect Exit / Lock Exit / Adverse Stop / Reversal` 자체가 맞았는가
- 너무 빨리 protect로 닫은 것은 아닌가
- hold를 줄인 뒤에도 final close action이 계속 나쁘게 남는가

즉 `PA3`는 기다림의 질,
`PA4`는 종료 액션의 질을 다룬다.

## 현재 first target family

현재 `must_release 10 / bad_exit 10`에서 가장 먼저 건드릴 family는 아래다.

```text
NAS100
+ SELL
+ exit_policy_profile=conservative
+ wait_quality_label=no_wait
+ Protect Exit
+ Flow: BB 20/2 mid 돌파지지 (+80점)
+ TopDown 1M: bullish (+20점)
+ hard_guard=adverse
```

대표 ticket:

- `91754280`
- `91754399`
- `91756959`
- `91740244`

이 family를 first target으로 잡는 이유:

1. `must_release`와 `bad_exit` 양쪽에 가장 두껍게 겹친다
2. `PA3 bad_wait timeout`과 같은 adverse context군이지만, 이쪽은 `no_wait Protect Exit`다
3. 즉 다음 질문은 “덜 기다렸어야 하나”가 아니라 “protect로 너무 빨리 잘랐나”가 된다

## 후속 target family

첫 target 다음에는 아래가 자연스럽다.

- `NAS100 SELL + Protect Exit + H1 Context: RSI oversold + hard_guard=adverse`
- `XAUUSD BUY + Protect Exit + Flow: BB 20/2 mid 이탈저항 + H1 overbought`

즉 PA4 초반은 `NAS SELL protect adverse`와 `XAU BUY protect adverse/plus_to_minus` 비교로 진행된다.

## current owner

### primary owner

- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
  - reason normalize
  - reason -> stage mapping
  - execution profile resolve
- [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py)
  - [ExitStageRouter](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py#L100)
  - [ExitActionExecutor](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py#L123)
- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
  - exit utility / winner / wait_selected shadow bundle

### evidence / label owner

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
  - `loss_quality_label`
  - `wait_quality_label`
- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv)
- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

## 첫 구현 원칙

첫 PA4 patch는 아래를 지킨다.

1. `PA3 bad_wait timeout` 문제와 섞지 않는다
2. `Protect Exit` 계열의 final close quality만 본다
3. `hard_guard=adverse`가 붙었다고 무조건 맞는 exit로 보지 않는다
4. `utility_exit_now / utility_hold / utility_reverse`와 `final close reason`이 어긋나는지 같이 본다

## 다음 연결

- [product_acceptance_pa4_exit_acceptance_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_checklist_ko.md)
- [product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md)
