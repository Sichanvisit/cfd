# Chart Flow Phase 4 Symbol Override Implementation Checklist

## 목적

이 문서는 Phase 4 `symbol override 분리`를 실제 코드로 옮길 때의
실행 순서와 범위 제한을 적은 구현 체크리스트다.

성격:

- 구현 기준 문서
- 범위 제어 문서
- override isolation 적용 순서를 고정하는 문서


## 현재 상태

2026-03-25 KST 기준 Phase 4는 `spec 고정 완료 / 구현 및 검증 완료` 상태다.

이미 끝난 것:

- Phase 0 freeze 완료
- Phase 1 painter policy extraction 완료
- Phase 2 common threshold baseline 완료
- Phase 3 strength standardization 완료
- Phase 4 symbol override isolation spec 작성 완료
- `chart_symbol_override_policy.py` 추가 완료
- router numeric override 이관 완료
- router context / relief override 이관 완료
- painter scene / visibility override 이관 완료
- override on/off 회귀 테스트 추가 완료

이 문서는 Phase 4 구현을 시작할 때
baseline과 override가 다시 섞이지 않도록 범위를 고정하는 문서다.


## 구현 반영 결과

이번 단계에서 실제 반영된 파일:

- `backend/trading/chart_symbol_override_policy.py`
- `backend/trading/engine/core/observe_confirm_router.py`
- `backend/trading/chart_painter.py`
- `tests/unit/test_observe_confirm_router_v2.py`
- `tests/unit/test_chart_painter.py`

회귀 검증:

- `pytest tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
- 결과: `92 passed`


## 선행 문서

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`
- `docs/chart_flow_phase3_strength_implementation_checklist_ko.md`


## 이번 단계 목표

이번 Phase 4의 목표는 아래 한 줄이다.

`override를 한 contract로 모으고, baseline은 그대로 둔 채 문턱과 문맥만 조정하게 만들기`

이번 단계에서 포함하는 것:

- symbol override 전용 policy file 추가
- router의 symbol-specific numeric override 이관
- router의 symbol-specific context / relief override 이관
- painter의 scene-specific visualization override 이관
- override on/off 회귀 테스트 추가

이번 단계에서 하지 않는 것:

- baseline policy 재조정
- strength 축 재설계
- 분포 계측 시스템 추가
- 심볼별 calibration rollout


## 작업 순서

현재 기준으로 아래 Step 1~8은 모두 반영 완료되었고,
다음 Phase 진입 시에는 "무엇을 이미 잠갔는지"를 확인하는 체크포인트로 사용한다.

### Step 1. Symbol Override Policy File 추가

목표:

- 심볼 예외를 공통 baseline 밖의 별도 contract로 분리한다

대상 파일:

- 신규 `backend/trading/chart_symbol_override_policy.py`

추가할 항목:

- `symbol_override_policy_v1`
- `build_symbol_override_policy_v1()`
- `symbols.XAUUSD`
- `symbols.BTCUSD`
- `symbols.NAS100`
- `override_policy.meaning_override_forbidden`
- `override_policy.strength_override_forbidden`
- `override_policy.family_disable_forbidden`

완료 조건:

- 심볼 예외가 한 파일에 모인다
- baseline 숫자와 override 숫자가 한 파일에 뒤섞이지 않는다


### Step 2. Override Getter 진입점 정리

목표:

- router와 painter가 같은 override contract를 읽을 수 있게 만든다

대상 파일:

- `backend/trading/engine/core/observe_confirm_router.py`
- `backend/trading/chart_painter.py`

작업:

- symbol normalize helper 추가
- override section getter 추가
- `router.confirm / probe / relief / context`
- `painter.scene_allow / relief_visibility`

완료 조건:

- router와 painter가 symbol name을 직접 비교하는 분기 대신 override getter를 통해 접근할 수 있다


### Step 3. Router Numeric Override 이관

목표:

- 상수로 흩어진 symbol-specific threshold를 override table로 옮긴다

대상 축:

- `XAU upper probe`
- `XAU lower second support relief`
- `BTC lower probe`
- `BTC lower structural relief`
- `NAS clean probe`

