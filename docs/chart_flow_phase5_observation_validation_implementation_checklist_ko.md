# Chart Flow Phase 5 Observation Validation Implementation Checklist

## 목적

이 문서는 Phase 5 `관측/검증 체계 추가`를 실제 코드로 옮길 때의
실행 순서와 범위 제한을 적은 구현 체크리스트다.

성격:

- 구현 기준 문서
- 범위 제어 문서
- 관측/검증 산출물의 최소 요건을 고정하는 문서


## 현재 상태

2026-03-25 KST 기준 Phase 5는 `spec 고정 완료 / 구현 및 검증 완료` 상태다.

이미 끝난 것:

- Phase 0 freeze 완료
- Phase 1 painter policy extraction 완료
- Phase 2 common threshold baseline 완료
- Phase 3 strength standardization 완료
- Phase 4 symbol override isolation 완료
- Phase 5 observation validation spec 작성 완료
- 관측 입력 소스 inventory 확정 완료
- distribution 집계 함수 추가 완료
- zone bucket 집계 추가 완료
- strength score / strength level 분포 집계 추가 완료
- flat exit anomaly 감시 추가 완료
- latest distribution report 저장 완료
- 관측/검증 회귀 테스트 추가 완료

이 문서는 Phase 5 구현을 시작할 때
"무엇을 어떤 순서로 만들지"를 고정하는 문서다.


## 구현 반영 결과

이번 단계에서 실제 반영된 파일:

- `backend/trading/chart_flow_distribution.py`
- `backend/trading/chart_painter.py`
- `tests/unit/test_chart_flow_distribution.py`
- `tests/unit/test_chart_painter.py`

회귀 검증:

- `pytest tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
- 결과: `96 passed`


## 선행 문서

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_phase5_observation_validation_spec_ko.md`
- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`
- `docs/chart_flow_phase4_symbol_override_implementation_checklist_ko.md`
- `docs/chart_flow_phase3_strength_standard_spec_ko.md`


## 이번 단계 목표

이번 Phase 5의 목표는 아래 한 줄이다.

`event 분포를 저장하고 비교해서, buy/sell/wait 편향을 수치로 설명할 수 있게 만들기`

이번 단계에서 포함하는 것:

- 관측 입력 소스 고정
- 심볼별 event family 집계
- zone 분포 집계
- score / strength level 분포 집계
- block / guard 분포 집계
- flat exit anomaly 감시
- latest JSON 리포트 저장
- 관측/검증 회귀 테스트 추가

이번 단계에서 하지 않는 것:

- Phase 6 calibration 수치 조정
- baseline 의미 변경
- symbol override 값 조정
- UI/차트 렌더링 변경


## 권장 구현 범위

대상 파일은 아래처럼 잡는 것이 자연스럽다.

- 신규 `backend/trading/chart_flow_distribution.py`
- 필요 시 `backend/trading/chart_painter.py`
- 필요 시 `backend/app/trading_application_runner.py`
- 신규 또는 보강 `tests/unit/test_chart_flow_distribution.py`

원칙:

- 집계 로직은 가능하면 별도 모듈로 분리
- painter는 event 기록 owner로 남기고, 분포 계산은 별도 모듈이 읽는 구조가 바람직
- runtime runner는 latest report 저장 타이밍만 책임지는 쪽이 안전


## 작업 순서

현재 기준으로 아래 Step 1~11은 모두 반영 완료되었고,
다음 Phase 진입 시에는 "어떤 관측 축이 이미 확보되었는지"를 확인하는 체크포인트로 사용한다.

### Step 1. Input Inventory 고정

목표:

- Phase 5가 읽을 입력 소스를 명확히 고정한다

우선 입력:

- `Common/Files/*_flow_history.json`

보조 입력:

- `data/runtime_status.json`
- `data/runtime_status.detail.json`
- 최신 rollout / analysis latest 파일

완료 조건:

- 어떤 리포트 필드가 어떤 입력에서 오는지 매핑이 있다
- 캡처/이미지 기반 추론은 Phase 5 범위에서 제외된다


### Step 2. Distribution Contract 추가

목표:

- latest distribution report의 schema를 코드 상수로 고정한다

권장 항목:

- `contract_version`
- `generated_at`
- `window`
- `baseline_mode`
- `symbols`
- `global_summary`
- `anomalies`

심볼별 필수 항목:

- `event_counts`
- `zone_counts`
- `strength_level_counts`
- `blocked_by_counts`
- `action_none_reason_counts`
- `probe_scene_counts`
- `flat_exit_count`

완료 조건:

- report schema가 코드와 문서에서 일치한다


### Step 3. Event Family 집계 구현

목표:

- 심볼별 `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY / WAIT` 빈도를 집계한다

필수 계산:

- `total_events`
- `buy_presence_ratio`
- `sell_presence_ratio`
- `neutral_ratio`
- `buy_minus_sell`

완료 조건:

- 최근 윈도우 기준으로 심볼별 family 분포가 계산된다


### Step 4. Zone Bucket 집계 구현

목표:

- `LOWER / MIDDLE / UPPER / UNKNOWN` 위치대 분포를 집계한다

권장 구현:

- `box_state` 우선
- `bb_state` 보조
- 둘 다 없으면 `UNKNOWN`

필수 출력:

- `symbol x zone x event_kind count`
- `symbol x zone x buy_presence_ratio`
- `symbol x zone x sell_presence_ratio`

완료 조건:

- lower에서 buy family, upper에서 sell family를 숫자로 비교할 수 있다


### Step 5. Score / Strength 분포 집계 구현

목표:

- signal score와 strength level이 실제 event family에 어떻게 분포하는지 기록한다

필수 입력:

- `score`
- `strength_level`

필수 출력:

- `strength_level_counts`
- `event_kind_by_strength_level`
- 필요 시 `zone_by_strength_level`

완료 조건:

- "강한데 왜 buy 체감이 약한지"를 event family와 같이 볼 수 있다


### Step 6. Block / Guard 편향 집계 구현

목표:

- 왜 directional event가 줄었는지 block 관점에서 설명할 수 있게 한다

필수 집계:

- `blocked_by_counts`
- `action_none_reason_counts`
- `probe_scene_counts`

완료 조건:

- 특정 심볼에서 `forecast_guard` 또는 `middle_sr_anchor_guard` 편향이 있는지 리포트로 볼 수 있다


### Step 7. Flat Exit Anomaly 감시 구현

목표:

- flat 상태에서 exit 계열이 다시 나타나는지 감시한다

필수 규칙:

- `my_position_count <= 0`
- event family가 `EXIT_NOW` 또는 terminal exit 계열

필수 출력:

- `flat_exit_count`
- `flat_exit_reasons`
- `flat_exit_symbols`

완료 조건:

- flat exit 재발 여부를 latest report에서 바로 확인할 수 있다


### Step 8. Latest Report 저장 경로 연결

목표:

- Phase 5 산출물을 항상 같은 위치에 저장하게 만든다

권장 파일:

- `data/analysis/chart_flow_distribution_latest.json`

권장 동작:

- 최근 `N시간` 또는 `N캔들` 기준으로 갱신
- overwrite latest 방식 유지

완료 조건:

- 최신 분포 리포트를 한 파일로 열람할 수 있다


### Step 9. Baseline 대비 편차 표 계산

목표:

- 심볼별 편향을 global summary와 비교할 수 있게 한다

필수 계산:

- `global_buy_presence_ratio`
- `global_sell_presence_ratio`
- `global_neutral_ratio`
- `buy_deviation`
- `sell_deviation`
- `neutral_deviation`

완료 조건:

- "XAU는 global 대비 buy가 얼마나 부족한가"를 바로 숫자로 볼 수 있다


### Step 10. 테스트 / 회귀 확인

목표:

- Phase 5가 이후 calibration 기반으로 신뢰할 수 있게 한다

우선 테스트:

- history fixture -> event family count 정확성
- zone bucket 매핑 정확성
- strength level count 정확성
- flat exit anomaly 검출
- empty / malformed history 방어

완료 조건:

- latest report가 비어 있거나 일부 기록이 깨져도 안전하게 생성된다
- 주요 집계 축이 fixture 기준으로 재현 가능하다


### Step 11. 문서 갱신

목표:

- 구현 후 문서와 실제 산출물이 어긋나지 않게 한다

갱신 대상:

- `docs/chart_flow_phase5_observation_validation_spec_ko.md`
- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- 필요 시 `docs/chart_flow_phase5_observation_validation_implementation_checklist_ko.md`

완료 조건:

- 실제 report schema와 문서 schema가 일치한다


## 구현 중 금지사항

- 차트 캡처만 보고 분포를 수동 추정해 리포트 대신 사용하지 않는다
- baseline 의미 변경을 Phase 5 구현과 같이 하지 않는다
- calibration 수치 조정을 관측 코드 구현과 같이 하지 않는다
- 심볼별 override를 Phase 5 안에서 늘리지 않는다
- UI 렌더링 변경으로 관측 문제를 우회하지 않는다


## Done Definition

Phase 5는 아래를 만족하면 구현 완료로 본다.

1. latest distribution report가 저장된다
2. 심볼별 event family 분포를 볼 수 있다
3. zone별 분포를 볼 수 있다
4. score / strength level 분포를 볼 수 있다
5. block / guard 편향을 볼 수 있다
6. flat exit anomaly를 감시할 수 있다
7. global 대비 심볼 편차를 계산할 수 있다
8. 관련 unit test가 추가되고 통과한다
