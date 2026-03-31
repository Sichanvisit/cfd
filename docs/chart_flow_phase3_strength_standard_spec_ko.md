# 차트 Flow Phase 3 Strength 10단계 표준화 상세안

## 목적

이 문서는 Phase 3에서 사용할 `strength_level 1..10` 공통 강도 축의 기준을 정의한다.

목표는 아래 한 줄이다.

`같은 6단계 buy는 심볼이 달라도 비슷한 체감 강도로 보이게 만들기`

즉 이 문서의 역할은:

- strength 계산 입력을 고정하고
- 버킷 의미를 고정하고
- event family별 시각 binding을 고정해서
- 심볼마다 달라 보이던 `약함 / 보통 / 강함` 체감을 공통 축으로 묶는 것이다.

작성 기준 시점:

- 2026-03-25 KST


## 1. 문서 관계

이 문서는 아래 문서를 이어받는다.

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase2_common_threshold_baseline_spec_ko.md`
- `docs/chart_flow_phase2_common_threshold_implementation_checklist_ko.md`

각 문서 역할은 아래와 같다.

- guide: 전체 semantic -> chart 흐름 설명
- policy v1: 현재 공통 policy 필드 구조
- phase2 spec/checklist: 공통 threshold baseline과 owner 고정
- phase3 spec: 공통 강도 축과 시각 binding 고정


## 2. Phase 3의 범위

이번 단계에서 고정할 것은 아래 4개다.

1. `strength_level 1..10` 버킷 의미
2. strength 계산 입력과 계산 순서
3. `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY`의 공통 level 매핑
4. 색 / 밝기 / 선 굵기 중 어떤 축을 level에 연결할지

이번 단계에서 하지 않을 것은 아래다.

- symbol override로 level을 따로 다르게 정의
- event family 의미 자체 변경
- strength를 entry/exit 관리 신호까지 한 번에 확장
- ML score나 미래 성과를 직접 strength에 섞기


## 3. 현재 이미 있는 강도 입력

현재 코드 기준으로 강도에 이미 사용 중이거나 사용할 수 있는 입력은 아래다.

| 입력 | 현재 위치 | 의미 |
| --- | --- | --- |
| `observe_confirm_v2.confidence` | painter scoring | semantic confidence |
| `probe_candidate_support` | painter scoring | probe readiness surrogate |
| `probe_pair_gap` | painter scoring | 방향 우위 차이 |
| `quick_trace_state == PROBE_READY` | painter scoring | ready 직전 bonus |
| `blocked_by` | painter translation | 강도 억제 또는 중립화 신호 |
| `semantic_readiness_bridge_v1.final.buy_support/sell_support` | router metadata | 최종 execution readiness |
| `edge_pair_law_v1.pair_gap` | router metadata | 방향 winner 명확도 |

중요한 점:

- 지금 painter는 `confidence / probe_candidate_support / probe_pair_gap`의 max 기반 score만 쓰고 있다
- Phase 3에서는 이 score를 버리지 않고, `readiness + gap + block penalty`를 더 분명하게 넣은 공통 strength 축으로 올리는 것이 목표다


## 4. Strength 계산 원칙

### 4-1. strength는 확률이 아니다

strength는 `이 신호가 맞을 확률`이 아니라,
`화면에서 얼마나 준비된 신호처럼 보여야 하는가`를 뜻한다.

즉 strength는 아래를 동시에 반영한다.

- semantic confidence
- probe/confirm readiness
- 방향 우위 차이
- soft/hard block에 따른 감쇠


### 4-2. strength와 event family는 분리한다

예시:

- `BUY_WAIT level 7`
- `BUY_PROBE level 7`

둘 다 같은 `7단계`일 수 있지만, 의미는 다르다.

- event family는 `무슨 종류의 신호인가`
- strength level은 `그 신호가 얼마나 강하게 보여야 하는가`

즉 level이 높다고 family가 자동으로 승격되면 안 된다.


### 4-3. strength는 baseline 위에서만 계산한다

Phase 2 baseline이 먼저 안정화되었기 때문에,
Phase 3는 그 위에서만 강도 축을 얹는다.

금지:

- baseline이 흔들리는 상태에서 level만 세밀하게 쪼개기
- 심볼별 override가 baseline보다 먼저 level 계산을 덮어쓰기


## 5. 공통 strength 계산식 v1

### 5-1. 입력 정규화

Phase 3 v1에서는 아래 4개 입력을 사용한다.

| 필드 | 정규화 규칙 |
| --- | --- |
| `confidence` | `0.0 ~ 1.0` 범위로 clamp |
| `candidate_support` | `0.0 ~ 1.0` 범위로 clamp |
| `pair_gap` | `0.0 ~ 1.0` 범위로 clamp |
| `blocked_penalty` | block 종류에 따라 `0.0 ~ 0.35` 차감 |

정규화 입력 원천:

- `confidence`: `observe_confirm_v2.confidence`
- `candidate_support`: `probe_candidate_support` 우선, 없으면 `semantic_readiness_bridge_v1.final.<side>_support`
- `pair_gap`: `probe_pair_gap` 우선, 없으면 `edge_pair_law_v1.pair_gap`


### 5-2. 계산식

권장 strength 계산식 v1:

```text
raw_strength =
    max(confidence, candidate_support)
    + (pair_gap * 0.35)
    + probe_ready_bonus
    - blocked_penalty

