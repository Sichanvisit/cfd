# BC1 State25 Context Bridge Skeleton 상세 계획

## 목표

`BC1`의 목적은 `state25_context_bridge.py`를 **실제 보정기 이전의 안정적인 skeleton**으로 먼저 세우는 것이다.

이번 단계에서는:
- context intake
- freshness / gating
- component activation
- overlap guard 기본 틀
- trace / failure / guard mode 기본 출력

까지를 구현한다.

즉 이번 단계는
**weight / threshold / size를 실제로 조정하는 단계가 아니라, 나중 번역기가 안전하게 들어갈 자리와 trace 뼈대를 먼저 고정하는 단계**다.


## 왜 BC1이 먼저 필요한가

지금 문서는 이미 `weight / threshold / size` 번역 원칙이 정리되어 있지만,
바로 translator부터 넣으면 아래 문제가 생길 수 있다.

- freshness 처리 위치가 흔들림
- overlap guard가 translator마다 제각각 붙음
- suppression / failure / guard mode가 통일되지 않음
- trace 구조가 나중에 계속 바뀜

그래서 BC1에서는 먼저 공통 골격을 고정한다.


## 이번 단계 범위

이번 `BC1`에서 구현할 것:

- `backend/services/state25_context_bridge.py`
- contract version 상수
- 기본 contract builder
- intake normalization
- freshness state 계산
- component activation / component activation reasons
- overlap source normalize
- failure / guard mode 기본 판정
- trace skeleton
- decision counterfactual placeholder
- linkage / override scope placeholder

이번 단계에서 하지 않을 것:

- 실제 weight delta 계산
- 실제 threshold delta 계산
- 실제 size delta 계산
- runtime export 합류
- detector/propose 연결
- bounded live rollout


## 구현 원칙

### 1. translator보다 trace를 먼저 고정한다

BC1은 “무엇을 얼마나 바꿀까”보다,
“무엇을 읽었고 왜 아직 안 바꿨는가”를 남기는 단계다.

### 2. component별 activation을 coarse skip보다 우선한다

예:

- HTF는 FRESH면 1.0
- previous_box는 LOW_CONFIDENCE + AGING이면 0.5
- share는 BOOSTER_ONLY라 0.2

이 구조를 먼저 깔아두면 BC2 이후 translator가 훨씬 단순해진다.

### 3. failure와 guard를 분리한다

`STALE_CONTEXT_SUPPRESSED`는 failure 성격이고,
`DOUBLE_COUNTING_SUPPRESSED`는 guard 성공 성격이다.

BC1부터 이 둘을 분리해서 출력한다.

### 4. decision counterfactual만 자리 확보한다

`outcome counterfactual`은 BC1에서 계산하지 않는다.
지금은 schema 자리만 열고, 실제 판단 변화 비교용 필드만 placeholder로 둔다.


## 입력 스키마

BC1 skeleton은 아래 입력을 읽을 수 있어야 한다.

### 기본 입력
- `symbol`
- `entry_stage`
- `consumer_check_side`
- `signal_timeframe`

### interpreted context
- `htf_alignment_state`
- `htf_against_severity`
- `previous_box_break_state`
- `previous_box_confidence`
- `previous_box_is_consolidation`
- `context_conflict_state`
- `late_chase_risk_state`
- `cluster_share_symbol_band`

### freshness 입력
- `trend_1h_age_seconds`
- `trend_4h_age_seconds`
- `trend_1d_age_seconds`
- `previous_box_age_seconds`

### overlap 입력
- `forecast_state25_runtime_bridge_v1`
- `belief_state25_runtime_bridge_v1`
- `barrier_state25_runtime_bridge_v1`
- `countertrend_continuation_signal_v1`


## 출력 스키마

BC1은 아래 구조를 안정적으로 반환해야 한다.

### meta
- `contract_version`
- `bridge_stage`
- `translator_state`

### normalized intake
- `context_inputs`
- `freshness`
- `component_activation`
- `component_activation_reasons`

### placeholder adjustment outputs
- `weight_adjustments_requested`
- `weight_adjustments_effective`
- `weight_adjustments_suppressed`
- `threshold_adjustment_requested`
- `threshold_adjustment_effective`
- `threshold_adjustment_suppressed`
- `size_adjustment_requested`
- `size_adjustment_effective`
- `size_adjustment_suppressed`

### placeholder rationale
- `context_bias_side`
- `context_bias_side_confidence`
- `context_bias_side_source_keys`
- `size_adjustment_state`

### guard / failure
- `double_counting_guard_active`
- `overlap_sources`
- `overlap_class`
- `stacking_limited`
- `failure_modes`
- `guard_modes`

### trace
- `caps_applied`
- `trace_reason_codes`
- `trace_lines_ko`
- `decision_counterfactual`
- `bridge_decision_id`
- `hindsight_link_key`
- `proposal_link_key`
- `override_scope`
- `override_scope_detail`


## freshness / activation 기준

### HTF

- age max가 작으면 `FRESH`
- 중간이면 `AGING`
- 크면 `STALE`

BC1에서는 보수적으로:
- `FRESH` -> activation `1.0`
- `AGING` -> activation `0.5`
- `STALE` -> activation `0.0`

### previous_box

- `HIGH / MEDIUM` confidence + fresh -> `1.0`
- `LOW_CONFIDENCE` 또는 `AGING` -> `0.5`
- `STALE` 또는 `is_consolidation = false` -> `0.0` 또는 강한 약화

### late_chase

- `late_chase_risk_state != NONE` -> `1.0`
- 아니면 `0.0`

### share

- share는 `BOOSTER_ONLY`
- band가 있으면 `0.2`
- 없으면 `0.0`


## overlap guard 기준

BC1에서는 overlap을 “읽고 분류”까지만 한다.

### overlap source normalize

다음 소스가 존재하면 `overlap_sources`에 넣는다.

- forecast
- belief
- barrier
- countertrend continuation

### overlap_class 기본값

BC1에서는 상세 해석보다 기본 분류만 둔다.

- forecast/belief/barrier가 있으면 `RISK_DUPLICATE`
- countertrend continuation이 있으면 `CONTINUATION_DUPLICATE`
- 아무것도 없으면 빈 문자열


## trace 원칙

BC1 trace는 아래를 보장해야 한다.

1. 무엇을 읽었는지
2. freshness가 어땠는지
3. activation이 왜 그렇게 나왔는지
4. 왜 아직 translator가 비활성인지
5. 어떤 guard/failure가 감지됐는지

즉 BC1 trace는 “무엇을 조정했는가”가 아니라
**“왜 아직 조정하지 않았고, BC2에서 무엇을 읽을 준비가 되었는가”**를 보여주는 trace다.


## 완료 기준

- `state25_context_bridge.py`가 안정적인 기본 contract를 반환한다
- 빈 row에서도 깨지지 않는다
- HTF / previous_box / late_chase / share activation이 계산된다
- overlap/failure/guard mode가 기본적으로 채워진다
- trace가 사람과 코드 양쪽에 읽히는 형태로 나온다


## 다음 단계 연결

BC1 다음은 자연스럽게:

1. `BC2 Weight-Only Translator`
2. `BC3 Runtime Trace Export`

즉 BC1은 bridge를 **작동시키는 단계가 아니라, 안전하게 작동시킬 준비를 끝내는 단계**다.
