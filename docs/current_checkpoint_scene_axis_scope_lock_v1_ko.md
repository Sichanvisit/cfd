# Current Checkpoint Scene Axis Scope Lock v1

## 목적

이 문서는 `scene axis`를 실제 구현에 붙이기 전에
반드시 먼저 잠가야 하는 규칙을 고정하는 `SA0 Scope Lock` 문서다.

이 문서의 목적은 4가지다.

1. `scene`, `gate`, `modifier`, `action`, `outcome`의 경계를 헷갈리지 않게 잠근다.
2. 외부 조언 중 지금 바로 채택해야 하는 것을 v1 구현 기준으로 고정한다.
3. SA1 이후 구현에서 흔들리기 쉬운 부분을 미리 막는다.
4. `scene axis`가 action resolver를 망치지 않고 도와주는 구조가 되게 만든다.

관련 문서:

- [current_sa0_scene_axis_baseline_matrix_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_sa0_scene_axis_baseline_matrix_v1_ko.md)
- [current_sa0_scene_axis_scope_lock_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_sa0_scene_axis_scope_lock_detailed_plan_ko.md)
- [current_checkpoint_scene_axis_design_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_design_v1_ko.md)
- [current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md)
- [current_state25_retrain_compare_promote_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_retrain_compare_promote_design_ko.md)

---

## 1. 한 줄 요약

이번 scope lock의 제일 중요한 문장은 이거다.

> `scene`은 action을 설명하고 bias를 주는 축이지,
> action을 혼자 최종 결정하는 축이 아니다.

즉 구조는 아래처럼 간다.

```text
scene -> action hint
score -> action competition
gate -> action suppression
resolver -> final action
```

이 순서가 흐려지면
scene axis는 설명을 늘리는 대신 결정을 더 흐리게 만들 수 있다.

---

## 2. 이번 외부 조언에서 바로 채택하는 것

이번에 가져온 조언 중에서
v1에서 바로 채택하는 것은 아래 8개다.

### 2-1. 채택 1: scene은 action보다 앞에 오지만 action을 지배하지 않는다

채택한다.

의미:

- `trend_exhaustion`이라고 해서 무조건 `PARTIAL_THEN_HOLD`로 가지 않는다.
- `failed_transition`이라고 해서 무조건 `FULL_EXIT`로 가지 않는다.
- scene은 최종 행동의 설명과 bias로만 작동한다.

### 2-2. 채택 2: gate는 독립 축으로 유지한다

채택한다.

의미:

- `ambiguous_structure`
- `dead_leg_wait`
- `low_edge_state`

는 fine scene이 아니라 gate 축으로 둔다.

### 2-3. 채택 3: modifier는 독립 scene처럼 커지지 못하게 막는다

채택한다.

의미:

- `reclaim`
- `thesis_void`
- `fvg_overlap`
- `orderblock_overlap`

은 v1에서 독립 scene이 아니라 modifier다.

### 2-4. 채택 4: scene confidence는 band로 쓴다

채택한다.

단순 연속 점수 하나만 두지 않고,
resolver가 쉽게 쓸 수 있게 band를 둔다.

- `high`
- `medium`
- `low`

### 2-5. 채택 5: scene maturity를 v1에 바로 넣는다

채택한다.

이유:

scene은 찍는 순간과 확정되는 순간이 다를 수 있기 때문이다.

- `provisional`
- `probable`
- `confirmed`

### 2-6. 채택 6: surface-scene alignment는 v1 필수다

채택한다.

이유:

surface와 scene이 어긋나는 순간이
초기 디버깅에서 가장 중요한 오류 신호이기 때문이다.

### 2-7. 채택 7: transition 추적을 v1으로 올린다

채택한다.

원래는 v1.1 정도로 미뤄도 됐지만,
path-aware 구조의 본질상 초반부터 필요하다.

### 2-8. 채택 8: SA2와 SA3 사이에 sanity check 단계를 넣는다

채택한다.

이름:

- `SA2.5 Heuristic Sanity Check`

이 단계 없이 바로 dataset export로 가면
오염된 scene seed가 누적될 수 있다.

---

## 3. 이번 v1에서 아직 보류하는 것

좋은 조언이지만,
지금 바로 v1 핵심에 넣지 않는 것은 아래다.

### 3-1. 보류 1: full 22 scene 동시 활성화

보류한다.

처음엔 5개 우선 scene만 적극 사용한다.

### 3-2. 보류 2: candidate scene model 조기 우선 적용

보류한다.

처음엔 heuristic seed와 log-only 관측을 먼저 본다.

