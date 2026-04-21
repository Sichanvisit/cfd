# Product Acceptance PA3 Wait / Hold Acceptance Detailed Reference

## 목적

이 문서는 `PA3. wait / hold acceptance`를 실제 구현 단계로 내리기 전에,
무엇을 `PA3` 문제로 볼지와 첫 구현축이 무엇인지 고정하기 위한 상세 기준 문서다.

PA1/PA2가 사실상 닫힌 현재 기준선은 아래다.

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

현재 summary:

- `must_show_missing = 0`
- `must_hide_leakage = 0`
- `must_enter_candidate = 0`
- `must_block_candidate = 0`
- `must_hold_candidate = 2`
- `must_release_candidate = 10`
- `bad_exit_candidate = 10`

즉 이제 acceptance 메인축은 chart/entry가 아니라 `hold / release / exit`다.

## PA3와 PA4의 경계

이번 phase에서 가장 먼저 고정할 것은 `PA3`와 `PA4`를 어디서 나누는가이다.

### PA3가 담당하는 것

- 포지션을 조금 더 참아야 했는가
- adverse 구간에서 recovery를 기다리는 판단이 적절했는가
- green close / recovery hold / belief hold / edge hold 같은 `hold patience` 축이 자연스러운가
- `bad_wait / good_wait / unnecessary_wait` 분류가 사용자 체감과 맞는가

즉 `닫을지 말지`보다 먼저, `조금 더 버틸지 / 바로 접을지`의 인내 판단을 다룬다.

### PA4가 담당하는 것

- 최종 close action 자체가 맞았는가
- Protect Exit / Adverse Stop / Reverse / Recovery Exit / Partial / Stop-up이 적절했는가
- exit 타이밍이 너무 이르거나 늦지 않았는가

즉 `종료 액션의 질`을 다룬다.

## 현재 baseline에서 보이는 첫 PA3 타깃

`must_hold 2`는 전부 아래 family다.

- `NAS100`
- `direction = SELL`
- `exit_policy_profile = conservative`
- `wait_quality_label = bad_wait`
- `exit_reason` 안에 `hard_guard=adverse | adverse_wait=timeout(...)`

대표 row:

- `ticket=91758855`
- `ticket=91765176`

이 family가 중요한 이유는 아래 두 가지다.

1. `PA3`의 본질 질문인 “여기서 더 기다렸어야 했는가 / 괜히 오래 버텼는가”가 직접 드러난다.
2. 같은 trade family가 `must_release`와 `bad_exit`에도 겹쳐 있지만, 그 출발점은 final exit quality보다 `adverse_wait patience` 쪽에 더 가깝다.

즉 `PA3 kickoff first target`은 아래로 본다.

```text
NAS SELL + conservative + hard_guard=adverse + adverse_wait=timeout + bad_wait
```

## 현재 baseline에서 보이는 후속 축

`must_release 10 / bad_exit 10`은 mostly 아래 두 family로 갈린다.

### NAS SELL Protect / Adverse family

- `symbol = NAS100`
- `direction = SELL`
- `exit_reason`에 `Protect Exit` 또는 `Adverse Stop`
- `Flow: BB 20/2 mid 돌파지지`, `TopDown 1M bullish` 같은 역방향 회복/반전 근거가 동반
- `loss_quality_label = bad_loss 또는 neutral_loss`
- `wait_quality_label = no_wait 또는 bad_wait`

### XAU BUY Protect Exit family

- `symbol = XAUUSD`
- `direction = BUY`
- `exit_reason = Protect Exit`
- `Flow: BB 20/2 mid 이탈저항`, `RSI overbought`
- `giveback_usd`가 크게 남고 `wait_quality_label = no_wait`

이들은 `PA3 kickoff` 다음에 `PA4 exit acceptance`로 내려갈 가능성이 높다.

## Step 2 casebook mini set

이번 턴에서는 `PA3 Step 2 casebook capture`를
아래 미니셋 문서로 먼저 고정했다.

- [product_acceptance_pa3_wait_hold_casebook_mini_set_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_casebook_mini_set_ko.md)

핵심 요약:

- `bad_wait` anchor는 `NAS SELL + hard_guard=adverse + adverse_wait=timeout(...)` 2건이다
- 비교군은 `NAS SELL protect exit no_wait`와 `XAU BUY protect exit no_wait`로 잡는다
- 현재 closed-trade surface에는 `good_wait / unnecessary_wait` label이 아직 없다
- 따라서 이번 phase 초반에는 `bad_wait vs no_wait control` 구조로 경계를 좁히는 것이 맞다

## Step 3 first adjustment design

이번 턴에서 정리한 `first adjustment design` 결론은 아래다.

### 1. 이번 축의 1차 문제는 warmup이 아니라 timeout 상한이다

대표 `bad_wait` 2건은

- `adverse_wait=timeout(349s)`
- `adverse_wait=timeout(174s)`

형태라서, `warmup(10s)`가 길어서 생긴 문제가 아니다.
즉 first patch에서 warmup을 더 줄이는 것은 우선순위가 아니다.

### 2. recovery_need도 지금은 1차 조정 포인트가 아니다

현재 closed-trade artifact에는 `adverse_wait=recovery(...)`로 분류된 row가 보이지 않는다.
즉 현 시점 문제는 `recovery 기준이 너무 엄격해서 못 빠져나온다`보다
`timeout 상한이 너무 길다`에 더 가깝다.

그래서 이번 first patch 방향은:

- `min_wait_s`: 유지
- `recovery_need`: 유지
- `max_wait_s`: `tf_confirm + weak peak`에서만 더 짧게 cap

으로 고정한다.

### 3. hold bias rewrite는 이번 축의 1차 owner가 아니다

[exit_wait_state_rewrite_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_rewrite_policy.py)
는 아래 rewrite를 가진다.

- `green_close_hold_bias`
- `belief_hold_bias`
- `symbol_edge_hold_bias`
- `state_fast_exit_cut`
- `belief_fast_exit_cut`

하지만 이번 `bad_wait timeout` family는
[exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
의 `adverse_wait=warmup/recovery/timeout/holding` 경계에서 먼저 결정된다.

즉 over-hold를 직접 만든 1차 owner는 `exit_service.py`이고,
rewrite layer는 `GREEN_CLOSE / RECOVERY_* / NONE`류 hold 체감 조정 owner로 분리하는 것이 맞다.

### 4. closed-trade label과 runtime surface는 같은 축이지만 같은 표현은 아니다

[trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py) 기준으로:

- `wait_quality_label=good_wait` 는 `adverse_wait=recovery(...)` reason string에 기대고
- `wait_quality_label=bad_wait` 는 `adverse_wait=timeout(...)` reason string에 기대며
- `wait_quality_label=unnecessary_wait` 도 recovery ratio 계산 뒤에만 나온다

반면 runtime에서는
[wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
가 `exit_wait_state_policy_v1 -> exit_wait_state_rewrite_v1 -> exit_wait_state_surface_v1`로
더 풍부한 wait-state surface를 만든다.

즉 현재 artifact에서 `good_wait / unnecessary_wait`가 0건인 것은
wait-state가 아예 없어서가 아니라,
closed-trade label 생성이 `exit_reason` 문자열과 recovery ratio에 더 강하게 의존하기 때문으로 본다.

## Step 3 결론

이번 first adjustment design의 결론은 아래 한 줄이다.

```text
이번 PA3-1 first patch는 hold bias나 recovery threshold를 넓게 건드리는 단계가 아니라,
NAS SELL adverse timeout bad_wait family의 max wait 상한만 먼저 좁히는 단계다.
```

## current owner 판단

roadmap 원문에는 `wait_engine.py`와 `entry_wait_*`가 PA3 owner로 적혀 있지만,
현재 artifact를 실제로 보면 first target owner는 조금 더 아래처럼 좁혀진다.

### primary owner

- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
  - `adverse_wait_state`
  - `adverse_wait=warmup/recovery/timeout/holding`
- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
  - exit wait engine entry point
- [exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_policy.py)
  - hold state family 판단
- [exit_wait_state_rewrite_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_rewrite_policy.py)
  - `green_close_hold_bias`, `belief_hold_bias`, `symbol_edge_hold_bias`
- [exit_wait_state_surface_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_surface_contract.py)
  - compact surface / runtime evidence

### evidence / logging owner

- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
  - `exit_wait_state_surface_v1` flattening
- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv)
  - `wait_quality_label`, `loss_quality_label`, `exit_policy_profile`

## Step 1 read-flow 요약

### exit_service.py

- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py) 는 `adverse_wait_state` dict를 ticket별로 유지한다.
- actual adverse flow는 아래처럼 보였다.
  - extreme adverse면 즉시 `adverse_wait=extreme`
  - giveback skip 조건이면 `adverse_wait=giveback_skip(...)`
  - warmup 미달이면 `adverse_wait=warmup(...)`
  - recovery 부족이면 `adverse_wait=recovery(...)`
  - timeout 도달이면 `adverse_wait=timeout(...)`
  - 그 외엔 `adverse_wait=holding(...)`
