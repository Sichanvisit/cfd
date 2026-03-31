# Chart Flow Phase 3 Strength Implementation Checklist

## 목적

이 문서는 Phase 3 `strength 1..10 표준화`를 실제 코드로 옮길 때의
실행 순서와 범위 제한을 적은 구현 체크리스트다.

성격:

- 구현 기준 문서
- 범위 제어 문서
- strength 축 적용 순서를 고정하는 문서


## 현재 상태

2026-03-25 KST 기준 이 체크리스트의 Step 1 ~ Step 8은 구현 완료 상태다.

이미 끝난 것:

- Phase 0 freeze 완료
- Phase 1 painter policy extraction 완료
- Phase 2 common threshold baseline 완료
- Phase 3 strength standard spec 작성 완료
- `common_expression_policy_v1`에 `strength.*` field 추가 완료
- painter 공통 strength score / level 계산 연결 완료
- directional family brightness / line width binding 적용 완료
- `save()` 8컬럼 width 출력 반영 완료
- MT5 `DrawHelper.mq5` consumer width 컬럼 대응 및 재컴파일 완료
- 회귀 테스트 확인 완료

검증 결과:

- `pytest tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
- `87 passed`
- `MetaEditor64.exe` compile
- `Experts\\Advisors\\DrawHelper.mq5`: `0 errors, 0 warnings`
- `MQL5\\DrawHelper.mq5`: `0 errors, 0 warnings`

이 문서는 현재 구현 범위를 추적하는 완료 기록 문서로도 함께 사용한다.


## 선행 문서

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase2_common_threshold_baseline_spec_ko.md`
- `docs/chart_flow_phase2_common_threshold_implementation_checklist_ko.md`
- `docs/chart_flow_phase3_strength_standard_spec_ko.md`


## 이번 단계 목표

이번 Phase 3의 목표는 아래 한 줄이다.

`같은 strength level은 심볼이 달라도 비슷한 체감 강도로 보이게 만들기`

이번 단계에서 포함하는 것:

- `strength.*` policy field 도입
- 공통 strength score 계산 함수 도입
- `strength_score -> strength_level 1..10` 버킷 함수 도입
- `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY` 공통 level 연결
- 밝기 / 선 굵기 binding 도입

이번 단계에서 하지 않는 것:

- symbol override 재조정
- event family 의미 변경
- router side 로직 재설계
- entry / exit / hold family까지 strength 확장
- 분포 집계 리포트 시스템 추가


## 작업 순서

### Step 1. Phase 3 Policy Field 추가

목표:

- shared policy에 strength 기준선을 먼저 고정한다

대상 파일:

- `backend/trading/chart_flow_policy.py`

추가할 항목:

- `strength.level_count`
- `strength.score_input_paths`
- `strength.pair_gap_weight`
- `strength.probe_ready_bonus`
- `strength.block_penalty_by_guard`
- `strength.bucket_edges`
- `strength.visual_binding`

완료 조건:

- strength 관련 숫자가 painter 본문 하드코딩 대신 policy에서 읽힐 수 있다
- Phase 3 spec의 기본값과 policy default가 일치한다


### Step 2. Painter Strength Getter 진입점 정리

목표:

- painter가 strength policy를 안정적으로 읽을 수 있게 한다

대상 파일:

- `backend/trading/chart_painter.py`

작업:

- `strength` getter helper 추가
- `score_input_paths`, `bucket_edges`, `block_penalty_by_guard`, `visual_binding` 접근 helper 추가
- fallback 규칙을 한 곳에서 처리하도록 묶기

완료 조건:

- strength 관련 해석이 여러 함수에 흩어지지 않고 공통 helper를 통해 접근된다


### Step 3. 공통 Strength Score 계산 함수 도입

목표:

- 현재 `_flow_event_signal_score(...)`를 Phase 3 spec 기준 strength score로 확장한다

대상 함수:

- `_flow_event_signal_score(...)`
- 또는 새 helper `_flow_event_strength_score(...)`

읽을 입력:

- `observe_confirm_v2.confidence`
- `probe_candidate_support`
- `semantic_readiness_bridge_v1.final.<side>_support`
- `probe_pair_gap`
- `edge_pair_law_v1.pair_gap`
- `blocked_by`

적용 규칙:

- `max(confidence, candidate_support)`를 기본 축으로 유지
- `pair_gap * weight`를 보조축으로 더한다
- `PROBE_READY` bonus를 추가한다
- `blocked_by` 종류에 따라 penalty를 차감한다
- 최종 score는 `0.0 ~ 1.0`으로 clamp한다