### 3-3. 보류 3: live action에 공격적 auto-bias

보류한다.

처음엔 log-only와 bounded adoption 순서를 지킨다.

---

## 4. 이번 v1의 가장 중요한 경계

이 경계는 절대 흐리면 안 된다.

### 4-1. surface

`surface`는 문제 종류다.

예:

- `initial_entry_surface`
- `follow_through_surface`
- `continuation_hold_surface`
- `protective_exit_surface`

### 4-2. scene

`scene`은 지금 시장에 벌어진 장면이다.

예:

- `breakout_retest_hold`
- `trend_exhaustion`
- `time_decay_risk`

### 4-3. gate

`gate`는 좋은 action이 있어 보여도
그 action을 막거나 약하게 만드는 보수 규칙이다.

예:

- `low_edge_state`
- `dead_leg_wait`
- `ambiguous_structure`

### 4-4. modifier

`modifier`는 장면을 더 잘 설명하는 보조 정보다.

예:

- `depth = reclaim`
- `severity = thesis_void`
- `structure_overlap = fvg`

### 4-5. action

`action`은 실제로 지금 할 일이다.

예:

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

### 4-6. outcome

`outcome`은 hindsight 기준에서
무엇이 맞았는지다.

예:

- `hindsight_best_management_action_label = FULL_EXIT`

---

## 5. scene naming guard

이번 조언에서 아주 중요한 포인트 중 하나는
scene과 action 이름이 너무 닮으면 헷갈린다는 점이다.

그래서 v1에서는 아래 원칙을 잠근다.

### 5-1. 원칙

scene 이름은 가능한 한
`시장 상태`를 설명해야 하고,
action 이름은 `명령`을 설명해야 한다.

즉:

- scene은 설명어
- action은 행동어

### 5-2. canonical scene 이름

v1 canonical scene 이름은 아래처럼 잡는다.

| 기존 표현 | canonical scene |
|---|---|
| `runner_hold` | `runner_healthy` |
| `partial_then_hold` | `profit_trim_zone` |
| `add_to_position` | `add_setup` |
| `rebuy_ready` | `rebuy_setup` |
| `fvg_fill` | `fvg_response_zone` |
| `time_decay_exit` | `time_decay_risk` |
| `protective_exit` | `protective_risk` |

아래는 scene 그대로 유지해도 된다.

- `trend_ignition`
- `breakout`
- `breakout_retest_hold`
- `liquidity_sweep_reclaim`
- `orderblock_reaction`
- `pullback_continuation`
- `reaccumulation`
- `redistribution`
- `failed_transition`
- `trend_exhaustion`
- `climax_reversal`

### 5-3. compatibility rule

초기 문서나 artifact에서 기존 표현이 남아 있더라도,
v1 구현의 canonical internal field는 위 표를 따른다.

즉:

- 화면/문서 alias는 허용
- 내부 canonical field는 분리

이렇게 해야 scene과 action이 섞이지 않는다.

---

## 6. v1 independent scene, gate, modifier lock

### 6-1. v1 coarse family lock

아래 5개를 coarse family로 고정한다.

- `ENTRY_INITIATION`
- `CONTINUATION`
- `POSITION_MANAGEMENT`
- `DEFENSIVE_EXIT`
- `NO_TRADE`

### 6-2. v1 fine scene dictionary lock

이번 v1 dictionary는 아래처럼 잠근다.

#### Entry Initiation

- `trend_ignition`
- `breakout`
- `breakout_retest_hold`
- `liquidity_sweep_reclaim`
- `orderblock_reaction`

#### Continuation

- `pullback_continuation`
- `reaccumulation`
- `redistribution`

#### Position Management

- `runner_healthy`
- `profit_trim_zone`
- `add_setup`
- `rebuy_setup`
- `fvg_response_zone`
- `time_decay_risk`

#### Defensive Exit

- `failed_transition`
- `protective_risk`
- `trend_exhaustion`
- `climax_reversal`

### 6-3. v1 gate lock

gate는 아래 3개만 사용한다.

- `ambiguous_structure`
- `dead_leg_wait`
- `low_edge_state`

### 6-4. v1 modifier lock

modifier는 아래 우선순위 집합으로 잠근다.

#### risk modifier

- `late_trend`
- `climax_risk`
- `thesis_void`

#### structure modifier

- `reclaim`
- `fvg_overlap`
- `orderblock_overlap`
- `retest_clean`

#### shape modifier

- `shallow_pullback`
- `deep_pullback`
- `compressed_range`

