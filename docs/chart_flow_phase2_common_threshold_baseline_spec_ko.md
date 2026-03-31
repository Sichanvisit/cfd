# 차트 Flow Phase 2 공통 Threshold Baseline 상세안

## 목적

이 문서는 Phase 2에서 잠글 `공통 threshold baseline`의 상세안을 정의한다.
목표는 심볼 특례를 잠시 꺼도 `XAUUSD / BTCUSD / NAS100`이 최소한 같은 언어로
`BUY_READY / BUY_WAIT / BUY_PROBE / WAIT / SELL_PROBE / SELL_WAIT / SELL_READY`
를 표시하게 만드는 것이다.

이 문서는 Phase 2에서 잠근 기준값과 owner를 기록하고,
현재 반영된 baseline 구현의 기준선으로 유지하는 문서다.

작성 기준 시점:

- 2026-03-25 KST


## 구현 상태

2026-03-25 KST 기준 Phase 2 baseline 구현은 완료되었다.

- 공통 policy 기준값은 `backend/trading/chart_flow_policy.py`에 반영되었다
- router confirm/probe baseline은 `backend/trading/engine/core/observe_confirm_router.py`에서 policy를 읽는다
- painter visual/anchor/readiness gate는 `backend/trading/chart_painter.py`에서 policy를 읽는다
- symbol-specific override는 이번 단계에서 baseline과 분리된 상태로 유지했다

검증 결과:

- `pytest tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
- `81 passed`

이 문서는 더 이상 "구현 전 초안"이 아니라,
현재 반영된 Phase 2 baseline의 기준 문서로 사용한다.


## 1. 문서 관계

이 문서는 아래 문서를 이어받는다.

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase0_freeze_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase1_painter_implementation_checklist_ko.md`
- `docs/chart_flow_phase2_common_threshold_implementation_checklist_ko.md`

역할은 다음과 같다.

- guide: 전체 semantic -> chart 흐름 설명
- phase0: baseline vs override 구분 고정
- policy v1: 공통 policy 필드 구조 고정
- phase2 spec: 공통 threshold의 초기값과 owner, 적용 규칙 고정
- phase2 checklist: 실제 구현 순서와 금지선 고정


## 2. Phase 2의 범위

이번 단계에서 상세화할 축은 아래 5개다.

1. probe 최소 `support`
2. probe 최소 `pair_gap`
3. directional wait를 살릴 최소 readiness
4. ready 승격용 confirm floor
5. wait brightness와 buy anchor 공통값

이번 단계에서 하지 않을 것은 아래다.

- 심볼별 특례 수치 복원
- scene/context 완화 override 이관
- strength `1..10` 단계 확장
- painter/router 동시 구현


## 3. 현재 코드가 이미 들고 있는 기준값

### 3-1. Router confirm baseline

현재 router는 `observe_confirm_router.py`에서 confirm floor와 advantage를 state별로 따로 들고 있다.

| field | 현재 값 |
| --- | --- |
| `readiness.confirm_floor_by_state.TREND_PULLBACK_*` | `0.03` |
| `readiness.confirm_floor_by_state.FAILED_SELL_RECLAIM_BUY_CONFIRM` | `0.03` |
| `readiness.confirm_floor_by_state.MID_RECLAIM_CONFIRM` | `0.035` |
| `readiness.confirm_floor_by_state.MID_REJECT_CONFIRM` | `0.035` |
| `readiness.confirm_floor_by_state.LOWER_REBOUND_CONFIRM` | `0.20` |
| `readiness.confirm_floor_by_state.UPPER_REJECT_CONFIRM` | `0.20` |
| `readiness.confirm_floor_by_state.LOWER_FAIL_CONFIRM` | `0.24` |
| `readiness.confirm_floor_by_state.UPPER_BREAK_CONFIRM` | `0.24` |
| `readiness.confirm_floor_by_state.DEFAULT` | `0.20` |

