# Teacher-Label State25 Labeled Row Acquisition 상세 기준서
## 목표

이 문서는 `Step 8 labeling QA` 다음에 바로 필요한
`teacher_pattern_* labeled row 확보 단계`
를 고정한다.

현재 상태는 다음과 같다.

- `teacher_pattern_* schema`는 이미 있다
- `state25 라벨러`도 이미 있다
- `Step 8 QA gate`도 이미 있다
- 하지만 기존 [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv) full backlog는 라벨러 도입 이전 row가 많아서 `labeled_rows = 0`으로 보일 수 있다

즉 지금 필요한 것은
`라벨 품질 검수`
가 아니라
`실제 라벨이 붙은 row를 충분히 확보하는 것`
이다.

## 왜 이 단계가 필요한가

Step 9 experiment tuning은

- 자산별 ATR 캘리브레이션
- 10K labeling QA
- baseline 모델
- confusion pair 조정

을 다루는데, 이 모든 것은 먼저 `teacher_pattern_*`가 실제로 채워진 row가 있어야 의미가 있다.

그래서 Step 9 전에는 반드시
`labeled row acquisition`
단계를 거쳐야 한다.

## 확보 방식 3가지

### 1. runtime accumulation

뜻:

- 런타임을 계속 켜두고
- 새 open snapshot에 teacher label이 붙은 뒤
- 실제 close row가 쌓이면서 자연스럽게 labeled row가 증가하게 둔다

장점:

- 가장 보수적이고 안전하다
- 실제 운영 경로 그대로 쌓이므로 provenance가 깨끗하다
- look-ahead 위험이 가장 낮다

단점:

- 시간이 걸린다
- 시장이 조용하면 Step 9 시작이 늦어진다

### 2. historical backfill

뜻:

- 기존 closed-history backlog에 대해
- 현재 라벨러 기준으로 `teacher_pattern_*`를 뒤에서부터 다시 채운다

장점:

- 빠르게 1K~10K seed dataset을 만들 수 있다
- Step 9를 빨리 시작할 수 있다

단점:

- historical row의 micro/state completeness 차이 때문에 누락이 생길 수 있다
- runtime과 동일 provenance는 아니므로 별도 source/review status가 필요하다

### 3. hybrid

뜻:

- runtime accumulation은 계속 켜 둔다
- 동시에 bounded backfill로 최근 window만 seed dataset으로 채운다

장점:

- 속도와 안전성을 동시에 잡는다
- Step 9를 기다리지 않고 시작할 수 있다
- 이후 runtime row가 들어오면 backfill seed를 자연스럽게 대체/보강한다

단점:

- provenance 구분을 더 엄격히 해야 한다

## 추천 결론

현재 단계에서는 `hybrid`가 가장 현실적이다.

즉:

1. `runtime accumulation`은 계속 유지
2. `bounded backfill`로 최근 window seed를 만든다
3. Step 8 QA gate로 둘을 함께 점검한다
4. Step 9는 `seed + fresh runtime` 조합으로 시작한다

## canonical provenance 규칙

### runtime row

- `teacher_label_source = rule_v2_draft`
- `teacher_label_review_status = unreviewed`

### backfill row

- `teacher_label_source = rule_v2_backfill`
- `teacher_label_review_status = backfilled_unreviewed`

핵심:

- 기존에 이미 채워진 `teacher_pattern_*`가 있으면 backfill이 덮어쓰지 않는다
- provenance는 runtime과 backfill을 섞어 쓰지 않는다

## backfill 범위 원칙

### 1차 seed

- 최근 row부터 역순으로 bounded window만 본다
- 권장 시작 범위: 최근 `1K ~ 2K` closed row

### 2차 확장

- Step 8 QA 결과가 안정적이면 최근 `5K`

### 3차 full backlog

- Step 9 baseline 품질이 좋고 provenance 관리가 안정적일 때만 확대

즉 처음부터 full backlog 전체를 무조건 덮지 않는다.

## 완료 기준

이 단계가 완료됐다고 보려면 최소 아래가 충족돼야 한다.

- runtime accumulation 경로 유지
- bounded backfill dry-run 가능
- bounded backfill apply 가능
- Step 8 QA report에서 `labeled_rows > 0`
- provenance가 runtime/backfill로 분리되어 보임
- Step 9가 시작 가능한 seed row가 확보됨

## 다음 단계 연결

이 단계가 닫히면 바로 다음은 [product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_experiment_tuning_roadmap_ko.md) 이다.
