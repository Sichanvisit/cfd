# Chart Flow Phase 2 Common Threshold Implementation Checklist

## 목적

이 문서는 Phase 2 `공통 threshold baseline`을 실제 코드로 옮길 때의
실행 순서와 범위 제한을 적은 구현 체크리스트다.

성격:

- 구현 기준 문서
- 범위 제어 문서
- baseline 적용 순서를 고정하는 문서


## 현재 상태

2026-03-25 KST 기준 이 체크리스트의 Step 1 ~ Step 8은 모두 구현 완료 상태다.

- Step 1: 공통 policy getter 진입점 추가 완료
- Step 2: router confirm baseline policy 연결 완료
- Step 3: router probe baseline policy 연결 완료
- Step 4: painter wait brightness policy 연결 완료
- Step 5: painter anchor policy 연결 완료
- Step 6: painter directional wait readiness gate 도입 완료
- Step 7: symbol override 경계 유지 확인 완료
- Step 8: 회귀 테스트 확인 완료

검증 결과:

- `pytest tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
- `81 passed`

이 문서는 현재 구현 범위를 추적하는 완료 기록 문서로도 함께 사용한다.


## 선행 문서

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase0_freeze_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase2_common_threshold_baseline_spec_ko.md`


## 이번 단계 목표

이번 Phase 2의 목표는 아래 한 줄이다.

`공통 threshold baseline만으로도 XAUUSD / BTCUSD / NAS100가 같은 언어로 보이게 만들기`

이번 단계에서 포함하는 것:

- router confirm baseline policy 연결
- router probe baseline policy 연결
- painter wait brightness policy 연결
- painter anchor policy 연결
- painter directional wait readiness gate 도입

이번 단계에서 하지 않는 것:

- 심볼별 override 복원
- strength `1..10` 확장
- probe scene/context 특례 이동
- 분포 계측/리포트 시스템 추가


## 작업 순서

### Step 1. Phase 2 Policy Getter 진입점 정리

목표:

- router와 painter가 Phase 2 baseline 숫자를 공통 policy에서 읽을 수 있게 만든다

작업:

- router용 policy getter 진입점 추가
- painter에 readiness / visual / anchor getter 추가
- 문서 기준 default를 그대로 반환해도 되는 최소 getter부터 만든다

완료 조건:

- confirm / probe / wait brightness / anchor / directional wait gate가
  하드코딩 숫자 대신 policy getter를 통해 접근될 수 있다


### Step 2. Router Confirm Baseline 이관

대상 함수:

- `_confirm_floor(...)`
- `_confirm_advantage(...)`

옮길 항목:

- `readiness.confirm_floor_by_state`
- `readiness.confirm_advantage_by_state`

완료 조건:

- state별 confirm floor와 advantage가 router 본문 하드코딩에서 빠진다
- 현재 기본값은 유지하되 owner가 policy로 이동한다


### Step 3. Router Probe Baseline 이관

대상 축:

- edge probe floor multiplier
- edge probe advantage multiplier
- edge probe support tolerance baseline

옮길 항목:

- `probe.default_floor_mult`
- `probe.default_advantage_mult`
- `probe.default_support_tolerance`

이번 단계에서 유지할 것:

- `XAU upper support tolerance`
- `BTC lower support tolerance`
- `NAS clean support tolerance`

완료 조건:

- 공통 probe baseline은 policy에서 읽고
- 심볼별 tolerance는 아직 override 상수로 남아 있다


### Step 4. Painter Visual Baseline 이관

대상 함수:

- `_flow_event_color(...)`

옮길 항목:

- `visual.wait_brightness_by_event_kind.BUY_WAIT.*`
- `visual.wait_brightness_by_event_kind.SELL_WAIT.*`

완료 조건:

- `BUY_WAIT`, `SELL_WAIT` 밝기/감쇠 기준이 함수 본문 하드코딩에서 빠진다
- 색상 체계 자체는 바꾸지 않는다