완료 조건:

- strength score 계산식이 문서와 코드에서 같다
- metadata가 비어 있어도 기존 row를 과도하게 0점 처리하지 않는다


### Step 4. Strength Level Bucket 함수 추가

목표:

- score를 `1..10` level로 공통 변환한다

대상 함수:

- 새 helper `_flow_event_strength_level(...)`

읽을 항목:

- `strength.bucket_edges`
- `strength.level_count`

완료 조건:

- 버킷 경계가 painter 본문 하드코딩이 아니라 policy 기준으로 작동한다
- 같은 score는 언제나 같은 level로 변환된다


### Step 5. Event Family에 공통 Level 연결

목표:

- strength level을 directional family에 동일하게 부여한다

대상 family:

- `BUY_WAIT`
- `SELL_WAIT`
- `BUY_PROBE`
- `SELL_PROBE`
- `BUY_READY`
- `SELL_READY`

원칙:

- level이 높아도 family를 자동 승격하지 않는다
- family는 기존 semantic translation이 결정하고
- strength는 표현 강도만 결정한다

완료 조건:

- `BUY_WAIT level 7`, `BUY_PROBE level 7`, `BUY_READY level 7`이 모두 가능하되 의미는 섞이지 않는다


### Step 6. Visual Binding 도입

목표:

- strength를 차트에서 읽히는 시각 축으로 연결한다

대상 함수:

- `_flow_event_color(...)`
- compact history / drawing style 계산부

적용 축:

- 밝기
- 선 굵기

유지할 것:

- buy / sell family base color
- anchor 위치 규칙

권장 규칙:

- `level 1~2`: dim
- `level 3~4`: slightly visible
- `level 5~6`: normal
- `level 7~8`: bright
- `level 9~10`: brightest
- `level 1~3 = line width 1`
- `level 4~7 = line width 2`
- `level 8~10 = line width 3`

완료 조건:

- family는 색으로 읽히고
- strength는 밝기/굵기로 읽힌다
- level 때문에 buy/sell 기본 색 정체성이 깨지지 않는다


### Step 7. Neutral / Terminal Family 경계 유지

목표:

- strength 확장이 의미 체계를 흔들지 않게 막는다

이번 단계에서 유지할 것:

- `WAIT`는 중립 family로 유지
- `ENTER_BUY`, `ENTER_SELL`, `EXIT_NOW`, `REVERSE_READY`, `HOLD`는 Phase 3 strength 적용 대상에서 제외
- structural wait recovery, soft block downgrade, directional wait readiness gate는 기존 의미를 유지

완료 조건:

- strength 적용 후에도 terminal family와 directional family의 역할이 섞이지 않는다


### Step 8. 테스트와 회귀 확인

우선 확인 테스트:

- `tests/unit/test_chart_painter.py`

추가가 필요한 테스트 방향:

- score 입력 fallback이 문서 순서대로 작동하는지
- block penalty가 level을 낮추되 family를 바꾸지 않는지
- 같은 score range가 같은 level로 매핑되는지
- `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY`가 공통 bucket을 쓰는지
- 밝기와 선 굵기가 level band 기준으로 바뀌는지

완료 조건:

- level bucket 테스트가 최소 1개 이상 추가된다
- block penalty 테스트가 최소 1개 이상 추가된다
- visual binding 테스트가 최소 1개 이상 추가된다


## 구현 중 금지사항

- symbol override 튜닝을 같이 넣지 않는다
- Phase 4 override isolation 작업을 미리 당겨오지 않는다
- Phase 5 계측 시스템을 같이 만들지 않는다
- level을 올린다고 family를 자동으로 `WAIT -> READY` 승격하지 않는다
- entry / exit family까지 한 번에 강도 체계를 확장하지 않는다
- router와 painter에서 서로 다른 strength 수식을 따로 두지 않는다


## Done Definition

이번 체크리스트는 아래 조건을 만족하면 완료다.

1. `common_expression_policy_v1`에 `strength.*` 필드가 들어간다
2. painter가 공통 strength score와 level bucket을 policy 기준으로 계산한다
3. `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY`가 같은 strength 축을 쓴다
4. family는 색으로, strength는 밝기/굵기로 읽히는 체계가 적용된다
5. strength 적용 후에도 기존 semantic family 의미는 유지된다


## 다음 단계

이 체크리스트가 끝나면 다음으로 넘어간다.

1. Phase 4 symbol override isolation 정리
2. Phase 5 분포/계측 리포트 추가
3. Phase 6 calibration rollout