### 6-5. modifier priority lock

modifier가 동시에 여러 개 붙을 때 우선순위는 아래다.

1. `gate modifier`
2. `risk modifier`
3. `structure modifier`
4. `shape modifier`

충돌 시에는
항상 더 보수적인 쪽을 우선한다.

---

## 7. v1 activated scene set

dictionary 전체와 실제 1차 활성화를 분리한다.

### 7-1. dictionary는 넓게 잠근다

scene vocabulary는 넓게 가져간다.

### 7-2. 그러나 heuristic 1차 활성화는 5개부터 시작한다

아래 5개를 먼저 적극 활성화한다.

- `trend_exhaustion`
- `low_edge_state`
- `time_decay_risk`
- `liquidity_sweep_reclaim`
- `breakout_retest_hold`

이유:

- action 차이가 분명하다
- heuristic 규칙을 만들기 쉽다
- 사람이 검증하기 쉽다
- 초기 dataset 품질이 상대적으로 안정적이다

### 7-3. 2차 활성화 후보

아래는 그 다음에 연다.

- `runner_healthy`
- `protective_risk`
- `failed_transition`
- `pullback_continuation`
- `profit_trim_zone`

---

## 8. scene confidence band lock

### 8-1. v1 값

`runtime_scene_confidence_band`는 아래 3개로 잠근다.

- `high`
- `medium`
- `low`

### 8-2. 의미

#### high

- scene 신뢰도가 높다
- action resolver가 scene bias를 강하게 참고할 수 있다

#### medium

- scene은 의미 있지만
- score 경쟁을 더 우선한다

#### low

- scene은 기록만 남기고
- action 영향은 거의 주지 않는다

### 8-3. 점수에서 band로 가는 예시

v1 heuristic에서는 아래처럼 단순화한다.

- `>= 0.80` -> `high`
- `0.60 ~ 0.79` -> `medium`
- `< 0.60` -> `low`

이 구간은 SA2에서 heuristic calibration 후 미세조정 가능하다.

---

## 9. scene action bias strength lock

scene confidence와 별개로,
scene이 action에 얼마나 세게 관여해야 하는지도 따로 둔다.

### 9-1. v1 값

`runtime_scene_action_bias_strength`는 아래 4개로 잠근다.

- `none`
- `soft`
- `medium`
- `hard`

### 9-2. 의미

#### none

scene은 저장만 하고
action에 영향 거의 없음

#### soft

scene이 작은 hint를 준다

#### medium

scene이 action 후보 순서를 조금 바꿀 수 있다

#### hard

scene이 보수 방향으로 강하게 bias를 준다
단, 여전히 최종 결정은 resolver가 한다

### 9-3. 중요한 원칙

`hard`라도 scene이 action을 단독 결정하지는 못한다.

예외에 가까운 것은 gate뿐이다.

---

## 10. scene maturity lock

### 10-1. v1 값

`runtime_scene_maturity`는 아래 3개로 잠근다.

- `provisional`
- `probable`
- `confirmed`

### 10-2. 의미

#### provisional

- 막 찍힌 장면
- 아직 뒤집힐 가능성이 크다

#### probable

- 어느 정도 맞아 보이지만
- 아직 완전히 확정된 것은 아니다

#### confirmed

- 이후 몇 봉과 구조가 scene 가설을 지지한다

### 10-3. resolver 사용 원칙

- `provisional`: 보수적 사용
- `probable`: hint 사용
- `confirmed`: 더 강한 bias 허용

### 10-4. maturity action activation rule

실시간 row에서 scene이 자주 바뀔 수 있으므로,
action bias 활성화 시점은 아래처럼 잠근다.

- `provisional`
  - scene은 기록 위주
  - action resolver는 기존 score와 기존 action을 우선 유지
- `probable`
  - scene bias를 action resolver가 반영할 수 있다
  - 다만 여전히 score competition이 더 중요하다
- `confirmed`
  - scene bias를 더 강하게 반영할 수 있다

한 줄 원칙:

> `probable` 이상이 되어야 scene action bias가 본격적으로 작동하고,
> `provisional`에서는 기존 action을 최대한 유지한다.

---

## 11. transition lock

### 11-1. transition은 v1 필수다

scene은 점보다 전이가 중요하다.

그래서 transition 관련 컬럼을 v1에 포함한다.

### 11-2. 최소 컬럼

- `runtime_scene_transition_from`
- `runtime_scene_transition_bars`
- `runtime_scene_transition_speed`

### 11-3. speed 값

- `fast`
- `normal`
- `slow`

