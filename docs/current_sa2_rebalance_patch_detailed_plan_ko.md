# Current SA2 Rebalance Patch Detailed Plan

## 목적

이번 패치의 목적은 `SA2.5`에서 확인된 3가지 편향을 바로 줄이는 것이다.

1. `trend_exhaustion`이 건강한 runner row까지 너무 많이 먹는 문제
2. `low_edge_state`가 실제 early row에서 한 건도 잡히지 않는 문제
3. `trend_exhaustion <-> time_decay_risk` 전이쌍이 과도하게 잡히는 문제

이번 패치는 `SA2를 다시 설계`하는 게 아니라,
현재 heuristic seed를 더 보수적이고 더 분리되게 다듬는 보강 패치다.

---

## SA2.5에서 실제로 본 문제

기준 artifact:

- [checkpoint_scene_sanity_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_scene_sanity_latest.json)

핵심 수치:

- `scene_filled_row_count = 1252`
- `trend_exhaustion = 1080`
- `time_decay_risk = 99`
- `breakout_retest_hold = 73`
- `low_edge_state = 0`

즉 “scene가 안 붙는다”가 아니라,
**붙기는 붙는데 특정 scene가 너무 많이 먹고, 특정 gate는 전혀 안 잡히는 상태**다.

---

## 이번 패치에서 내리는 결정

## 결정 1. `trend_exhaustion`은 더 늦고 더 약해진 구간에서만 허용한다

이전 규칙은 아래가 너무 넓었다.

- late checkpoint
- partial exit score가 높음
- runner_secured 또는 giveback

이러면 건강한 runner도 많이 들어온다.

### 새 원칙

`trend_exhaustion`은

- 이미 늦은 구간이고
- 아직 완전히 실패하진 않았지만
- `partial` 쪽 근거가 `hold`보다 우세하고
- 실제 피로 징후가 있는 경우

에만 붙인다.

### 구현 방향

- `partial_exit_ev >= hold_quality + margin`
- `continuation - reversal`이 너무 크게 벌어져 있으면 제외
- `giveback_ratio`, `reversal pressure`, `late-trend weakening` 중 최소 하나 이상이 더 강하게 필요
- `OPEN_LOSS` 성격 row에는 붙이지 않는다

한 줄로 말하면:

> `trend_exhaustion`은 “좋은 추세”가 아니라 “좋은 추세의 후반 피로”일 때만 붙여야 한다.

---

## 결정 2. `low_edge_state`는 flat row만 보지 않는다

이전 규칙은 사실상

- `FLAT`이거나
- `size_fraction < 0.75`

에 너무 기대고 있었다.

그런데 실전에서 `low_edge_state`는
이미 포지션이 있어도
“여기서 더 싣는 건 edge가 약하다”를 뜻할 수 있다.

### 새 원칙

`low_edge_state`는

- entry/follow-through checkpoint에서
- signal이 균형적이고
- 강한 확신이 없고
- 지금 새로 진입/추가하기엔 edge가 약한 상태

를 가리키는 gate다.

### 구현 방향

- `position_side != FLAT`이어도 허용
- 단 `gate_block_level = entry_block`이라
  기존 포지션 관리 자체를 막지는 않는다
- `balanced_checkpoint_state` 계열, `signal spread 작음`, `max_signal 과도하지 않음`
  조합이면 gate 후보로 본다

한 줄로 말하면:

> `low_edge_state`는 “아무 포지션도 없을 때만”이 아니라 “지금 여기서 새로 공격하기엔 edge가 약할 때”를 뜻한다.

---

## 결정 3. `trend_exhaustion <-> time_decay_risk`는 지금은 허용 pair로 승격하지 않는다

이번 SA2.5에서 이 pair가 가장 많이 보였지만,
바로 허용 pair로 넣지는 않는다.

왜냐하면 지금 단계에서는
이 전이의 상당수가

- 다른 trade/path가 섞여서 생긴 것인지
- 실제 heuristic 흔들림인지

먼저 구분해야 하기 때문이다.

### 새 원칙

- 우선 `transition audit key`를 `symbol only`가 아니라
  `trade_link_key -> leg_id -> symbol` 순으로 더 정교하게 본다
- 그 다음에도 많이 남는다면
  그때 허용 pair 승격 여부를 결정한다

즉 지금 결론은:

> 이 전이는 바로 “허용된 자연 전이”로 보지 않고,
> 먼저 같은 path 안에서만 보도록 바꿔서 재측정한다.

---

## 구현 파일

### 수정 파일