- 즉 `must_hold 2` family의 직접 owner는 여기다.

### wait_engine.py

- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py) 는 `build_exit_wait_state(...)` 에서
  - `build_exit_wait_state_input_v1`
  - `resolve_exit_wait_state_policy_v1`
  - `apply_exit_wait_state_rewrite_v1`
  - `build_exit_wait_state_surface_v1`
  순으로 exit wait surface를 만든다.
- 이 레이어는 adverse timeout 자체를 결정한다기보다,
  timeout 이후 hold/rewrite 체감이 어떻게 surface에 남는지를 담당한다.

### exit_wait_state_policy.py

- [exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_policy.py) 는
  `green_close_hold`, `recovery_to_small_profit`, `recovery_to_breakeven`, `adverse_loss_expand` 같은
  state family를 결정한다.
- 핵심 포인트는
  - `adverse_risk and not tf_confirm`면 빠르게 `active_cut`
  - adverse risk가 없고 duration/profit이 작으면 `recovery_*`
  - adverse risk와 negative profit이면 `adverse_loss_expand`
  - 그 외 양호 조건이면 `green_close_hold`
  로 흐른다는 점이다.

### 현재 해석

- `exit_service.py` 는 time/recovery gate owner
- `exit_wait_state_policy.py` 는 hold state family owner
- `wait_engine.py` 는 그 둘을 runtime surface로 묶는 orchestration owner

즉 PA3-1 first patch는 `exit_service.py` 중심으로 보고,
필요하면 `exit_wait_state_policy.py` / `wait_engine.py` 가 그 뒤를 받치는 구조로 가는 게 자연스럽다.

### regression owner

- [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py)
- [test_exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_wait_state_policy.py)
- [test_exit_wait_state_rewrite_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_wait_state_rewrite_policy.py)
- [test_exit_wait_state_surface_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_wait_state_surface_contract.py)
- [test_loss_quality_wait_behavior.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_loss_quality_wait_behavior.py)
- [test_exit_end_to_end_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_end_to_end_contract.py)

## PA3 kickoff 질문

첫 축에서 답해야 하는 질문은 아래다.

1. `adverse_wait timeout`의 warmup / recovery_need / timeout 기준이 너무 공격적인가
2. `bad_wait`로 찍히는 NAS SELL family에서 실제로는 조금 더 회복을 볼 여지가 있었는가
3. `green_close_hold_bias / belief_hold_bias / symbol_edge_hold_bias`가 adverse 상황까지 과도하게 hold를 밀고 있는가, 아니면 반대로 거의 안 먹고 있는가
4. closed-trade labeler의 `wait_quality_label`이 실제 exit_wait_state surface와 충분히 같은 의미를 보고 있는가

## 첫 실행축 제안

PA3는 phase-level로는 넓지만, kickoff implementation은 아래 한 축으로 시작하는 게 맞다.

```text
PA3-1.
NAS SELL adverse_wait timeout bad_wait family
-> hold patience / recovery wait 기준 재점검
-> exit_wait_state surface와 closed-trade label 일치 여부 점검
-> must_hold 2 해소
```

그 다음 순서는 아래다.

1. `PA3-1` NAS SELL bad_wait timeout
2. `PA3-2` XAU BUY protect exit no_wait residue와의 경계 정리
3. `PA4-1` Protect Exit / Adverse Stop final close quality 재조정