### 11-4. v1 핵심 transition pair

초기에는 아래 전이만 집중 추적한다.

- `trend_ignition -> breakout`
- `breakout -> breakout_retest_hold`
- `breakout -> time_decay_risk`
- `pullback_continuation -> runner_healthy`
- `runner_healthy -> trend_exhaustion`
- `trend_exhaustion -> climax_reversal`
- `runner_healthy -> protective_risk`
- `protective_risk -> failed_transition`
- `time_decay_risk -> rebuy_setup`

이 전이들은 path-aware 구조와 직접 연결되므로
v1에서 먼저 본다.

---

## 12. surface-scene alignment lock

### 12-1. v1 필수 컬럼

- `runtime_scene_family_alignment`

### 12-2. 값

- `aligned`
- `upgrade`
- `downgrade`
- `conflict`

### 12-3. 의미

#### aligned

surface와 scene coarse family가 자연스럽게 맞는다.

#### upgrade

scene이 surface보다 더 보수적인 방향을 제안한다.

예:

- `continuation_hold_surface`
- scene은 `protective_risk`

이 경우는 scene 쪽을 더 신뢰할 수 있다.

#### downgrade

scene이 surface보다 더 공격적인 방향을 제안한다.

예:

- `protective_exit_surface`
- scene은 `breakout_retest_hold`

이 경우는 자동 action 변경 금지,
보수적으로 유지한다.

#### conflict

surface와 scene이 강하게 어긋난다.

이 경우는 기본적으로
`log_only + review flag`다.

### 12-4. resolver rule lock

아래 규칙을 잠근다.

1. `aligned`
   - 정상 처리
2. `upgrade`
   - 보수 방향 bias 허용
3. `downgrade`
   - 자동 공격 전환 금지
4. `conflict`
   - log-only 우선, manual review 가능

---

## 13. gate block level lock

### 13-1. v1 필수 컬럼

- `runtime_scene_gate_block_level`

### 13-2. 값

- `none`
- `entry_block`
- `all_block`

### 13-3. gate별 기본 block level

| gate | block level | 의미 |
|---|---|---|
| `none` | `none` | 제약 없음 |
| `low_edge_state` | `entry_block` | 신규 진입, 추가 진입, 재진입 억제 |
| `dead_leg_wait` | `all_block` | 신규 진입과 공격적 추가 모두 차단 |
| `ambiguous_structure` | `all_block` | 신규 진입과 공격적 추가 모두 차단 |

### 13-4. resolver 적용 원칙

- `entry_block`
  - `ENTER`, `ADD`, `REBUY` 억제
  - 기존 포지션 관리 자체는 가능
- `all_block`
  - 신규 공격 행동 억제
  - `WAIT`, `PARTIAL_EXIT`, 방어적 행동 우선

---

## 14. hindsight scene resolution lock

scene axis는 hindsight 기준도 잠가야 한다.

### 14-1. 기본 원칙

hindsight scene은 이후 `N`봉의 결과를 보고 판정한다.

v1 기본 horizon은
symbol/tf 튜닝 전 공통 기본값으로
`20 bars`를 둔다.

### 14-2. v1 기본 규칙

#### `time_decay_risk`

- 이후 `N`봉 동안 `±0.3R` 안에 머물고
- 변동성 축소가 유지되면
- hindsight는 `time_decay_risk`

#### `failed_transition`

- 이후 구조 붕괴가 확인되고
- `-1R` 또는 thesis break가 확인되면
- hindsight는 `failed_transition`

#### `trend_exhaustion`

- 이후 3 leg 내에 확장 둔화와 반전이 확인되면
- hindsight는 `trend_exhaustion`

#### `breakout_retest_hold`

- retest 후 `2R+` 확장 또는 구조 유지가 확인되면
- hindsight는 `breakout_retest_hold`

#### `liquidity_sweep_reclaim`

- reclaim 후 빠른 복귀 확장이 확인되면
- hindsight는 `liquidity_sweep_reclaim`

### 14-3. 판정 불가

판정이 불가하면:

- `hindsight_scene_fine_label = unresolved`
- `hindsight_scene_quality_tier = diagnostic_only`

---

## 15. SA1에 실제로 추가할 최소 컬럼

이번 scope lock 기준으로
SA1에서 최소 아래 컬럼을 추가한다.

### 15-1. runtime scene core

- `runtime_scene_coarse_family`
- `runtime_scene_fine_label`
- `runtime_scene_gate_label`
- `runtime_scene_modifier_json`
- `runtime_scene_confidence`
- `runtime_scene_confidence_band`
- `runtime_scene_action_bias_strength`
- `runtime_scene_source`
- `runtime_scene_maturity`

