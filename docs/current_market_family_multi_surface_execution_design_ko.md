## Immediate Runtime Correction Before CL

지금은 `continuous operating layer`를 바로 여는 것보다,
현재 runtime에서 반복 관측되는 `wrong-side active-action conflict`를 먼저 교정하는 것이 맞다.

핵심 문제는 센서 부재가 아니다.

- 같은 row 안에서 directional layer는 반대 방향을 보고 있다
- 하지만 old baseline이 이미 `BUY/SELL` 실행 우선권을 쥐고 있다
- candidate bridge는 아직 `baseline_no_action`일 때만 개입한다

즉 현재 병목은 `새로운 판단 부재`가 아니라
`owner precedence + active-action conflict resolution 부재`다.

따라서 `CL1` 이전에 아래 순서를 선행한다.

1. `P0A Wrong-Side Active-Action Conflict Audit`
2. `P0B Active-Action Conflict Guard`
3. `P0C Baseline-vs-Directional Bridge Conflict Resolution`
4. `P0D Wrong-Side Conflict Harvest`
5. `P0E XAU Upper-Reversal Conflict Validation`

### 핵심 설계 원칙: Execution Precedence Layer

현재 필요한 것은 새 feature를 더 붙이는 것이 아니라,
여러 owner가 낸 판단을 실제 실행 전에 한 번 정리하는
`Execution Precedence Layer`다.

```text
[baseline owner]
[directional owner]
[breakout owner]
[state25 / semantic / shadow owner]
        ↓
[conflict resolver / execution precedence layer]
        ↓
[final executable action]
```

즉 각 owner가 action/state/confidence를 낸 뒤,
바로 실행하지 않고 `충돌 정리 -> 강등/유지/승격`을 거친다.

### 핵심 설계 원칙: Override보다 Downgrade 우선

첫 교정은 반대 방향 강제 실행이 아니라,
현재 wrong-side active action을 먼저 낮추는 것이 맞다.

초기 상태기계는 아래 원칙을 따른다.

- `KEEP`
- `WATCH`
- `PROBE`
- `OVERRIDE`

초기 P0에서는 `OVERRIDE`보다 `WATCH/PROBE` 강등을 우선한다.
1차 runtime 적용은 `WATCH` 강등만 실제로 열고,
`PROBE/OVERRIDE`는 trace/log state로만 예약한다.

권장 1차 로그 필드:

- `active_action_conflict_detected`
- `active_action_conflict_guard_eligible`
- `active_action_conflict_guard_applied`
- `active_action_conflict_resolution_state`
- `active_action_conflict_kind`
- `active_action_conflict_baseline_action`
- `active_action_conflict_directional_action`
- `active_action_conflict_directional_state`
- `active_action_conflict_bias_gap`
- `active_action_conflict_reason_summary`

### 핵심 설계 원칙: Bridge Two-Mode

기존 bridge는 `baseline_no_action rescue`에만 강하다.
앞으로는 아래 두 모드를 모두 가진다.

1. `no_action_rescue`
2. `active_action_conflict_resolution`

1차 runtime bridge 구현은 아래 원칙을 따른다.

- actual action이 비어 있어도, `active_action_conflict_guard_v1.baseline_action`으로
  원래 baseline active action을 복원해서 본다
- `active_action_conflict_resolution`에서는 baseline과 반대 방향 candidate만 선택 대상으로 본다
- 즉 P0C의 첫 목적은 반대 방향 실행이 아니라
  `wrong-side active action이 막힌 뒤 어떤 candidate가 남는지`를 row/trace에 남기는 것이다

권장 중간 상태:

- `baseline_action_conflict`
- `conflict_guard_downgrade`
- `directional_override_candidate`

즉 bridge는 단순 candidate picker가 아니라,
`execution precedence resolver`의 일부가 된다.

### 핵심 설계 원칙: Harvest도 같은 구조로 연결