옮길 값 예:

- floor multiplier
- advantage multiplier
- support tolerance
- structural threshold set

완료 조건:

- router 본문 상수는 baseline-only 상수만 남는다
- symbol-specific numeric threshold는 override policy에서 읽는다


### Step 4. Router Context / Relief Override 이관

목표:

- scene/context 특례를 router override contract로 옮긴다

대상 로직:

- `_btc_lower_buy_context_ok(...)`
- `_btc_midline_rebound_transition(...)`
- `xau_local_upper_reject_watch`
- `xau_local_mixed_upper_reject_override`
- `xau_second_support_probe_relief`
- `btc_lower_structural_probe_relief`
- `xau_structural_probe_relief`

원칙:

- context allow / relief gate만 override에 둔다
- final semantic family 의미는 baseline translation을 유지한다

완료 조건:

- symbol-specific context 분기가 contract 기반으로 읽힌다
- XAU/BTC/NAS 예외가 router 본문 여러 군데에 흩어져 있지 않다


### Step 5. Painter Scene Override 이관

목표:

- painter의 scene-specific visualization 특례를 override contract로 옮긴다

대상 scene:

- `xau_second_support_buy_probe`
- `xau_upper_sell_probe`
- `btc_lower_buy_conservative_probe`
- `nas_clean_confirm_probe`

대상 relief:

- `xau_second_support_probe_relief`

원칙:

- painter override는 `보일지 / 억제할지 / 완화할지`만 다룬다
- semantic side/family를 새로 만들지 않는다

완료 조건:

- painter 본문의 직접 scene 이름 비교가 override getter 기반으로 축소된다
- scene visualization 특례가 한 contract에서 추적 가능하다


### Step 6. Override Off Baseline 회귀 확인

목표:

- override를 꺼도 baseline이 깨지지 않는지 먼저 확인한다

테스트 방향:

- XAU/BTC/NAS에서 override off 시 baseline event family 유지
- `BUY_WAIT / SELL_WAIT / PROBE / READY` 의미 불변
- soft block / directional wait / strength 동작 유지

완료 조건:

- override off가 "심볼 무력화"가 아니라 "특례 제거"로만 작동한다


### Step 7. Override On Compatibility 회귀 확인

목표:

- 기존 특례가 contract 기반으로 그대로 재현되는지 확인한다

우선 확인 대상:

- XAU second support buy probe relief
- XAU upper sell probe context
- BTC lower buy conservative probe
- BTC midline rebound transition
- NAS clean confirm probe

완료 조건:

- override on에서 기존 특례 행동이 회귀 없이 유지된다
- on/off 차이가 family 의미가 아니라 빈도/문턱 차이로 나타난다


### Step 8. 문서와 계약 갱신

목표:

- 구현 결과를 문서와 맞춘다

갱신 대상:

- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- 필요 시 `docs/chart_flow_buy_wait_sell_guide_ko.md`

완료 조건:

- 실제 override policy 구조와 문서 contract가 일치한다
- owner 분리가 문서상으로도 명확하다


## 구현 중 금지사항

- common baseline policy에 symbol 이름을 직접 넣지 않는다
- override를 이용해 `BUY/SELL/WAIT` 의미를 바꾸지 않는다
- symbol별 strength bucket을 따로 만들지 않는다
- soft block / directional wait 의미를 심볼별로 바꾸지 않는다
- router와 painter가 서로 다른 override source를 따로 들고 가지 않는다
- Phase 5 계측 작업을 같이 당겨오지 않는다


## Done Definition

이번 체크리스트는 아래 조건을 만족하면 완료다.

1. symbol-specific override가 한 policy contract로 모인다
2. baseline policy와 override policy가 분리된다
3. router가 numeric / context / relief override를 contract에서 읽는다
4. painter가 scene / visibility override를 contract에서 읽는다
5. override off에서도 baseline은 유지된다
6. override on에서도 기존 특례는 재현된다


## 다음 단계

이 체크리스트가 끝나면 다음으로 넘어간다.

1. Phase 5 분포/계측 리포트 추가
2. Phase 6 calibration rollout
