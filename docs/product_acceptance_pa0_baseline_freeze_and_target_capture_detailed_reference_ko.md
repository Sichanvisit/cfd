# Product Acceptance PA0 Baseline Freeze and Target Capture Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 product acceptance 재정렬의 첫 단계인
`PA0 baseline freeze and target capture`
를 상세 기준으로 고정하는 문서다.

PA0의 목적은 코드를 먼저 바꾸는 것이 아니다.
먼저 아래를 흔들리지 않게 고정하는 것이다.

- 지금 차트가 실제로 어떻게 보이는가
- 지금 자동 진입이 어떤 family에서 열리고 막히는가
- 최근 청산/보유 판단이 어떤 성격으로 남아 있는가
- 사용자가 좋다고 느끼는 장면과 싫다고 느끼는 장면을 어떤 casebook 분류로 묶을 것인가

즉 PA0는
`수정 단계`
가 아니라
`이후 PA1~PA4에서 공통 기준으로 사용할 baseline을 얼리는 단계`
다.

## 2. 왜 PA0가 먼저인가

현재 프로젝트는 이미 아래가 많이 구축되어 있다.

- scene 기반 chart / entry 구조
- consumer-coupled check / entry 계약
- BF bridge summary
- wait / exit contract
- profitability / operations surface

하지만 지금 필요한 건
새 기능 추가보다
`내가 원하는 제품 동작`
을 기준선으로 다시 고정하는 일이다.

이 기준선 없이 바로 PA1 chart acceptance modifier로 들어가면,

- 원래도 이랬는지
- 최근 bridge 영향으로 바뀐 건지
- symbol별 문제인지
- scene / modifier / painter 중 어디가 원인인지

를 나중에 다시 추적하기 어려워진다.

따라서 PA0는 이후 모든 acceptance 작업의 공통 출발점이다.

## 3. PA0가 답해야 하는 질문

PA0에서는 최소 아래 질문에 답할 수 있어야 한다.

### 3-1. Chart Acceptance 질문

- 최근 `BTCUSD / NAS100 / XAUUSD`는 어떤 장면에서 주로 체크가 보이는가
- 어떤 `observe_reason / blocked_by / probe_scene`에서 `display_ready=true`가 많이 생기는가
- `check_stage`와 `display_score / repeat_count`는 실제로 어떻게 매핑되고 있는가
- 어디가 `must-show missing`이고 어디가 `must-hide leakage`인가

### 3-2. Entry Acceptance 질문

- 실제 자동 진입이 어떤 family에서 열리고 있는가
- `action`이 열린 row와 `entry_ready`까지만 갔다가 막힌 row는 무엇인가
- `must-enter` seed와 `must-block` seed를 어떤 기준으로 고를 것인가

### 3-3. Hold / Exit Acceptance 질문

- 최근 closed trade에서 어떤 exit reason / giveback / wait_quality가 많이 보이는가
- 어떤 row를 `must-hold`, `must-release`, `good-exit`, `bad-exit` seed로 먼저 볼 것인가

## 4. 이번 PA0의 범위

이번 PA0에서 직접 다루는 범위는 아래다.

- 최근 `entry_decisions.csv` row baseline freeze
- 현재 `runtime_status.json` 정책/런타임 snapshot freeze
- 현재 `chart_flow_distribution_latest.json` chart density snapshot freeze
- 최근 `trade_closed_history.csv` 기반 closed trade seed 수집
- tri-symbol baseline summary
- casebook seed queue 생성

이번 단계에서 하지 않는 것은 아래다.

- scene rule 수정
- modifier contract 수정
- symbol override 값 수정
- entry / wait / exit owner 의미 변경
- painter visual 조정

즉 PA0는 관찰과 기준선 고정까지만 한다.

## 5. 직접 owner와 데이터 source

### 5-1. 코드 owner

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [exit_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_service.py)

### 5-2. 데이터 source