wrong-side conflict는 단순 diagnostic log가 아니라,
다음 rebuild/eval에 들어갈 failure label이어야 한다.

권장 failure taxonomy:

- primary conflict
  - `wrong_side_sell_pressure`
  - `wrong_side_buy_pressure`
- continuation miss
  - `missed_up_continuation`
  - `missed_down_continuation`
- context
  - `false_down_pressure_in_uptrend`
  - `false_up_pressure_in_downtrend`

## Continuous Operating Layer

지금까지의 `PF0 ~ MF17`은 `market-family + multi-surface + bounded rollout gate`를 만드는 단계였다.
즉 후보를 만들고, preview로 평가하고, signoff packet과 activation contract까지 올리는 구조는 이미 갖춰졌다.

다음 단계의 중심은 더 많은 전략 로직을 붙이는 것이 아니라,
아래 운영 루프를 자동으로 닫는 것이다.

```text
runtime rows 누적
-> auto-harvest
-> dataset rebuild
-> preview evaluation refresh
-> candidate package refresh
-> signoff queue refresh
-> manual signoff or hold
-> bounded canary activation
-> canary monitoring
-> downgrade / rollback / stabilize
```

핵심 철학은 다음 세 가지다.

1. `후보 생성`
- candidate는 규칙 조각이 아니라 `symbol + surface + version` 단위의 운영 객체여야 한다.

2. `후보 평가`
- preview eval, failure harvest, market adapter, KPI collector가 모두 동일 candidate identity를 기준으로 묶여야 한다.

3. `후보 운영`
- signoff, canary, rollback, retire까지 같은 lifecycle을 공유해야 한다.

## Candidate Lifecycle

운영층의 기본 단위는 `candidate package`다.

최소 package 필드는 아래와 같다.

- `candidate_id`
- `candidate_version`
- `symbol`
- `surface`
- `scope`
- `created_at`
- `based_on_dataset_version`
- `based_on_eval_version`
- `expected_change_summary`
- `dominant_improvement_metric`
- `dominant_risk_metric`
- `recent_sample_count`
- `top_scene_families`
- `top_failure_labels`
- `activation_recommendation`
- `rollback_trigger_set`
- `status`

권장 status는 아래와 같다.

- `preview_only`
- `ready_for_signoff`
- `canary_live`
- `stable`
- `rolled_back`
- `retired`

## Manual-Exception-Only 방향

장기적으로는 사람이 모든 데이터를 직접 검토하는 구조가 아니라,
애매한 것만 보는 구조가 목표다.

세 버킷으로 나누는 것이 맞다.

1. `auto_apply`
- clear failure harvest
- obvious negative continuation sample
- high-confidence label apply

2. `manual_exception`
- signoff 직결 candidate
- watch/probe 경계
- drift 급증
- new scene family

3. `diagnostic_only`
- sample 부족
- 개선 효과 불명확
- regime drift 중 생성된 임시 후보

## Symbol-Specific Observability

shared surface를 유지하더라도, 관측은 symbol별로 분리되어야 한다.

필수 registry는 아래 네 가지다.

- `symbol_surface_registry`
- `symbol_transition_registry`
- `symbol_scene_family_registry`
- `symbol_drift_registry`

## Surface KPI and Canary Control

운영층에서는 `PnL 하나`로 판단하지 않는다.
surface별 KPI와 canary 가드가 함께 필요하다.

## LLM Layer Role

LLM은 승인자가 아니라 설명 계층이어야 한다.

# Current Market-Family Multi-Surface Execution Design

## 목적

이 문서는 현재 CFD 실행 시스템의 과잉 차단 문제를
`단일 진입 점수` 관점이 아니라
`시장별 특성 + 상황별 surface 분리` 관점으로 다시 정의한다.

핵심 문제는 단순히 "threshold가 높다"가 아니다.

> 지금 시스템은 완전 좋은 것만 들어가고,
> 그 다음 괜찮은 follow-through, continuation, runner 보존 구간을
> 과하게 기다리거나 너무 빨리 잘라내는 경향이 있다.

