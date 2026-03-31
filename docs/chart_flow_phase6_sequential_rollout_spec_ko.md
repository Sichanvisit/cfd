# Chart Flow Phase 6 Sequential Rollout Spec

## 목적

이 문서는 Phase 6 `순차 rollout`의 상세 기준을 정의한다.

목표는 아래 한 줄이다.

`한 번에 다 바꾸지 않고, baseline을 먼저 안정화한 뒤 override와 calibration을 얹는다`

즉 이 문서의 역할은:

- Phase 1~5에서 만든 구조를 어떤 순서로 운영에 태울지 고정하고
- 각 단계에서 무엇을 보고 다음 단계로 넘어갈지 gate를 정하고
- 어떤 조정은 허용하고 어떤 조정은 금지할지 제한하고
- 다시 "캡처를 보고 한꺼번에 다 바꾸는" 방식으로 되돌아가지 않게 만드는 것이다.

작성 기준 시점:

- 2026-03-25 KST


## 구현 반영 상태

2026-03-25 KST 기준 Phase 6의 supporting implementation은 반영 완료 상태다.

반영 파일:

- `backend/trading/chart_flow_rollout_status.py`
- `backend/trading/chart_painter.py`
- `tests/unit/test_chart_flow_rollout_status.py`
- `tests/unit/test_chart_painter.py`

반영 범위:

- latest distribution report 기반 rollout status contract 추가
- stage A~E gate 계산 추가
- baseline-only comparison slot 추가
- history schema coverage 요약 추가
- painter flow history 저장 후 rollout status latest 자동 갱신 추가

검증 결과:

- `pytest tests/unit/test_chart_flow_rollout_status.py tests/unit/test_chart_painter.py tests/unit/test_chart_flow_distribution.py tests/unit/test_observe_confirm_router_v2.py`
- 결과: `99 passed`


## 현재 전제 상태

2026-03-25 KST 기준으로 아래 기반은 이미 준비된 상태다.

- Phase 1: painter policy extraction 완료
- Phase 2: common threshold baseline 도입 완료
- Phase 3: strength 1..10 표준화 완료
- Phase 4: symbol override isolation 완료
- Phase 5: observation / validation report 구축 완료

추가로,
Phase 6 자체도 운영 판단을 위한 latest rollout status 산출물까지는 준비된 상태다.
다만 실제 `baseline-only -> override-on -> micro calibration` 운영 rollout은 별도로 진행해야 한다.

즉 Phase 6은 새로운 semantic 구조를 만드는 단계가 아니라,
이미 정리된 baseline을 실제 운영 순서로 안정화하는 단계다.


## 1. 문서 관계

이 문서는 아래 문서를 이어받는다.

