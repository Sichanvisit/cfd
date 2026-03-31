# 차트 Flow Phase 0 Freeze

## 목적

이 문서는 `buy / wait / sell` 표현 체계를 안정화하기 위한 Phase 0 결과물을 고정한다.

Phase 0의 목적은 로직을 더 추가하는 것이 아니라,
현재 구조에서 아래 항목을 더 이상 암묵적으로 두지 않고 명시적으로 고정하는 것이다.

- 무엇이 source of truth인가
- 어떤 event family가 공통 baseline인가
- 어떤 규칙이 공통 baseline에 속하는가
- 어떤 규칙이 symbol override인가

작성 기준 시점:

- 2026-03-25 KST


## 1. Source Of Truth

Phase 0에서 source of truth는 아래 4개다.

| 구분 | 파일 | 역할 |
| --- | --- | --- |
| 개념 기준서 | `docs/chart_flow_buy_wait_sell_guide_ko.md` | 전체 semantic-to-chart 설명서 |
| 라우팅 기준 | `backend/trading/engine/core/observe_confirm_router.py` | observe/confirm/action과 probe/confirm 문턱의 주 소유자 |
| 차트 번역 기준 | `backend/trading/chart_painter.py` | 최종 row를 차트 event family로 번역하는 주 소유자 |
| exit 전달 기준 | `backend/app/trading_application_runner.py` | flat 상태에서 stale exit payload를 차단하는 주 소유자 |

추가 확인 기준:

- `tests/unit/test_chart_painter.py`
- `tests/unit/test_trading_application_runner_profile.py`

운영 원칙:

- 문서와 코드가 충돌하면 먼저 문서에 정의된 semantic 의미를 확인한다
- 그 다음 code path가 문서 의미를 어기고 있는지 본다
- Phase 0에서는 새 의미를 만들지 않고 현재 의미를 freeze한다


## 2. Event Semantics Freeze

현재 chart vocabulary는 아래 event family를 공통 baseline으로 사용한다.

| Event Kind | Freeze 의미 | 분류 |
| --- | --- | --- |
| `BUY_READY` | 방향과 실행 승인이 모두 `BUY` | directional confirm |
| `SELL_READY` | 방향과 실행 승인이 모두 `SELL` | directional confirm |
| `BUY_WAIT` | 방향은 `BUY`지만 실행은 아직 wait | directional wait |
| `SELL_WAIT` | 방향은 `SELL`지만 실행은 아직 wait | directional wait |
| `BUY_PROBE` | buy 방향 초기 probe 시각화 | directional early probe |
| `SELL_PROBE` | sell 방향 초기 probe 시각화 | directional early probe |
| `BUY_WATCH` | buy 감시 상태 | directional watch |
| `SELL_WATCH` | sell 감시 상태 | directional watch |
| `WAIT` | 중립 또는 conflict 또는 방향 미확정 | neutral wait |
| `ENTER_BUY` | 실제 buy 진입 발생 | terminal entry |
| `ENTER_SELL` | 실제 sell 진입 발생 | terminal entry |
| `EXIT_NOW` | 즉시 정리 계열 | terminal exit |
| `REVERSE_READY` | 반전 준비 | terminal reversal |
| `HOLD` | 보유 유지 | terminal hold |

이 의미는 Phase 0에서 freeze한다.


## 3. 공통 해석 규칙 Freeze

아래 규칙은 Phase 0 시점의 공통 baseline으로 고정한다.

### 3-1. Directional Wait

- `WAIT + side="BUY"`는 `BUY_WAIT`
- `WAIT + side="SELL"`는 `SELL_WAIT`
- `WAIT + side=""`만 중립 `WAIT`

즉 `WAIT`는 무조건 중립이 아니다.


### 3-2. Soft Block Downgrade

아래 조건은 방향 삭제가 아니라 실행 downgrade로 해석한다.

- `action_none_reason == "execution_soft_blocked"`
- `blocked_by == "energy_soft_block"`
- `blocked_by.endswith("_soft_block")`

Freeze 의미:

- `BUY_READY -> BUY_WAIT`
- `SELL_READY -> SELL_WAIT`


### 3-3. Structural Guard Recovery

아래 structural guard는 directional 의미가 남아 있으면 중립 `WAIT`로 묻지 않는다.

- `middle_sr_anchor_guard`
- `outer_band_guard`

Freeze 의미:

- buy 문맥이면 `BUY_WAIT`
- sell 문맥이면 `SELL_WAIT`
- 단, probe visual이거나 conflict row면 중립 `WAIT` 가능


### 3-4. Probe / Watch / Ready 계층

공통 계층은 아래 순서로 freeze한다.

`PROBE -> WATCH -> WAIT -> READY -> ENTER`

의미:

- `PROBE`: 초기 directional 탐색
- `WATCH`: directional 감시
- `WAIT`: 방향은 있으나 실행 대기
- `READY`: 실행 승인
- `ENTER`: 실제 진입 완료


### 3-5. Exit 계열은 별도 family

`EXIT_NOW`, `REVERSE_READY`, `HOLD`는 방향 신호가 아니라 포지션 관리 신호로 freeze한다.

즉:

- buy/sell family와 섞어 해석하면 안 된다
- flat 상태에서는 보이면 안 된다


### 3-6. Flat Exit Suppression

아래 조건이 true면 exit 계열은 무효다.

- `my_position_count <= 0`

Freeze 의미:

- runner는 exit payload를 비운다
- painter도 방어적으로 exit payload를 무시한다


## 4. 공통 Baseline Inventory

아래 항목은 현재 기준에서 `공통 baseline`으로 분류한다.

| 항목 | 현재 소유자 | 이유 |
| --- | --- | --- |
| event family 의미 | guide + painter | 모든 심볼에서 동일해야 함 |
| directional wait 해석 | painter | `WAIT + BUY/SELL` 의미는 공통이어야 함 |
| soft block downgrade | painter | block은 문턱 완화이지 의미 변경이 아님 |
| structural wait recovery 원칙 | painter | buy/sell이 neutral에 묻히지 않게 하는 공통 규칙 |
| `PROBE -> WATCH -> WAIT -> READY -> ENTER` 계층 | router + painter | 모든 심볼에서 같은 단계 순서를 써야 함 |
| flat 상태 exit suppression | runner + painter | symbol과 무관한 안전 규칙 |
| confirm floor / advantage의 state별 의미 | router | state별 confirm 구조는 공통 기반이어야 함 |
| `edge_pair_law_v1`, `semantic_readiness_bridge_v1` 사용 | router | raw detector가 아니라 semantic handoff를 공통 입력으로 쓰기 때문 |
| buy/sell event family별 시각 어휘 | painter | 같은 family는 같은 visual 문법을 써야 함 |


## 5. Symbol Override Inventory

아래 항목은 현재 코드 기준에서 `symbol override`로 분류한다.

중요:

- override는 존재 자체가 잘못은 아니다
- 다만 baseline 아래 분리되어 있어야 한다


### 5-1. Router Override

| 심볼 | override | 코드 성격 | 현재 목적 |
| --- | --- | --- | --- |
| `XAUUSD` | `_XAU_UPPER_*` 계열 상수 | upper reject sell probe/confirm 완화 | 상단 structural reject를 더 민감하게 포착 |
| `XAUUSD` | `_XAU_LOWER_SECOND_SUPPORT_*` 계열 상수 | lower second support buy relief | 하단 second support buy probe 복원 |
| `XAUUSD` | `xau_second_support_probe_relief` | mid 구간에서도 제한적 lower rebound buy 허용 | 하단 반등 buy가 완전히 사라지지 않게 완화 |
| `XAUUSD` | `xau_local_upper_reject_context` / `xau_structural_probe_relief` | upper reject sell context 완화 | 상단 reject sell이 구조적으로 살아있을 때 probe/confirm 완화 |
| `BTCUSD` | `_BTC_LOWER_*` 계열 상수 | lower rebound buy probe 완화 | BTC 하단 구조 반등 buy 조건 조정 |
| `BTCUSD` | `btc_lower_structural_probe_relief` | lower structural probe relief | 하단 반등 buy를 구조적으로 살리는 예외 |
| `BTCUSD` | `_btc_lower_buy_context_ok(...)` | lower buy 문맥 제한 | BTC에서 middle buy 남발 방지 |
| `BTCUSD` | `_btc_midline_rebound_transition(...)` | midline 전환 특례 | lower rebound가 mid로 올라왔을 때 sell watch 또는 만료 처리 |
| `NAS100` | `_NAS_CLEAN_*` 계열 상수 | clean confirm probe 완화 | NAS clean confirm probe scene 조정 |


