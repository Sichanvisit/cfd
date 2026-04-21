# Current Checkpoint Scene Axis Design v1

## 목적

이 문서는 현재 구축된 `path-aware checkpoint` 구조 위에
`scene axis`를 어떻게 추가할지 상세하게 설명하는 설계 문서다.

이 문서의 목적은 3가지다.

1. 지금 우리가 무엇을 이미 만들었고, 무엇이 아직 비어 있는지 아주 쉽게 설명한다.
2. `state25처럼 나눈다`는 말을 현재 checkpoint 구조에 맞는 실무적인 형태로 다시 정의한다.
3. 실제로 구현할 때 필요한 `컬럼`, `task 이름`, `구현 순서`를 바로 이어서 제시한다.

이 문서는 새 시스템을 갈아엎는 문서가 아니다.
오히려 이미 만든 것을 유지한 채,
그 위에 `scene`이라는 새로운 축을 하나 더 얹는 문서다.

관련 기준 문서:

- [current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md)
- [current_path_aware_checkpoint_decision_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_roadmap_ko.md)
- [current_sa0_scene_axis_baseline_matrix_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_sa0_scene_axis_baseline_matrix_v1_ko.md)
- [current_sa0_scene_axis_scope_lock_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_sa0_scene_axis_scope_lock_detailed_plan_ko.md)
- [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
- [current_state25_retrain_compare_promote_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_retrain_compare_promote_design_ko.md)
- [current_forecast_state25_learning_bridge_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_forecast_state25_learning_bridge_design_ko.md)

---

## 1. 제일 쉽게 이해하기

### 1-1. 지금 시스템은 이미 절반 이상 만들어져 있다

아주 쉽게 말하면,
우리는 이미 아래 3개 중 2개는 만들어 둔 상태다.

- `지금 어느 시간대인가`
- `그래서 지금 뭘 해야 하나`
- `지금 실제로 어떤 장면이 벌어지고 있는가`

현재 시스템은 앞의 2개는 꽤 잘한다.

- `surface`
  - 지금이 진입 국면인지
  - 추종 국면인지
  - 보유 관리 국면인지
  - 방어 청산 국면인지
- `action`
  - 그래서 `HOLD`인지
  - `PARTIAL_EXIT`인지
  - `FULL_EXIT`인지
  - `REBUY`인지

그런데 아직 약한 게 하나 있다.

- `scene`
  - 지금 이 순간이 `breakout`인지
  - `pullback_continuation`인지
  - `trend_exhaustion`인지
  - `low_edge_state`인지

즉, 지금은
`무슨 시간인지`와 `뭘 해야 하는지`는 있는데,
그 둘 사이를 연결해 주는
`지금 무슨 장면이냐`가 약하다.

이번 문서의 핵심은 바로 이것이다.

> 기존 checkpoint row 위에
> `scene` 축을 하나 더 붙여서
> 차트를 더 잘게 읽고,
> 그 장면을 따로 학습하게 만들자.

### 1-2. 초등학생 비유

학교로 비유하면 이렇다.

- `surface`는 지금이 무슨 수업 시간인지다.
  - 수학 시간
  - 체육 시간
  - 쉬는 시간
- `scene`은 교실 안에서 지금 무슨 상황이 벌어졌는지다.
  - 선생님이 막 설명 시작함
  - 시험 직전이라 조용함
  - 친구가 틀리고 다시 고침
  - 떠들어서 지금은 가만히 있어야 함
- `action`은 내가 지금 뭘 해야 하는지다.
  - 손들기
  - 기다리기
  - 조금만 하기
  - 완전히 멈추기

지금 우리 시스템은
`수학 시간인지 체육 시간인지`와
`손들지 가만히 있지`는 아는데,
`지금 교실에서 무슨 상황인지`를 아직 충분히 잘 나누지 못하고 있다.

그래서 그 중간에
`scene` 축을 넣어야 한다.

---

## 2. 지금 이미 있는 것과 없는 것

### 2-1. 이미 있는 것

현재 체크포인트 구조에는 아래가 이미 있다.

- `surface`
  - `initial_entry_surface`
  - `follow_through_surface`
  - `continuation_hold_surface`
  - `protective_exit_surface`
- `leg / checkpoint`
  - `leg_id`
  - `checkpoint_id`
  - `checkpoint_type`
- `runtime score`
  - `runtime_continuation_odds`
  - `runtime_reversal_odds`
  - `runtime_hold_quality_score`
  - `runtime_partial_exit_ev`
  - `runtime_full_exit_risk`
  - `runtime_rebuy_readiness`
- `action`
  - `management_action_label`
  - `management_action_confidence`
  - `management_action_reason`
- `hindsight`
  - `hindsight_best_management_action_label`
  - `hindsight_quality_tier`
- `dataset / eval / snapshot`

즉,
`checkpoint row -> score -> action -> hindsight`
까지는 이미 길이 나 있다.

### 2-2. 아직 약한 것

지금 약한 것은 아래다.

- 이 row가 `breakout_retest_hold`인지
- `runner_hold`인지
- `trend_exhaustion`인지
- `dead_leg_wait`인지

즉,
행동은 있는데 장면이 약하다.

그래서 지금은 아래 같은 문제가 생긴다.

- 같은 `HOLD`라도
  - 건강한 runner를 드는 `HOLD`인지
  - 애매하지만 그냥 버티는 `HOLD`인지
  - 재축적을 기다리는 `HOLD`인지
  - 시간만 끌고 있는 `HOLD`인지
  가 섞여 버린다.

이걸 분리해 주는 것이 `scene axis`다.

---

## 3. state25처럼 나눈다는 말의 진짜 뜻

### 3-1. 라벨을 따라가자는 뜻이 아니다

`state25처럼 나누자`는 말을 잘못 이해하면 이렇게 된다.

- 상태 이름을 많이 만든다
- 22개를 한 번에 분류한다
- 모델도 하나로 크게 만든다

이건 지금 구조에서는 좋지 않다.

우리가 state25에서 배워야 하는 진짜 포인트는
라벨 개수가 아니라 `역할 분리`다.

state25는 한 번에 모든 걸 맞히려 하지 않는다.
대신 아래처럼 역할을 나눈다.

- 큰 그룹
- 패턴
- wait 품질
- belief 결과
- barrier 결과
- forecast transition
- forecast management

즉,
`큰 문제를 작은 문제들로 쪼개서 따로 배우고, 비교하고, 승격한다`
는 철학을 가져와야 한다.

### 3-2. checkpoint에도 같은 철학을 적용한다

checkpoint 쪽도 똑같이 보면 된다.

한 번에 `22개 장면 + 행동 + 결과`를 맞히게 하지 말고,
이렇게 쪼갠다.

- `coarse family`
  - 지금이 Entry/Continuation/Management/Defensive/NoTrade 중 무엇인가
- `fine scene`
  - 그 coarse 안에서 세부 장면이 무엇인가
- `action`
  - 지금 무엇을 해야 하나
- `outcome`
  - 나중에 보니 무엇이 맞았나

즉,
`scene`과 `action`과 `outcome`은 서로 다른 층이다.

---

## 4. surface, scene, action, outcome의 차이

이 네 개를 꼭 분리해서 생각해야 한다.

### 4-1. surface

`surface`는 문제 종류다.

예:

- `initial_entry_surface`
- `follow_through_surface`
- `continuation_hold_surface`
- `protective_exit_surface`

### 4-2. scene

`scene`은 지금 실제로 벌어진 장면이다.

예:

- `breakout`
- `breakout_retest_hold`
- `runner_hold`
- `time_decay_exit`
- `trend_exhaustion`
- `ambiguous_structure`

### 4-3. action

`action`은 지금 취할 행동이다.

예:

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

### 4-4. outcome

`outcome`은 나중에 되돌아봤을 때 무엇이 맞았는지다.

예:

- hindsight로 보니 `FULL_EXIT`가 맞았다
- hindsight로 보니 `WAIT`가 맞았다
- hindsight로 보니 `PARTIAL_THEN_HOLD`가 맞았다

### 4-5. 같은 row 안에서도 네 층이 모두 다를 수 있다

예를 들면:

- `surface = continuation_hold_surface`
- `scene = trend_exhaustion`
- `action = PARTIAL_THEN_HOLD`
- `outcome = hindsight_best_management_action_label = PARTIAL_THEN_HOLD`

또 다른 예:

- `surface = continuation_hold_surface`
- `scene = dead_leg_wait`
- `action = WAIT`
- `outcome = WAIT`

즉,
scene과 action은 같은 것이 아니다.

---

## 5. 왜 22개를 하나의 거대한 분류기로 만들면 안 되는가

이유는 4개다.

### 5-1. 데이터가 금방 희소해진다

22개를 한 번에 맞히려 하면
각 라벨에 데이터가 너무 적어진다.

### 5-2. 방향까지 붙이면 바로 폭발한다

`breakout` 하나만 해도
롱/숏, 자산, surface까지 곱해지면 너무 빨리 커진다.

그래서 방향은 scene 이름에 넣지 말고
별도 `direction` 필드로 두는 것이 좋다.

### 5-3. 장면과 행동이 섞인다

예를 들어:

- `failed_transition`은 장면이다
- `FULL_EXIT`는 행동이다

이 둘을 같은 라벨 테이블로 섞으면
학습도 평가도 애매해진다.

### 5-4. No-Trade는 어디서나 나올 수 있다

`No-Trade`는 entry 때도 나오고
hold 때도 나온다.

그래서 No-Trade는
새 surface가 아니라 `gate axis`로 두는 편이 낫다.

---

## 6. 22개 장면을 현재 surface에 붙이는 방식

### 6-1. Entry Initiation 계열

이 장면들은 주로 `initial_entry_surface`에 붙는다.

- `trend_ignition`
- `breakout`
- `breakout_retest_hold`
- `liquidity_sweep_reclaim`
- `orderblock_reaction`

### 6-2. Continuation 계열

이 장면들은 주로 `follow_through_surface`에 붙는다.

- `pullback_continuation`
- `reaccumulation`
- `redistribution`

### 6-3. Position Management 계열

이 장면들은 주로 `continuation_hold_surface`에 붙는다.

- `runner_hold`
- `partial_then_hold`
- `add_to_position`
- `rebuy_ready`
- `fvg_fill`
- `time_decay_exit`

### 6-4. Defensive Exit 계열

이 장면들은 주로 `protective_exit_surface`에 붙는다.

- `failed_transition`
- `protective_exit`
- `trend_exhaustion`
- `climax_reversal`

### 6-5. No-Trade 계열

이 장면들은 특정 surface 하나에만 속하지 않는다.
전 surface를 덮는 `gate axis`로 둔다.

- `ambiguous_structure`
- `dead_leg_wait`
- `low_edge_state`

### 6-6. modifier로 두는 것

아래는 처음부터 독립 장면으로 두지 않고
modifier나 subflag로 두는 편이 더 안정적이다.

- `reclaim`
  - `pullback_continuation`의 depth/shape modifier
- `thesis_void`
  - `failed_transition`의 severity modifier
- `fvg_overlap`
  - entry/management 장면의 structure modifier
- `orderblock_overlap`
  - entry 장면의 structure modifier

---

## 7. scene axis를 현재 구조에 어떻게 얹는가

현재 구조는 대략 이렇다.

```text
runtime row
-> leg detection
-> checkpoint segmentation
-> checkpoint context
-> score calculation
-> management action resolver
-> hindsight label
-> dataset / eval / snapshot
```

여기에 scene을 끼우면 이렇게 된다.

```text
runtime row
-> leg detection
-> checkpoint segmentation
-> checkpoint context
-> runtime scene coarse/fine/gate tagging
-> score calculation
-> management action resolver
-> hindsight scene resolution
-> hindsight action resolution
-> dataset / eval / snapshot
-> state25-style candidate / compare / promote
```

즉,
기존 엔진을 버리지 않고
중간에 `scene tagging` 층을 하나 더 추가한다.

---

## 8. 추가할 컬럼

### 8-1. v1 최소 컬럼

가장 먼저 추가해야 할 최소 컬럼은 아래 8개다.

| 컬럼 | 설명 |
|---|---|
| `runtime_scene_coarse_family` | 현재 row의 큰 장면 가족 |
| `runtime_scene_fine_label` | 현재 row의 세부 장면 |
| `runtime_scene_gate_label` | no-trade gate 또는 보수 gate |
| `runtime_scene_modifier_json` | reclaim, severity, fvg/ob 겹침 등 |
| `runtime_scene_confidence` | scene 판정 신뢰도 |
| `runtime_scene_source` | `heuristic_v1`, `candidate_model_v1`, `manual_resolution` 등 |
| `hindsight_scene_fine_label` | 나중에 다시 봤을 때 더 맞았던 장면 |
| `hindsight_scene_quality_tier` | auto/manual/diagnostic 품질 구분 |

### 8-2. v1.1 권장 컬럼

아래는 처음부터 있으면 좋지만,
조금 뒤에 붙여도 되는 컬럼이다.

| 컬럼 | 설명 |
|---|---|
| `runtime_scene_reason` | 왜 이 장면으로 판정했는지 짧은 이유 |
| `runtime_scene_version` | 룰 버전 또는 candidate 버전 |
| `runtime_scene_transition_from` | 직전 scene |
| `runtime_scene_transition_to` | 다음 유력 scene |
| `hindsight_scene_modifier_json` | hindsight 기준 modifier |
| `scene_resolution_status` | `resolved`, `manual_exception`, `diagnostic_only` |
| `scene_family_alignment_ok` | surface와 coarse family가 맞는지 |

### 8-3. coarse family 값

`runtime_scene_coarse_family` 값은 아래 5개로 고정하는 것을 권장한다.

- `ENTRY_INITIATION`
- `CONTINUATION`
- `POSITION_MANAGEMENT`
- `DEFENSIVE_EXIT`
- `NO_TRADE`

### 8-4. fine scene 값

`runtime_scene_fine_label` 값은 v1에서 아래를 우선 사용한다.

- `trend_ignition`
- `breakout`
- `breakout_retest_hold`
- `liquidity_sweep_reclaim`
- `orderblock_reaction`
- `pullback_continuation`
- `reaccumulation`
- `redistribution`
- `runner_hold`
- `partial_then_hold`
- `add_to_position`
- `rebuy_ready`
- `fvg_fill`
- `time_decay_exit`
- `failed_transition`
- `protective_exit`
- `trend_exhaustion`
- `climax_reversal`

### 8-5. gate label 값

`runtime_scene_gate_label`은 아래를 우선 사용한다.

- `none`
- `ambiguous_structure`
- `dead_leg_wait`
- `low_edge_state`

### 8-6. modifier 예시

`runtime_scene_modifier_json` 예시는 아래처럼 간단히 시작하면 된다.

```json
{
  "depth": "reclaim",
  "severity": "thesis_void",
  "structure_overlap": ["fvg", "orderblock"],
  "late_trend": true
}
```

---

## 9. 새 task 이름

scene axis를 state25처럼 운영하려면
학습 task도 역할별로 나누는 것이 좋다.

### 9-1. 권장 task 목록

- `checkpoint_coarse_family_task`
- `checkpoint_entry_scene_task`
- `checkpoint_continuation_scene_task`
- `checkpoint_management_scene_task`
- `checkpoint_defensive_scene_task`
- `checkpoint_no_trade_gate_task`
- `checkpoint_management_action_task`
- `checkpoint_management_outcome_task`

### 9-2. 각 task의 역할

#### `checkpoint_coarse_family_task`

먼저 이 row가 큰 가족 중 어디인지 본다.

- Entry냐
- Continuation이냐
- Management냐
- Defensive냐
- NoTrade냐

#### `checkpoint_entry_scene_task`

coarse가 `ENTRY_INITIATION`일 때만 세부 장면을 판정한다.

- `trend_ignition`
- `breakout`
- `breakout_retest_hold`
- `liquidity_sweep_reclaim`
- `orderblock_reaction`

#### `checkpoint_continuation_scene_task`

coarse가 `CONTINUATION`일 때만 판정한다.

- `pullback_continuation`
- `reaccumulation`
- `redistribution`

#### `checkpoint_management_scene_task`

coarse가 `POSITION_MANAGEMENT`일 때만 판정한다.

- `runner_hold`
- `partial_then_hold`
- `add_to_position`
- `rebuy_ready`
- `fvg_fill`
- `time_decay_exit`

#### `checkpoint_defensive_scene_task`

coarse가 `DEFENSIVE_EXIT`일 때만 판정한다.

- `failed_transition`
- `protective_exit`
- `trend_exhaustion`
- `climax_reversal`

#### `checkpoint_no_trade_gate_task`

모든 surface 위에서 공통 gate를 판정한다.

- `ambiguous_structure`
- `dead_leg_wait`
- `low_edge_state`

#### `checkpoint_management_action_task`

scene과 score를 받아서
최종 행동을 고른다.

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

#### `checkpoint_management_outcome_task`

hindsight 기준으로
무엇이 맞았는지 따로 본다.

즉,
scene과 action과 outcome을 분리해서 배운다.

---

## 10. 현재 코드에 어디를 붙이면 되는가

### 10-1. `path_checkpoint_context.py`

파일:
[path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)

여기는 `scene axis`가 가장 먼저 들어갈 곳이다.

추가 역할:

- `runtime_scene_coarse_family`
- `runtime_scene_fine_label`
- `runtime_scene_gate_label`
- `runtime_scene_modifier_json`
- `runtime_scene_confidence`
- `runtime_scene_source`

즉,
checkpoint row를 저장할 때
scene 컬럼도 같이 쓰게 만든다.

### 10-2. `path_checkpoint_scoring.py`

파일:
[path_checkpoint_scoring.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scoring.py)

여기서는 기존 score 계산을 유지한다.

추가 역할:

- scene tagger가 참고할 feature를 제공
- coarse/fine 판정 룰에 필요한 score 재사용

즉,
score 엔진을 새로 만들지 않고
scene 판정에도 재사용한다.

### 10-3. `path_checkpoint_action_resolver.py`

파일:
[path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)

현재는 score 중심으로 action을 고른다.

앞으로는 여기에
scene 결과를 입력으로 추가한다.

예:

- `runtime_scene_fine_label = trend_exhaustion`
  - `HOLD`보다 `PARTIAL_THEN_HOLD` 쪽 우선
- `runtime_scene_gate_label = low_edge_state`
  - `WAIT` 강화
- `runtime_scene_fine_label = failed_transition`
  - `FULL_EXIT` 쪽 강화

### 10-4. `path_checkpoint_dataset.py`

파일:
[path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

여기서는 dataset export에 scene 축을 추가한다.

추가 역할:

- `runtime_scene_*` 저장
- `hindsight_scene_*` 저장
- scene/action/outcome을 같은 row에서 비교 가능하게 정리

### 10-5. 새 scene pipeline 파일들

처음부터 다 만들 필요는 없지만,
최종적으로는 아래 파일군이 필요해진다.

- `backend/services/checkpoint_scene_candidate_pipeline.py`
- `backend/services/checkpoint_scene_compare_report.py`
- `backend/services/checkpoint_scene_runtime_bridge.py`
- `scripts/build_checkpoint_scene_dataset.py`
- `scripts/build_checkpoint_scene_eval.py`
- `scripts/build_checkpoint_scene_candidate_watch.py`

이건 `state25`의 sibling pipeline으로 이해하면 된다.

---

## 11. 구현 순서

아래 순서는
현재 구축물을 망가뜨리지 않고
가장 안전하게 확장하는 순서다.

### SA0. Scene Axis Scope Lock

#### 목적

scene 체계의 범위를 고정한다.

#### 할 일

- coarse family 확정
- fine scene 목록 확정
- gate label 확정
- modifier로 둘 것과 독립 label로 둘 것 확정

#### 산출물

- `scene axis spec v1`
- label table
- modifier table

#### 완료 기준

- 22개 중 무엇이 진짜 독립 label인지 문서로 고정
- `reclaim`, `thesis_void`, `fvg_overlap` 같은 modifier가 분리됨

### SA1. Scene Schema Extension

#### 목적

checkpoint row에 scene 컬럼을 추가한다.

#### 주요 파일

- [path_checkpoint_context.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_context.py)

#### 할 일

- runtime scene 컬럼 추가
- hindsight scene 컬럼 자리 추가
- csv/jsonl storage schema 확장

#### 산출물

- scene 컬럼이 포함된 `checkpoint_rows.csv`
- scene 컬럼이 포함된 detail jsonl

#### 완료 기준

- 새 row에 scene 컬럼이 비어 있어도 저장은 깨지지 않음
- 기존 pipeline과 충돌하지 않음

### SA2. Heuristic Scene Tagger

#### 목적

model 없이 rule 기반으로 먼저 scene을 붙인다.

#### 왜 이 단계가 필요한가

처음부터 model로 가면 데이터가 없다.
먼저 heuristic로 seed를 만들어야 한다.

#### 먼저 붙이기 좋은 장면

- `trend_exhaustion`
- `low_edge_state`
- `time_decay_exit`
- `liquidity_sweep_reclaim`
- `breakout_retest_hold`

#### 주요 파일

- 새 helper 또는 `path_checkpoint_context.py` 내부 tagger
- 일부 feature 재사용은 [path_checkpoint_scoring.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scoring.py)

#### 완료 기준

- 최근 row에서 scene coarse/fine/gate가 실제로 찍힘
- label 분포가 너무 한쪽으로 쏠리지 않음

### SA3. Scene Dataset Export

#### 목적

scene이 학습 가능한 dataset으로 내려가게 만든다.

#### 주요 파일

- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)

#### 할 일

- `runtime_scene_*` export
- `hindsight_scene_*` export
- scene confusion / coverage report 추가

#### 산출물

- `checkpoint_scene_dataset.csv`
- `checkpoint_scene_eval_latest.json`

#### 완료 기준

- scene 분포와 coverage를 artifact로 볼 수 있음
- 어떤 scene이 sparse한지 바로 보임

### SA4. Scene Candidate Pipeline

#### 목적

scene 축을 state25식으로 candidate/train/compare/promote할 수 있게 만든다.

#### 주요 파일

- `checkpoint_scene_candidate_pipeline.py`
- `checkpoint_scene_compare_report.py`

#### 할 일

- coarse family candidate
- management scene candidate
- no-trade gate candidate

를 먼저 만든다.

#### 완료 기준

- heuristic만 있는 상태를 벗어나
- candidate 모델과 비교 가능해짐

### SA5. Log-Only Runtime Bridge

#### 목적

scene candidate를 runtime에 연결하되,
아직 live decision은 바꾸지 않는다.

#### 주요 파일

- `checkpoint_scene_runtime_bridge.py`

#### 할 일

- `runtime_scene_source = candidate_model_v1`
- `log_only` 비교 필드 저장
- heuristic vs candidate 차이 기록

#### 완료 기준

- runtime에 candidate scene이 보이지만
- 실제 action은 아직 바뀌지 않음

### SA6. Action Resolver Integration

#### 목적

scene을 실제 action resolver가 참고하게 만든다.

#### 주요 파일

- [path_checkpoint_action_resolver.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_action_resolver.py)

#### 예시 규칙

- `scene = trend_exhaustion`
  - `PARTIAL_THEN_HOLD` 우세
- `scene = failed_transition`
  - `FULL_EXIT` 우세
- `gate = low_edge_state`
  - `WAIT` 우세
- `scene = breakout_retest_hold` + hold 구조 강함
  - `ADD / HOLD` 우세

#### 완료 기준

- scene-aware action resolver가 snapshot에서 분포 차이를 보여줌
- precision이 악화되지 않음

### SA7. Bounded Adoption

#### 목적

scene-aware action을 조심스럽게 운영에 반영한다.

#### 순서

- `log_only`
- `review`
- `canary`
- `bounded_live`

#### 완료 기준

- rollback이 가능함
- 특정 symbol/surface에서만 제한적으로 활성화 가능함

### SA8. State25-Style Promotion Loop

#### 목적

scene axis도 state25처럼
재학습, 비교, 승격 루프를 갖게 만든다.

#### 할 일

- retrain
- compare
- promote decision
- log_only binding
- canary binding

#### 완료 기준

- checkpoint scene도 state25와 같은 운영 성숙도를 가짐

---

## 12. 처음부터 다 하지 말고 무엇부터 붙여야 하나

처음부터 22개 전부를 완벽하게 넣으려 하면 흔들린다.

그래서 시작은 아래 5개가 좋다.

- `trend_exhaustion`
- `low_edge_state`
- `time_decay_exit`
- `liquidity_sweep_reclaim`
- `breakout_retest_hold`

이 5개가 좋은 이유는 아래와 같다.

- 행동 차이가 분명하다
- 사람이 봐도 비교적 설명하기 쉽다
- rule seed를 만들기 좋다
- action resolver와 직접 연결되기 쉽다

그 다음 순서로는 아래가 좋다.

- `runner_hold`
- `partial_then_hold`
- `failed_transition`
- `protective_exit`
- `pullback_continuation`

---

## 13. 무엇을 절대 하면 안 되는가

### 13-1. 22개를 새 surface로 만들지 않는다

surface는 국면이다.
scene은 장면이다.

둘을 섞으면 안 된다.

### 13-2. 22개를 한 모델이 한 번에 맞히게 하지 않는다

coarse/fine/gate/action/outcome을 나눠야 한다.

### 13-3. hindsight를 runtime feature로 직접 쓰지 않는다

이건 leakage가 된다.

runtime에서 쓸 수 있는 것은
그 시점에 알 수 있는 정보뿐이다.

### 13-4. scene과 action을 같은 라벨로 보지 않는다

예:

- `trend_exhaustion`은 scene
- `PARTIAL_THEN_HOLD`는 action

### 13-5. No-Trade를 한 곳에만 가두지 않는다

No-Trade는 entry에서도,
hold에서도,
protective 단계에서도 나올 수 있다.

그래서 gate로 둬야 한다.

---

## 14. 최종적으로 머릿속에 이렇게 잡으면 된다

현재 시스템은 이렇게 생겼다.

```text
surface -> checkpoint -> score -> action -> hindsight
```

앞으로는 이렇게 확장된다.

```text
surface -> checkpoint -> scene -> score -> action -> hindsight -> candidate/promote
```

즉,
새 엔진을 만드는 것이 아니라
현재 엔진 가운데에 `scene`이라는 설명 층을 하나 더 넣는 것이다.

이 `scene` 층이 들어오면 아래가 가능해진다.

- 왜 같은 HOLD가 다른 HOLD인지 설명 가능
- 왜 어떤 WAIT는 좋은 WAIT이고 어떤 WAIT는 나쁜 WAIT인지 설명 가능
- 왜 어떤 FULL_EXIT는 정답이고 어떤 FULL_EXIT는 조급한 청산인지 설명 가능
- checkpoint 결과를 state25식으로 더 잘게 학습 가능

---

## 15. 아주 짧은 결론

`state25처럼 나눈다`는 말은
22개 이름을 한 덩어리로 붙이자는 뜻이 아니다.

진짜 뜻은 이거다.

> 기존 4개 surface와 checkpoint/action 구조는 그대로 두고,
> 그 위에 `scene axis`를 추가한 뒤,
> 그 scene axis를 `coarse -> fine -> gate -> action -> outcome`
> 순서로 나눠서 state25식 candidate/retrain/compare/promote 흐름으로 운영하자.

이 문서를 기준으로 바로 다음 단계는 `SA0 Scene Axis Scope Lock`이다.
즉, 먼저 `독립 장면`, `modifier`, `gate`를 문서로 잠그는 것이 첫 단계다.

---

## 16. Scope Lock 반영 상태

이 문서는 방향 설계 문서다.
실제 구현 기준은 별도 scope-lock 문서에서 더 엄격하게 잠갔다.

반영된 핵심 변경은 아래와 같다.

- `scene`은 action을 설명하고 bias를 주지만, 단독으로 최종 action을 결정하지 않는다
- `scene_confidence`는 단순 수치뿐 아니라 `high / medium / low` band로도 본다
- `scene_maturity`를 `provisional / probable / confirmed`로 둔다
- `surface-scene alignment`를 v1 필수로 둔다
- `scene transition`을 v1 필수로 끌어올린다
- `gate block level`을 명시해서 신규 진입 차단과 전체 보수화 범위를 구분한다
- `SA2`와 `SA3` 사이에 `SA2.5 Heuristic Sanity Check`를 둔다

즉, 이 문서는 큰 그림이고
[current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
가 실제 구현 기준 문서다.

---

## 17. 읽는 순서

이 축을 처음 보는 사람이면 아래 순서로 읽는 것이 가장 이해가 쉽다.

1. 이 문서
   - scene axis가 왜 필요한지, 전체 방향이 무엇인지 이해
2. [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
   - 구현 전에 꼭 잠가야 하는 경계와 규칙 확인
3. [current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md)
   - 기존 checkpoint 기본 구조 확인
4. [current_path_aware_checkpoint_decision_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_roadmap_ko.md)
   - 기본 PA 트랙과 구현 순서 확인
5. [current_state25_retrain_compare_promote_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_retrain_compare_promote_design_ko.md)
   - state25식 역할 분리와 candidate/promote 철학 참고
6. [current_forecast_state25_learning_bridge_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_forecast_state25_learning_bridge_design_ko.md)
   - bridge/log-only/promotion 연결 철학 참고

---

## 18. 빠른 이해용 운용 요약

### 18-1. gate block level 요약

방향 문서만 읽어도 gate가 실제로 무엇을 막는지 바로 보이도록
핵심 테이블을 아래처럼 둔다.

| gate | 신규진입 | 추가진입 | 보유관리 |
|---|---|---|---|
| `none` | 허용 | 허용 | 정상 |
| `low_edge_state` | 차단 | 차단 | 정상 |
| `dead_leg_wait` | 차단 | 차단 | 축소 bias |
| `ambiguous_structure` | 차단 | 차단 | 축소 bias |

의미는 간단하다.

- `low_edge_state`
  - 방향은 보이지만 돈이 안 되는 자리라 신규 공격만 막는다
- `dead_leg_wait`
  - 에너지가 죽어서 신규 공격을 막고, 가진 것도 줄이는 쪽으로 기운다
- `ambiguous_structure`
  - 구조 자체가 흐리므로 가장 보수적으로 간다

### 18-2. surface-scene 불일치 처리 원칙

불일치 처리 원칙은 아래 한 줄로 기억하면 된다.

- scene이 surface보다 더 보수적이면 -> scene 우선
- scene이 surface보다 더 공격적이면 -> surface 유지
- 판단이 애매하면 -> `log_only + manual review`

즉, 항상 더 보수적인 쪽이 먼저다.

### 18-3. maturity와 action 전환 원칙

scene이 실시간으로 깜빡일 때 action도 같이 흔들리면 오히려 나빠질 수 있다.
그래서 기본 원칙은 아래처럼 둔다.

- `provisional`
  - 기록은 하지만 action bias는 거의 주지 않는다
- `probable`
  - 이때부터 scene bias를 action resolver가 참고할 수 있다
- `confirmed`
  - 이때는 scene bias를 더 강하게 쓸 수 있다

즉 한 줄로 말하면:

> `probable` 이상이 되어야 action bias가 본격적으로 작동하고,
> `provisional`에서는 기존 action을 최대한 유지한다.

---

## 19. 이 구조가 주는 첫 번째 효과와 첫 번째 문제

### 19-1. 가장 먼저 체감할 효과

가장 먼저 좋아지는 것은 이거다.

> 같은 `HOLD`인데 왜 결과가 다른지 설명할 수 있게 된다.

예:

- `runner_healthy + HOLD`
  - 건강한 추세 유지
- `reaccumulation + HOLD`
  - 횡보 중 인내
- `time_decay_risk + HOLD`
  - 사실은 나갔어야 했던 HOLD
- `trend_exhaustion + HOLD`
  - 줄였어야 했던 HOLD

즉 action만 보면 같은 `HOLD`라도
scene이 붙는 순간부터 무엇을 고쳐야 하는지가 드러난다.

### 19-2. 가장 먼저 부딪힐 문제

가장 먼저 부딪히는 문제는 이거다.

> scene이 `provisional -> probable -> confirmed`로 올라갈 때
> action을 언제 바꿀 것인가

예:

- 봉 1: `runner_healthy`
- 봉 2: `runner_healthy`
- 봉 3: `trend_exhaustion (provisional)`
- 봉 4: `trend_exhaustion (probable)`
- 봉 5: `trend_exhaustion (confirmed)`

이때 봉 3부터 바로 `PARTIAL_THEN_HOLD`로 흔들리면 안 된다.
그래서 위의 maturity 원칙이 중요하다.

즉:

- `provisional`에서는 기록 위주
- `probable`부터 bias 시작
- `confirmed`에서 강한 bias

로 가는 것이 맞다.
