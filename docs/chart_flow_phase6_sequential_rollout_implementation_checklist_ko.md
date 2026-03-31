# Chart Flow Phase 6 Sequential Rollout Implementation Checklist

## 목적

이 문서는 Phase 6 `순차 rollout`을 실제 운영에 적용할 때의
실행 순서와 범위 제한을 적은 rollout 체크리스트다.

성격:

- 운영 기준 문서
- gate / stop 기준 문서
- calibration 범위 제어 문서


## 현재 상태

2026-03-25 KST 기준 Phase 6은 `spec 고정 완료 / rollout checklist 작성 완료 / supporting implementation 완료 / 실제 운영 rollout 미실행` 상태다.

이미 끝난 것:

- Phase 0 freeze 완료
- Phase 1 painter policy extraction 완료
- Phase 2 common threshold baseline 완료
- Phase 3 strength standardization 완료
- Phase 4 symbol override isolation 완료
- Phase 5 observation validation 완료
- Phase 6 sequential rollout spec 작성 완료
- `chart_flow_rollout_status.py` 추가 완료
- stage A~E rollout gate 계산 추가 완료
- baseline-only comparison slot 추가 완료
- painter latest rollout status 자동 저장 완료
- rollout status 회귀 테스트 추가 완료

아직 남은 것:

- baseline-only 관측 운영
- override-on 관측 운영
- stage별 decision gate 기록
- 분포 비교 기반 micro calibration

이 문서는 Phase 6를 실제로 굴릴 때
"무엇을 어떤 순서로 보고, 어떤 경우에 멈출지"를 고정하는 문서다.


## 구현 반영 결과

이번 단계에서 실제 반영된 파일:

- `backend/trading/chart_flow_rollout_status.py`
- `backend/trading/chart_painter.py`
- `tests/unit/test_chart_flow_rollout_status.py`
- `tests/unit/test_chart_painter.py`

회귀 검증:

- `pytest tests/unit/test_chart_flow_rollout_status.py tests/unit/test_chart_painter.py tests/unit/test_chart_flow_distribution.py tests/unit/test_observe_confirm_router_v2.py`
- 결과: `99 passed`


## 선행 문서

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_spec_ko.md`
- `docs/chart_flow_phase6_baseline_compare_sampled_mode_spec_ko.md`
- `docs/chart_flow_phase6_baseline_compare_sampled_mode_implementation_checklist_ko.md`
- `docs/chart_flow_phase5_observation_validation_spec_ko.md`
- `docs/chart_flow_phase5_observation_validation_implementation_checklist_ko.md`
- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`
- `docs/chart_flow_phase3_strength_standard_spec_ko.md`


## 이번 단계 목표

이번 Phase 6의 목표는 아래 한 줄이다.

`baseline -> strength -> override -> calibration 순서를 지키면서, 분포와 anomaly를 보고 천천히 운영 안정화를 진행하기`

이번 단계에서 포함하는 것:

- baseline-only / override-on 관측 순서 고정
- stage별 observation window 고정
- advance gate / stop gate 점검
- anomaly 발생 시 stop / rollback 판단
- 분포 리포트 기반 micro calibration 착수 기준 고정

이번 단계에서 하지 않는 것:

- event family 의미 재정의
- baseline과 override를 다시 섞는 구조 변경
- screenshot 체감만으로 조정하기
- 한 번에 여러 축을 동시에 조정하기


## 권장 운영 범위

주로 보는 산출물은 아래다.

- `data/analysis/chart_flow_distribution_latest.json`
- `data/runtime_status.json`
- `data/runtime_status.detail.json`
- `Common/Files/*_flow_history.json`

원칙:

- rollout 판단의 1차 기준은 distribution report다
- 캡처는 보조 증거로만 쓰고, 최종 판단은 수치와 anomaly로 한다
- 가능하면 같은 observation window로 baseline-only와 override-on을 비교한다


## 작업 순서

현재 기준으로 아래 Step 1~10은 Phase 6를 실제로 운영에 태울 때의 기준 순서다.

### Step 1. Rollout Input Freeze

목표:

- Phase 6에서 무엇을 보고 판단할지 입력을 먼저 고정한다

필수 입력:

- latest distribution report
- latest runtime status
- latest flow history

권장 확인:

- `flat_exit_count`
- `buy_presence_ratio / sell_presence_ratio / neutral_ratio`
- `zone_presence`
- `strength_level_counts`
- `blocked_by_counts`

완료 조건:

- rollout 중 어떤 숫자를 보고 판단할지 합의된 상태다
- 캡처만 보고 넘어가는 상태가 아니다


### Step 2. Baseline-Only 비교 모드 준비

목표:

- override-on 결과만 보지 않고, baseline-only 비교가 가능한 상태를 만든다

작업:

- 가능하면 baseline-only report를 별도로 생성하거나
- 같은 history 기준으로 override-on 결과와 나란히 비교할 메모를 만든다

완료 조건:

- baseline 문제인지 override 문제인지 분리해서 볼 수 있다


### Step 3. Stage A Semantic Baseline Verification

목표:

- semantic 의미가 실제 운영에서도 유지되는지 확인한다

반드시 볼 것:

- `WAIT + BUY -> BUY_WAIT`
- `WAIT + SELL -> SELL_WAIT`
- soft block이면 `READY -> WAIT`
- flat 상태에서 `EXIT_NOW` 억제

