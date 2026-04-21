# Current Path Checkpoint Rule Tuning External Review Request

## 목적

이 문서는 다른 언어모델이나 외부 리뷰어에게,
현재 `path-aware checkpoint` 구조에서
`management action` 규칙과 `hindsight bootstrap label` 규칙을
어떻게 더 안정적으로 다듬는 것이 좋은지
구현 가능한 수준으로 조언을 얻기 위한 요청서다.

이번 문서의 초점은 아키텍처 재설계가 아니다.

- `leg detector`
- `checkpoint segmenter`
- `checkpoint context storage`
- `passive scoring`
- `dataset / eval`
- `best action resolver`

위 구조는 이미 들어가 있다.

지금 묻고 싶은 것은 다음이다.

> 현재 checkpoint row마다
> `WAIT / HOLD / PARTIAL_EXIT / PARTIAL_THEN_HOLD / FULL_EXIT / REBUY`
> 중 무엇이 맞는지 규칙으로 정할 때,
> 어떤 evidence를 어떻게 묶고,
> 어떤 threshold와 gating을 쓰고,
> 어떤 라벨만 auto-apply 하고
> 어떤 라벨은 manual-exception으로 남기는 것이 좋은가?

즉 이 문서는 구조가 아니라
**규칙(rule) 튜닝**에 대한 외부 조언 요청이다.

---

## 현재 구현된 범위

현재 시스템은 다음 단계까지 구현되어 있다.

1. `PA1 leg detector`
2. `PA2 checkpoint segmenter`
3. `PA3 checkpoint context storage`
4. `PA4 passive score calculation`
5. `PA5 hindsight label / dataset / eval`
6. `PA6 best action resolver`

관련 구현 파일은 주로 아래다.

- `backend/services/path_checkpoint_action_resolver.py`
- `backend/services/path_checkpoint_dataset.py`
- `backend/services/path_checkpoint_context.py`
- `backend/services/path_checkpoint_scoring.py`
- `backend/services/exit_manage_positions.py`
- `backend/services/path_checkpoint_open_trade_backfill.py`
- `backend/services/path_checkpoint_position_side_observation.py`

관련 산출물은 주로 아래다.

- `data/runtime/checkpoint_rows.csv`
- `data/runtime/checkpoint_rows.detail.jsonl`
- `data/datasets/path_checkpoint/checkpoint_dataset.csv`
- `data/datasets/path_checkpoint/checkpoint_dataset_resolved.csv`
- `data/analysis/shadow_auto/checkpoint_action_eval_latest.json`
- `data/analysis/shadow_auto/checkpoint_management_action_snapshot_latest.json`
- `data/analysis/shadow_auto/checkpoint_position_side_observation_latest.json`

---

## 현재 구조를 짧게 요약하면

현재 흐름은 아래와 같다.

```text
runtime row
  -> leg assignment
  -> checkpoint assignment
  -> checkpoint context row 저장
  -> passive score 계산
  -> management action resolver
  -> hindsight bootstrap label
  -> dataset / eval / observation
```

핵심 score는 현재 다음을 계산하고 있다.

- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`
- `runtime_rebuy_readiness`

현재 management action resolver는 아래 후보를 다룬다.

- `WAIT`
- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`

다만 아직 `REBUY`, `FULL_EXIT`, `HOLD` 쪽 사례는 live data가 충분치 않아서
`WAIT`와 `PARTIAL_EXIT`, 일부 `PARTIAL_THEN_HOLD` 중심으로 먼저 보이고 있다.

---

## 현재 실제 상태

기준 시점:

- `2026-04-10`
- KST

### 1. observation 기준 현재 position-side 수집 상태

`checkpoint_position_side_observation_latest.json`

- `row_count = 6`
- `position_side_row_count = 3`
- `open_profit_row_count = 1`
- `open_loss_row_count = 0`
- `runner_secured_row_count = 0`

`management_action_counts`

- `WAIT = 1`
- `PARTIAL_EXIT = 1`
- `PARTIAL_THEN_HOLD = 1`

`recommended_next_action`

- `keep_collecting_exit_manage_position_side_rows`

즉 pipeline은 열렸지만,
아직 position-side checkpoint row 자체가 적고,
특히 `open_loss`, `runner_secured` 사례가 거의 없다.