### Step 5. Painter Anchor Baseline 이관

대상 함수:

- `_event_price(...)`

옮길 항목:

- `anchor.buy_upper_reclaim_mode`
- `anchor.buy_middle_ratio`
- `anchor.buy_probe_ratio`
- `anchor.buy_default_ratio`
- `anchor.sell_mode`
- `anchor.neutral_mode`

완료 조건:

- buy 위치 기준이 policy getter를 통해 결정된다
- sell은 `high`, neutral은 `close` 기준을 유지한다


### Step 6. Directional Wait Readiness Gate 도입

대상 함수:

- `_resolve_flow_event_kind(...)`

읽을 입력:

- `metadata.semantic_readiness_bridge_v1.final.buy_support`
- `metadata.semantic_readiness_bridge_v1.final.sell_support`
- `metadata.edge_pair_law_v1.pair_gap`

옮길 항목:

- `readiness.directional_wait_min_support_by_side`
- `readiness.directional_wait_min_pair_gap_by_side`

적용 규칙:

- side가 있는 `WAIT`가 모두 directional wait로 번역되기 전에 최소 readiness를 한 번 확인한다
- metadata가 비어 있으면 기존 동작을 유지한다
- readiness가 공통 baseline보다 약하면 directional wait 대신 중립 `WAIT`로 남긴다

완료 조건:

- 완전 노이즈성 directional wait가 줄어든다
- 기존 structural wait recovery와 soft block downgrade 의미는 유지된다


### Step 7. Symbol Override 경계 유지 확인

이번 단계에서 유지할 예외:

- `xau_second_support_buy_probe`
- `xau_upper_sell_probe`
- `btc_lower_buy_conservative_probe`
- `nas_clean_confirm_probe`
- `xau_second_support_probe_relief`
- router의 심볼별 probe tolerance

완료 조건:

- baseline 이관 후에도 심볼 예외는 아직 그대로 동작한다
- override를 baseline 구현에 섞지 않는다


### Step 8. 테스트와 회귀 확인

우선 확인 테스트:

- `tests/unit/test_chart_painter.py`
- `tests/unit/test_observe_confirm_router_v2.py`

추가가 필요한 테스트 방향:

- confirm floor policy override가 router에 반영되는지
- probe baseline override가 router에 반영되는지
- wait brightness policy override가 painter에 반영되는지
- anchor policy override가 painter에 반영되는지
- directional wait gate가 metadata 값에 따라 `BUY_WAIT/SELL_WAIT`와 `WAIT`를 구분하는지

완료 조건:

- baseline 숫자 이관 때문에 기존 event family가 깨지지 않는다
- policy override 테스트가 최소 1개 이상씩 추가된다


## 구현 중 금지사항

- override를 baseline 구현과 같이 옮기지 않는다
- strength 단계화까지 같이 넣지 않는다
- event family 의미와 threshold 조정을 한 번에 하지 않는다
- router와 painter에서 같은 뜻의 숫자를 각자 다른 값으로 남기지 않는다
- metadata가 없는 row를 새 gate 때문에 과도하게 중립화하지 않는다


## Done Definition

이번 체크리스트는 아래 조건을 만족하면 완료다.

1. router가 confirm/probe 공통 baseline을 policy에서 읽는다
2. painter가 wait brightness와 anchor baseline을 policy에서 읽는다
3. directional wait gate가 policy와 metadata를 통해 작동한다
4. symbol override는 여전히 분리된 상태로 유지된다
5. `XAUUSD / BTCUSD / NAS100`가 baseline만으로도 최소한 같은 event family 언어를 유지한다


## 다음 단계

이 체크리스트가 끝나면 다음으로 넘어간다.

1. Phase 2 회귀 캡처와 분포 확인
2. Phase 4 symbol override isolation 정리
3. Phase 5 계측/분포 리포트 추가
4. Phase 6 strength 확장
