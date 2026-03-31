# 차트 Flow Common Expression Policy Draft

> 이 초안은 이후 `docs/chart_flow_common_expression_policy_v1_ko.md`에서 필드 스펙이 확정되었다.

## 목적

이 문서는 `buy / wait / sell` 표현을 안정화하기 위해,
현재 코드에 흩어져 있는 공통 기준값을 `common expression policy`로 추출하기 위한 Phase 1 초안이다.

중요:

- 이 문서는 아직 코드에 적용된 정책이 아니다
- 현재 코드에서 이미 사용 중인 기준값을 모아 공통 baseline 후보로 정리한 설계 초안이다
- symbol override는 이 문서의 baseline 위에 별도 얹는 것을 원칙으로 한다

작성 기준 시점:

- 2026-03-25 KST


## 1. 문서 위치

이 문서는 아래 두 문서 다음 단계에 해당한다.

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase0_freeze_ko.md`

관계는 다음과 같다.

- Phase 0 Freeze: 의미와 override 목록을 고정
- Common Policy Draft: baseline으로 끌어올릴 공통 항목과 owner를 정의
- 코드 반영: 이 정책을 router/painter에 실제로 연결


## 2. 공통 Policy의 목적

common expression policy가 필요한 이유는 명확하다.

- 같은 semantic 의미가 심볼마다 다른 threshold로 보이지 않게 하기 위해
- router와 painter가 다른 수치 감각을 쓰지 않게 하기 위해
- symbol별 특례를 baseline 아래 얇은 override로 밀어 넣기 위해

즉 이 policy의 목적은 "정교한 튜닝"이 아니라
"같은 의미를 같은 문법으로 표현하는 공통 기준선 확보"다.


## 3. Owner 원칙

| 영역 | owner | 책임 |
| --- | --- | --- |
| event family 의미 | 문서 + painter | `BUY_WAIT`, `SELL_PROBE`, `EXIT_NOW` 의미 고정 |
| confirm/probe readiness 기준 | router | `floor`, `advantage`, `probe readiness`의 주 소유자 |
| chart event translation | painter | semantic row를 event family로 번역 |
| rendering policy | painter | 색, 밝기, 위치, 선형태 |
| flat exit suppression | runner + painter | 포지션 없을 때 exit family 억제 |
| symbol exception | override table | baseline이 아닌 특수 완화/문턱 |

원칙:

- 의미는 router와 painter가 공동으로 공유하되, 문서가 최종 기준
- 문턱값은 가급적 router/painter 본문에 흩어두지 않고 policy에서 읽는다
- painter는 semantic owner가 아니라 rendering/translation owner다


## 4. Common Policy Scope

Phase 1에서 공통 policy로 뽑아야 할 항목은 아래다.

| 분류 | policy 항목 | 현재 출처 |
| --- | --- | --- |
| Event semantics | event family 정의 | `chart_painter.py`, freeze 문서 |
| Readiness | confirm floor, confirm advantage | `observe_confirm_router.py` |
| Probe baseline | probe floor multiplier, advantage multiplier, tolerance | `observe_confirm_router.py`, `chart_painter.py` |
| Wait translation | directional wait, soft block downgrade, structural wait recovery | `chart_painter.py` |
| Visual score | score 입력값, bonus 규칙 | `chart_painter.py` |
| Visual style | base color, brightness band | `chart_painter.py` |
| Anchor | buy/sell marker 위치 기준 | `chart_painter.py` |


## 5. Draft Policy Schema

공통 policy는 최종적으로 아래처럼 나뉘는 것이 바람직하다.

```text
common_expression_policy
├─ semantics
├─ readiness
├─ probe
├─ translation
├─ scoring
├─ visual
└─ anchor
```


### 5-1. `semantics`

역할:

- event family 의미를 고정

필드 예시:

- `directional_wait_enabled = true`
- `soft_block_downgrades_ready = true`
- `flat_exit_suppression_enabled = true`
- `structural_wait_recovery_enabled = true`


### 5-2. `readiness`

역할:

- confirm readiness의 state별 기준 정의

필드 예시:

- `confirm_floor_by_state`
- `confirm_advantage_by_state`


### 5-3. `probe`

역할:

- probe 전환 문턱과 promotion penalty 정의

필드 예시:

- `probe_floor_mult_default`
- `probe_advantage_mult_default`
- `probe_support_tolerance_default`
- `probe_min_support_by_context`
- `probe_min_pair_gap_by_context`
- `probe_promotion_gate_support_penalty`
- `probe_promotion_gate_gap_penalty`


### 5-4. `translation`

역할:

- 어떤 semantic row를 어떤 chart family로 번역할지 정의

필드 예시:

- `neutral_block_guards`
- `structural_wait_recovery_guards`
- `watch_reason_suffixes`
- `probe_reason_groups`


### 5-5. `scoring`

역할:

- 차트 표시 강도용 score 계산식 정의

필드 예시:

- `score_inputs = [confidence, candidate_support, pair_gap]`
- `score_reduce = max`
- `probe_ready_bonus = 0.05`


### 5-6. `visual`

역할:

- 색, 밝기, 이벤트 family별 시각 기준 정의

필드 예시:

- `base_color_by_event_kind`
- `wait_brighten_thresholds`
- `wait_dim_thresholds`
- `wait_brighten_alpha_caps`


### 5-7. `anchor`

역할:

- event kind/reason별 마커 위치 기준 정의

필드 예시:

- `buy_upper_reclaim_anchor = body_low`
- `buy_mid_anchor_ratio = 0.48`
- `buy_probe_anchor_ratio = 0.30`
- `buy_default_anchor_ratio = 0.36`
- `sell_default_anchor = high`


## 6. 현재 코드 기준 baseline 후보값

아래 값은 "이미 코드에 존재하는 기준"을 공통 policy 후보로 옮긴 것이다.


### 6-1. Confirm Floor / Advantage Draft

| state group | floor | advantage | 현재 의미 |
| --- | --- | --- | --- |
| `TREND_PULLBACK_*`, `FAILED_SELL_RECLAIM_BUY_CONFIRM` | `0.03` | `0.003` | 비교적 가벼운 confirm |
| `MID_RECLAIM_CONFIRM`, `MID_REJECT_CONFIRM` | `0.035` | `0.01` | middle confirm |
| `LOWER_REBOUND_CONFIRM` | `0.20` | `0.003` | lower rebound confirm |
| `UPPER_REJECT_CONFIRM` | `0.20` | `0.02` | upper reject confirm |
| `LOWER_FAIL_CONFIRM`, `UPPER_BREAK_CONFIRM` | `0.24` | `0.02` | 더 강한 confirm 요구 |

정책 해석:

- 이 표는 symbol override 이전의 공통 baseline 후보다
- symbol별 완화는 나중에 multiplier나 override table로만 조정한다


### 6-2. Probe Baseline Draft

#### Router 쪽 공통 baseline

| 항목 | 기본값 후보 | 현재 출처 |
| --- | --- | --- |
| `probe_floor_mult_default` | `0.72` | `_EDGE_PROBE_FLOOR_MULT` |
| `probe_advantage_mult_default` | `0.25` | `_EDGE_PROBE_ADVANTAGE_MULT` |
| `probe_support_tolerance_default` | `0.015` | `_EDGE_PROBE_SUPPORT_TOLERANCE` |

#### Painter 쪽 공통 baseline

| context | side | min_support | min_pair_gap |
| --- | --- | --- | --- |
| `upper_reject` / structural upper probe | `SELL` | `0.16` | `0.03` |
| `upper_reject` / structural upper probe | `BUY` | `0.18` | `0.04` |
| `lower_rebound_probe_observe` | `BUY` | `0.22` | `0.12` |
| `lower_rebound_probe_observe` | `SELL` | `0.26` | `0.18` |

Promotion gate penalty 후보:

- `support_penalty = +0.08`
- `pair_gap_penalty = +0.05`

주의:

- 이 값들은 아직 painter에 남아 있는 기준이다
- 최종 목표는 router/painter가 같은 policy를 보게 만드는 것이다


### 6-3. Translation Draft

공통 번역 규칙 후보:

| 규칙 | draft 값 |
| --- | --- |
| directional wait 허용 | `true` |
| soft block downgrade | `true` |
| structural wait recovery | `true` |
| neutral block guards | `middle_sr_anchor_guard`, `outer_band_guard` |
| probe promotion gate neutralization | `true` |
| conflict row neutral wait 유지 | `true` |


### 6-4. Scoring Draft

| 항목 | draft 값 | 현재 의미 |
| --- | --- | --- |
| score inputs | `confidence`, `probe_candidate_support`, `probe_pair_gap` | signal score 후보 |
| score reduce | `max` | 세 값 중 가장 강한 readiness 사용 |
| `PROBE_READY` bonus | `+0.05` | ready 직전 probe 강조 |

초기 정책 원칙:

- score는 확률이 아니라 chart intensity용 readiness surrogate다
- Phase 1에서는 단순 max 기반을 유지해도 된다
- 10단계 strength는 Phase 2 이후 별도 확장


### 6-5. Visual Draft

#### Base Colors

| event kind | draft color |
| --- | --- |
| `BUY_READY` | `65280` |
| `SELL_READY` | `255` |
| `BUY_PROBE` | `0x00E6FF66` |
| `SELL_PROBE` | `2555904` |
| `BUY_WATCH` | `0x00F5FF99` |
| `SELL_WATCH` | `255` |
| `BUY_WAIT` | `0x00C8FF4D` |
| `SELL_WAIT` | `128` |
| `WAIT` | `13421772` |
| `ENTER_BUY` | `65407` |
| `ENTER_SELL` | `16711935` |
| `EXIT_NOW` | `26367` |
| `REVERSE_READY` | `16711808` |
| `HOLD` | `16776960` |

#### Wait Brightness

| event kind | brighten threshold | dim threshold |
| --- | --- | --- |
| `BUY_WAIT` | `>= 0.30` | `< 0.06` |
| `SELL_WAIT` | `>= 0.34` | `< 0.06` |

초기 원칙:

- buy 계열은 support/trend 녹색보다 더 밝게 유지
- wait 밝기 보정은 현재 Phase 1에서는 `BUY_WAIT`, `SELL_WAIT`까지만 유지 가능
- probe/ready까지 확장은 추후 strength 정책으로 분리


### 6-6. Anchor Draft

| 조건 | anchor draft |
| --- | --- |
| `upper_reclaim`, `upper_support_hold` buy | `body_low` |
| `middle_`, `mid_` buy | `low + span * 0.48` 상한 적용 |
| `BUY_PROBE`, `BUY_WATCH` | `low + span * 0.30` 상한 적용 |
| generic buy | `low + span * 0.36` 상한 적용 |
| sell / exit / reverse | `high` |
| neutral wait | `close` |

초기 원칙:

- buy는 무조건 low에 박지 않는다
- sell은 기본적으로 high 기준을 유지한다
- neutral wait는 close 축으로 남긴다


## 7. Override 허용 범위 Draft

아래 항목만 symbol override로 허용하는 것이 좋다.

| 허용 | 예시 |
| --- | --- |
| floor multiplier | XAU/BTC/NAS별 confirm/probe 완화 |
| advantage multiplier | upper/lower probe 문턱 완화 |
| support tolerance | 특정 상품의 변동성 대응 |
| context relief | `MID`에서도 제한적 lower/upper probe 허용 |
| scene allowlist | 특정 `probe_scene_id`에 대한 문맥 완화 |

반대로 아래는 override 금지 항목으로 본다.

| 비허용 | 이유 |
| --- | --- |
| event family 의미 변경 | baseline이 무너짐 |
| soft block 의미 변경 | 심볼마다 readiness 의미가 달라짐 |
| flat exit suppression 해제 | 안전 규칙 훼손 |
| wait/ready 계층 재정의 | chart vocabulary 일관성 붕괴 |


## 8. Common Policy로 옮길 우선순위

Phase 1에서 한 번에 모든 값을 옮길 필요는 없다.
우선순위는 아래처럼 잡는 편이 좋다.

### Priority 1

- directional wait 규칙
- soft block downgrade 규칙
- structural wait recovery 규칙
- probe min support / pair gap

### Priority 2

- confirm floor / advantage
- score inputs / score bonus
- wait brightness 기준

### Priority 3

- anchor ratio
- family별 visual style 상세값
- strength 확장 입력값


## 9. 코드 반영 전 체크리스트

Phase 1 초안이 코드로 옮겨지기 전에 아래 질문에 답할 수 있어야 한다.

1. 이 값은 baseline인가 override인가
2. 이 값의 owner는 router인가 painter인가
3. 이 값을 바꾸면 semantic 의미가 바뀌는가, threshold만 바뀌는가
4. 이 값은 모든 심볼에 먼저 공통 적용 가능한가
5. 공통 적용이 어렵다면 정말 override로 남겨야 하는가


## 10. 다음 단계

이 문서 다음의 실제 실행 순서는 아래다.

1. 이 초안을 기준으로 `common expression policy` 필드 목록 확정
2. painter에 있는 baseline 후보값부터 policy로 추출
3. router의 공통 floor/advantage와 probe baseline을 같은 policy 계층으로 연결
4. 그 후 event distribution 계측 추가
5. 마지막에 symbol override table 연결