- [path_checkpoint_scene_tagger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_tagger.py)
- [path_checkpoint_scene_sanity.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_sanity.py)

### 테스트 수정

- [test_path_checkpoint_scene_tagger.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_scene_tagger.py)
- [test_path_checkpoint_scene_sanity.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_scene_sanity.py)
- [test_build_checkpoint_scene_sanity_check.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_build_checkpoint_scene_sanity_check.py)

---

## 구체 수정안

## 1. `trend_exhaustion` 좁히기

### 이전 문제

- `runner_secured`만 있어도 잘 붙음
- `giveback=0`인 건강한 runner도 late bars만 많으면 먹힘
- `OPEN_LOSS`와 섞이는 late row도 일부 들어옴

### 새 규칙

- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `bars_since_leg_start >= symbol threshold`
- `unrealized_pnl_state = OPEN_PROFIT` 또는 `runner_secured = true`
- `partial_exit_ev >= max(0.60, hold_quality + 0.02)`
- 아래 중 하나 이상
  - `giveback_ratio >= 0.18`
  - `reversal_odds >= 0.52`
  - `continuation_odds - reversal_odds <= 0.24`
- 추가 억제 규칙
  - `continuation_odds > 0.90`이고 `giveback_ratio < 0.12`면 제외
  - `OPEN_LOSS`는 제외

### 기대 효과

- healthy runner row가 `trend_exhaustion`으로 덜 들어감
- `trend_exhaustion`은 더 늦고 더 피로한 장면에만 남음

---

## 2. `time_decay_risk` 좁히기

### 이전 문제

- `OPEN_LOSS` late row가 time_decay로도 자주 들어옴
- 그래서 `trend_exhaustion <-> time_decay_risk` 흔들림이 커짐

### 새 규칙

- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `bars_since_leg_start >= symbol threshold`
- `unrealized_pnl_state in {FLAT, OPEN_PROFIT}`
- `runner_secured = false`
- `hold_quality_score <= 0.36`
- `partial_exit_ev <= 0.46`
- `continuation_odds <= 0.56`
- `small_motion` 유지

### 기대 효과

- severe loss/protective row가 time_decay로 잘못 분류되는 것을 줄임
- time_decay는 진짜 “안 가는 포지션” 위주로 남음

---

## 3. `low_edge_state` 완화

### 이전 문제

- 사실상 flat/small-size 위주로만 후보를 봄
- 실제 early hold row는 gate에 못 들어옴

### 새 규칙

- `checkpoint_type in {INITIAL_PUSH, FIRST_PULLBACK_CHECK, RECLAIM_CHECK}`
- `surface_name in {initial_entry_surface, follow_through_surface, continuation_hold_surface}`
- `abs(continuation - reversal) <= 0.10`
- `max_signal <= 0.68`
- `full_exit_risk < 0.70`
- `rebuy_readiness < 0.66`
- `runtime_score_reason`이 `balanced_checkpoint_state` 계열이면 가산점
- `position_side`는 제한하지 않음

### 기대 효과

- 실제 early row에서도 entry-block gate가 찍히기 시작함
- “추가 진입은 말자” 성격의 row를 더 잘 남김

---

## 4. transition audit key 강화

### 이전 방식

- symbol 기준으로만 이전 scene를 따라감

문제:

- 같은 symbol 안의 다른 trade/path가 섞이면
  가짜 transition이 생김

### 새 방식

- `trade_link_key`가 있으면 그것을 우선
- 없으면 `leg_id`
- 그것도 없으면 `symbol`

### 기대 효과

- transition count가 path-aware하게 바뀜
- `trend_exhaustion <-> time_decay_risk`가 실제 흔들림인지 더 정확히 보임

---

## 테스트 포인트

### 꼭 확인할 것

1. healthy runner row가 더 이상 쉽게 `trend_exhaustion`이 되지 않는가
2. open-loss late row가 `time_decay_risk`로 잘못 분류되지 않는가
3. early balanced row에서 `low_edge_state`가 실제로 잡히는가
4. transition pair count가 audit key 강화 후 줄어드는가

---

## 완료 기준

- `trend_exhaustion` 점유율이 현재보다 유의미하게 낮아진다
- `low_edge_state`가 0건에서 벗어난다
- `unexpected_transition_pair_counts`가 줄어든다
- `recommended_next_action`이 지금보다 덜 보수적으로 바뀔 여지가 생긴다

---

## 한 줄 결론

이번 패치는 scene 엔진을 더 크게 만드는 작업이 아니라, **지금 붙은 heuristic seed가 한쪽으로 쏠리지 않게 균형을 다시 맞추는 작업**이다.