- `docs/chart_flow_buy_wait_sell_guide_ko.md`
- `docs/chart_flow_common_expression_policy_v1_ko.md`
- `docs/chart_flow_phase6_baseline_compare_sampled_mode_spec_ko.md`
- `docs/chart_flow_phase6_baseline_compare_sampled_mode_implementation_checklist_ko.md`
- `docs/chart_flow_phase2_common_threshold_baseline_spec_ko.md`
- `docs/chart_flow_phase2_common_threshold_implementation_checklist_ko.md`
- `docs/chart_flow_phase3_strength_standard_spec_ko.md`
- `docs/chart_flow_phase3_strength_implementation_checklist_ko.md`
- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`
- `docs/chart_flow_phase4_symbol_override_implementation_checklist_ko.md`
- `docs/chart_flow_phase5_observation_validation_spec_ko.md`
- `docs/chart_flow_phase5_observation_validation_implementation_checklist_ko.md`

각 문서 역할은 아래와 같다.

- guide: 전체 semantic -> chart 흐름 설명
- policy v1: 공통 policy field와 owner 정의
- phase6 baseline compare sampled mode: baseline-only shadow 비교 모드 상세안
- phase6 baseline compare sampled checklist: sampled mode 구현 순서와 범위 제한
- phase2: 공통 threshold baseline 정의
- phase3: strength 10단계와 visual binding 정의
- phase4: symbol override를 baseline 밖으로 격리
- phase5: 분포를 수치로 관측하는 기준과 산출물 정의
- phase6: 위 구조를 어떤 순서로 운영에 적용하고 검증할지 정의


## 2. Phase 6의 범위

이번 단계에서 고정할 것은 아래 5개다.

1. rollout 순서
2. 단계별 observation window
3. 단계별 advance gate와 stop gate
4. rollout 중 허용되는 조정 축
5. baseline-only / override-on 비교 원칙

이번 단계에서 하지 않을 것은 아래다.

- event family 의미 재정의
- Phase 1~4 구조를 다시 열어 큰 설계 변경하기
- screenshot 체감만으로 수치 조정하기
- override로 semantic 의미를 바꾸기


## 3. 왜 Phase 6이 필요한가

Phase 1~5가 끝났다고 해서 바로 안정화가 끝나는 것은 아니다.

여전히 아래 위험이 남아 있다.

- baseline은 맞는데 override 복원 순서가 잘못되어 다시 한쪽으로 쏠릴 수 있다
- strength가 들어간 뒤 visual 체감이 특정 symbol에서 과장될 수 있다
- 분포 리포트가 있어도 "언제 조정하고 언제 멈출지" 기준이 없으면 다시 감으로 튜닝하게 된다
- 한 번에 여러 축을 같이 바꾸면 어떤 변화가 원인인지 분리할 수 없다

따라서 Phase 6의 핵심은
`좋은 구조를 천천히 운영에 얹는 순서와 게이트를 고정하는 것`
이다.


## 4. Rollout 원칙

### 4-1. baseline을 먼저 본다

모든 판단의 1차 기준은 baseline이다.

원칙:

- 먼저 `semantic baseline -> common threshold -> strength`가 공통 언어로 동작하는지 확인한다
- override는 그 다음에 복원한다
- override가 켜진 상태에서도 baseline이 무너지면 안 된다


### 4-2. 한 번에 한 축만 바꾼다

한 단계에서 바꾸는 축은 가능한 한 하나로 제한한다.

예:

- semantic 의미 점검 단계에서 threshold를 같이 건드리지 않는다
- threshold 단계에서 strength bucket을 같이 건드리지 않는다
- override 단계에서 event family 의미를 같이 건드리지 않는다


### 4-3. 모든 변경 뒤에는 관측 윈도우가 있어야 한다

rollout은 `변경 -> 관측 -> 비교 -> 결정` 순서로 간다.

권장 관측 윈도우:

- quick check: 최근 `16캔들`
- stability check: 최근 `64캔들`
- 필요 시: 최근 `6시간`, `24시간`

금지:

- 변경 직후 캡처 한두 장만 보고 다음 단계로 바로 넘어가기


### 4-4. anomaly는 즉시 stop gate로 본다

아래는 즉시 멈추고 원인을 보는 편이 맞다.

- `flat_exit_count > 0`
- 특정 단계 적용 직후 `EXIT_NOW`가 flat 상태에서 재발
- event family 의미가 바뀌는 수준의 unexpected change
- override 적용 후 `BUY_WAIT` / `SELL_WAIT`가 사라지는 semantic regression


### 4-5. override는 미세조정만 한다

override는 아래만 바꿀 수 있다.

- confirm floor multiplier
- advantage multiplier
- probe tolerance
- structural relief on/off
- 특정 probe scene / context 완화

override가 바꾸면 안 되는 것:

- `BUY_WAIT` / `SELL_WAIT` 의미
- soft block downgrade 의미
- `WAIT / PROBE / READY / ENTER / EXIT` 계층
- terminal exit의 position requirement


## 5. 순차 rollout 단계

### 5-1. Stage A. Semantic Baseline Verification

목표:

- 차트 semantic 의미가 심볼과 무관하게 같은 뜻으로 읽히는지 확인한다

관측 포인트:

- `WAIT + BUY -> BUY_WAIT`
- `WAIT + SELL -> SELL_WAIT`
- soft block이면 `READY -> WAIT`
- flat 상태에서는 `EXIT_NOW` 금지

권장 윈도우:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

허용 조정:

- semantic drift 수정
- 문서/코드 기준 불일치 수정

비허용 조정:

- confirm floor 조정
- probe support 조정
- symbol 특례 추가

advance gate:

- semantic regression이 없다
- `flat_exit_count = 0`
- directional wait가 필요한 문맥에서 실제로 `BUY_WAIT` / `SELL_WAIT`가 살아난다

stop gate:

- `WAIT`가 다시 전부 neutral로 눌린다
- flat인데 exit family가 다시 기록된다


### 5-2. Stage B. Common Threshold Baseline

목표:

- 심볼 특례 없이도 공통 threshold가 기본 언어로 동작하는지 확인한다

관측 포인트:

- `BUY_WAIT / SELL_WAIT / BUY_PROBE / SELL_PROBE / BUY_READY / SELL_READY / WAIT` 분포
- lower / middle / upper zone별 directional family 분포
- `blocked_by`, `action_none_reason` 분포

권장 윈도우:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

허용 조정:

- `confirm_floor`
- `confirm_advantage`
- `probe min support`
- `probe min pair_gap`
- directional wait 최소 readiness
- wait brightness threshold
- buy anchor ratio

비허용 조정:

- 심볼별 의미 변경
- strength bucket 수정
- override 성격의 scene 예외 추가

advance gate:

- baseline-only 기준으로도 event family가 공통 언어로 읽힌다
- 극단적 쏠림이 있어도 시장 위치로 설명 가능하다
- 특정 symbol만 semantic적으로 잠겨 있는 상태가 아니다

stop gate:

- 특정 symbol이 모든 구간에서 일방적으로 neutral 또는 한쪽 directional로 고정된다
- zone별 분포가 의미와 다르게 나온다


### 5-3. Stage C. Strength Rollout

목표:

- 같은 strength level이 심볼과 event family가 달라도 비슷한 체감으로 보이게 만든다

관측 포인트:

- `strength_level 1..10` 분포
- `event_kind x strength_level`
- `zone x strength_level`
- 같은 level의 색/밝기/선 굵기 체감

권장 윈도우:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

허용 조정:

- level bucket edge
- alpha/brightness binding
- line width band

비허용 조정:

- strength를 이용해 semantic 문제를 덮기
- symbol마다 다른 strength 체계를 쓰기

advance gate:

- 같은 `level 6` directional family가 심볼이 달라도 비슷한 강도로 보인다
- level이 높아질수록 시각 강도가 일관되게 증가한다
- 특정 symbol만 level 1~3에 과도하게 몰리는 현상이 semantic 오류로 이어지지 않는다

stop gate:

- visual만 과장되고 semantic readiness와 체감이 어긋난다
- 특정 event family에서 level 변화가 거의 구분되지 않는다


### 5-4. Stage D. Symbol Override Restore

목표:

- baseline을 무너뜨리지 않는 범위에서 symbol override를 다시 얹는다

관측 포인트:

- baseline-only vs override-on 분포 차이
- override 적용 전후 event family 유지 여부
- symbol별 zone 편차 완화 여부

권장 윈도우:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`