- [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [runtime_status.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [chart_flow_distribution_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
- [trade_closed_history.csv](C:\Users\bhs33\Desktop\project\cfd\trade_closed_history.csv)

## 6. PA0에서 고정할 casebook 분류

PA0에서는 아직 정답을 확정하지 않는다.
대신 아래 분류로 seed를 수집한다.

### 6-1. Chart / Entry seed

- `aligned`
- `must-show missing`
- `must-hide leakage`
- `must-enter candidate`
- `must-block candidate`
- `visually similar divergence`

### 6-2. Hold / Exit seed

- `must-hold candidate`
- `must-release candidate`
- `good-exit candidate`
- `bad-exit candidate`

즉 PA0의 산출물은
최종 판정표가 아니라
이후 PA1~PA4에서 바로 끌어다 쓸 수 있는 casebook seed list다.

## 7. baseline 수집 원칙

### 7-1. tri-symbol 비교를 기본 단위로 둔다

PA0는 반드시 아래 세 심볼을 같이 본다.

- `BTCUSD`
- `NAS100`
- `XAUUSD`

이유는 acceptance 문제의 상당수가
단일 심볼 절대값보다
비슷한 장면을 각 심볼이 얼마나 다르게 읽는지에서 드러나기 때문이다.

### 7-2. nested contract 필드를 우선 읽는다

가능하면 아래 nested payload를 우선 기준으로 읽는다.

- `consumer_check_state_v1`
- `entry_wait_context_v1`
- `entry_wait_bias_bundle_v1`
- `transition_forecast_v1`
- `trade_management_forecast_v1`

즉 top-level flatten 필드가 있더라도,
가능하면 canonical nested contract와 같이 대조해 읽는다.

### 7-3. PA0 candidate는 seed일 뿐 verdict가 아니다

`must-show missing`, `bad-exit` 같은 이름이 있더라도
PA0에서 그것이 최종 확정이라는 뜻은 아니다.

PA0에서는
`나중에 바로 다시 검토해야 할 대표 장면`
을 빠르게 골라내는 것이 목적이다.

## 8. baseline 산출물

PA0 완료 시 최소 아래 산출물이 있어야 한다.

### 8-1. tri-symbol baseline summary

심볼별로 아래가 요약돼야 한다.

- recent row count
- stage density
- display ready ratio
- top observe reasons
- top blocked / non-action reasons
- chart flow event density

### 8-2. chart / entry seed lists

- `must-show missing` 대표 후보
- `must-hide leakage` 대표 후보
- `must-enter candidate` 대표 후보
- `must-block candidate` 대표 후보

### 8-3. hold / exit seed lists

- `must-hold candidate`
- `must-release candidate`
- `good-exit candidate`
- `bad-exit candidate`

### 8-4. divergence seed list

비슷한 `box_state / bb_state / reason family`인데
심볼 또는 stage 해석이 갈라지는 대표 사례를 모은다.

## 9. 구현 산출물 경로

PA0 baseline capture 구현체는 아래 경로에 최신 산출물을 남긴다.

- `data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json`
- `data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.csv`
- `data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.md`

이 산출물은 이후

- PA1 chart acceptance
- PA2 entry acceptance
- PA3 wait / hold acceptance
- PA4 exit acceptance

의 공통 입력 기준으로 쓴다.

## 10. 완료 기준

아래가 만족되면 PA0는 1차 close-out 가능하다.

1. tri-symbol baseline summary가 생성된다
2. chart / entry / exit seed queue가 각각 남는다
3. must-show / must-hide / must-enter / must-block / must-hold / must-release / good-exit / bad-exit의 seed가 최소한 대표 사례 수준으로 확보된다
4. 다음 단계에서 바로 참조할 latest json/csv/md 산출물이 남는다
5. PA1 chart acceptance modifier 구현 전에 기준선이 문서와 데이터 양쪽에서 고정된다

## 11. 한 줄 요약

```text
PA0는 코드를 먼저 바꾸는 단계가 아니라,
tri-symbol chart/entry/exit 기준선을 얼리고
다음 acceptance 단계에서 바로 쓸 casebook seed를 수집하는 단계다.
```