### 2. dataset / eval 기준 상태

`checkpoint_dataset_resolved.csv`

- `resolved_row_count = 6`
- `position_side_row_count = 3`

`checkpoint_action_eval_latest.json`

- `resolved_row_count = 6`
- `position_side_row_count = 3`
- `manual_exception_count = 5`
- `runtime_proxy_match_rate = 0.833333`
- `runner_capture_rate = 1.0`
- `partial_then_hold_quality = 1.0`
- `premature_full_exit_rate = 0.0`
- `missed_rebuy_rate = 0.0`
- `hold_precision = 0.0`
- `full_exit_precision = 0.0`
- `recommended_next_action = collect_more_live_position_side_checkpoint_rows_before_pa6`

`hindsight_label_counts`

- `WAIT = 5`
- `PARTIAL_THEN_HOLD = 1`

즉 현재 문제는
규칙이 완전히 틀렸다는 것보다는,
**manual-exception이 너무 많고,
hindsight가 아직 WAIT 쪽에 많이 몰려 있다는 점**이다.

---

## 현재 규칙상 중요한 부분

### management action resolver 쪽

현재 runtime resolver는 score 경쟁 구조를 사용한다.

예를 들면 아래 요소를 같이 본다.

- continuation 우세 여부
- reversal 우세 여부
- hold quality
- partial exit EV
- full exit risk
- rebuy readiness
- checkpoint type
- position state

현재 live에서 가장 자주 보이는 건

- 약한 환경이면 `WAIT`
- 수익 보호/축소 쪽 근거가 있으면 `PARTIAL_EXIT`
- continuation이 남아 있고 일부 잠그는 게 좋아 보이면 `PARTIAL_THEN_HOLD`

이다.

### hindsight bootstrap label 쪽

현재 bootstrap label은 아직 보수적으로 간다.

대표적으로:

- `OPEN_PROFIT + continuation 우세 + partial/hold가 일정 수준`이면
  `PARTIAL_THEN_HOLD`
- `OPEN_PROFIT + hold_quality 우세`면
  `HOLD`
- `OPEN_PROFIT + partial_exit_ev 우세`면
  `PARTIAL_EXIT`
- `OPEN_LOSS + full_exit_risk 높음 + reversal 우세`면
  `FULL_EXIT`
- 나머지는 많이 `WAIT`

즉 지금은 오탐보다 과소적용을 더 두려워하는 상태다.

---

## 대표 사례

아래는 지금 외부 리뷰어가 규칙을 볼 때 참고하면 좋은 실제 대표 row다.

### 사례 A. BTCUSD active row, flat-profit 성격, partial_exit 애매

- `symbol = BTCUSD`
- `position_side != FLAT`
- `unrealized_pnl_state = FLAT`
- `runtime_continuation_odds = 0.4728`
- `runtime_reversal_odds = 0.6960`
- `runtime_hold_quality_score = 0.24516`
- `runtime_partial_exit_ev = 0.4120`
- `runtime_full_exit_risk = 0.377696`
- `runtime_proxy_management_action = PARTIAL_EXIT`
- `hindsight_best_action_label = WAIT`

이 row는 현재 runtime에서는 `PARTIAL_EXIT` 쪽으로 기울지만,
hindsight bootstrap은 아직 `WAIT`로 남는다.

즉 질문은 이거다.

> active position인데 profit이 거의 없고,
> reversal은 continuation보다 높지만,
> full_exit까지 강하진 않은 row를
> `WAIT`로 둘지,
> `PARTIAL_EXIT`로 볼지,
> `FULL_EXIT`로 끌어올릴지
> 어떤 규칙이 가장 안정적인가?

### 사례 B. NAS100 active row, flat-profit 성격, 약한 wait

- `symbol = NAS100`
- `position_side != FLAT`
- `unrealized_pnl_state = FLAT`
- `runtime_continuation_odds = 0.5088`
- `runtime_reversal_odds = 0.5760`
- `runtime_hold_quality_score = 0.29856`
- `runtime_partial_exit_ev = 0.4024`
- `runtime_full_exit_risk = 0.305216`
- `runtime_proxy_management_action = WAIT`
- `hindsight_best_action_label = WAIT`

