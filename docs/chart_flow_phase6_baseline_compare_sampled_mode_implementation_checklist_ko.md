# Chart Flow Phase 6 Baseline Compare Sampled Mode Implementation Checklist

## 현재 상태

- 2026-03-25 KST 기준 구현 및 검증 완료
- 완료 항목:
  - Step 1. Mode contract 추가
  - Step 2. Baseline compare gate 추가
  - Step 3. baseline-only shadow 경로 구현
  - Step 4. baseline distribution latest 저장
  - Step 5. Stage D 자동 비교 연결
  - Step 6. decision log 입력 보강
  - Step 7. `OFF / SAMPLED / ALWAYS` 테스트 추가
  - Step 8. sampled mode 부하/운영 점검용 산출물 연결
- 검증:
  - `pytest tests/unit/test_chart_flow_baseline_compare.py tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_flow_rollout_status.py tests/unit/test_chart_painter.py tests/unit/test_observe_confirm_router_v2.py`
  - `104 passed`

## 목적

이 문서는 Phase 6 `baseline compare sampled mode`를 실제 코드로 옮길 때의
실행 순서와 범위 제한을 적은 구현 체크리스트다.

성격:

- 구현 기준 문서
- 범위 제어 문서
- sampled shadow compare 적용 순서를 고정하는 문서


## 현재 상태

2026-03-25 KST 기준 baseline compare sampled mode는
`spec 고정 완료 / implementation checklist 작성 완료 / 코드 미착수` 상태다.

이미 끝난 것:

- Phase 0 freeze 완료
- Phase 1 painter policy extraction 완료
- Phase 2 common threshold baseline 완료
- Phase 3 strength standardization 완료
- Phase 4 symbol override isolation 완료
- Phase 5 observation validation 완료
- Phase 6 sequential rollout supporting implementation 완료
- baseline compare sampled mode spec 작성 완료

아직 남은 것:

- mode contract 추가
- sampled interval gate 추가
- baseline-only distribution latest 생성 경로 추가
- Stage D 자동 비교 닫기
- sampled mode 회귀 테스트 추가


## 선행 문서

- `docs/chart_flow_phase6_baseline_compare_sampled_mode_spec_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_spec_ko.md`
- `docs/chart_flow_phase6_sequential_rollout_implementation_checklist_ko.md`
- `docs/chart_flow_phase5_observation_validation_spec_ko.md`
- `docs/chart_flow_phase4_symbol_override_isolation_spec_ko.md`


## 이번 단계 목표

이번 sampled mode의 목표는 아래 한 줄이다.

`실운영 override-on 경로는 그대로 두고, 15분 sampled shadow baseline-only 리포트를 만들어 Stage D 비교를 자동화하기`

이번 단계에서 포함하는 것:

- `OFF / SAMPLED / ALWAYS` mode contract
- baseline compare interval gate
- baseline-only distribution latest 생성
- rollout status Stage D 자동 비교 연결
- sampled mode 테스트 추가

이번 단계에서 하지 않는 것:

- live order path 변경
- chart draw 출력 변경
- event family 의미 변경
- baseline threshold 재설계


## 권장 구현 범위

대상 파일은 아래처럼 잡는 것이 자연스럽다.

- 신규 또는 보강 `backend/trading/chart_flow_rollout_status.py`
- 보강 `backend/trading/chart_painter.py`
- 필요 시 신규 `backend/trading/chart_flow_baseline_compare.py`
- 신규 또는 보강 `tests/unit/test_chart_flow_rollout_status.py`
- 신규 또는 보강 `tests/unit/test_chart_painter.py`

원칙:

- sampled compare 제어는 가능하면 별도 helper/contract로 분리
- 실운영 `override-on` 경로와 shadow `baseline-only` 경로를 섞지 않기
- `baseline-only`는 주문/차트 출력과 무관한 분석 산출물로만 남기기


## 작업 순서

### Step 1. Mode Contract 추가

목표:

- sampled compare 기능을 켜고 끌 수 있는 공통 계약을 추가한다

필수 항목:

- `mode`
- `interval_minutes`
- `baseline_output_path`
- `last_run_ts`

허용 모드:

- `OFF`
- `SAMPLED`
- `ALWAYS`

완료 조건:

- 기본값이 `OFF`다
- sampled interval 기본값이 `15분`이다


### Step 2. Baseline Compare Gate 추가

목표:

- sampled mode일 때 매 루프가 아니라 interval 기준으로만 shadow compare가 돌게 만든다

필수 규칙:

- `OFF`면 생성 안 함
- `SAMPLED`면 interval 경과 시에만 생성
- `ALWAYS`면 매번 생성

완료 조건:

- sampled mode가 과도한 재생성을 하지 않는다


### Step 3. 진짜 Baseline-Only Shadow 경로 구현

목표:

- symbol override를 제거한 baseline-only 결과를 별도 생성한다

핵심 원칙:

- `router override off`
- `painter override off`
- 주문 없음
- 차트 draw 출력 없음
- 분석용 latest distribution만 생성

완료 조건:

- baseline-only가 단순 painter 후처리 토글이 아니라 진짜 override-free shadow 결과다


### Step 4. Baseline Distribution Latest 저장

목표:

- baseline-only 결과를 고정된 latest 파일로 저장한다

권장 산출물:

- `data/analysis/chart_flow_distribution_baseline_latest.json`

완료 조건:

- override-on latest와 baseline-only latest가 동시에 존재할 수 있다


### Step 5. Stage D 자동 비교 연결

목표:

- rollout status가 baseline-only 파일을 읽어 Stage D를 자동 판정하게 만든다

반드시 볼 것:

- directional wait regression
- probe regression
- ready regression
- presence delta

완료 조건:

- baseline-only 파일이 있으면 `Stage D = pending`이 아니라 실제 판정이 나온다


### Step 6. Decision Log 보강

목표:

- sampled compare가 왜 `advance / hold / stop`이 됐는지 요약이 남게 한다

권장 항목:

- baseline-only available 여부
- sampled mode
- sampled interval
- 마지막 baseline refresh 시각
- Stage D summary

완료 조건:

- rollout status만 봐도 sampled compare 상태를 알 수 있다


### Step 7. OFF / SAMPLED / ALWAYS 회귀 테스트 추가

목표:

- mode별 동작이 섞이지 않게 고정한다

필수 테스트:

- `OFF`면 baseline latest 미생성
- `SAMPLED`면 interval 전 재생성 안 함
- `SAMPLED`면 interval 후 생성
- `ALWAYS`면 매번 생성
- baseline latest가 생기면 Stage D 자동 판정

완료 조건:

- sampled mode가 운영 중 예측 가능하게 동작한다


### Step 8. 부하/운영 점검

목표:

- sampled mode가 운영에 과부하를 주지 않는지 확인한다

권장 확인:

- 생성 주기
- 파일 쓰기 횟수
- 루프 지연 체감
- latest 리포트 정상 갱신 여부

완료 조건:

- `15분 sampled`가 실운영에 과하지 않다


## 하지 말아야 할 것

- baseline compare 구현 중 live order 로직을 건드리기
- shadow baseline 결과를 실차트 draw에 섞어 쓰기
- sampled mode 구현과 semantic 의미 변경을 같이 하기
- Stage D를 닫기 위해 override 의미를 바꾸기


## 완료 기준

- sampled mode contract가 존재한다
- `OFF / SAMPLED / ALWAYS`가 예측 가능하게 동작한다
- baseline-only latest가 별도로 생성된다
- rollout status가 baseline-only 비교를 읽어 Stage D를 자동 판정한다
- sampled mode 테스트가 통과한다


## 한 줄 결론

이 체크리스트의 핵심은
`실운영 경로는 건드리지 않고, sampled shadow baseline compare만 안전하게 추가하는 것`
이다.