| field | 현재 값 |
| --- | --- |
| `readiness.confirm_advantage_by_state.TREND_PULLBACK_*` | `0.003` |
| `readiness.confirm_advantage_by_state.FAILED_SELL_RECLAIM_BUY_CONFIRM` | `0.003` |
| `readiness.confirm_advantage_by_state.MID_RECLAIM_CONFIRM` | `0.01` |
| `readiness.confirm_advantage_by_state.MID_REJECT_CONFIRM` | `0.01` |
| `readiness.confirm_advantage_by_state.LOWER_REBOUND_CONFIRM` | `0.003` |
| `readiness.confirm_advantage_by_state.DEFAULT` | `0.02` |

의미:

- confirm floor는 `확정 승격`의 최소 support 기준이다
- confirm advantage는 같은 자리에서 buy/sell 중 어느 쪽이 더 우세한지 보는 차이값 기준이다


### 3-2. Router probe baseline

현재 router는 edge probe용 공통 baseline과 심볼별 probe tolerance를 따로 들고 있다.

| field | 현재 값 | 비고 |
| --- | --- | --- |
| `probe.default_floor_mult` | `0.72` | 공통 edge probe baseline |
| `probe.default_advantage_mult` | `0.25` | 공통 edge probe baseline |
| `probe.default_support_tolerance` | `0.015` | 공통 edge probe baseline |
| `XAU upper support tolerance` | `0.04` | override |
| `BTC lower support tolerance` | `0.010` | override |
| `NAS clean support tolerance` | `0.012` | override |

의미:

- 공통 probe는 confirm보다 완화된 조건으로 허용한다
- 심볼별 tolerance는 Phase 4 override로 남겨야 한다


### 3-3. Painter probe baseline

현재 painter는 probe 시각화 최소값을 이미 policy로 읽을 수 있게 되어 있다.

| field | 현재 값 |
| --- | --- |
| `probe.upper_min_support_by_side.SELL` | `0.16` |
| `probe.upper_min_support_by_side.BUY` | `0.18` |
| `probe.upper_min_pair_gap_by_side.SELL` | `0.03` |
| `probe.upper_min_pair_gap_by_side.BUY` | `0.04` |
| `probe.lower_min_support_by_side.BUY` | `0.22` |
| `probe.lower_min_support_by_side.SELL` | `0.26` |
| `probe.lower_min_pair_gap_by_side.BUY` | `0.12` |
| `probe.lower_min_pair_gap_by_side.SELL` | `0.18` |
| `probe.promotion_gate_support_penalty` | `0.08` |
| `probe.promotion_gate_pair_gap_penalty` | `0.05` |

의미:

- router가 probe 후보를 만들더라도, painter는 차트에 그릴 최소 시각화 문턱을 한 번 더 갖고 있다
- Phase 2의 핵심은 이 값들이 흩어진 임의값이 아니라 공통 policy 값으로 보이게 만드는 것이다


### 3-4. Painter wait brightness baseline

현재 painter wait 밝기 보정은 아래처럼 굴고 있다.

| event kind | brighten threshold | dim threshold |
| --- | --- | --- |
| `BUY_WAIT` | `0.30` | `0.06` |
| `SELL_WAIT` | `0.34` | `0.06` |

의미:

- 이 값은 event family를 바꾸는 기준이 아니라, 같은 `BUY_WAIT` / `SELL_WAIT` 안에서
  얼마나 또렷하게 보이게 할지 정하는 시각적 baseline이다


### 3-5. Painter buy anchor baseline

현재 buy 마커 위치는 아래 기준으로 잡힌다.

| field | 현재 값 |
| --- | --- |
| `anchor.buy_upper_reclaim_mode` | `body_low` |
| `anchor.buy_middle_ratio` | `0.48` |
| `anchor.buy_probe_ratio` | `0.30` |
| `anchor.buy_default_ratio` | `0.36` |
| `anchor.sell_mode` | `high` |
| `anchor.neutral_mode` | `close` |

의미:

- buy는 무조건 캔들 `low`에 붙이지 않고 약간 위로 띄운다
- sell은 기본적으로 `high`, neutral은 `close`를 쓴다


## 4. Phase 2에서 확정할 공통 policy 필드

### 4-1. `readiness`

Phase 2에서 `readiness`는 아래 4개를 기준으로 본다.

