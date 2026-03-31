# Chart Flow Phase 4 Symbol Override Isolation Spec

## 목적

이 문서는 Phase 4 `symbol override 분리`의 상세 기준을 정의한다.

목표는 아래 한 줄이다.

`override는 baseline을 바꾸지 않고, 빈도와 문턱만 조절하는 예외 계층으로 격리한다`

즉 이 문서의 역할은:

- 현재 `XAUUSD / BTCUSD / NAS100` 특례가 어디에 흩어져 있는지 inventory를 고정하고
- 어떤 축은 override로 허용하고 어떤 축은 금지할지 정하고
- baseline과 override의 owner를 분리하고
- 이후 구현 시 "공통 의미"와 "심볼별 문턱"이 다시 섞이지 않게 만드는 것이다.

작성 기준 시점:

- 2026-03-25 KST


## 구현 반영 상태

2026-03-25 KST 기준 Phase 4 구현은 반영 완료 상태다.

반영 파일:

- `backend/trading/chart_symbol_override_policy.py`
- `backend/trading/engine/core/observe_confirm_router.py`
- `backend/trading/chart_painter.py`
- `tests/unit/test_observe_confirm_router_v2.py`
- `tests/unit/test_chart_painter.py`

반영 범위:

- `XAUUSD / BTCUSD / NAS100` override를 전용 contract로 분리
- router의 numeric / context / relief override를 contract 기반으로 이관
- painter의 scene allow / relief visibility override를 contract 기반으로 이관
- override on/off 회귀 테스트 추가

검증 결과:

- `pytest tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
- 결과: `92 passed`


## 1. 문서 관계

이 문서는 아래 문서를 이어받는다.

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase0_freeze_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase2_common_threshold_baseline_spec_ko.md`
- `docs/chart_flow_phase2_common_threshold_implementation_checklist_ko.md`
- `docs/chart_flow_phase3_strength_standard_spec_ko.md`
- `docs/chart_flow_phase3_strength_implementation_checklist_ko.md`

각 문서 역할은 아래와 같다.

- guide: 전체 semantic -> chart 흐름 설명
- phase0: baseline vs override 분리 기준 고정
- policy v1: 공통 baseline policy 필드 고정
- phase2: 공통 threshold baseline 구축
- phase3: 공통 strength 축 구축
- phase4: 심볼 예외를 baseline 밖으로 격리


## 2. Phase 4의 범위

이번 단계에서 고정할 것은 아래 4개다.

1. 현재 심볼별 override inventory
2. override가 허용되는 축과 금지되는 축
3. baseline policy와 symbol override policy의 owner 분리
4. router / painter가 읽을 override contract 초안

이번 단계에서 하지 않을 것은 아래다.

- Phase 5 분포 계측 구현
- Phase 6 심볼별 calibration rollout
- event family 의미 재정의
- override를 이용한 강도 축 재설계


## 3. 왜 Phase 4가 필요한가

지금 구조는 baseline이 이미 많이 정리되었지만,
심볼별 특례가 아직 여러 위치에 분산되어 있다.

이 상태를 그대로 두면 아래 문제가 반복된다.

- baseline을 조정했는데 어떤 심볼은 옛 특례 때문에 다르게 보인다
- router에서 이미 완화된 행을 painter가 다시 다른 scene 예외로 만진다
- XAU/BTC/NAS 조정이 쌓일수록 "이게 baseline인지 예외인지"가 흐려진다
- 분포 이상이 생겨도 baseline 문제인지 override 문제인지 구분이 안 된다

따라서 Phase 4의 핵심은
`특례를 없애는 것`이 아니라
`특례를 baseline 밖으로 명확히 밀어내는 것`
이다.


## 4. 현재 override inventory

### 4-1. Router에 있는 심볼별 numeric override

현재 router 본문에 직접 박혀 있는 대표 상수는 아래와 같다.

파일:

- `backend/trading/engine/core/observe_confirm_router.py`

대표 축:

- `XAU upper probe`
  - `_XAU_UPPER_STRUCTURAL_REJECT_MIN`
  - `_XAU_UPPER_PROBE_FLOOR_MULT`
  - `_XAU_UPPER_PROBE_ADVANTAGE_MULT`
  - `_XAU_UPPER_PROBE_SUPPORT_TOLERANCE`
- `XAU lower second support relief`
  - `_XAU_LOWER_SECOND_SUPPORT_STRUCTURAL_MIN`
  - `_XAU_LOWER_SECOND_SUPPORT_RECLAIM_MIN`
  - `_XAU_LOWER_SECOND_SUPPORT_SECONDARY_MIN`
  - `_XAU_LOWER_SECOND_SUPPORT_PERSISTENCE_MIN`
  - `_XAU_LOWER_SECOND_SUPPORT_BELIEF_MIN`
- `BTC lower probe`
  - `_BTC_LOWER_PROBE_FLOOR_MULT`
  - `_BTC_LOWER_PROBE_ADVANTAGE_MULT`
  - `_BTC_LOWER_PROBE_SUPPORT_TOLERANCE`
- `BTC lower structural relief`
  - `_BTC_LOWER_STRUCTURAL_SUPPORT_MIN`
  - `_BTC_LOWER_STRUCTURAL_RECLAIM_MIN`
  - `_BTC_LOWER_STRUCTURAL_SECONDARY_MIN`
- `NAS clean probe`
  - `_NAS_CLEAN_PROBE_FLOOR_MULT`
  - `_NAS_CLEAN_PROBE_ADVANTAGE_MULT`
  - `_NAS_CLEAN_PROBE_SUPPORT_TOLERANCE`

성격:

- numeric threshold override
- baseline multiplier override
- structural relief gate


### 4-2. Router에 있는 심볼별 context / transition override

현재 router에는 숫자 외에 context 특례도 들어 있다.

대표 함수:

- `_btc_lower_buy_context_ok(...)`
- `_btc_midline_rebound_transition(...)`
- `xau_local_upper_reject_watch`
- `xau_local_mixed_upper_reject_override`
- `xau_second_support_probe_relief`
- `btc_lower_structural_probe_relief`
- `xau_structural_probe_relief`

성격:

- 특정 symbol만 scene/context를 완화
- 특정 symbol만 local structural reject/reclaim을 probe 또는 confirm 쪽으로 열어줌
- transition/watch reason을 심볼 특화 문맥으로 생성


### 4-3. Painter에 있는 scene-specific visualization override

현재 painter에는 chart 표시를 위한 scene 예외가 들어 있다.

파일:

- `backend/trading/chart_painter.py`

대표 scene:

- `xau_second_support_buy_probe`
- `xau_upper_sell_probe`
- `btc_lower_buy_conservative_probe`
- `nas_clean_confirm_probe`

대표 relief metadata:

- `xau_second_support_probe_relief`

성격:

- probe scene context fallback
- 특정 relief가 있을 때 `WAIT -> BUY_PROBE/BUY_WAIT` 시각 복원
- 특정 scene은 기본 box/bb context보다 느슨하게 허용


### 4-4. Override로 보이면 안 되는 것

아래는 symbol 분기처럼 보여도 Phase 4 대상 override가 아니다.

- `Painter._candidate_symbols_for_draw(...)`
  - `NAS100 -> NAS100ft`
  - `XAUUSD -> XAUUSD.crp`
  - `BTCUSD -> BTCUSD.crp`
  - 이것은 파일 alias / IO 호환 처리이지 semantic override가 아니다
- common baseline policy
  - `chart_flow_policy.py`
  - 이건 모든 심볼 공통 policy다
- raw semantic engine 내부 일반 relief
  - barrier / belief / forecast 공통 relief는 Phase 4의 symbol override와 구분해야 한다


## 5. 허용되는 override 축

Phase 4에서 허용하는 축은 아래와 같다.

### 5-1. Threshold / multiplier

예:

- confirm floor multiplier
- confirm advantage multiplier
- probe floor multiplier
- probe advantage multiplier
- support tolerance