권장 관측 창:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

advance gate:

- semantic regression이 없다
- `flat_exit_count = 0`
- directional wait가 필요한 자리에서 실제로 directional wait가 기록된다

stop gate:

- directional wait가 다시 neutral로 눌린다
- flat 상태에서 exit family가 재등장한다


### Step 4. Stage B Common Threshold Baseline

목표:

- 공통 threshold만으로도 차트 언어가 과도하게 깨지지 않는지 확인한다

반드시 볼 것:

- `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY / WAIT`
- `LOWER / MIDDLE / UPPER` zone 분포
- `blocked_by`, `action_none_reason`

권장 관측 창:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

advance gate:

- baseline-only에서도 공통 언어가 유지된다
- 한쪽 쏠림이 있더라도 시장 위치로 설명 가능하다
- 특정 symbol만 semantic적으로 잠겨 있지 않다

stop gate:

- 특정 symbol이 모든 구간에서 한쪽 family나 neutral에 고정된다
- zone 분포가 semantic 기대와 다르다


### Step 5. Stage C Strength Rollout

목표:

- strength level이 실제 체감 강도로 잘 읽히는지 확인한다

반드시 볼 것:

- `strength_level_counts`
- `event_kind_by_strength_level`
- level별 color / brightness / width 체감

권장 관측 창:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

advance gate:

- 같은 level이 symbol이 달라도 비슷한 강도로 보인다
- level 상승에 따라 시각 강도도 자연스럽게 올라간다

stop gate:

- visual 체감이 semantic readiness와 어긋난다
- 특정 family에서 level 차이가 거의 느껴지지 않는다


### Step 6. Stage D Symbol Override Restore

목표:

- override를 다시 얹되 baseline 의미를 흐리지 않게 한다

반드시 볼 것:

- baseline-only vs override-on 차이
- override 적용 전후 event family 유지 여부
- symbol별 편차 완화 여부

권장 관측 창:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

advance gate:

- override를 켜도 event family 의미는 그대로다
- override가 문턱과 빈도만 조절한다
- symbol별 편차가 설명 가능하게 줄어든다

stop gate:

- override 적용만으로 family 의미가 바뀐다
- 특정 symbol이 다시 과도하게 재쏠린다


### Step 7. Stage E Micro Calibration

목표:

- 분포 리포트를 기준으로 마지막 수치 미세조정을 한다

반드시 볼 것:

- `buy_presence_ratio / sell_presence_ratio / neutral_ratio`
- `buy_minus_sell`
- `zone_presence`
- `blocked_by_counts`
- `probe_scene_counts`
- `flat_exit_count`

권장 관측 창:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`
- review: 최근 `24시간`

허용 조정:

- small multiplier tuning
- small tolerance tuning
- structural relief on/off 재조정

비허용 조정:

- semantic 의미 되돌리기
- baseline을 심볼별로 다시 분해하기
- override 예외 분기 추가를 기본 수단으로 쓰기

완료 조건:

- 편차를 숫자로 설명할 수 있다
- 조정이 숫자 중심으로 끝난다


### Step 8. Anomaly Stop / Rollback 판단

목표:

- 이상 징후가 생기면 즉시 멈추고 되돌릴 기준을 고정한다

즉시 stop 대상:

- `flat_exit_count > 0`
- semantic family regression
- override 적용 후 directional wait 소실
- visual-semantic 괴리 급증

권장 대응:

- 마지막 단계 변경만 되돌린다
- baseline은 건드리지 않고 override / binding / multiplier부터 확인한다

완료 조건:

- anomaly가 생겼을 때 "무엇부터 되돌릴지"가 명확하다


### Step 9. Stage Decision Log 기록

목표:

- 각 stage에서 왜 advance / stop / hold를 선택했는지 남긴다

최소 기록 항목:

- stage 이름
- observation window
- 핵심 분포 숫자
- anomaly 유무
- decision: `advance / hold / stop / rollback`

완료 조건:

- 다음 조정 시 과거 판단 근거를 다시 추적할 수 있다


### Step 10. Phase 6 Done Check

목표:

- rollout이 끝났는지 마지막으로 확인한다

최종 확인:

- baseline-only로도 차트 언어가 유지된다
- override-on에서도 의미가 바뀌지 않는다
- strength 체감이 심볼 간 크게 어긋나지 않는다
- `flat_exit_count = 0`이 유지된다
- 조정이 예외 분기 추가보다 수치 미세조정 중심으로 끝난다

완료 조건:

- Phase 6 완료 기준을 충족한다


## 하지 말아야 할 것

이번 Phase 6에서는 아래를 하지 않는 편이 맞다.

- 의미 수정과 threshold 조정을 한 번에 같이 적용하기
- baseline과 override를 한 커밋에서 동시에 크게 바꾸기
- screenshot 체감만으로 심볼 특례를 추가하기
- anomaly가 있는데도 observation window 없이 다음 단계로 넘어가기


## 한 줄 결론

Phase 6 checklist의 핵심은
`무엇을 먼저 켜고, 무엇을 관측하고, 어떤 경우에 멈출지`
를 고정하는 것이다.

즉 이 문서는 rollout을 빠르게 하기 위한 문서가 아니라,
`rollout이 흔들리지 않게 하기 위한 운영 가드레일`
이다.
