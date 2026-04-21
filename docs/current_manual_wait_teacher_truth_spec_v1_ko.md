# Manual Wait Teacher Truth Spec v1

## 목적

이 문서는 차트 수동 표기를 기준으로 `좋은 wait / 중립 wait / 나쁜 wait`를 명시적으로 고정하는 수동 teacher truth 규격이다.

핵심 원칙:

- heuristic barrier label을 억지로 넓히지 않는다.
- 사용자가 차트에서 직접 표시한 `옳은 진입 / 옳은 청산 / 기다림의 성격`을 별도 truth layer로 적재한다.
- 이 truth layer는 기존 Barrier main label을 덮어쓰지 않는다.
- 초기에는 `box/range regime` 표본부터 시작한다.

## 왜 별도 truth layer가 필요한가

현재 heuristic barrier/wait-family는 운영 replay 기준으로 잘 쌓이고 있지만, `correct_wait`처럼 좁고 애매한 라벨은 시장 구조에 따라 거의 나오지 않을 수 있다.

그래서 수동 표기 truth는 아래 용도로 쓴다.

- heuristic이 놓친 `좋은 wait`를 따로 모은다.
- `good wait`와 `bad wait`를 사람이 명시한 기준으로 비교한다.
- 나중에 heuristic barrier/wait-family와 manual truth를 대조해 bias를 교정한다.

## 수동 teacher label 집합

아래 6개를 v1의 공식 수동 wait teacher label로 고정한다.

### 좋은 wait

- `good_wait_better_entry`
  - 기다림이 더 좋은 진입 위치를 만들었다.
- `good_wait_protective_exit`
  - 기다림 뒤 continuation이 있었고, 이후 보호적 청산이 맞았다.
- `good_wait_reversal_escape`
  - 기다림 중 반전/논리 붕괴가 확인됐고, 이후 탈출이 맞았다.

### 중립 wait

- `neutral_wait_small_value`
  - 기다림이 아주 큰 개선은 아니었지만 약간의 가치가 있었다.

### 나쁜 wait

- `bad_wait_missed_move`
  - 기다렸는데 유의미한 기회를 놓쳤다.
- `bad_wait_no_timing_edge`
  - 기다렸지만 더 좋은 진입도 continuation도 없었다.

## wait-family 매핑

수동 teacher label은 아래 wait-family로 자동 매핑한다.

| manual label | polarity | wait-family | subtype | usage |
|---|---|---|---|---|
| `good_wait_better_entry` | `good` | `timing_improvement` | `better_entry_after_wait` | `usable` |
| `good_wait_protective_exit` | `good` | `protective_exit` | `profitable_wait_then_exit` | `usable` |
| `good_wait_reversal_escape` | `good` | `reversal_escape` | `wait_then_escape_on_reversal` | `usable` |
| `neutral_wait_small_value` | `neutral` | `neutral_wait` | `small_value_wait` | `diagnostic` |
| `bad_wait_missed_move` | `bad` | `failed_wait` | `wait_but_missed_move` | `usable` |
| `bad_wait_no_timing_edge` | `bad` | `failed_wait` | `wait_without_timing_edge` | `diagnostic` |

즉 `좋은 wait`는 아래 셋만 먼저 인정한다.

- 더 좋은 진입을 만든 기다림
- 수익 보호 청산으로 이어진 기다림
- 반전 탈출로 이어진 기다림

이 셋에 안 들어가면 일단 `neutral` 또는 `bad`로 둔다.

## 라벨 판정 기준

### 1. `good_wait_better_entry`

아래가 모두 성립하면 이 라벨을 우선 고려한다.

- 기다림 전 진입보다 명확히 더 좋은 재진입 지점이 있었다.
- 그 뒤 continuation이 실제로 있었다.
- 청산이 단순 손절 회피가 아니라 entry quality 개선으로 설명된다.

차트 표기 기준:

- `anchor_time`
- `annotated_entry_time`
- `annotated_exit_time`

세 점이 모두 명확해야 한다.

### 2. `good_wait_protective_exit`

아래가 성립하면 이 라벨을 준다.

- wait 이후 실제 continuation이 있었다.
- continuation을 충분히 먹은 뒤, 더 오래 버티는 것보다 보호적 청산이 낫다.
- 핵심은 “좋은 진입”이 아니라 “좋은 보호 청산”이다.

