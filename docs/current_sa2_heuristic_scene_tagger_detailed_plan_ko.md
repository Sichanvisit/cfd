# Current SA2 Heuristic Scene Tagger Detailed Plan

## 목적

`SA2`의 목적은 기존 `checkpoint row` 위에 첫 번째 `scene tag`를 실제로 붙이기 시작하는 것이다.

이 단계에서 가장 중요한 원칙은 아래 3개다.

1. `scene`은 기록과 설명의 층이지, 아직 `action`을 직접 바꾸는 층이 아니다.
2. `SA2`는 `model`이 아니라 `heuristic seed`로 시작한다.
3. `SA2`는 모든 22개 장면을 다루지 않고, 행동 차이가 분명한 starter set 5개만 먼저 연다.

즉 이 단계는

```text
checkpoint row가 생긴다
-> score가 붙는다
-> heuristic scene tag가 붙는다
-> 기존 action resolver는 그대로 돈다
```

까지를 만드는 단계다.

---

## 이번 단계에서 하는 것 / 안 하는 것

### 하는 것

- `checkpoint row`에 실제 `runtime_scene_*` 값을 채운다
- `starter scene/gate 5개`를 heuristic으로 태그한다
- `scene_confidence_band`, `scene_maturity`, `scene_action_bias_strength`, `scene_family_alignment`, `scene_gate_block_level`을 같이 채운다
- `previous runtime scene`을 읽어 최소 수준의 `transition`도 같이 남긴다
- 모든 결과를 `log-only`로 기록한다

### 안 하는 것

- `scene`이 `management_action_label`을 직접 바꾸게 하지 않는다
- `candidate model`이나 `promote loop`를 아직 붙이지 않는다
- `scene dataset export` 전용 artifact는 아직 만들지 않는다
- 22개 전체 scene을 한 번에 열지 않는다

---

## starter set 5개

이번 SA2에서 실제로 태그하는 대상은 아래 5개다.

### fine scene 4개

- `trend_exhaustion`
- `time_decay_risk`
- `liquidity_sweep_reclaim`
- `breakout_retest_hold`

### gate 1개

- `low_edge_state`

이 5개를 고른 이유는 단순하다.

- 현재 row에 이미 있는 필드만으로 보수적으로 판정 가능하다
- 장면과 행동의 차이가 비교적 선명하다
- 나중에 `SA6 action bias`로 연결할 때도 의미가 분명하다

---

## 변경 파일

### 신규 파일

- [path_checkpoint_scene_tagger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_tagger.py)
- [test_path_checkpoint_scene_tagger.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_scene_tagger.py)

### 연동 파일

- [path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)
- [test_path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_context.py)

### 참고 파일

- [path_checkpoint_scene_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_contract.py)
- [path_checkpoint_scoring.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scoring.py)
- [path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)

---

## 핵심 입력 필드

SA2는 새 feature를 상상해서 쓰지 않는다.
지금 이미 checkpoint row에 저장되고 있는 값만 쓴다.

### 구조/문맥 필드

- `surface_name`
- `checkpoint_type`
- `bars_since_leg_start`
- `bars_since_last_push`
- `bars_since_last_checkpoint`
- `position_side`
- `unrealized_pnl_state`
- `runner_secured`
- `checkpoint_rule_family_hint`
- `exit_stage_family`

### score 필드

- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`
- `runtime_rebuy_readiness`
- `runtime_score_reason`

### raw reason 필드

- `blocked_by`
- `action_none_reason`
- `consumer_check_reason`
- `setup_reason`
- `entry_candidate_bridge_mode`
- `observe_action`
- `observe_side`

### position/path 필드

- `current_profit`
- `mfe_since_entry`
- `mae_since_entry`
- `giveback_from_peak`
- `giveback_ratio`

---

## heuristic 규칙

## 1. `trend_exhaustion`

### 목적

아직 완전히 실패한 건 아니지만, 후반 leg에서 힘이 빠지고 일부 확보 쪽으로 읽어야 하는 장면을 태그한다.

### 기본 조건

- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `bars_since_leg_start >= symbol threshold`
- `runtime_partial_exit_ev >= 0.56`
- `runtime_continuation_odds >= runtime_reversal_odds - 0.02`
- `runtime_full_exit_risk < 0.74`
- 아래 중 하나 이상
  - `runner_secured = true`
  - `giveback_ratio >= 0.18`
  - `source / score_reason`에 `runner`, `late`, `lock` 성격이 보임

### symbol threshold

- `BTCUSD`: 10 bars
- `XAUUSD`: 8 bars
- `NAS100`: 8 bars

### confidence 예시

- base `0.56`
- `bars_since_leg_start >= threshold + 2`면 `+0.08`
- `runtime_partial_exit_ev >= 0.62`면 `+0.10`
- `giveback_ratio >= 0.25`면 `+0.06`
- `runner_secured = true`면 `+0.06`

### 출력

- `runtime_scene_coarse_family = DEFENSIVE_EXIT`
- `runtime_scene_fine_label = trend_exhaustion`
- `runtime_scene_modifier_json = {"late_trend": true}`

---

## 2. `time_decay_risk`

### 목적

틀렸기 때문이 아니라, 너무 오래 안 가는 포지션이라서 효율상 나가야 하는 장면을 태그한다.

### 기본 조건

- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `bars_since_leg_start >= symbol time-decay threshold`
- `unrealized_pnl_state in {FLAT, OPEN_LOSS}` 또는 `current_profit`이 매우 작음
- `runtime_hold_quality_score <= 0.42`
- `runtime_continuation_odds <= 0.58`
- `runtime_score_reason`이 `balanced_checkpoint_state` 계열이거나, `hold`은 약하고 `exit`도 아주 강하지 않은 상태

### symbol threshold

- `BTCUSD`: 30 bars
- `XAUUSD`: 20 bars
- `NAS100`: 15 bars

### confidence 예시

- base `0.60`
- `bars_since_leg_start >= threshold + 3`면 `+0.10`
- `unrealized_pnl_state = FLAT`면 `+0.08`
- `runtime_hold_quality_score <= 0.30`면 `+0.06`

### 출력

- `runtime_scene_coarse_family = POSITION_MANAGEMENT`
- `runtime_scene_fine_label = time_decay_risk`
- `runtime_scene_modifier_json = {}`

---

## 3. `liquidity_sweep_reclaim`

### 목적

잘못된 방향 압박이나 reclaim형 복귀가 감지되는 장면을 entry 계열 scene으로 기록한다.

### 기본 조건

- `checkpoint_type in {FIRST_PULLBACK_CHECK, RECLAIM_CHECK}`
- reason blob에 아래 중 하나 이상
  - `wrong_side`
  - `active_action_conflict_guard`
  - `sweep`
  - `reclaim`
- `runtime_continuation_odds >= 0.62`
- `runtime_reversal_odds <= 0.52`
- `observe_action / observe_side`가 leg 방향과 크게 어긋나지 않음

### confidence 예시

- base `0.58`
- `wrong_side` 또는 `active_action_conflict_guard`면 `+0.14`
- `checkpoint_type = RECLAIM_CHECK`면 `+0.10`
- `runtime_continuation_odds >= 0.72`면 `+0.08`

### 출력

- `runtime_scene_coarse_family = ENTRY_INITIATION`
- `runtime_scene_fine_label = liquidity_sweep_reclaim`
- `runtime_scene_modifier_json = {"reclaim": true}`

---

## 4. `breakout_retest_hold`

### 목적

돌파 후 되돌림이 깨진 레벨 근처에서 멈추고 다시 지지받는 구조를 보수적으로 태그한다.

### 기본 조건

- `checkpoint_type in {FIRST_PULLBACK_CHECK, RECLAIM_CHECK}`
- `surface_name in {follow_through_surface, continuation_hold_surface}`
- `runtime_continuation_odds >= 0.60`
- `runtime_hold_quality_score >= 0.38`
- 아래 중 하나 이상
  - `runtime_reversal_odds <= runtime_continuation_odds - 0.04`
  - `reason blob`에 `breakout`, `follow_through`, `reclaim` 성격이 있음
  - `runtime_score_reason`이 `continuation_hold_bias` 계열

### confidence 예시

- base `0.56`
- `checkpoint_type = RECLAIM_CHECK`면 `+0.10`
- `reason blob`에 `breakout/reclaim`이 있으면 `+0.10`
- `runtime_continuation_odds >= 0.70`면 `+0.08`

### 출력

- `runtime_scene_coarse_family = ENTRY_INITIATION`
- `runtime_scene_fine_label = breakout_retest_hold`
- `runtime_scene_modifier_json = {"retest_clean": true}` 또는 `{"reclaim": true}`

---

## 5. `low_edge_state` gate

### 목적

setup은 보여도 지금 새로 들어가거나 더 싣기에는 edge가 약한 상태를 gate로 남긴다.

### 기본 조건

- `position_side = FLAT` 또는 `position_size_fraction < 0.75`
- `checkpoint_type in {INITIAL_PUSH, FIRST_PULLBACK_CHECK, RECLAIM_CHECK}`
- `abs(runtime_continuation_odds - runtime_reversal_odds) <= 0.06`
- `max(signal scores) <= 0.62`
- `runtime_full_exit_risk`도 극단적으로 높지 않고, `runtime_rebuy_readiness`도 확실히 높지 않음

### confidence 예시

- base `0.58`
- `position_side = FLAT`면 `+0.06`
- `max(signal scores) <= 0.56`면 `+0.08`
- `checkpoint_type in {FIRST_PULLBACK_CHECK, RECLAIM_CHECK}`면 `+0.06`

### 출력

- `runtime_scene_gate_label = low_edge_state`
- `runtime_scene_gate_block_level = entry_block`
- fine scene이 없으면 `runtime_scene_fine_label = unresolved` 유지

---

## confidence / band / maturity 규칙

## 1. confidence score -> band

- `>= 0.80` -> `high`
- `0.60 ~ 0.79` -> `medium`
- `< 0.60` -> `low`

## 2. maturity

기본 규칙은 아래처럼 간다.

- 명확한 태그가 없으면 `provisional`
- 새 scene가 처음 잡혔고 confidence가 `>= 0.60`이면 `probable`
- 직전 scene과 같고 이번 confidence도 `>= 0.80`이면 `confirmed`

즉 `confirmed`는 “같은 scene이 이어지고 있고, 이번 판정도 강하다”일 때만 준다.

## 3. action bias strength

- tag 없음 -> `none`
- `low` band -> `soft`
- `medium` band -> `medium`
- `high` band + 보수적 장면 (`trend_exhaustion`, `time_decay_risk`, `low_edge_state`) -> `hard`
- `high` band + entry scene (`breakout_retest_hold`, `liquidity_sweep_reclaim`) -> `medium`

중요한 원칙:

- `provisional`에서는 bias가 있더라도 action을 직접 흔들지 않는다
- `probable` 이상부터 나중 단계에서 resolver가 참고할 수 있다

---

## alignment 규칙

scene이 붙으면 `surface`와의 관계도 같이 저장한다.

### aligned

- `ENTRY_INITIATION` scene on `initial_entry_surface` or `follow_through_surface`
- `POSITION_MANAGEMENT` scene on `continuation_hold_surface`
- `DEFENSIVE_EXIT` scene on `protective_exit_surface`

### upgrade

- scene이 surface보다 더 보수적일 때
- 예: `continuation_hold_surface` 위에 `trend_exhaustion`

### downgrade

- scene이 surface보다 더 공격적일 때
- 예: `protective_exit_surface` 위에 `breakout_retest_hold`

### conflict

- 의미가 심하게 엇갈릴 때
- v1에서는 자동 전환하지 않고 `log-only` 성격으로 남긴다

---

## transition 규칙

SA2에서 최소한 아래 3개는 바로 채운다.

- `runtime_scene_transition_from`
- `runtime_scene_transition_bars`
- `runtime_scene_transition_speed`

### 입력

- 직전 runtime latest row의 `checkpoint_runtime_scene_*` prefixed 값

### 기본 규칙

- 직전 fine scene과 이번 fine scene이 같으면
  - `transition_from = previous fine scene`
  - `transition_bars = previous transition_bars + 1`
- 직전과 다르면
  - `transition_from = previous fine scene`
  - `transition_bars = 0`

### speed

- `transition_bars = 0` -> `fast`
- `1 ~ 2` -> `normal`
- `>= 3` -> `slow`
- fine scene이 여전히 `unresolved`면 `unknown`

---

## 구현 순서

## SA2A. scene tagger module 추가

- [path_checkpoint_scene_tagger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_tagger.py)
- 입력: `symbol`, `runtime_row`, `checkpoint_row`, `symbol_state`, `position_state`, `previous_runtime_row`
- 출력: `runtime_scene_*` payload + detail

## SA2B. record path 연동

- [path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py) 안 `record_checkpoint_context()`
- 순서:
  1. context row 생성
  2. passive score 계산
  3. heuristic scene tagger 호출
  4. scene payload merge
  5. action resolver 호출

## SA2C. 테스트

### 신규 테스트

- `trend_exhaustion` 태그
- `time_decay_risk` 태그
- `liquidity_sweep_reclaim` 태그
- `breakout_retest_hold` 태그
- `low_edge_state` gate 태그
- explicit override가 있으면 덮어쓰지 않는지
- previous runtime scene 기반 transition이 붙는지

### 회귀 테스트

- [test_path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_context.py)
- [test_path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_dataset.py)
- [test_entry_try_open_entry_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_try_open_entry_policy.py)
- [test_exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_service.py)

## SA2D. 관찰

이 단계에서는 별도 bounded adoption은 하지 않는다.
대신 새 checkpoint row에 실제로 아래가 찍히는지만 본다.

- `runtime_scene_fine_label`
- `runtime_scene_gate_label`
- `runtime_scene_confidence_band`
- `runtime_scene_maturity`
- `runtime_scene_family_alignment`

---

## 완료 기준

- 새 runtime checkpoint row에 실제 scene 값이 들어간다
- `starter set 5개`가 테스트에서 태깅된다
- 기존 action resolver 분포가 갑자기 깨지지 않는다
- scene 없는 row는 안전하게 `unresolved / none / low / provisional`로 남는다
- 직전 scene이 있으면 최소 transition 값이 함께 남는다

---

## 한 줄 결론

`SA2`는 scene model을 붙이는 단계가 아니라, 지금 있는 checkpoint row 위에 첫 번째 heuristic scene seed를 안전하게 심는 단계다. 이 seed가 제대로 찍혀야 `SA2.5`, `SA3`, `SA6`가 흔들리지 않는다.
