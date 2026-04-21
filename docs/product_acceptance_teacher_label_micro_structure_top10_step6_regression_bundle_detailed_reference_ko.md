# Teacher-Label Micro-Structure Top10 Step 6 상세 기준서

## 목표

Step 6의 목적은 새 feature를 더 만드는 것이 아니라, Step 1부터 Step 5까지 만든 micro-structure 경로가 한 흐름으로 실제로 이어지는지 검증하는 것이다.

검증하려는 흐름은 아래와 같다.

`1분봉 OHLCV -> micro_structure_v1 -> StateRawSnapshot -> StateVectorV2 metadata -> ForecastFeatures harvest -> entry hot payload / closed-history compact`

## 이번 단계에서 꼭 확인할 것

1. Step 1 helper가 만든 `micro_structure_v1` 값이 Step 2 raw snapshot canonical field로 승격되는지
2. Step 3에서 semantic state와 source micro value가 vector/forecast harvest로 실제 수확되는지
3. Step 4 hot payload surface가 위 값을 flat field로 끌어내는지
4. Step 5 closed compact 경로가 semantic/numeric micro 값을 잃지 않는지
5. gap anchor가 없어도 전체 파이프라인이 실패하지 않고 `GAP_CONTEXT_MISSING`으로 안전하게 떨어지는지

## Step 6 검증 축

### 축 1. breakout/continuation 계열 smoke

- 압축 + 연속봉 + volume burst가 있는 샘플을 넣는다
- semantic state가 최소한 non-empty로 수확되고
- source micro numeric 값이 helper 출력과 일치해야 한다

### 축 2. reversal/wick 계열 smoke

- 꼬리와 retest가 반복되는 샘플을 넣는다
- `micro_reversal_risk_state`가 `WATCH` 이상으로 올라오는지 본다
- hot payload에서도 같은 semantic state를 다시 읽을 수 있어야 한다

### 축 3. missing anchor safety

- gap anchor 없는 샘플을 넣는다
- helper의 `gap_fill_progress`는 `None`
- vector/forecast semantic state는 `GAP_CONTEXT_MISSING`
- hot payload에서는 numeric gap 값이 빈 값이어야 한다

## Step 6에서 production code를 건드리는 기준

- 원칙적으로는 테스트와 문서만으로 닫는 단계다
- 다만 cross-stage 회귀에서 실제 연결 누락이 발견되면 그 연결 버그는 바로 수정한다

## Step 6 완료 기준

- Step 1~5 cross-stage regression file 추가
- 대표 smoke 2개 + missing anchor safety 1개 통과
- 기존 Step 1~5 핵심 회귀를 함께 돌려도 깨지지 않음