### 3. `good_wait_reversal_escape`

아래가 성립하면 이 라벨을 준다.

- 기다리는 동안 thesis break 또는 반대 힘이 명확해졌다.
- 그 뒤 reduce/exit가 유효했다.
- 핵심은 “기다림 뒤 반전 탈출”이다.

### 4. `neutral_wait_small_value`

아래처럼 애매한 경우다.

- 약간의 wait value는 있었지만 아주 크지 않다.
- 더 좋은 진입이 명확하지 않다.
- 큰 continuation도 아니고, 큰 손실 회피도 아니다.

이건 초기엔 비교용이 아니라 진단용으로만 쌓는다.

### 5. `bad_wait_missed_move`

아래가 성립하면 이 라벨을 준다.

- 기다림 때문에 유의미한 상승/하락 기회를 놓쳤다.
- 이후 continuation이 충분했다.
- 기다림이 개선이 아니라 기회 상실로 읽힌다.

### 6. `bad_wait_no_timing_edge`

아래가 성립하면 이 라벨을 준다.

- 기다렸지만 더 좋은 진입도 없었다.
- continuation도 거의 없었다.
- 결과적으로 wait 자체가 가치 없는 선택이었다.

## 입력 항목

수동 annotation은 아래 필드로 적는다.

- `annotation_id`
- `symbol`
- `timeframe`
- `side`
- `chart_context`
- `box_regime_scope`
- `anchor_time`
- `anchor_price`
- `annotated_entry_time`
- `annotated_entry_price`
- `annotated_exit_time`
- `annotated_exit_price`
- `manual_wait_teacher_label`
- `manual_wait_teacher_confidence`
- `barrier_main_label_hint`
- `wait_outcome_reason_summary`
- `annotation_note`
- `annotation_source`
- `review_status`
- `revisit_flag`
- `label_version`

## 운영 원칙

### 1. 처음엔 박스장만

초기 truth는 최근 `box/range regime`에서만 만든다.
추세장보다 `good wait / bad wait` 경계가 더 명확하기 때문이다.

### 2. 모든 동그라미를 다 쓰지 않는다

차트에 표시가 많더라도, 1차 표본은 대표 20~30개만 고른다.

### 3. Barrier main label과 분리

수동 teacher truth는 heuristic barrier label을 덮어쓰지 않는다.

- Barrier main label = heuristic outcome
- manual wait teacher = human truth

둘을 나중에 비교한다.

### 4. compare/gate에는 바로 넣지 않는다

초기엔 report/diagnostic/teacher review에만 쓴다.
충분한 표본이 쌓이면 auxiliary truth로 확대한다.

## 파일 위치

초기 템플릿:

- [manual_wait_teacher_annotations.template.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_wait_teacher_annotations.template.csv)

정규화 스키마:

- [manual_wait_teacher_annotation_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/manual_wait_teacher_annotation_schema.py)
- [manual_wait_teacher_annotations.example.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_wait_teacher_annotations.example.csv)
- [manual_wait_teacher_annotations.example.csv](/C:/Users/bhs33/Desktop/project/cfd/data/manual_annotations/manual_wait_teacher_annotations.example.csv)

## 2026-04-06 Answer-Key Positioning

`manual_wait_teacher` should now be read as a `standalone teacher corpus`.

It is primarily:

- an ideal / counterfactual answer key
- a calibration surface for heuristic owners
- a bias-correction review set
- a casebook source

It is not primarily:

- an executed-trade replay reconstruction dataset
- a mandatory closed-history backfill target
- a direct baseline/candidate training seed

Operational rule:

- closed-history matching may be attempted as a secondary path
- matching failure is not a blocker
- the first-class next artifact is a `manual vs heuristic comparison report`

Reference:

- [current_manual_vs_heuristic_comparison_report_template_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md)

## 한 줄 결론

v1에서는 `좋은 wait`를 아래 셋으로 못 박는다.

- `good_wait_better_entry`
- `good_wait_protective_exit`
- `good_wait_reversal_escape`

그리고 나머지는 억지로 `correct_wait`로 밀지 않고,

- `neutral_wait_small_value`
- `bad_wait_missed_move`
- `bad_wait_no_timing_edge`

로 분리해서 수동 teacher truth로 적재한다.