이 row는 runtime도 hindsight도 `WAIT`다.
하지만 실제 운영에서는 이런 flat row가 자주 생긴다.

즉 질문은 이거다.

> active position인데 수익도 손실도 거의 없고,
> continuation / reversal이 모두 애매한 row는
> 그냥 `WAIT`로 두는 것이 맞는가,
> 아니면 특정 checkpoint type이나 source에 따라
> 더 적극적으로 `HOLD` 또는 `PARTIAL_EXIT`를 줘야 하는가?

### 사례 C. NAS100 active row, open-profit continuation, partial-then-hold

- `symbol = NAS100`
- `position_side != FLAT`
- `current_profit = 0.27`
- `unrealized_pnl_state = OPEN_PROFIT`
- `runtime_continuation_odds = 0.6958`
- `runtime_reversal_odds = 0.4840`
- `runtime_hold_quality_score = 0.44317`
- `runtime_partial_exit_ev = 0.50692`
- `runtime_full_exit_risk = 0.220956`
- `runtime_proxy_management_action = PARTIAL_THEN_HOLD`
- `hindsight_best_action_label = PARTIAL_THEN_HOLD`
- `hindsight_reason = bootstrap_profit_runner_capture`

이 row는 현재 가장 명확한 non-WAIT 성공 사례다.

즉 질문은 이거다.

> 이런 open-profit continuation row에서
> `HOLD`와 `PARTIAL_THEN_HOLD`를 가르는 기준은
> 어떤 threshold 조합이 가장 실무적인가?

---

## 지금 특히 어려운 규칙 문제

현재 실제로 가장 애매한 부분은 아래 4개다.

### 1. active but flat-profit row

즉:

- 포지션은 살아 있음
- 손익은 거의 0 근처
- continuation / reversal 모두 중간
- hold / partial / full_exit 어느 쪽도 강하지 않음

이때 현재는 `WAIT` 쪽으로 많이 남는데,
이게 과도하게 보수적인지,
아니면 실제로 맞는지 조언이 필요하다.

### 2. open-profit continuation row

즉:

- 수익은 나고 있음
- continuation 우세
- full_exit 위험은 낮음
- 일부 잠그는 게 좋은지, 그냥 hold가 좋은지 애매

여기서 `HOLD`와 `PARTIAL_THEN_HOLD`의 경계를
어떻게 두는 게 좋은지 조언이 필요하다.

### 3. future runner-secured row

현재 live artifact에선 `runner_secured_row_count = 0`이다.

하지만 앞으로 매우 중요할 것으로 본다.

즉:

- 일부 익절이 끝났고
- break-even 또는 lock 상태로 runner가 남아 있고
- continuation이 살아 있는 row

이런 row는 거의 항상 `WAIT`가 아니라
`HOLD` 또는 `PARTIAL_THEN_HOLD` 또는 `RUNNER_HOLD` 성격이 될 텐데,
taxonomy를 지금 수준에서 더 세분해야 하는지도 궁금하다.

### 4. manual-exception을 얼마나 줄일 것인가

현재 `manual_exception_count = 5 / 6` 수준이다.

이건 의도적으로 보수적으로 잡은 결과지만,
너무 오래 이 상태면 학습/운영이 느려진다.

즉 질문은:

> 어떤 라벨은 지금 단계에서 auto-apply 해도 안전하고,
> 어떤 라벨은 여전히 manual-exception으로 남겨야 하는가?

---

## 현재 외부 리뷰어에게 묻고 싶은 핵심 질문

아래 질문에 대해
추상론이 아니라
**rule / threshold / gating / precedence** 관점으로 답을 듣고 싶다.

### 질문 1. active flat-profit row는 무엇을 기준으로 WAIT vs PARTIAL_EXIT vs FULL_EXIT로 갈라야 하는가

특히 아래 조합에서 조언이 필요하다.

- `position_side != FLAT`
- `unrealized_pnl_state = FLAT`
- `reversal > continuation`
- 하지만 `full_exit_risk`는 중간

이런 row는

- 그냥 `WAIT`
- 약한 `PARTIAL_EXIT`
- 바로 `FULL_EXIT`

중 어디가 맞는가.

그리고 판단에 아래 변수들을 얼마나 강하게 써야 하는가.

