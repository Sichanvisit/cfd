# Current SA1 Scene Schema Extension Detailed Plan

## 목적

이 문서는 `SA1 Scene Schema Extension`에서
실제로 무엇을 바꿨는지와
이 단계가 왜 `SA2 Heuristic Scene Tagger`보다 먼저 필요한지 정리한 기록 문서다.

핵심 목적은 단순하다.

> scene을 아직 "판단"하지 않고,
> 먼저 checkpoint row, runtime latest row, dataset export에
> scene 컬럼이 안전하게 흐를 수 있는 자리를 만드는 것

즉 이번 단계는
`scene logic`이 아니라
`scene storage contract`를 여는 단계다.

관련 기준 문서:

- [current_checkpoint_scene_axis_design_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_design_v1_ko.md)
- [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)

---

## 1. 이번 단계에서 실제로 한 일

### 1-1. checkpoint runtime row schema 확장

파일:
[path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)

추가한 scene 컬럼:

- `runtime_scene_coarse_family`
- `runtime_scene_fine_label`
- `runtime_scene_gate_label`
- `runtime_scene_modifier_json`
- `runtime_scene_confidence`
- `runtime_scene_confidence_band`
- `runtime_scene_action_bias_strength`
- `runtime_scene_source`
- `runtime_scene_maturity`
- `runtime_scene_transition_from`
- `runtime_scene_transition_bars`
- `runtime_scene_transition_speed`
- `runtime_scene_family_alignment`
- `runtime_scene_gate_block_level`
- `hindsight_scene_fine_label`
- `hindsight_scene_quality_tier`

### 1-2. runtime latest row sync 확장

위 컬럼들이
`runtime.latest_signal_by_symbol[symbol]`에도
`checkpoint_runtime_scene_*` prefix 형태로 같이 반영되게 했다.

즉 이후 SA2에서 scene heuristic이 붙으면
runtime watch나 downstream runtime row에서도 바로 읽을 수 있다.

### 1-3. 기본 안전값 추가

이번 단계에서는 scene을 아직 판정하지 않는다.
대신 아래 기본값으로 안전하게 저장한다.

- `runtime_scene_gate_label = none`
- `runtime_scene_modifier_json = {}`
- `runtime_scene_confidence = 0.0`
- `runtime_scene_confidence_band = low`
- `runtime_scene_action_bias_strength = none`
- `runtime_scene_source = schema_only`
- `runtime_scene_maturity = provisional`
- `runtime_scene_transition_bars = 0`
- `runtime_scene_gate_block_level = none`

즉 아직 scene 판단이 없더라도
schema는 열리고,
resolver를 흔들지 않는 보수 기본값이 들어간다.

### 1-4. dataset export schema 확장

파일:
[path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

`PATH_CHECKPOINT_DATASET_COLUMNS`에 scene 컬럼을 추가해서,
기존 checkpoint dataset과 resolved dataset이
scene 축을 잃지 않고 그대로 들고 가게 만들었다.

이 단계의 목적은
scene을 아직 잘 맞히는 것이 아니라,
scene 정보가 row -> csv -> resolved dataset으로
끊기지 않고 흐르게 만드는 것이다.

---

## 2. 이번 단계에서 하지 않은 것

아래는 일부러 아직 하지 않았다.

- heuristic scene 판정
- candidate scene model
- scene-aware action bias
- scene 기반 bounded runtime adoption
- hindsight scene 자동 판정 로직

즉,
이번 단계는 `SA1`답게
자리만 만들었고
판단은 아직 넣지 않았다.

---

## 3. 왜 이 순서가 맞는가

scene 축을 너무 빨리 판단까지 넣으면
나중에 스키마가 바뀔 때마다
checkpoint row와 dataset과 테스트가 같이 흔들린다.

그래서 먼저 해야 하는 것은 아래다.

1. 컬럼을 고정
2. runtime latest row와 csv에 반영
3. dataset export까지 통과
4. 그다음에 SA2에서 heuristic을 붙임

즉 이번 단계는
집을 짓기 전에 벽에 콘센트를 먼저 심는 단계에 가깝다.

---

## 4. 테스트와 검증

### 신규/갱신 테스트

- [test_path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_context.py)
- [test_path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_dataset.py)

핵심 검증 포인트:

- scene 컬럼이 checkpoint row에 기본값으로 들어가는가
- scene 컬럼이 csv schema migration에 안전하게 반영되는가
- runtime latest row에 `checkpoint_runtime_scene_*`가 들어가는가
- dataset / resolved dataset이 scene 컬럼을 유지하는가

### 실행한 테스트

- `python -m pytest tests/unit/test_path_checkpoint_context.py tests/unit/test_path_checkpoint_dataset.py`
- `python -m pytest tests/unit/test_entry_try_open_entry_policy.py tests/unit/test_exit_service.py`

결과:

- scene schema 관련 테스트 `18 passed`
- 영향권 회귀 테스트 `17 passed`

---

## 5. 현재 상태 해석

지금 상태를 한 줄로 말하면 이렇다.

> scene을 읽는 능력은 아직 없지만,
> scene을 담고 전달하고 저장하는 통로는 열렸다.

즉:

- `SA1` 완료
- 다음은 `SA2 Heuristic Scene Tagger`

---

## 6. 다음 단계

다음으로 자연스럽게 이어지는 건 `SA2`다.

우선순위는 아래 5개 scene부터다.

- `trend_exhaustion`
- `low_edge_state`
- `time_decay_risk`
- `liquidity_sweep_reclaim`
- `breakout_retest_hold`

그리고 SA2에서는 아래를 같이 넣는 것이 맞다.

- `runtime_scene_confidence`
- `runtime_scene_confidence_band`
- `runtime_scene_action_bias_strength`
- `runtime_scene_maturity`
- `runtime_scene_family_alignment`
- `runtime_scene_gate_block_level`

즉 SA2는
이번에 만든 빈 자리에
처음으로 heuristic scene seed를 넣는 단계다.