| field | owner | 초기값 | 목적 |
| --- | --- | --- | --- |
| `readiness.confirm_floor_by_state` | router | 기존 값 유지 | ready 승격 공통 baseline |
| `readiness.confirm_advantage_by_state` | router | 기존 값 유지 | ready 승격 공통 baseline |
| `readiness.directional_wait_min_support_by_side` | painter | `{"BUY": 0.05, "SELL": 0.05}` | directional wait 최소 support |
| `readiness.directional_wait_min_pair_gap_by_side` | painter | `{"BUY": 0.02, "SELL": 0.02}` | directional wait 최소 우위 차이 |

설명:

- `confirm_*`는 기존 router 값이 이미 공통 baseline 역할을 하고 있으므로 Phase 2에서 다시 바꾸지 않는다
- `directional_wait_min_*`는 Phase 2에서 새로 도입하는 공통 gate다
- 이 값은 `BUY_WAIT / SELL_WAIT`를 없애기 위한 gate가 아니라, 완전 노이즈성 directional wait를 줄이기 위한 하한이다

적용 규칙:

1. `observe_confirm_v2.action == WAIT` 이고 side가 `BUY/SELL`이면 directional wait 후보다
2. `semantic_readiness_bridge_v1.final.<side>_support`가 있으면 `directional_wait_min_support_by_side`와 비교한다
3. `edge_pair_law_v1.pair_gap`가 있으면 `directional_wait_min_pair_gap_by_side`와 비교한다
4. 두 값이 없으면 Phase 2 이행 중에는 기존 동작을 유지한다
5. 값이 충분하지 않으면 `BUY_WAIT / SELL_WAIT` 대신 중립 `WAIT`로 남긴다

초기값 근거:

- `0.05` support는 현재 `edge_pair_law_v1.winner_clear` 기준의 support 축과 맞닿아 있다
- `0.02` pair gap은 현재 기본 confirm advantage의 default 값과 맞닿아 있다
- 즉 confirm보다는 약하지만, 완전 무의미한 directional wait는 걸러내는 중간값이다


### 4-2. `probe`

Phase 2의 probe baseline은 아래처럼 잠근다.

| field | owner | 초기값 |
| --- | --- | --- |
| `probe.default_floor_mult` | router | `0.72` |
| `probe.default_advantage_mult` | router | `0.25` |
| `probe.default_support_tolerance` | router | `0.015` |
| `probe.upper_min_support_by_side` | painter | `{"SELL": 0.16, "BUY": 0.18}` |
| `probe.upper_min_pair_gap_by_side` | painter | `{"SELL": 0.03, "BUY": 0.04}` |
| `probe.lower_min_support_by_side` | painter | `{"BUY": 0.22, "SELL": 0.26}` |
| `probe.lower_min_pair_gap_by_side` | painter | `{"BUY": 0.12, "SELL": 0.18}` |
| `probe.promotion_gate_support_penalty` | painter | `0.08` |
| `probe.promotion_gate_pair_gap_penalty` | painter | `0.05` |

적용 원칙:

- router는 `probe 후보를 만들 최소 baseline`을 담당한다
- painter는 `차트에 probe를 그릴 최소 baseline`을 담당한다
- 두 층 모두 공통 policy 값을 읽어야 하며, 하드코딩 값이 남아 있으면 안 된다
- 심볼별 tolerance는 Phase 2에서 baseline에 넣지 않고 Phase 4 override로 남긴다


### 4-3. `visual`

Phase 2에서 visual은 `wait brightness`만 잠근다.

| field | owner | 초기값 |
| --- | --- | --- |
| `visual.wait_brightness_by_event_kind.BUY_WAIT.brighten_threshold` | painter | `0.30` |
| `visual.wait_brightness_by_event_kind.BUY_WAIT.dim_threshold` | painter | `0.06` |
| `visual.wait_brightness_by_event_kind.SELL_WAIT.brighten_threshold` | painter | `0.34` |
| `visual.wait_brightness_by_event_kind.SELL_WAIT.dim_threshold` | painter | `0.06` |

원칙:

- 밝기 기준은 event family를 바꾸면 안 된다
- Phase 2에서는 `BUY_WAIT`와 `SELL_WAIT`만 잠그고, probe/ready의 강도 단계화는 Phase 6으로 미룬다