### 15-2. transition / alignment / gate

- `runtime_scene_transition_from`
- `runtime_scene_transition_bars`
- `runtime_scene_transition_speed`
- `runtime_scene_family_alignment`
- `runtime_scene_gate_block_level`

### 15-3. hindsight scene

- `hindsight_scene_fine_label`
- `hindsight_scene_quality_tier`

즉 SA1 최소 컬럼 집합은 총 16개다.

---

## 16. SA2 heuristic seed 기준

SA2에서는 5개 우선 장면만 rule 기반으로 먼저 붙인다.

### 16-1. `trend_exhaustion`

권장 seed 규칙:

- leg 내 swing count `>= 3`
- 마지막 swing 크기 `<` 이전 swing 크기의 `70%`
- 볼륨 다이버전스 또는 push 약화

confidence 예시:

- 3개 충족 -> `0.85`
- 2개 충족 -> `0.65`

### 16-2. `low_edge_state`

권장 seed 규칙:

- stop 거리 `>` `1.5 x ATR20`
- 또는 target 거리 `< 1.0 x ATR20`
- 또는 기대 R/R `< 1.5`

### 16-3. `time_decay_risk`

권장 seed 규칙:

- 자산별 기준 bars 초과
- 현재 PnL이 `±0.3R` 이내
- ATR 축소

### 16-4. `liquidity_sweep_reclaim`

권장 seed 규칙:

- wick이 prior swing을 잠깐 돌파
- close가 다시 안쪽 복귀
- volume spike
- 다음 봉 reclaim 방향 지지

### 16-5. `breakout_retest_hold`

권장 seed 규칙:

- 직전 breakout 존재
- retest가 breakout level 근처에서 멈춤
- retest volume 약화
- 반발 캔들 확인

---

## 17. SA2.5 sanity check lock

SA2와 SA3 사이에 아래 체크를 반드시 둔다.

### 17-1. 분포 확인

- 최근 200개 이상 row에서
- 특정 scene이 `80%+`를 먹으면 기준이 너무 느슨한지 확인
- 특정 scene이 `1% 미만`이면 기준이 너무 빡빡한지 확인

### 17-2. alignment 확인

- `runtime_scene_family_alignment`
  분포 확인
- `conflict` 비율이 과도하면 heuristic 수정

### 17-3. transition sanity 확인

- 불가능한 transition이 과도한지 확인

예:

- `failed_transition -> breakout_retest_hold`
  가 즉시 과도하게 나오면 규칙 점검

### 17-4. 사람 눈 샘플 확인

- 최근 샘플 최소 20개
- 사람이 표본을 직접 보고
  scene이 너무 이상하지 않은지 확인

---

## 18. 수정된 구현 순서

이번 scope lock 기준 구현 순서는 아래로 고정한다.

1. `SA0 Scene Axis Scope Lock`
2. `SA1 Scene Schema Extension`
3. `SA2 Heuristic Scene Tagger`
4. `SA2.5 Heuristic Sanity Check`
5. `SA3 Scene Dataset Export`
6. `SA5 Log-Only Runtime Bridge`
7. `SA6 Action Resolver Integration`
8. `SA4 Scene Candidate Pipeline`
9. `SA7 Bounded Adoption`
10. `SA8 State25-Style Promotion Loop`

### 왜 SA4보다 SA5/SA6을 먼저 두는가

이건 아주 중요하다.

처음엔 model보다
아래 3개를 먼저 안정화해야 한다.

- scene 분포
- surface-scene alignment
- scene transition 일관성

즉,
초기에는 heuristic scene이 row에서 어떻게 찍히는지부터 안정화하고,
그다음 candidate pipeline을 여는 것이 맞다.

---

## 19. 최종 결론

이번 scope lock의 결론은 아래다.

1. `scene axis`는 현재 시스템에 잘 맞는다.
2. 하지만 scene은 action을 설명하고 bias를 주는 축이지, action을 혼자 결정하면 안 된다.
3. `gate`, `maturity`, `alignment`, `transition`, `confidence band`, `action bias strength`는 v1에서 바로 잠가야 한다.
4. scene은 라벨만 붙이는 축이 아니라, `context + transition + gate + action bias`를 묶는 중간 설명 계층이다.

즉 한 줄로 정리하면:

> SA0에서 이 경계를 제대로 잠가두면,
> SA1부터는 흔들리지 않고 구현을 이어갈 수 있다.