strength_score = clamp(raw_strength, 0.0, 1.0)
strength_level = bucket(strength_score, 1..10)
```

권장 보조 규칙:

- `probe_ready_bonus = 0.05`
  - `quick_trace_state == PROBE_READY`
  - event kind in `BUY_READY / SELL_READY / BUY_PROBE / SELL_PROBE`
- `blocked_penalty`
  - no block: `0.00`
  - `energy_soft_block`, `*_soft_block`: `0.08`
  - `probe_promotion_gate`: `0.10`
  - `forecast_guard`, `barrier_guard`: `0.12`
  - `middle_sr_anchor_guard`, `outer_band_guard`: `0.15`
  - hard neutral conflict row: `0.20 ~ 0.35`

설명:

- `max(confidence, candidate_support)`를 유지하는 이유는 현재 구현과의 연속성을 지키기 위해서다
- `pair_gap`는 readiness의 보조축으로만 반영한다
- `blocked_penalty`는 level을 낮추되, event family를 자동으로 바꾸지는 않는다


### 5-3. fallback 규칙

입력이 비어 있을 때는 아래 순서를 쓴다.

1. `observe_confirm_v2.confidence`
2. `probe_candidate_support`
3. `semantic_readiness_bridge_v1.final.<side>_support`
4. `probe_pair_gap`
5. `edge_pair_law_v1.pair_gap`

원칙:

- 값이 없다고 강도를 0으로 만들기보다, 남아 있는 입력으로 보수적으로 계산한다
- metadata가 비어 있는 live row도 최대한 기존 동작을 유지한다


## 6. Strength Level 1..10 버킷 정의

권장 버킷 v1:

| level | score range | 의미 |
| --- | --- | --- |
| `1` | `< 0.05` | 거의 보이지 않아야 하는 약한 힌트 |
| `2` | `0.05 ~ 0.11` | 아주 약한 힌트 |
| `3` | `0.11 ~ 0.18` | 약한 directional signal |
| `4` | `0.18 ~ 0.26` | directional signal이 보일 만함 |
| `5` | `0.26 ~ 0.35` | 보통 강도 |
| `6` | `0.35 ~ 0.45` | 명확한 보통 강도 |
| `7` | `0.45 ~ 0.58` | 강한 signal |
| `8` | `0.58 ~ 0.72` | 매우 강한 signal |
| `9` | `0.72 ~ 0.86` | confirm 직전 또는 soft-blocked strong signal |
| `10` | `>= 0.86` | 사실상 enter-ready 급 강도 |

핵심 해석:

- `1~2`: 거의 약함
- `3~4`: directional wait/probe가 보일 정도
- `5~6`: 보통
- `7~8`: 강함
- `9~10`: 매우 강함 또는 ready 직전


## 7. Event Family별 level 해석 규칙

같은 level이라도 family에 따라 읽는 법은 다르다.

| family | level 해석 |
| --- | --- |
| `BUY_WAIT / SELL_WAIT` | 방향은 유지되지만 아직 실행 확정은 아님 |
| `BUY_PROBE / SELL_PROBE` | 초기 진입 탐색 신호 |
| `BUY_READY / SELL_READY` | 실행 승인 직전 또는 승인 상태 |
| `WAIT` | directional side가 없는 중립 대기 |

규칙:

- `BUY_WAIT level 7`은 강한 directional wait다
- `BUY_PROBE level 7`은 강한 probe지만 여전히 probe다
- `BUY_READY level 4` 같은 경우는 가능하더라도 시각적으로는 과장되면 안 된다

즉 event family와 level을 함께 읽어야 한다.


## 8. 시각 binding 표준안

### 8-1. 어떤 축을 level에 연결할 것인가

권장 우선순위:

1. `밝기`
2. `선 굵기`
3. `색상 미세 이동`

권장하지 않는 것:

- level마다 완전히 다른 색으로 바꾸기
- buy/sell family의 기본 색 정체성을 깨기


### 8-2. v1 binding 원칙

| 시각 축 | 적용 방식 |
| --- | --- |
| 색상 | family base color 유지 |
| 밝기 | level이 높을수록 밝아짐 |
| 선 굵기 | `level 1~3 = thin`, `4~7 = medium`, `8~10 = thick` |
| 위치(anchor) | level과 직접 연결하지 않음 |

즉 v1에서는:

- family를 색으로 구분
- strength를 밝기와 굵기로 구분


### 8-3. level과 밝기 권장 맵

| level band | 밝기 해석 |
| --- | --- |
| `1~2` | dim |
| `3~4` | slightly visible |
| `5~6` | normal |
| `7~8` | bright |
| `9~10` | brightest |


### 8-4. level과 선 굵기 권장 맵

| level band | line width |
| --- | --- |
| `1~3` | `1` |
| `4~7` | `2` |
| `8~10` | `3` |


## 9. Policy 필드 제안

Phase 3에서 추가할 policy 필드 제안은 아래와 같다.

### `strength`

| field | type | default | owner |
| --- | --- | --- | --- |
| `strength.level_count` | `int` | `10` | painter |
| `strength.score_input_paths` | `list[str]` | 아래 표 참조 | painter |
| `strength.pair_gap_weight` | `float` | `0.35` | painter |
| `strength.probe_ready_bonus` | `float` | `0.05` | painter |
| `strength.block_penalty_by_guard` | `dict[str, float]` | 아래 표 참조 | painter |
| `strength.bucket_edges` | `list[float]` | `[0.05,0.11,0.18,0.26,0.35,0.45,0.58,0.72,0.86]` | painter |
| `strength.visual_binding` | `dict[str, object]` | 아래 표 참조 | painter |

권장 `score_input_paths`:

- `observe_confirm_v2.confidence`
- `probe_candidate_support`
- `semantic_readiness_bridge_v1.final.buy_support`
- `semantic_readiness_bridge_v1.final.sell_support`
- `probe_pair_gap`
- `edge_pair_law_v1.pair_gap`

권장 `block_penalty_by_guard`:

```text
energy_soft_block: 0.08
probe_promotion_gate: 0.10
forecast_guard: 0.12
barrier_guard: 0.12
middle_sr_anchor_guard: 0.15
outer_band_guard: 0.15
```


## 10. 구현 순서 초안

Phase 3 구현은 아래 순서를 권장한다.

1. strength policy 필드와 spec을 먼저 고정한다
2. 현재 `_flow_event_signal_score(...)`를 strength 계산 함수로 확장한다
3. `strength_score -> strength_level` bucket 변환 함수를 추가한다
4. painter에 밝기/선 굵기 binding을 붙인다
5. `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY` 공통 회귀 테스트를 추가한다
6. 심볼별 baseline 분포를 비교한다


## 11. 완료 기준

Phase 3 완료는 아래 조건을 만족해야 한다.

| 체크 | 통과 기준 |
| --- | --- |
| 공통 bucket | `1..10` 의미가 문서와 코드에서 같다 |
| 공통 계산식 | 심볼마다 다른 수식이 아니라 같은 strength 식을 쓴다 |
| 공통 visual binding | family는 색으로, strength는 밝기/굵기로 읽힌다 |
| 체감 일관성 | 같은 `level 6` buy가 심볼마다 크게 다른 강도로 보이지 않는다 |


## 12. 결론

Phase 3의 핵심은 색을 화려하게 나누는 것이 아니다.

- 같은 의미의 signal에
- 같은 입력축을 사용해서
- 같은 level을 계산하고
- 같은 시각 축으로 보여주게 만드는 것

즉 strength 표준화의 본질은
`표현 다양화`가 아니라
`체감 강도의 공통 언어 만들기`
다.
