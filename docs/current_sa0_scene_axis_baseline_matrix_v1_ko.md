# Current SA0 Scene Axis Baseline Matrix v1

## 목적

이 문서는 `scene axis` 구현의 토대를 흔들리지 않게 잡기 위한
`SA0 baseline matrix` 문서다.

쉽게 말하면,
앞으로 SA1, SA2, SA3에서 구현자가 헷갈리지 않게
`무엇을 독립 label로 보고`,
`무엇을 gate로 보고`,
`무엇을 modifier로 보고`,
`어떤 경우에 action을 보수적으로 유지해야 하는지`
를 표로 잠가두는 문서다.

이 문서는 `설계 설명`보다 더 기초적인 문서다.
즉 "이론"보다 "기준표"에 가깝다.

관련 문서:

- [current_checkpoint_scene_axis_design_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_design_v1_ko.md)
- [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
- [current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md)

---

## 1. 제일 먼저 잠그는 원칙

이 문서에서 가장 중요한 원칙은 아래 5개다.

1. `surface`는 문제 종류다.
2. `scene`은 지금 벌어진 장면이다.
3. `action`은 실제로 할 일이다.
4. `gate`는 action을 막거나 약하게 만드는 보수 장치다.
5. `scene`은 action을 설명하고 bias를 주지만, 혼자 action을 결정하지 못한다.

즉 최종 구조는 아래처럼 본다.

```text
surface -> checkpoint -> scene -> score -> gate -> resolver -> action -> hindsight
```

---

## 2. 문서 읽는 순서

토대를 잡을 때는 아래 순서로 보면 된다.

1. 이 문서
   - 가장 기초적인 기준표 확인
2. [current_checkpoint_scene_axis_scope_lock_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_scope_lock_v1_ko.md)
   - 범위와 세부 규칙 확인
3. [current_checkpoint_scene_axis_design_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_scene_axis_design_v1_ko.md)
   - 큰 구조와 방향 확인
4. [current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_spec_v1_ko.md)
   - 기존 checkpoint 기본 구조 확인
5. [current_path_aware_checkpoint_decision_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_path_aware_checkpoint_decision_implementation_roadmap_ko.md)
   - PA/SA 구현 순서 확인

---

## 3. 핵심 축 구분표

| 축 | 질문 | 예시 | 직접 action 결정? |
|---|---|---|---|
| `surface` | 지금 무슨 종류의 문제인가 | `initial_entry_surface`, `continuation_hold_surface` | 아니오 |
| `checkpoint_type` | leg 안에서 지금 어느 위치인가 | `INITIAL_PUSH`, `RUNNER_CHECK` | 아니오 |
| `scene` | 지금 시장에 무슨 장면이 벌어졌나 | `breakout`, `trend_exhaustion` | 아니오 |
| `gate` | 지금 보수적으로 막아야 하나 | `low_edge_state`, `dead_leg_wait` | 일부 차단 |
| `modifier` | 장면을 더 자세히 설명하면 어떤가 | `reclaim`, `thesis_void` | 아니오 |
| `score` | continuation/reversal/hold 품질은 어떤가 | `runtime_hold_quality_score` | 아니오 |
| `action` | 지금 뭘 해야 하나 | `HOLD`, `FULL_EXIT` | 예 |
| `outcome` | 나중에 보니 뭐가 맞았나 | hindsight label | 아니오 |

한 줄로 요약하면:

- `checkpoint_type`은 위치
- `scene`은 장면
- `action`은 행동

이 셋은 서로 다른 축이다.

---

## 4. independent scene baseline

아래는 v1에서 독립 scene으로 보는 baseline 표다.

### 4-1. Entry Initiation

| coarse | scene | 설명 | 주로 연결되는 surface |
|---|---|---|---|
| `ENTRY_INITIATION` | `trend_ignition` | 추세 점화 시작 | `initial_entry_surface` |
| `ENTRY_INITIATION` | `breakout` | 레벨 돌파 | `initial_entry_surface` |
| `ENTRY_INITIATION` | `breakout_retest_hold` | 돌파 후 리테스트 유지 | `initial_entry_surface` |
| `ENTRY_INITIATION` | `liquidity_sweep_reclaim` | 유동성 스윕 후 복귀 | `initial_entry_surface` |
| `ENTRY_INITIATION` | `orderblock_reaction` | order block 반응 | `initial_entry_surface` |

### 4-2. Continuation

| coarse | scene | 설명 | 주로 연결되는 surface |
|---|---|---|---|
| `CONTINUATION` | `pullback_continuation` | 눌림 후 지속 | `follow_through_surface` |
| `CONTINUATION` | `reaccumulation` | 재축적 | `follow_through_surface` |
| `CONTINUATION` | `redistribution` | 재분배 | `follow_through_surface` |

### 4-3. Position Management

| coarse | scene | 설명 | 주로 연결되는 surface |
|---|---|---|---|
| `POSITION_MANAGEMENT` | `runner_healthy` | 건강한 runner 유지 장면 | `continuation_hold_surface` |
| `POSITION_MANAGEMENT` | `profit_trim_zone` | 일부 확보가 자연스러운 구간 | `continuation_hold_surface` |
| `POSITION_MANAGEMENT` | `add_setup` | 추가 진입 구조 | `continuation_hold_surface` |
| `POSITION_MANAGEMENT` | `rebuy_setup` | 재진입 준비 구조 | `continuation_hold_surface` |
| `POSITION_MANAGEMENT` | `fvg_response_zone` | FVG 채움 반응 구간 | `continuation_hold_surface` |
| `POSITION_MANAGEMENT` | `time_decay_risk` | 시간이 지나며 기대값이 죽는 구간 | `continuation_hold_surface` |

### 4-4. Defensive Exit

| coarse | scene | 설명 | 주로 연결되는 surface |
|---|---|---|---|
| `DEFENSIVE_EXIT` | `failed_transition` | 구조 실패/전환 | `protective_exit_surface` |
| `DEFENSIVE_EXIT` | `protective_risk` | 방어 청산을 고려할 위험 장면 | `protective_exit_surface` |
| `DEFENSIVE_EXIT` | `trend_exhaustion` | 과열/소진 | `protective_exit_surface` |
| `DEFENSIVE_EXIT` | `climax_reversal` | 클라이맥스성 반전 | `protective_exit_surface` |

---

## 5. gate baseline

gate는 독립 scene이 아니라 별도 억제 축이다.

| gate | 의미 | 신규진입 | 추가진입 | 보유관리 |
|---|---|---|---|---|
| `none` | 제약 없음 | 허용 | 허용 | 정상 |
| `low_edge_state` | 방향은 보이지만 돈이 안 되는 자리 | 차단 | 차단 | 정상 |
| `dead_leg_wait` | 방향은 보이지만 에너지가 죽은 자리 | 차단 | 차단 | 축소 bias |
| `ambiguous_structure` | 구조 자체가 불명확한 자리 | 차단 | 차단 | 축소 bias |

즉 gate는 아래처럼 작동한다.

- `low_edge_state`
  - 새로 공격적으로 들어가는 것만 막는다
- `dead_leg_wait`
  - 새 공격도 막고, 있는 포지션도 줄이는 쪽으로 기운다
- `ambiguous_structure`
  - 가장 보수적으로 다룬다

---

## 6. modifier baseline

modifier는 독립 scene처럼 커지지 못하게 막는다.

| modifier family | modifier | 설명 |
|---|---|---|
| `risk` | `late_trend` | 추세 후반 위험 |
| `risk` | `climax_risk` | 급격한 과열 위험 |
| `risk` | `thesis_void` | thesis가 거의 무너진 상태 |
| `structure` | `reclaim` | 되찾기 구조 |
| `structure` | `fvg_overlap` | FVG 겹침 |
| `structure` | `orderblock_overlap` | OB 겹침 |
| `structure` | `retest_clean` | 리테스트가 깔끔함 |
| `shape` | `shallow_pullback` | 얕은 눌림 |
| `shape` | `deep_pullback` | 깊은 눌림 |
| `shape` | `compressed_range` | 압축된 범위 |

### modifier priority

modifier 우선순위는 아래다.

1. gate 관련 보수 신호
2. risk modifier
3. structure modifier
4. shape modifier

충돌 시 항상 더 보수적인 해석을 우선한다.

---

## 7. maturity baseline

scene은 바로 확정되지 않을 수 있다.
그래서 maturity를 따로 둔다.

| maturity | 의미 | action 영향 |
|---|---|---|
| `provisional` | 막 찍힌 가설 | 거의 없음 |
| `probable` | 어느 정도 맞아 보임 | 일부 bias 허용 |
| `confirmed` | 구조와 이후 진행이 지지함 | 강한 bias 허용 |

### 핵심 원칙

> `probable` 이상이 되어야 scene bias가 action에 본격 반영되고,
> `provisional`에서는 기존 action과 score를 최대한 유지한다.

---

## 8. confidence band baseline

| band | 의미 | resolver 사용 |
|---|---|---|
| `high` | 신뢰도 높음 | scene hint 강하게 반영 가능 |
| `medium` | 중간 | score 경쟁 우선, scene은 보조 |
| `low` | 약함 | 기록 위주, action 영향 거의 없음 |

권장 기본 매핑:

- `>= 0.80` -> `high`
- `0.60 ~ 0.79` -> `medium`
- `< 0.60` -> `low`

---

## 9. action bias strength baseline

scene이 action에 얼마나 세게 관여할지를 따로 둔다.

| bias strength | 의미 |
|---|---|
| `none` | 영향 없음 |
| `soft` | 약한 hint |
| `medium` | 후보 순서 정도 조정 |
| `hard` | 보수 방향으로 강한 bias |

중요:

`hard`라도 scene이 혼자 최종 action을 결정하지는 못한다.
최종 결정은 항상 resolver가 한다.

---

## 10. alignment baseline

surface와 scene이 어긋날 때의 기준표다.

| alignment | 의미 | 처리 원칙 |
|---|---|---|
| `aligned` | 자연스럽게 맞음 | 정상 처리 |
| `upgrade` | scene이 더 보수적임 | scene 우선 |
| `downgrade` | scene이 더 공격적임 | surface 유지 |
| `conflict` | 강하게 충돌함 | `log_only + manual review` |

### 한 줄 원칙

- scene이 surface보다 더 보수적이면 -> scene 우선
- scene이 surface보다 더 공격적이면 -> surface 유지
- 판단이 애매하면 -> `log_only + manual review`

즉 항상 보수적인 쪽이 먼저다.

---

## 11. transition baseline

scene은 점보다 전이가 중요하다.
v1에서는 아래 전이를 우선 본다.

| from | to | 의미 |
|---|---|---|
| `trend_ignition` | `breakout` | 점화 후 돌파 |
| `breakout` | `breakout_retest_hold` | 돌파 후 검증 |
| `breakout` | `time_decay_risk` | 돌파 실패/정체 |
| `pullback_continuation` | `runner_healthy` | 눌림 후 정상 진행 |
| `runner_healthy` | `trend_exhaustion` | 건강한 추세에서 소진으로 |
| `trend_exhaustion` | `climax_reversal` | 과열 후 반전 |
| `runner_healthy` | `protective_risk` | 정상 진행에서 방어 경계로 |
| `protective_risk` | `failed_transition` | 경고에서 붕괴로 |
| `time_decay_risk` | `rebuy_setup` | 시간 손절 후 재진입 기회 |

transition 추적 기본 컬럼:

- `runtime_scene_transition_from`
- `runtime_scene_transition_bars`
- `runtime_scene_transition_speed`

---

## 12. SA1 최소 컬럼 baseline

SA1에서 실제로 storage에 넣는 최소 컬럼은 아래다.

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

즉 SA1은
scene을 맞히는 단계가 아니라
scene이 지나갈 통로를 먼저 여는 단계다.

---

## 13. SA2에서 처음 열 장면 5개

처음 heuristic으로 붙일 장면은 아래 5개로 잠근다.

- `trend_exhaustion`
- `low_edge_state`
- `time_decay_risk`
- `liquidity_sweep_reclaim`
- `breakout_retest_hold`

이유:

- 사람이 봐도 설명하기 쉽다
- 행동 차이가 뚜렷하다
- rule seed를 만들기 쉽다
- 잘못 붙었는지 검증하기 쉽다

---

## 14. SA2.5 sanity baseline

SA2와 SA3 사이에는 반드시 sanity check를 둔다.

최소 확인 항목:

- 최근 200개 row에서 scene 분포 확인
- 특정 scene이 80% 이상이면 기준이 너무 느슨한지 확인
- 특정 scene이 1% 미만이면 기준이 너무 빡빡한지 확인
- `alignment=conflict` 비율 확인
- 전이 분포가 너무 이상하지 않은지 확인
- 사람이 샘플 20개 눈으로 직접 확인

---

## 15. SA 단계별 해석

이 문서를 기준으로 SA는 이렇게 이해하면 된다.

- `SA0`
  - 토대 잠금
- `SA1`
  - 컬럼/통로 만들기
- `SA2`
  - heuristic scene seed 붙이기
- `SA2.5`
  - heuristic sanity 검증
- `SA3`
  - scene dataset / hindsight 연결
- `SA4`
  - scene candidate pipeline
- `SA5`
  - log-only runtime bridge
- `SA6`
  - action resolver에 scene bias 연결
- `SA7`
  - bounded adoption
- `SA8`
  - retrain/compare/promote 루프

---

## 16. 아주 짧은 결론

이 문서의 목적은 복잡한 설명이 아니다.

한 줄로 줄이면 이거다.

> `scene axis`를 붙이기 전에,
> 무엇이 진짜 장면이고 무엇이 gate이고 무엇이 modifier인지,
> 그리고 언제 보수적으로 유지해야 하는지를 먼저 표로 잠가두자.

이 문서가 잠기면
그 다음 SA1, SA2, SA3은 훨씬 덜 흔들리게 된다.