- `checkpoint_type`
- `source`
- `mfe_since_entry`
- `mae_since_entry`
- `giveback_from_peak`
- `shock_at_profit`

### 질문 2. open-profit continuation row에서 HOLD vs PARTIAL_THEN_HOLD vs PARTIAL_EXIT를 어떻게 나누는가

현재 가설은 아래다.

- continuation이 충분히 높고 full_exit_risk가 낮으면
  `HOLD` 또는 `PARTIAL_THEN_HOLD`
- partial_exit_ev가 의미 있고 runner 관리 가치가 있으면
  `PARTIAL_THEN_HOLD`
- continuation은 남아도 exhaustion 또는 giveback이 커지면
  `PARTIAL_EXIT`

이 구분을 더 실무적으로 다듬고 싶다.

특히 다음 입력이 1급 evidence인지 궁금하다.

- `runner_secured`
- `position_size_fraction`
- `mfe_since_entry`
- `giveback_from_peak`
- `bars_since_last_push`
- `checkpoint_type`
- `source`

### 질문 3. runner-secured row는 별도 taxonomy가 필요한가

현재 action taxonomy는 아래다.

- `WAIT`
- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`

질문은:

> `runner_secured = true`인 row가 많아지면
> `HOLD` 안에 흡수해도 충분한가,
> 아니면 `RUNNER_HOLD` 같은 별도 label이 필요한가?

### 질문 4. auto-apply 가능한 라벨과 manual-exception으로 남겨야 할 라벨을 어떻게 나누는가

예를 들면 현재 내부 감각은 이렇다.

- 비교적 auto-apply 후보
  - obvious `FULL_EXIT`
  - obvious `PARTIAL_THEN_HOLD`
  - obvious `WAIT`
- 더 조심해야 하는 후보
  - `HOLD`
  - `PARTIAL_EXIT`
  - late trend 구간의 `REBUY`

이 분리가 맞는지,
아니면 다른 기준이 더 좋은지 묻고 싶다.

### 질문 5. manual_exception_count를 줄일 때 가장 안전한 순서는 무엇인가

현재 `manual_exception_count = 5 / 6`은 너무 높다.

하지만 바로 공격적으로 줄이면
잘못된 auto-apply가 늘 수 있다.

그래서 묻고 싶은 건 아래다.

- 제일 먼저 auto-apply를 넓혀도 되는 family는 무엇인가
- 마지막까지 manual로 남겨야 하는 family는 무엇인가
- `confidence band`를 둔다면 어떻게 자르는 것이 좋은가

---

## 외부 리뷰어가 답해주면 좋은 형식

가능하면 아래 형식으로 답해주길 원한다.

### A. 규칙 분해

예:

- `if active_flat_profit and reversal strong and giveback high -> PARTIAL_EXIT`
- `if open_profit and continuation strong and runner_secured false and partial_ev high -> PARTIAL_THEN_HOLD`

처럼 바로 코드로 옮길 수 있는 룰 형태

### B. threshold 제안

예:

- continuation 최소값
- reversal 우세 margin
- hold_quality 최소값
- partial_exit_ev 최소값
- full_exit_risk 임계값
- giveback / mfe 관련 임계값

### C. precedence 제안

즉 어떤 action이 어떤 action보다 먼저 먹는지

예:

1. `FULL_EXIT`
2. `PARTIAL_THEN_HOLD`
3. `PARTIAL_EXIT`
4. `HOLD`
5. `WAIT`

같은 우선순위 제안

### D. auto-apply / manual-exception 분리 제안

예:

- `FULL_EXIT`는 조건 충족 시 auto
- `PARTIAL_EXIT`는 초기엔 manual
- `HOLD`는 runner-secured + continuation strong일 때만 auto

처럼 실무적인 분리

---

## 우리가 현재 보는 가설

내부적으로는 현재 아래 방향을 유력하게 본다.

1. `WAIT`를 무턱대고 줄이면 안 된다
2. 대신 `active flat-profit row`를 너무 오래 전부 `WAIT`로 두는 것도 비효율적이다
3. `open-profit continuation row`는 `PARTIAL_THEN_HOLD`를 늘릴 여지가 있다
4. `runner_secured`와 `giveback_from_peak`는 앞으로 매우 중요한 규칙 입력이 될 가능성이 높다
5. `HOLD`와 `PARTIAL_EXIT`는 가장 애매하므로 늦게 auto-apply 하는 편이 안전하다

이 가설이 맞는지,
아니면 다른 규칙 구조가 더 좋은지 듣고 싶다.

---

## 아주 짧은 질문 블록

아래 질문에 대한 구현형 답변을 부탁한다.

1. active position이지만 profit이 거의 0인 checkpoint row를 `WAIT`, `PARTIAL_EXIT`, `FULL_EXIT`로 가를 때 가장 좋은 rule set은 무엇인가?
2. open-profit continuation row를 `HOLD`, `PARTIAL_THEN_HOLD`, `PARTIAL_EXIT`로 가를 때 가장 좋은 threshold 조합은 무엇인가?
3. `runner_secured`, `mfe_since_entry`, `giveback_from_peak`, `shock_at_profit`, `checkpoint_type`, `source`를 1급 규칙 입력으로 써야 하는가?
4. 어떤 라벨은 지금 단계에서 auto-apply 해도 안전하고, 어떤 라벨은 manual-exception으로 남겨야 하는가?
5. `manual_exception_count`를 줄이되 과신하지 않으려면 어떤 순서로 rule adoption을 넓히는 것이 좋은가?

가능하면 답변은
**추상적인 설명보다 바로 코드로 옮길 수 있는 rule 형태**
로 부탁한다.

---

## 복붙용 짧은 전달문

아래는 다른 언어모델에 바로 붙여넣을 수 있는 축약 버전이다.

```text
나는 CFD 자동매매 시스템에서 path-aware checkpoint layer를 구현해 두었고,
현재는 checkpoint row마다 management action과 hindsight bootstrap label을
어떤 규칙으로 더 안정적으로 붙일지 조언이 필요합니다.