### 4-4. `anchor`

Phase 2에서 anchor는 buy 위치 기준만 잠근다.

| field | owner | 초기값 |
| --- | --- | --- |
| `anchor.buy_upper_reclaim_mode` | painter | `body_low` |
| `anchor.buy_middle_ratio` | painter | `0.48` |
| `anchor.buy_probe_ratio` | painter | `0.30` |
| `anchor.buy_default_ratio` | painter | `0.36` |
| `anchor.sell_mode` | painter | `high` |
| `anchor.neutral_mode` | painter | `close` |

원칙:

- buy는 볼린저밴드 하단 끝 틈에 과하게 몰리지 않게 한다
- anchor는 위치 기준이지 의미 기준이 아니다
- 심볼별 buy 위치 특례는 Phase 4 override로만 허용한다


## 5. Owner 규칙

Phase 2에서는 threshold의 owner를 아래처럼 나눈다.

| 축 | owner | 이유 |
| --- | --- | --- |
| confirm floor / advantage | router | confirm 승격은 upstream semantic 판단이기 때문 |
| probe 후보 baseline | router | observe/probe 후보를 만드는 층이 router이기 때문 |
| probe 시각화 baseline | painter | 같은 probe 후보라도 차트에 그릴 최소 문턱은 painter가 결정하기 때문 |
| directional wait gate | painter | event family 번역의 마지막 owner가 painter이기 때문 |
| wait brightness | painter | 시각적 강도 보정이기 때문 |
| anchor | painter | 차트 위치 표현이기 때문 |

중요한 규칙:

- owner가 다르더라도 값은 공통 policy에서 읽어야 한다
- router와 painter가 같은 뜻의 threshold를 서로 다른 숫자로 따로 들고 있으면 안 된다
- symbol override는 owner를 바꾸면 안 되고 값만 얇게 덮어써야 한다


## 6. 적용 순서 초안

Phase 2 구현은 아래 순서를 권장한다.

1. `common_expression_policy`에 readiness/probe/visual/anchor의 baseline 숫자를 확정한다
2. router의 confirm/probe baseline 상수를 policy getter로 치환한다
3. painter의 wait brightness와 anchor 상수를 policy getter로 치환한다
4. painter에 `directional_wait_min_support_by_side`, `directional_wait_min_pair_gap_by_side` gate를 넣는다
5. symbol override를 끈 상태에서 XAU/BTC/NAS 캔들 리플레이를 본다
6. baseline만으로 event family가 유지되는지 확인한 뒤에만 Phase 4 override 복원으로 간다


## 7. Gate B 판정 기준

Phase 2 완료는 아래 조건을 만족해야 한다.

| 체크 | 통과 기준 |
| --- | --- |
| 공통 policy 사용 | router와 painter 모두 baseline 숫자를 policy에서 읽는다 |
| 의미 일관성 | `BUY_WAIT`, `SELL_WAIT`, `BUY_PROBE`, `SELL_PROBE`, `BUY_READY`, `SELL_READY` 의미가 심볼마다 바뀌지 않는다 |
| override 분리 | 심볼 특례를 꺼도 baseline은 동작한다 |
| 시각 일관성 | 같은 수준의 wait/probe가 심볼마다 완전히 다른 체감으로 보이지 않는다 |


## 8. Phase 2에서 일부러 하지 않는 것

- `XAU upper`, `XAU second support`, `BTC lower`, `NAS clean` 특례 수치 복원
- `strength_level 1..10` 색상/밝기 확장
- scene/context 완화 override 재배치
- live 분포 튜닝

이것들은 baseline이 먼저 안정화된 뒤에만 다뤄야 한다.


## 9. 결론

Phase 2의 본질은 새 threshold를 많이 추가하는 것이 아니다.

- 이미 있는 confirm/probe/visual/anchor 기준값을
- 공통 policy 아래 다시 묶고
- directional wait에만 최소 readiness gate를 하나 추가해서
- `심볼 특례 없이도 같은 언어로 보이게` 만드는 것이다

즉 이번 단계의 목표는
`더 정교한 표현`이 아니라
`같은 의미가 같은 기준으로 보이게 하는 최소 공통 baseline`
이다.
