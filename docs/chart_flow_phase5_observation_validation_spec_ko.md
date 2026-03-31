# Chart Flow Phase 5 Observation Validation Spec

## 목적

이 문서는 Phase 5 `관측/검증 체계 추가`의 상세 기준을 정의한다.

목표는 아래 한 줄이다.

`buy / sell / wait 분포를 체감이 아니라 수치로 비교할 수 있게 만든다`

즉 이 문서의 역할은:

- 어떤 event를 어떤 단위로 집계할지 고정하고
- 어떤 축으로 분포를 비교할지 정하고
- 어떤 출력물을 기준 리포트로 삼을지 정하고
- 이후 calibration이 "캡처를 보고 느낌으로 조정"되지 않게 만드는 것이다.

작성 기준 시점:

- 2026-03-25 KST


## 구현 반영 상태

2026-03-25 KST 기준 Phase 5 구현은 반영 완료 상태다.

반영 파일:

- `backend/trading/chart_flow_distribution.py`
- `backend/trading/chart_painter.py`
- `tests/unit/test_chart_flow_distribution.py`
- `tests/unit/test_chart_painter.py`
- `tests/unit/test_observe_confirm_router_v2.py`

반영 범위:

- symbol별 flow history 기반 분포 집계 모듈 추가
- event family / zone / strength / block / flat-exit anomaly 집계 추가
- latest distribution report 저장 연결
- 관측/검증 회귀 테스트 추가

검증 결과:

- `pytest tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
- 결과: `96 passed`


## 1. 문서 관계

이 문서는 아래 문서를 이어받는다.

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase2_common_threshold_baseline_spec_ko.md`
- `docs/chart_flow_phase2_common_threshold_implementation_checklist_ko.md`
- `docs/chart_flow_phase3_strength_standard_spec_ko.md`
- `docs/chart_flow_phase3_strength_implementation_checklist_ko.md`
- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`
- `docs/chart_flow_phase4_symbol_override_implementation_checklist_ko.md`

각 문서 역할은 아래와 같다.

- guide: 전체 semantic -> chart 흐름 설명
- phase2: 공통 threshold baseline 정의
- phase3: strength 10단계 정의
- phase4: symbol override 격리
- phase5: 실제 분포를 관측하고 비교하는 기준 정의


## 2. Phase 5의 범위

이번 단계에서 고정할 것은 아래 5개다.

1. event 분포 집계 단위
2. zone 분포 집계 단위
3. strength score / strength level 집계 단위
4. anomaly 감시 축
5. 분포 리포트 산출물 형식

이번 단계에서 하지 않을 것은 아래다.

- Phase 6 calibration 숫자 조정
- baseline 의미 변경
- override 의미 변경
- ML 평가 지표 설계


## 3. 왜 Phase 5가 필요한가

Phase 1~4까지 끝나면 구조는 정리되지만,
아직 아래 질문은 체감으로만 남아 있을 수 있다.

- "buy가 너무 안 뜨는 것 같은데 실제로도 그런가"
- "XAU만 유난히 wait가 많은가"
- "BTC는 probe가 많고 ready가 적은가"
- "NAS는 lower/middle/upper 중 어디에서 주로 sell로 기우는가"
- "flat인데 exit가 다시 뜨는 문제가 재발했는가"

이 질문들을 수치로 바꾸지 않으면,
이후 calibration은 다시 눈대중과 캡처 위주로 돌아갈 가능성이 높다.

따라서 Phase 5의 핵심은
`분포를 보기 위한 공통 측정 언어를 만드는 것`
이다.


## 4. 관측 원칙

### 4-1. raw보다 실제 표시 결과를 우선 본다

Phase 5의 1차 기준은
`실제로 chart에 기록된 event_kind`
다.

즉 아래가 우선이다.

- `BUY_WAIT`
- `SELL_WAIT`
- `BUY_PROBE`
- `SELL_PROBE`
- `BUY_READY`
- `SELL_READY`
- `WAIT`
- 필요 시 `BUY_WATCH / SELL_WATCH / ENTER_* / EXIT_NOW / HOLD`

이유:

- 사용자가 실제로 보는 것은 chart event다
- router 내부 confidence만 높아도 painter에서 억제되면 체감은 달라진다
- 따라서 calibration 기준도 최종 표시 결과를 우선 봐야 한다


### 4-2. baseline과 override를 분리해서 볼 수 있어야 한다

Phase 5 리포트는 가능하면 아래 두 모드를 분리해서 지원하는 것이 좋다.

- `baseline-only`
- `override-on`

이유:

- baseline 문제인지 override 문제인지 구분해야 한다
- 특정 심볼의 분포 편향이 공통 baseline 때문인지 예외 때문인지 분리해서 봐야 한다

초기 구현에서는 `override-on`만 먼저 지원해도 되지만,
리포트 schema는 baseline 비교가 가능하도록 열어두는 것이 좋다.


### 4-3. 최근성 윈도우를 명시해야 한다

분포는 반드시 윈도우와 함께 읽어야 한다.

허용 윈도우:

- 최근 `N시간`
- 최근 `N캔들`

권장 기본값:

- `6h`
- `12h`
- `24h`
- `최근 64캔들`

금지:

- 윈도우 없이 누적 전체 분포만 보고 판단하기


## 5. 필수 집계 축

### 5-1. Symbol x Event Family 분포

심볼별로 반드시 집계할 event는 아래다.

- `BUY_WAIT`
- `SELL_WAIT`
- `BUY_PROBE`
- `SELL_PROBE`
- `BUY_READY`
- `SELL_READY`
- `WAIT`

선택 집계:

- `BUY_WATCH`
- `SELL_WATCH`
- `ENTER_BUY`
- `ENTER_SELL`
- `EXIT_NOW`
- `HOLD`

핵심 지표:

- `total_events`
- `directional_buy_events`
- `directional_sell_events`
- `neutral_wait_events`
- `buy_presence_ratio`
- `sell_presence_ratio`
- `neutral_ratio`

권장 계산:

- `directional_buy_events = BUY_WAIT + BUY_PROBE + BUY_READY + BUY_WATCH`
- `directional_sell_events = SELL_WAIT + SELL_PROBE + SELL_READY + SELL_WATCH`
- `buy_presence_ratio = directional_buy_events / total_events`
- `sell_presence_ratio = directional_sell_events / total_events`
- `neutral_ratio = WAIT / total_events`


### 5-2. Symbol x Zone 분포

event는 반드시 위치대와 같이 봐야 한다.

공통 zone bucket은 아래처럼 단순화한다.

- `LOWER`
- `MIDDLE`
- `UPPER`
- `UNKNOWN`

권장 매핑:

- `box_state in {LOWER, LOWER_EDGE, BELOW}` -> `LOWER`
- `box_state in {MIDDLE, MID}` -> `MIDDLE`
- `box_state in {UPPER, UPPER_EDGE, ABOVE}` -> `UPPER`
- box 정보가 약하면 `bb_state`를 보조로 사용
- 둘 다 비어 있으면 `UNKNOWN`

반드시 볼 표:

- `symbol x zone x event_kind`
- `symbol x zone x buy_presence_ratio`
- `symbol x zone x sell_presence_ratio`

핵심 질문:

- lower에서 buy family가 얼마나 살아나는가
- upper에서 sell family가 얼마나 살아나는가
- middle에서 directional wait가 과도하게 쏠리는가


### 5-3. Strength Score x Strength Level 분포

Phase 3에서 strength 축이 들어갔으므로,
Phase 5에서는 아래 둘을 같이 기록해야 한다.

- `signal_score`
- `strength_level`

필수 집계:

- `symbol x strength_level count`
- `event_kind x strength_level count`
- `zone x strength_level count`

핵심 확인:

- 특정 심볼만 level 1~3에 몰리는가
- 특정 심볼만 probe는 많고 ready level은 드문가
- 같은 level 6이라도 실제 event family 분포가 심볼마다 크게 다른가


### 5-4. Block / Guard 분포

체감 문제는 종종 event 자체보다 block에서 생긴다.

반드시 집계할 축:

- `blocked_by`
- `action_none_reason`
- `probe_scene_id`

권장 질문:

- `forecast_guard` 때문에 buy probe가 중립 wait로 자주 눌리는가
- `middle_sr_anchor_guard`가 특정 심볼에서 과도한가
- 특정 scene이 다른 scene보다 훨씬 자주 blocked되는가


### 5-5. Flat Exit 재발 감시

flat 상태에서 exit 계열이 다시 그려지는 문제는
재발 여부를 별도 anomaly로 감시해야 한다.

필수 조건:

- `my_position_count <= 0`
- event family가 `EXIT_NOW` 또는 terminal exit 계열

필수 지표:

- `flat_exit_count`
- `flat_exit_symbols`
- `flat_exit_reasons`

완료 기준:

- Phase 5 리포트에서 `flat_exit_count == 0` 여부를 항상 확인할 수 있어야 한다


## 6. 권장 입력 소스

### 6-1. Primary Source

우선 소스는 chart flow history다.

예:

- `Common/Files/XAUUSD_flow_history.json`
- `Common/Files/BTCUSD_flow_history.json`
- `Common/Files/NAS100_flow_history.json`

이유:

- 최종 chart event가 이미 기록되어 있다
- event_kind / side / reason / score가 함께 남는다


### 6-2. Secondary Source

보조 소스는 runtime snapshot row다.

예:

- `data/runtime_status.json`
- `data/runtime_status.detail.json`
- 최신 semantic rollout manifest

용도:

- 현재 라이브 상태 확인
- flow history에 없는 부가 필드 보강


### 6-3. 추론 금지

금지:

- 이미지 캡처만 보고 분포를 추정하기
- chart 색상만 보고 event family를 역추론하기

Phase 5는 반드시 저장된 event 기록을 기준으로 해야 한다.


## 7. 권장 산출물

### 7-1. 최신 분포 JSON

권장 파일:

- `data/analysis/chart_flow_distribution_latest.json`

권장 top-level 구조:

```json
{
  "contract_version": "chart_flow_distribution_v1",
  "generated_at": "2026-03-25T03:10:00+09:00",
  "window": {
    "mode": "hours",
    "value": 12
  },
  "baseline_mode": "override_on",
  "symbols": {},
  "global_summary": {},
  "anomalies": {}
}
```


### 7-2. 심볼별 요약 표

권장 필드:

- `symbol`
- `total_events`
- `buy_presence_ratio`
- `sell_presence_ratio`
- `neutral_ratio`
- `buy_minus_sell`
- `flat_exit_count`


### 7-3. Zone 분포 표

권장 필드:

- `symbol`
- `zone`
- `BUY_WAIT`
- `SELL_WAIT`
- `BUY_PROBE`
- `SELL_PROBE`
- `BUY_READY`
- `SELL_READY`
- `WAIT`


### 7-4. Baseline 대비 편차 표

권장 목적:

- 심볼별로 "공통 기대치에서 얼마나 벗어나는지"를 본다

권장 필드:

- `symbol`
- `buy_presence_ratio`
- `sell_presence_ratio`
- `neutral_ratio`
- `global_buy_presence_ratio`
- `global_sell_presence_ratio`
- `global_neutral_ratio`
- `buy_deviation`
- `sell_deviation`
- `neutral_deviation`

권장 계산:

- `buy_deviation = symbol_buy_presence_ratio - global_buy_presence_ratio`
- `sell_deviation = symbol_sell_presence_ratio - global_sell_presence_ratio`
- `neutral_deviation = symbol_neutral_ratio - global_neutral_ratio`


## 8. 리포트 해석 원칙

### 8-1. buy가 적다는 말을 수치로 바꾼다

예:

- "XAU는 최근 12시간 `buy_presence_ratio`가 0.06이고 global은 0.18"
- "BTC는 lower zone의 `BUY_PROBE + BUY_WAIT`가 18건인데 XAU는 3건"

이런 식으로 말할 수 있어야 한다.


### 8-2. neutral이 많은 이유를 block 분포로 같이 본다

예:

- `WAIT`가 많은 것이 문제인지
- `forecast_guard` 때문에 directional이 눌린 것인지
- `probe_scene_id`가 아예 적은 것인지

를 분리해서 봐야 한다.


### 8-3. strength는 단독 해석하지 않는다

예:

- level 7이 많아도 전부 `SELL_WAIT`면 buy 체감은 여전히 약할 수 있다
- level 4가 많아도 lower zone의 `BUY_WAIT`가 꾸준하면 기능적으로는 정상일 수 있다

따라서 strength는 event family와 zone과 같이 봐야 한다.


## 9. 권장 anomaly 규칙

### 9-1. Flat Exit

- `flat_exit_count > 0`이면 anomaly


### 9-2. Extreme Imbalance

권장 초기 규칙:

- `abs(buy_minus_sell) >= 0.35`가 일정 윈도우 이상 지속되면 경고


### 9-3. Zone Mismatch

예:

- lower zone인데 `BUY_*`가 지나치게 드물다
- upper zone인데 `SELL_*`가 지나치게 드물다

이 규칙은 초기에는 hard fail보다 리포트 경고로 두는 것이 좋다.


## 10. 완료 기준

Phase 5 완료 기준은 아래와 같다.

1. 심볼별 `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY / WAIT` 분포를 최근 윈도우 기준으로 볼 수 있다
2. lower / middle / upper zone별 분포를 함께 볼 수 있다
3. signal score / strength level 분포를 event family와 같이 볼 수 있다
4. `blocked_by / action_none_reason / probe_scene_id` 편향을 같이 볼 수 있다
5. flat 상태 exit 재발 여부를 anomaly로 확인할 수 있다
6. "buy가 너무 안 뜬다"를 체감이 아니라 수치로 설명할 수 있다


## 11. 구현 전 체크포인트

Phase 5 구현에 들어가기 전에는 아래를 다시 확인하는 것이 좋다.

- Phase 2 baseline이 현재 코드와 일치하는가
- Phase 3 strength level이 실제 chart event에 기록되고 있는가
- Phase 4 override on/off가 현재 contract 기준으로 동작하는가
- flow history가 최근 윈도우를 분석하기에 충분히 보존되고 있는가


## 12. 다음 문서

이 spec 다음에는 아래 문서가 이어지는 것이 자연스럽다.

- `docs/chart_flow_phase5_observation_validation_implementation_checklist_ko.md`

그 문서에서는 아래를 다루면 된다.

- 어떤 입력 파일을 읽을지
- 어떤 집계 함수를 만들지
- 어떤 JSON 리포트를 저장할지
- 어떤 테스트로 회귀를 잡을지