허용 조정:

- floor multiplier
- advantage multiplier
- structural relief
- scene/context 완화

비허용 조정:

- symbol마다 `BUY_WAIT`를 다르게 해석
- symbol마다 soft block을 `READY`로 유지
- symbol마다 `WAIT / PROBE / READY` 계층 변경

advance gate:

- override를 켜도 event family 의미는 그대로다
- override 효과가 빈도와 문턱 조절에 머문다
- baseline 대비 편차가 설명 가능하게 줄어든다

stop gate:

- override 적용만으로 family 의미가 바뀐다
- 특정 symbol만 과도하게 한쪽으로 재쏠린다


### 5-5. Stage E. Distribution-Based Micro Calibration

목표:

- 분포 리포트를 기준으로 마지막 미세조정을 한다

관측 포인트:

- symbol별 `buy_presence_ratio / sell_presence_ratio / neutral_ratio`
- `buy_minus_sell`
- zone별 imbalance
- `blocked_by`, `action_none_reason`, `probe_scene_id`
- `flat_exit_count`

권장 윈도우:

- quick: 최근 `16캔들`
- stability: 최근 `64캔들`
- review: 최근 `24시간`

허용 조정:

- small multiplier tuning
- small tolerance tuning
- structural relief on/off 재조정

비허용 조정:

- semantic 의미 되돌리기
- baseline을 심볼별로 쪼개기
- painter와 router가 서로 다른 기본값을 다시 들게 만들기

advance gate:

- 편차를 숫자로 설명할 수 있다
- 조정 후 분포가 더 예측 가능해진다
- override는 여전히 미세조정 역할만 한다

stop gate:

- 조정이 누적될수록 baseline 설명력이 약해진다
- 숫자 조정보다 예외 분기 추가가 더 많아진다


## 6. 단계별 관측 창과 게이트 요약

| Stage | 목적 | 최소 관측 창 | 주 지표 | advance gate | stop gate |
| --- | --- | --- | --- | --- | --- |
| A | semantic baseline 확인 | `16캔들` + `64캔들` | directional wait, flat exit | 의미 회귀 없음 | flat exit, directional wait 소실 |
| B | 공통 threshold baseline 확인 | `16캔들` + `64캔들` | event/zone/block 분포 | baseline-only로 공통 언어 유지 | symbol lock, zone mismatch |
| C | strength 체감 정렬 | `16캔들` + `64캔들` | level 분포, visual binding | 같은 level 체감 유사 | visual-semantic 불일치 |
| D | symbol override 복원 | `16캔들` + `64캔들` | baseline vs override diff | override가 문턱만 조절 | family 의미 변화 |
| E | 최종 미세조정 | `16캔들` + `64캔들` + `24h` | deviation, imbalance, anomaly | 편차가 숫자로 설명 가능 | 예외 분기 재증가 |


## 7. baseline-only / override-on 비교 원칙

Phase 6에서 가장 중요한 비교는 아래 둘이다.

- `baseline-only`
- `override-on`

읽는 원칙:

- baseline-only는 공통 언어가 살아 있는지 본다
- override-on은 실제 운영에서 빈도와 문턱이 얼마나 보정되는지 본다
- 두 모드의 차이가 event family 의미 변화로 이어지면 안 된다

권장 비교 항목:

- `symbol x event_kind`
- `symbol x zone_presence`
- `symbol x strength_level`
- `symbol x buy_minus_sell`
- `anomalies.flat_exit_count`


## 8. rollout 중 허용되는 조정과 금지되는 조정

### 허용

- policy 값의 작은 수치 조정
- strength visual binding의 작은 bucket 조정
- symbol override multiplier / relief 조정
- report window 확장

### 금지

- 의미와 수치 조정을 한 커밋에서 같이 바꾸기
- screenshot 체감만으로 심볼 특례 추가하기
- painter와 router에 서로 다른 baseline 값을 다시 두기
- override를 이용해 semantic 문제를 가리기


## 9. 권장 산출물

Phase 6에서 남겨야 할 산출물은 아래다.

- 최신 distribution report
- baseline-only vs override-on 비교 메모
- stage별 decision log
- anomaly 발생 시 stop / rollback 메모

운영 기준 파일 예:

- `data/analysis/chart_flow_distribution_latest.json`
- 필요 시 stage별 review note


## 10. 완료 기준

Phase 6 완료는 아래 조건을 함께 만족할 때로 본다.

- 공통 baseline만으로도 차트가 과하게 한쪽으로 고정되지 않는다
- override를 꺼도 semantic 언어는 유지된다
- override를 켜도 event family 의미는 바뀌지 않는다
- strength level이 심볼 간에 비슷한 체감으로 읽힌다
- `flat_exit_count`가 운영 관측 창에서 계속 `0`을 유지한다
- calibration이 예외 분기 추가가 아니라 숫자 미세조정 중심으로 끝난다


## 11. 한 줄 결론

Phase 6은 "무엇을 더 만들까"보다
`언제 멈추고, 언제 다음 단계로 넘어가며, 무엇만 조정할 것인가`
를 고정하는 단계다.

즉 순차 rollout의 본질은
`좋은 구조를 급하게 다 켜지 않고, 관측과 게이트를 두고 천천히 운영에 올리는 것`
이다.
