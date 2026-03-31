# Chart Flow Phase 6 Baseline Compare Sampled Mode Spec

## 구현 상태

- 2026-03-25 KST 기준 구현 완료
- sampled compare 모드: `OFF / SAMPLED / ALWAYS`
- 기본 sampled interval: `15분`
- 구현 파일:
  - `backend/trading/chart_flow_baseline_compare.py`
  - `backend/trading/chart_flow_rollout_status.py`
  - `backend/trading/chart_painter.py`
- 산출물:
  - `data/analysis/chart_flow_distribution_compare_override_latest.json`
  - `data/analysis/chart_flow_distribution_baseline_latest.json`
  - `data/analysis/chart_flow_rollout_status_latest.json`
- 검증:
  - `pytest tests/unit/test_chart_flow_baseline_compare.py tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_flow_rollout_status.py tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
  - `104 passed`

## 목적

이 문서는 Phase 6에서 사용할
`baseline-only vs override-on 비교 모드`
의 실현상세와 구현 로드맵을 정의한다.

목표는 아래 한 줄이다.

`상시 이중 실행 없이도, 필요할 때 baseline-only 비교 리포트를 만들어 override가 의미를 바꾸는지 점검할 수 있게 한다`

작성 기준 시점:

- 2026-03-25 KST


## 선행/후속 문서

- `docs/chart_flow_phase6_sequential_rollout_spec_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_implementation_checklist_ko.md`
- `docs/chart_flow_phase6_baseline_compare_sampled_mode_implementation_checklist_ko.md`


## 1. 왜 이 문서가 필요한가

현재는 아래가 이미 있다.

- `override-on distribution report`
- `rollout status latest`
- Stage A/B/C/E gate 계산

하지만 Stage D는 아직 완전히 닫히지 않았다.

이유:

- Stage D는 `baseline-only`와 `override-on`을 비교해야 하는데
- 현재 자동 생성되는 것은 `override-on` 리포트뿐이기 때문이다

즉 문제는 "비교 형식이 없다"가 아니라
`비교 기준선 데이터가 자동으로 생산되지 않는다`
는 점이다.


## 2. 이 모드가 의미하는 것

### 2-1. `override-on`

실제 운영 경로다.

- common baseline 적용
- symbol override 적용
- chart / distribution / rollout status 생성

즉 사용자가 실제로 보고 있는 현재 결과다.


### 2-2. `baseline-only`

비교용 shadow 경로다.

- common baseline만 적용
- symbol override는 끔
- chart 표시는 하지 않음
- 주문에도 관여하지 않음
- 비교용 distribution report만 생성

즉 "같은 입력을 공통 baseline만으로 해석했으면 어땠을까"를 보는 기준선이다.


### 2-3. Stage D가 실제로 보고 싶은 것

Stage D의 핵심 질문은 이것이다.

- override가 `BUY_WAIT`를 더 자주 보이게 한 것인가
- 아니면 override가 `BUY_WAIT`를 아예 다른 family로 바꿔버린 것인가

허용되는 변화:

- 빈도 변화
- 문턱 변화
- readiness 완화

허용되지 않는 변화:

- family 의미 변화
- directional wait 소실
- soft block 의미 역전


## 3. 왜 컴퓨터를 한 대 더 쓸 필요는 없는가

이 기능은 별도 PC가 필요한 기능이 아니다.

필요한 것은:

- 두 번째 하드웨어가 아니라
- 같은 입력을 다른 모드로 한 번 더 평가하는 `shadow 비교 경로`
다.

즉 한 컴퓨터에서 아래처럼 충분하다.

1. 실운영 `override-on`
2. 비교용 `baseline-only`

중요:

- `baseline-only`는 차트 표시와 주문에 관여하지 않아야 한다
- 분석용 JSON만 저장해야 한다


## 4. 왜 상시가 아니라 sampled mode가 적절한가

상시 dual-write는 가능하지만 기본 운영으로는 과할 수 있다.

이유:

- router / painter 양쪽에서 override를 끈 shadow 계산이 추가된다
- 비교 리포트는 매 루프마다 필요하지 않다
- Phase 6의 목적은 "초정밀 실시간 비교"가 아니라 "구조적 drift 확인"이다

따라서 sampled mode가 더 현실적이다.

권장 기본값:

- `OFF`

권장 운영값:

- `SAMPLED`
- `15분마다 1회`

디버그 전용:

- `ALWAYS`


## 5. 모드 계약

정식 이름 제안:

- `chart_flow_baseline_compare_mode_v1`

허용 모드:

| mode | 의미 | 권장도 |
| --- | --- | --- |
| `OFF` | baseline-only 비교 리포트를 만들지 않음 | 기본값 |
| `SAMPLED` | 지정 주기마다 baseline-only shadow 리포트를 생성 | 추천 |
| `ALWAYS` | 매 루프/매 이벤트마다 baseline-only를 생성 | 디버그 전용 |

권장 기본 설정:

- `mode = OFF`
- `interval_minutes = 15`


## 6. 진짜 baseline-only가 되려면 어디까지 꺼야 하나

이 부분이 가장 중요하다.

단순히 painter scene override만 끄면 진짜 baseline-only가 아니다.

이유:

- symbol override는 [observe_confirm_router.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\observe_confirm_router.py) 에도 들어 있다
- painter는 이미 override가 반영된 최종 semantic row를 받아 그리는 경우가 많다

따라서 비교 기준선은 아래 둘을 같이 꺼야 한다.

1. router override off
2. painter override off

즉 baseline-only는
`최종 표시 단계만 끄는 모드`
가 아니라
`symbol-specific exception 계층 전체를 제거한 shadow 해석 결과`
여야 한다.


## 7. sampled mode 권장 구조

### 7-1. 실운영 경로

- 기존 운영 유지
- `override-on` 그대로 사용
- chart / order / distribution / rollout status 계속 생성


### 7-2. shadow 비교 경로

- sampled interval이 되었을 때만 실행
- 같은 입력 row 또는 같은 snapshot 기준으로 shadow evaluation 수행
- `router override off`
- `painter override off`
- baseline-only distribution latest 생성


### 7-3. 비교 상태 경로

- rollout status 생성 시
  - `override-on distribution latest`
  - `baseline-only distribution latest`
  둘을 읽어 Stage D를 판정


## 8. 산출물

권장 파일은 아래처럼 분리한다.

| 산출물 | 설명 |
| --- | --- |
| `data/analysis/chart_flow_distribution_latest.json` | 실제 운영용 `override-on` |
| `data/analysis/chart_flow_distribution_baseline_latest.json` | sampled shadow `baseline-only` |
| `data/analysis/chart_flow_rollout_status_latest.json` | 둘 비교 포함 Phase 6 gate 결과 |

추가로 있으면 좋은 것:

| 산출물 | 설명 |
| --- | --- |
| `decision_log_latest` | 마지막 advance / hold / stop 이유 요약 |
| sampled 실행 시각 | 마지막 baseline refresh 시각 |


## 9. sampled mode가 실제로 주는 도움

이 모드가 있으면 아래 질문을 더 명확히 볼 수 있다.

- XAU의 buy 부족이 baseline 문제인가
- BTC의 probe 과다가 override 때문인가
- NAS의 sell 편향이 시장 위치 때문인가, override 때문인가
- override가 directional wait를 살린 것인가, family를 바꾼 것인가

즉 미세조정의 대상이

- baseline threshold인지
- strength binding인지
- symbol override인지

를 더 정확히 분리하는 데 도움이 된다.

필수는 아니지만,
`미세조정을 감각이 아니라 원인 분리 중심으로 하게 만드는 보조 계측 장치`
로는 꽤 유용하다.


## 10. 권장 구현 범위

이번 기능은 아래 범위로 제한하는 것이 안전하다.

- 새 mode contract 추가
- sampled interval gate 추가
- baseline-only distribution latest 생성 경로 추가
- rollout status Stage D 자동 비교 닫기
- 테스트 추가

이번 기능에서 하지 말아야 할 것:

- live order path 변경
- chart 표현 의미 변경
- Phase 2/3 baseline 재조정
- override 정책 의미 수정


## 11. 권장 구현 순서

### Step 1. mode contract 추가

추가할 것:

- `OFF / SAMPLED / ALWAYS`
- `interval_minutes`
- baseline output path


### Step 2. sampled scheduler gate 추가

추가할 것:

- 마지막 baseline compare 실행 시각
- `15분마다` 또는 설정 interval마다만 shadow refresh


### Step 3. baseline-only 생성 경로 구현

원칙:

- router override off
- painter override off
- 주문 / 표시 없음
- 분석용 distribution만 저장


### Step 4. rollout status Stage D 자동 비교 연결

추가할 것:

- baseline distribution latest 자동 입력
- directional wait regression
- probe/ready regression
- presence delta


### Step 5. 테스트 추가

반드시 볼 것:

- `OFF`면 baseline file이 안 생김
- `SAMPLED`면 interval 이내엔 재생성 안 함
- `ALWAYS`면 매번 갱신
- baseline-only가 없을 때 `Stage D = pending`
- baseline-only가 있으면 `Stage D`가 자동 판정


### Step 6. 운영 점검

확인할 것:

- sampled baseline file 생성 여부
- rollout status의 Stage D 상태 변화
- 부하 증가가 과하지 않은지


## 12. 추천 결론

가장 현실적인 운영값은 아래다.

- 기본: `OFF`
- 안정화 기간: `SAMPLED`
- interval: `15분`
- 목적: Phase 6 Stage D 비교와 미세조정 원인 분리

즉 이 모드는 상시 운영 기능이라기보다
`안정화 기간 동안만 켜두는 shadow calibration 보조 장치`
로 보는 것이 맞다.


## 13. 한 줄 요약

이 문서가 제안하는 것은
`상시 이중 실행`
이 아니라
`15분마다 한 번 baseline-only shadow 리포트를 생성해서, override가 의미를 바꾸지 않는지 확인하는 sampled 비교 모드`
다.