### 5-2. Painter Override

| 심볼/scene | override | 현재 목적 |
| --- | --- | --- |
| `xau_second_support_buy_probe` | `bb_state`가 lower가 아니면 기본적으로 buy probe 억제 | XAU second support buy 과잉 표시 방지 |
| `xau_second_support_buy_probe + xau_second_support_probe_relief` | `MID/MIDDLE`에서도 제한적 허용 | XAU 하단 반등 buy 복원 |
| `xau_upper_sell_probe` | 특정 box 문맥에서만 sell probe 허용 | 상단 sell probe 오표시 방지 |
| `btc_lower_buy_conservative_probe` | `MID/MIDDLE`에서도 lower context 인정 | BTC lower probe 완화 |
| `nas_clean_confirm_probe` | `MID/MIDDLE`에서도 lower context 인정 | NAS clean confirm probe 완화 |


## 6. Baseline vs Override 분류표

Phase 0 완료 기준에 맞춰 아래처럼 분류한다.

| 분류 | 포함 항목 | 현재 상태 |
| --- | --- | --- |
| 공통 baseline | event family 의미, directional wait, soft block downgrade, structural wait recovery 원칙, flat exit suppression, 공통 confirm 구조, 공통 visual family | Freeze 대상 |
| symbol override | XAU upper/lower relief, BTC lower relief, BTC midline transition, NAS clean probe scene, scene-specific context 완화 | 분리 목록화 대상 |

Phase 0의 핵심은 이 표를 명시적으로 가져가는 것이다.


## 7. 코드 포인터

### Router

- `backend/trading/engine/core/observe_confirm_router.py`
  - `_confirm_floor(...)`
  - `_confirm_advantage(...)`
  - `_btc_lower_buy_context_ok(...)`
  - `_btc_midline_rebound_transition(...)`
  - `xau_second_support_probe_relief` 계산 구간
  - `btc_lower_structural_probe_relief` 계산 구간
  - `xau_local_upper_reject_context` / `xau_structural_probe_relief` 계산 구간


### Painter

- `backend/trading/chart_painter.py`
  - `_resolve_flow_event_kind(...)`
  - `_resolve_blocked_structural_wait(...)`
  - `_resolve_flow_observe_side(...)`
  - `_resolve_probe_visual_allowed(...)`


### Runner

- `backend/app/trading_application_runner.py`
  - `_snapshot_exit_fields(...)`


## 8. Phase 0 완료 판정

Phase 0는 아래 조건을 만족하면 완료로 본다.

1. source of truth가 문서와 코드 포인터로 명시되어 있다
2. 공통 event family 의미가 freeze되어 있다
3. 공통 baseline 목록이 분리되어 있다
4. symbol override 목록이 분리되어 있다
5. 앞으로의 작업이 "baseline 수정"인지 "override 수정"인지 구분해서 말할 수 있다


## 9. Phase 0 이후 바로 할 일

Phase 0 이후에는 바로 튜닝에 들어가지 않고 아래 순서로 간다.

1. common expression policy 초안 작성
   - `docs/chart_flow_common_expression_policy_draft_ko.md`
   - `docs/chart_flow_common_expression_policy_v1_ko.md`
   - `docs/chart_flow_painter_priority1_policy_extraction_list_ko.md`
2. painter 기준값을 common policy로 이관
3. router의 공통 threshold를 가능한 범위에서 같은 policy로 이관
4. event distribution 계측 추가
5. 그 다음에만 symbol override를 분리 복원