현재 action taxonomy는
WAIT / HOLD / PARTIAL_EXIT / PARTIAL_THEN_HOLD / FULL_EXIT / REBUY
입니다.

현재 checkpoint row마다 다음 score가 있습니다.
- runtime_continuation_odds
- runtime_reversal_odds
- runtime_hold_quality_score
- runtime_partial_exit_ev
- runtime_full_exit_risk
- runtime_rebuy_readiness

현재 상태 요약:
- resolved_row_count = 6
- position_side_row_count = 3
- manual_exception_count = 5
- hindsight_label_counts = WAIT 5 / PARTIAL_THEN_HOLD 1
- open_profit_row_count = 1
- open_loss_row_count = 0
- runner_secured_row_count = 0

대표 사례:
1. BTCUSD active flat-profit row
   continuation 0.4728
   reversal 0.6960
   hold_quality 0.24516
   partial_exit 0.4120
   full_exit_risk 0.377696
   runtime_proxy PARTIAL_EXIT
   hindsight WAIT

2. NAS100 active flat-profit row
   continuation 0.5088
   reversal 0.5760
   hold_quality 0.29856
   partial_exit 0.4024
   full_exit_risk 0.305216
   runtime_proxy WAIT
   hindsight WAIT

3. NAS100 active open-profit row
   current_profit 0.27
   continuation 0.6958
   reversal 0.4840
   hold_quality 0.44317
   partial_exit 0.50692
   full_exit_risk 0.220956
   runtime_proxy PARTIAL_THEN_HOLD
   hindsight PARTIAL_THEN_HOLD

내가 묻고 싶은 것은:
1. active flat-profit row를 WAIT / PARTIAL_EXIT / FULL_EXIT로 가르는 rule
2. open-profit continuation row를 HOLD / PARTIAL_THEN_HOLD / PARTIAL_EXIT로 가르는 rule
3. runner_secured, mfe_since_entry, giveback_from_peak, shock_at_profit, checkpoint_type, source를 얼마나 강하게 써야 하는지
4. 어떤 라벨을 auto-apply 하고 어떤 라벨을 manual-exception으로 남겨야 하는지
5. manual_exception_count를 줄일 때 가장 안전한 adoption 순서가 무엇인지

추상적인 설명이 아니라,
if/then rule, threshold, precedence 형태로 구현 가능한 답변을 원합니다.
```