따라서 다음 단계는 점수 하나를 더 잘 만드는 것이 아니라,
서로 다른 시장과 서로 다른 실행 상황을
서로 다른 surface로 분리해서 다루는 것이다.

---

## 왜 새 축이 필요한가

최근 실행 로그를 보면 같은 문제처럼 보여도 시장별 병목이 다르다.

기준: [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)

- `NAS100`
  - 최근 80행 전부 `wait`
  - 전부 `observe_state_wait`
  - 대표 observe: `conflict_box_upper_bb20_lower_upper_dominant_observe`
- `BTCUSD`
  - 최근 80행 전부 `wait`
  - `observe_state_wait`가 다수
  - 일부 `middle_sr_anchor_guard`
- `XAUUSD`
  - 최근 80행 전부 `wait`
  - 전부 `outer_band_guard + probe_not_promoted`
  - 대표 observe: `outer_band_reversal_support_required_observe`

최신 구현 반영 상태:

- `MF5` runtime split 반영 후
  fresh entry row에서 market-family별 surface가 실제로 기록되기 시작함
- `2026-04-09 01:58 KST` 재기동 이후
  [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
  recent row 기준
  - `XAUUSD -> follow_through_surface / pullback_resume`
  - `BTCUSD -> initial_entry_surface / timing_better_entry`
  가 실제 append됨
- `MF7` 1차 bounded bridge도 운영 경로에 반영되어,
  XAU follow-through 구간을 전부 같은 wait로 보지 않고
  별도 surface로 추적할 수 있는 상태가 됨

즉 지금 문제는 "전 시장 공통 threshold 완화"가 아니다.
각 시장이 막히는 위치와 이유가 다르다.

---

## 단일 점수 체계의 한계

지금처럼 `좋은 진입 점수` 하나로 시스템을 몰아가면 아래 문제가 생긴다.

- 초기 진입만 잘 잡고 추종 구간은 다 놓친다
- 되돌림 후 재개와 초기 돌파를 같은 언어로 섞어버린다
- runner를 보존해야 하는 장면과 빠른 보호청산 장면을 구분하지 못한다
- NAS / BTC / XAU의 다른 미시 구조를 한 모델이 평평하게 눌러버린다

사용자가 차트에서 직접 체크와 색깔을 구분해 둔 이유도 여기에 있다.
그 구분은 단순 시각 보조가 아니라, 서로 다른 실행 상황을 나누는 약한 라벨이다.

따라서 이 체크/색 시스템은 버릴 것이 아니라
`학습 가능한 다중 surface 라벨 체계`로 승격해야 한다.

---

## 현재 핵심 진단

### 1. Entry는 "좋은 것만" 연다

XAU 기준 최근 비교:

- 실제 체결 2건
  - `2026-04-09 00:15:30` BUY
  - `2026-04-09 00:29:12` BUY
- 두 건 모두 `range_lower_reversal_buy`
- 둘 다 `core_shadow_probe_action`
- 둘 다 `ready_for_entry = true`
- 둘 다 `structural_relief_applied = true`

반면 같은 계열 XAU 최근 wait row는:

- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`
- `ready_for_entry = false`
- `structural_relief_applied = false`
- `same_side_barrier`가 높다

즉 XAU는 "신호를 못 본다"보다
`좋은 장면은 열지만, follow-through 후보를 너무 많이 observe/wait로 묶는다`가 더 정확하다.

### 2. Exit는 runner를 빨리 자른다

기준: [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)

- `2026-04-09 00:15:30` XAU BUY
  - `00:17:32`에 `Target` 종료
  - `+258pt`
- `2026-04-09 00:29:12` XAU BUY
  - `00:31:12`에 `Lock Exit / profit_giveback` 종료
  - `+194pt`

사용자 관찰대로 이후 가격이 더 갔다면,
이건 "진입은 맞았는데 연장을 너무 빨리 포기한 것"에 가깝다.

### 3. 시장별로 다른 문제를 같은 점수로 해결하면 안 된다

- `NAS100`
  - no-action / observe 과다
- `BTCUSD`
  - observe + middle anchor 정체
- `XAUUSD`
  - probe는 보지만 outer-band / promotion이 과도하게 보수적

---

## 새 설계 원칙

### 원칙 1. 시장별 family를 분리한다

최소한 아래 세 family를 독립 surface로 본다.

- `NAS100`
- `BTCUSD`
- `XAUUSD`

필요하면 이후 `symbol + scene family`까지 더 세분화한다.

### 원칙 2. 실행 상황을 surface로 분리한다

최소 surface는 아래 4개다.

1. `initial_entry_surface`
   - 처음 들어갈지
2. `follow_through_surface`
   - 이미 방향성이 맞는 뒤 구간에서 추가 기회를 줄지
3. `continuation_hold_surface`
   - runner를 계속 들고 갈지
4. `protective_exit_surface`
   - 진짜 위험이어서 보호청산할지

즉 `entry / wait / exit`를 한 줄로 배우는 대신,
실행 단계를 나눠서 서로 다른 owner와 라벨을 둔다.

### 원칙 3. 체크/색깔은 약한 supervision으로 승격한다

차트에서 사람이 구분한 체크/색 정보는
다음 라벨 축으로 변환할 수 있다.

- `initial_break`
- `reclaim`
- `continuation`
- `pullback_resume`
- `runner_hold`
- `protect_exit`
- `failed_follow_through`

즉 시각적 구분을 데이터 구조로 올리는 것이다.

### 원칙 4. 단일 owner가 아니라 bounded multi-owner로 간다

지금처럼 baseline만 owner이고 semantic/state25/shadow/breakout이 조언만 하는 구조를
한 번에 뒤집지는 않는다.

대신 각 surface에 대해 bounded consumer를 붙인다.

예:

- `initial_entry_surface`
  - baseline / probe / breakout candidate
- `follow_through_surface`
  - breakout / continuation / state25 hint
- `continuation_hold_surface`
  - exit orchestrator 안의 runner-preserve layer
- `protective_exit_surface`
  - hard risk / recovery / protect 정책

### 원칙 5. 글로벌 완화 대신 market-family bounded bridge를 쓴다

예를 들면 XAU는 전역 threshold 완화가 아니라
`outer_band_guard`의 중간 barrier 구간만 bounded probe로 살리는 식으로 간다.

현재 적용 예:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
  에 `bounded_xau_outer_band_followthrough_probe`,
  `xau_outer_band_follow_through` relief가 반영되어 있음
- 즉 XAU는 "전역 진입 완화"가 아니라
  `outer_band_guard + supportive probe plan + bounded barrier`
  조합에서만 제한적으로 follow-through 후보를 살리는 방향으로 감

### 원칙 6. Surface는 상태 분류가 아니라 목적 함수다

surface를 나눴다면,
각 surface가 무엇을 최적화하는지까지 같이 정의해야 한다.

- `initial_entry_surface`
  - 진입 후 일정 구간에서 `+EV`인지
- `follow_through_surface`
  - 이미 열린 방향을 추가 확장할 가치가 있는지
- `continuation_hold_surface`
  - 지금 들고 있는 포지션이 더 갈 확률이 반전 확률보다 높은지
- `protective_exit_surface`
  - 지금 안 자르면 손실 확대 또는 giveback 확대인지

즉 surface는 "상태 이름"이 아니라
서로 다른 목표 함수를 가진 실행 단위다.

### 원칙 7. Promotion gate는 절대 score보다 상대 분포를 우선 본다

시장마다 scale이 다르고,
상황마다 score 의미도 다르다.

그래서 장기적으로는

- `score > x` 같은 절대 문턱

보다

- 같은 market-family / 같은 scene cluster 안에서
  현재 row가 기대값 분포상 어디에 있는지

를 더 강하게 보아야 한다.

즉 gate는 점차
`절대값 threshold`에서
`상대 위치 percentile / cluster-relative rank`
로 이동해야 한다.

### 원칙 8. Do-Nothing도 의사결정으로 모델링한다

현재 시스템의 강점 중 하나는 wait/observe를 많이 본다는 점이다.
하지만 이걸 단순 "아무 것도 안 함"으로 두면 안 된다.

반드시 아래 축을 같이 봐야 한다.

- `do_nothing_ev`
- `enter_ev`
- `probe_ev`
- 필요 시 `runner_hold_ev`

즉 wait도 passive default가 아니라
"지금 안 하는 게 최선인가"를 판단하는 action이어야 한다.

### 원칙 9. Surface는 상태 + 시간이다

breakout, follow-through, continuation hold는 전부 시간 문제다.

따라서 snapshot만으로는 부족하고,
최소 아래 시간 축을 같이 둬야 한다.

- `time_since_breakout`
- `time_since_entry`
- `bars_in_state`
- `momentum_decay`
- `time_since_last_relief`

즉 같은 상태라도 시간축이 다르면 다른 판단이 나와야 한다.

### 원칙 10. 시장별 모델 분리보다 market adapter를 우선 쓴다

지금 단계에서는

- NAS 전용 모델
- BTC 전용 모델
- XAU 전용 모델

처럼 완전 분리하는 것보다,

- 공통 surface
- 공통 목적 함수
- `market_family` feature 또는 bounded adapter

구조가 더 낫다.

이유:

- 데이터 부족 방지
- 일반화 유지
- 유지보수 단순화
- 새로운 family 추가 시 확장성 확보

### 원칙 11. Countertrend / Continuation은 BUY/SELL보다 먼저 UP/DOWN으로 본다

현재 XAU 하락 continuation 경로는
`anti-buy evidence -> SELL candidate`
형태의 bootstrap으로 먼저 들어가 있다.

하지만 이 구조를 최종 형태로 고정하면
시스템이 하락 continuation에만 편향될 위험이 있다.

따라서 다음 일반화 원칙을 명시한다.

- 내부 증거는 `BUY/SELL`보다 먼저
  `UP/DOWN` 방향 언어로 정리한다
- 현재 XAU 경로는 `DOWN bootstrap`으로 유지하되
  이후 `UP symmetry`까지 확장한다
- 최종 실행층에서만
  `UP_ENTER -> BUY`
  `DOWN_ENTER -> SELL`
  로 변환한다

즉 앞으로 continuation 계층은
`반대 매매`
가 아니라
`방향 독립(direction-agnostic) 상태기계`
로 설계한다

### 원칙 12. SELL-specific 확장은 금지하고 dual-write migration으로 간다

지금 운영 중인 XAU down-continuation 경로는
실험적 bootstrap이다.

따라서 다음 migration 원칙을 둔다.

- 기존
  `countertrend_continuation_*`
  필드는 즉시 제거하지 않는다
- 동시에 새 필드로
  `anti_long_score`
  `anti_short_score`
  `pro_up_score`
  `pro_down_score`
  를 추가한다
- 기존 XAU down bootstrap은
  먼저 `DOWN_WATCH / DOWN_PROBE / DOWN_ENTER`
  쪽으로 매핑한다
- fresh runtime 관측이 쌓인 뒤에야
  `UP_WATCH / UP_PROBE / UP_ENTER`
  대칭 경로를 같은 surface에 올린다

즉 migration은
`바로 전면 치환`
이 아니라
`dual-write -> DOWN 검증 -> UP 확장 -> 실행층 연결`
순서로 간다

---

## 핵심 surface 정의

## 1. Initial Entry Surface

역할:

- baseline 첫 진입
- probe 승격
- breakout 초기 진입

주요 입력:

- baseline score
- utility gate
- probe plan
- breakout candidate
- semantic/state25 hint

현재 병목:

- NAS/BTC는 no-action / observe가 너무 많다
- XAU는 outer-band / probe_not_promoted가 많다

목표 함수:

- `entry_forward_ev`
- `entry_regret_if_wait`
- `entry_false_positive_cost`

## 2. Follow-Through Surface

역할:

- 이미 방향이 맞는 뒤,
  추가 진입 또는 소형 추종 진입을 허용할지 판단

이 surface가 필요한 이유:

- 사용자는 "타점 자체는 좋았는데 그 이후 추가 기회를 너무 놓친다"를 확인했다
- 현재 시스템은 initial 진입만 허용하고,
  follow-through를 거의 `wait_more`로 눌러버린다
- 또한 현재 XAU down bootstrap처럼
  기존 반등 BUY family를 막은 뒤
  continuation 방향 후보를 따로 표기해야 하는 장면이 있다

주요 입력:

- breakout continuation
- barrier drag
- confirm alignment
- follow-through maturity
- probe runner state
- continuation direction evidence
- rebound-failure / reject-failure evidence

목표 함수:

- `follow_through_extension_ev`
- `miss_if_wait_cost`
- `late_follow_through_penalty`
- `wrong_direction_escalation_cost`

## 3. Continuation Hold Surface

역할:

- 이미 진입한 포지션을
  계속 들고 갈지
  partial만 할지
  runner를 보존할지
  판단

이 surface가 필요한 이유:

- XAU는 진입 후 더 갔는데도
  `Target`, `Lock Exit`, `profit_giveback`으로 너무 빨리 잠근다

주요 입력:

- continuation quality
- barrier after entry
- trend spread
- giveback risk
- exit maturity

목표 함수:

- `runner_hold_ev`
- `runner_giveback_risk`
- `partial_then_hold_ev`

기본 행동 후보:

- `HOLD_RUNNER`
- `PARTIAL_THEN_HOLD`
- `LOCK_PROFIT`

## 4. Protective Exit Surface

역할:

- 진짜 위험일 때만 강하게 자르는 layer

이 surface는 continuation hold surface와 분리해야 한다.
그렇지 않으면 "조금 흔들림"도 모두 보호청산으로 오해한다.

목표 함수:

- `protect_exit_loss_avoidance_ev`
- `protect_exit_false_cut_cost`

기본 행동 후보:

- `EXIT_PROTECT`
- `PARTIAL_REDUCE`
- `WAIT_MORE`

---

## EV / 분포 기반 판단 원칙

현재는 일부 구간에서 threshold가 실무적으로 필요하지만,
다음 구조는 아래 방향으로 이동해야 한다.

1. 절대 점수
   - `score > x`
2. cluster-relative 분포
   - 같은 market-family / 같은 scene / 같은 surface 안에서
     현재 row가 상위 몇 %인지
3. proxy EV 비교
   - `do_nothing_ev`
   - `probe_ev`
   - `enter_ev`
   - `runner_hold_ev`

즉 장기적으로는
"문턱을 넘었냐"보다
"지금 가능한 선택지 중 어느 쪽의 기대값이 더 크냐"를 보는 구조로 가야 한다.

---

## 시간 축 설계

surface별로 다음 시간 feature를 공통 축으로 도입한다.

- `time_since_breakout`
- `time_since_entry`
- `bars_in_state`
- `bars_since_probe_activation`
- `momentum_decay`
- `time_since_last_barrier_relief`
- `bars_since_rebound_failure`
- `bars_since_reject_failure`
- `continuation_persistence_bars`

예:

- `initial_breakout + 1~3 bar`
  - follow-through 의미가 강함
- 같은 구조라도 `10 bar`가 지나면
  - initial 의미는 약해지고 continuation 해석으로 넘어가야 함

---

## Direction-Agnostic Countertrend / Continuation State Machine

현재 XAU 하락 continuation 경로는
실무적으로 필요한 bootstrap이지만,
최종 구조는 아래처럼 대칭이어야 한다.

### Evidence Layer

반드시 두 종류의 증거를 분리한다.

- 방향 반대 thesis 증거
  - `anti_long_score`
  - `anti_short_score`
- 방향 continuation 증거
  - `pro_up_score`
  - `pro_down_score`

중요:

- `anti_long_score`는
  "지금 롱 thesis가 약하다"는 뜻이지
  곧바로 `SELL_ENTER`를 뜻하지 않는다
- `pro_down_score`는
  "실제로 아래 continuation 실행 가치가 있다"는 뜻이다
- 이 둘은 서로 대체물이 아니라
  별도 점수로 남아야 한다

### State Layer

실행 전 단계 상태는 최소 아래처럼 둔다.

- `DO_NOTHING`
- `UP_WATCH`
- `DOWN_WATCH`
- `UP_PROBE`
- `DOWN_PROBE`
- `UP_ENTER`
- `DOWN_ENTER`

의미:

- `WATCH`
  - 반대 thesis는 약하지만
    실행 continuation 근거는 아직 약한 상태
- `PROBE`
  - continuation 구조가 일부 확인되어
    bounded small-size 후보가 되는 상태
- `ENTER`
  - continuation 구조, 시간축, guard 정렬이 모두 맞아
    bounded live 실행 후보가 되는 상태

### Execution Mapping

실행층에서는 마지막에만 방향을 주문 방향으로 변환한다.

- `UP_ENTER -> BUY`
- `DOWN_ENTER -> SELL`
- `DO_NOTHING`은 독립 action으로 유지

즉 시스템은
`BUY/SELL`을 먼저 고르는 것이 아니라
`UP/DOWN continuation 상태`
를 먼저 만든 뒤
실행층에서만 주문 언어로 바꾼다.

### Symmetric Feature Contract

DOWN continuation proto feature:

- `recent_lower_low_count`
- `recent_lower_high_count`
- `bb20_mid_reclaim_failed`
- `same_side_down_follow_through_strength`
- `break_below_local_support_recent`
- `bars_since_rebound_failure`

UP continuation proto feature:

- `recent_higher_high_count`
- `recent_higher_low_count`
- `bb20_mid_reject_failed`
- `same_side_up_follow_through_strength`
- `break_above_local_resistance_recent`
- `bars_since_reject_failure`

즉 하락용 SELL 로직을 복붙하는 것이 아니라,
위/아래가 대칭인 continuation evidence contract를 만들어야 한다.

### Bootstrap Strategy

현재 운영 경로는 아래 순서로 확장한다.

1. 현재 XAU down continuation path를
   `DOWN bootstrap`으로 유지
2. fresh runtime에서
   `countertrend_continuation_*`
   materialization을 먼저 검증
3. dual-write로
   `anti_long / anti_short / pro_up / pro_down`
   를 추가
4. `DOWN_*` 상태를 먼저 안정화
5. 이후 같은 surface에
   `UP_*` 대칭 경로를 추가

즉 지금 필요한 것은
SELL 로직 확대가 아니라
`direction-agnostic continuation owner`로 가는
안전한 이행 경로다.

---

## 실패 케이스도 독립 라벨로 본다

성공 케이스만으로는 guard가 보수적으로만 진화하기 쉽다.

반드시 실패 라벨도 수집해야 한다.

- `failed_follow_through`
- `false_breakout`
- `early_exit_regret`
- `late_entry_chase_fail`
- `missed_good_wait_release`

이 실패 라벨은

- MF2 체크/색 formalization
- MF10 multi-surface dataset export

에서 같이 쓰인다.

---

## 시장별 1차 과제

## NAS100

문제:

- observe_state_wait 과다
- conflict family를 너무 넓게 wait로 눌러버림

과제:

- `conflict_box_*` family 분해
- no-action에서 follow-through 가능한 장면 분리
- `WAIT`와 `WATCH`를 분리

## BTCUSD

문제:

- middle anchor / observe 정체
- bounded probe promotion 여지가 있으나 아직 좁다

과제:

- `middle_sr_anchor_guard` 완화 조건 정밀화
- observe에서 probe로 올라가는 bridge 강화
- 추세/반등 장면을 분리

## XAUUSD

문제:

- outer-band guard가 너무 강함
- 좋은 initial entry 이후 follow-through와 runner hold를 놓침
- down continuation 장면을
  아직 SELL-specific bootstrap으로만 보기 시작한 상태

과제:

- `outer_band_guard` bounded bridge
- `probe_not_promoted` 중 moderate barrier 구간만 소형 probe로 승격
- `profit_giveback / lock exit / target`의 runner 보존형 완화
- current XAU down bootstrap을
  `DOWN_WATCH / DOWN_PROBE / DOWN_ENTER`
  상태로 정규화
- 이후 up/down 대칭 continuation evidence를 같은 surface에 통합

---

## 데이터와 라벨 원천

이 트랙은 아래 자산을 같이 쓴다.

- runtime rows
  - [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
- closed trade history
  - [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)
- breakout canonical seed / preview dataset
  - [breakout_aligned_training_seed_latest.csv](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/breakout_event/breakout_aligned_training_seed_latest.csv)
  - [breakout_shadow_preview_training_set_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/breakout_shadow_preview_training_set_latest.json)
- manual truth / calibration outputs
- 차트 체크 / 색 / scene 구분

추가 라벨 원천:

- `trade_closed_history` 기반 early-exit regret 후보
- breakout historical calibration bridge
- runner 보존 실패 retrospective
- do-nothing 대비 regret 비교 row

즉 이 문서의 방향은 "새로 모든 걸 만들자"가 아니라,
이미 있는 수동 구분과 runtime detail을
시장별/상황별 학습 surface로 재조립하자는 것이다.

---

## 구현 삽입 지점

### Entry

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)

### Breakout / Follow-through

- [breakout_event_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_runtime.py)
- [breakout_event_overlay.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_overlay.py)

### Exit / Runner Preservation

- [exit_manage_positions.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_manage_positions.py)
- [exit_execution_orchestrator.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_execution_orchestrator.py)

---

## 성공 기준

### Entry

- NAS/BTC/XAU가 모두 "최근 80행 전부 wait" 상태를 벗어난다
- `WAIT`만이 아니라 `WATCH / PROBE / ENTER`가 분포를 가진다

### Follow-through

- XAU처럼 좋은 initial entry 뒤 구간에서
  전부 `outer_band_guard + probe_not_promoted`로만 끝나지 않는다

### EV / gate

- `WAIT_MORE`가 단순 default가 아니라
  `do_nothing_ev` 기반 선택으로 남는다
- 최소 일부 gate는 절대 threshold가 아니라
  cluster-relative 분포 기반으로 판단된다

### Exit

- 좋은 진입 뒤 최소 일부는
  `full exit` 대신 `partial + runner hold`가 생긴다

### Failure learning

- `failed_follow_through / false_breakout / early_exit_regret`
  같은 실패 라벨이 최소 일부 dataset에 materialize된다

### Learning

- 단일 점수가 아니라
  `initial / follow-through / hold / protect`
  별 preview dataset이 따로 생긴다

---

## 한 줄 결론

다음 단계의 핵심은
`좋은 진입 점수 하나를 더 날카롭게 만들기`가 아니다.

> NAS / BTC / XAU가 서로 다른 이유로 막히는 현실을 받아들이고,
> 초기 진입 / follow-through / runner hold / protective exit를
> 서로 다른 surface로 분리해서 배우고 실행하게 만드는 것

이 설계가 있어야
하나의 완벽한 타점에만 몰리지 않고,
여러 시장과 여러 상황 속의 좋은 정보를 살아 있게 만들 수 있다.