원칙:

- baseline 숫자를 직접 갈아엎는 게 아니라 multiplier / tolerance 수준으로만 조절


### 5-2. Structural relief gate

예:

- second support relief on/off
- lower structural relief on/off
- upper structural reject relief on/off

원칙:

- relief는 directional family를 강제로 바꾸는 것이 아니라
- 특정 문맥에서 probe/confirm gate를 느슨하게 하는 역할이어야 한다


### 5-3. Scene / context allow relaxation

예:

- 특정 probe scene에서 local upper/lower context 허용
- 특정 clean confirm scene의 context 완화
- 특정 midline transition watch 허용

원칙:

- context를 "열어주는" 예외는 가능하지만
- event family 의미를 다시 쓰는 예외는 불가


### 5-4. Painter-side visualization relief

예:

- 특정 relief metadata가 있으면 `MID`에서도 `BUY_PROBE` 허용
- 특정 scene에서 probe visual suppression 완화

원칙:

- painter override는 `보이게 할지 / 억제할지`만 다룬다
- semantic meaning 자체를 재결정하면 안 된다


## 6. 금지되는 override 축

아래는 Phase 4에서 금지한다.

- 어떤 심볼만 `BUY_WAIT` 자체를 사용하지 않기
- 어떤 심볼만 soft block을 `READY`로 유지하기
- 어떤 심볼만 `WAIT`를 전부 directional wait로 강제하기
- 어떤 심볼만 strength bucket 기준을 따로 쓰기
- 어떤 심볼만 `BUY/SELL/WAIT` 의미를 다시 정의하기
- router에서 side를 바꾼 뒤 painter에서 또 다른 side로 덮어쓰기

핵심 금지 원칙:

`override는 의미를 바꾸지 못하고, 문턱과 문맥만 조정할 수 있다`


## 7. Target Owner 분리

Phase 4 이후 owner는 아래처럼 나뉘어야 한다.

### 7-1. Common baseline owner

파일:

- `backend/trading/chart_flow_policy.py`

역할:

- 모든 심볼 공통 semantic / readiness / probe / translation / strength / visual baseline

금지:

- symbol 이름이 들어가는 필드 추가


### 7-2. Symbol override owner

권장 신규 파일:

- `backend/trading/chart_symbol_override_policy.py`

역할:

- `XAUUSD / BTCUSD / NAS100` override table만 보관
- router / painter가 공통 contract로 읽는 source of truth

금지:

- common baseline 기본값을 다시 복제
- event family 의미 정의 포함


### 7-3. Router owner

역할:

- numeric threshold override 적용
- structural relief gate 적용
- context/transition override 적용

원칙:

- router는 semantic decision owner다
- override가 있어도 final side/action family semantics는 common contract 위에서만 나와야 한다


### 7-4. Painter owner

역할:

- scene-specific visualization override 적용
- relief metadata가 있을 때 probe/wait 복원 여부 조절

원칙:

- painter는 semantic meaning을 새로 만들지 않는다
- router가 준 family를 시각화 측면에서 보정만 한다


## 8. 권장 override contract v1

정식 계약 이름:

- `symbol_override_policy_v1`

권장 구조:

```text
symbol_override_policy_v1
├─ contract_version
├─ symbols
│  ├─ XAUUSD
│  │  ├─ router
│  │  │  ├─ confirm
│  │  │  ├─ probe
│  │  │  ├─ relief
│  │  │  └─ context
│  │  └─ painter
│  │     ├─ scene_allow
│  │     └─ relief_visibility
│  ├─ BTCUSD
│  └─ NAS100
└─ override_policy
```


### 8-1. Router override schema

```text
symbols.<SYMBOL>.router
├─ confirm
│  ├─ floor_mult_by_scene
│  └─ advantage_mult_by_scene
├─ probe
│  ├─ floor_mult_by_scene
│  ├─ advantage_mult_by_scene
│  └─ support_tolerance_by_scene
├─ relief
│  ├─ <relief_name>.enabled
│  └─ <relief_name>.thresholds
└─ context
   ├─ <context_name>.enabled
   └─ <context_name>.rules
```


### 8-2. Painter override schema

```text
symbols.<SYMBOL>.painter
├─ scene_allow
│  ├─ <scene_id>.enabled
│  └─ <scene_id>.context_relaxation
└─ relief_visibility
   ├─ <relief_name>.enabled
   └─ <relief_name>.bb_state_relaxation
```


### 8-3. Override policy meta

```text
override_policy
├─ meaning_override_forbidden = true
├─ strength_override_forbidden = true
├─ family_disable_forbidden = true
└─ allowed_axes = [
     "confirm_multiplier",
     "probe_multiplier",
     "support_tolerance",
     "structural_relief",
     "scene_context_relaxation",
     "visual_relief_visibility",
   ]
```


## 9. Symbol별 초기 migration 대상

### 9-1. XAUUSD

router로 이동할 것:

- upper reject probe multiplier / tolerance
- lower second support relief threshold set
- local upper reject context / confirm override
- structural probe relief

painter로 이동할 것:

- `xau_second_support_buy_probe`
- `xau_upper_sell_probe`
- `xau_second_support_probe_relief` visibility rule


### 9-2. BTCUSD

router로 이동할 것:

- lower probe multiplier / tolerance
- lower structural relief threshold set
- lower buy context rule
- midline rebound transition rule

painter로 이동할 것:

- `btc_lower_buy_conservative_probe`


### 9-3. NAS100

router로 이동할 것:

- clean confirm probe multiplier / tolerance

painter로 이동할 것:

- `nas_clean_confirm_probe`


## 10. 구현 순서 초안

Phase 4 구현은 아래 순서를 권장한다.

1. current override inventory를 문서 기준으로 freeze한다
2. `chart_symbol_override_policy.py`를 추가한다
3. router numeric constant를 override table로 이관한다
4. router context / relief 분기를 override table로 이관한다
5. painter scene-specific override를 override table로 이관한다
6. override on/off regression test를 추가한다

중요:

- baseline policy는 먼저 건드리지 않는다
- override를 옮길 때 semantic meaning이 바뀌면 실패다


## 11. 테스트 기준

Phase 4에서 필요한 테스트 방향은 아래와 같다.

- override off여도 baseline event family가 유지되는지
- XAU / BTC / NAS override on에서 기존 특례가 동일하게 재현되는지
- override on/off가 family를 바꾸지 않고 frequency / threshold만 바꾸는지
- painter scene override가 semantic family를 뒤집지 않는지
- router override와 painter override가 같은 symbol에서 충돌하지 않는지

권장 테스트 분리:

- `tests/unit/test_observe_confirm_router_v2.py`
- `tests/unit/test_chart_painter.py`
- 필요 시 `tests/unit/test_chart_symbol_override_policy.py`


## 12. 완료 기준

Phase 4 완료는 아래 조건을 만족해야 한다.

| 체크 | 통과 기준 |
| --- | --- |
| override storage | `XAUUSD / BTCUSD / NAS100` 특례가 한 contract/table로 모인다 |
| meaning 보호 | override가 `BUY/SELL/WAIT` 의미를 바꾸지 않는다 |
| baseline 유지 | override off여도 baseline은 정상 작동한다 |
| allowed axes 준수 | override는 threshold/context/relief 축만 조정한다 |
| owner 분리 | router / painter가 같은 override contract를 읽되 역할은 겹치지 않는다 |


## 13. 결론

Phase 4의 핵심은 특례를 더 많이 만드는 것이 아니다.

- 이미 있는 특례를
- baseline 밖으로 빼내고
- 허용 범위를 제한하고
- owner를 분리해서
- 나중에 Phase 5 / Phase 6에서 계측과 calibration을 할 수 있게 만드는 것이다.

즉 symbol override isolation의 본질은
`예외를 확대하는 것`이 아니라
`예외를 격리해서 baseline을 보호하는 것`
이다.
