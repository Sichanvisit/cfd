# Teacher-Label Micro-Structure Top10 Step 8 상세 기준서
## 목표

Step 8의 목적은 이미 compact row에 붙기 시작한 `teacher_pattern_*` 라벨을
`그대로 학습/실험으로 넘겨도 되는지`
운영 기준으로 검수하는 것이다.

이번 단계는 새 패턴을 만드는 단계가 아니다.

- Step 7A에서 만든 `teacher_pattern_* schema`
- state25 라벨러 초안이 붙인 `rule_v2_draft`
- 기존 labeling QA 기준서의 `look-ahead 금지 / confusion pair / 희소 패턴 / 검수 프로세스`

를 실제 코드의 QA gate로 내리는 단계다.

## Step 8에서 확인하는 것

1. `teacher_pattern_id`가 실제 row에 붙었는가
2. `teacher_label_source`, `teacher_label_version`, `teacher_lookback_bars`가 빠지지 않았는가
3. `12-23`, `5-10`, `2-16` watchlist pair가 어떻게 나타나는가
4. `3`, `17`, `19` rare watch pattern이 1% 미만인지
5. `entry / wait / exit` bias 분포가 어떻게 형성되는가
6. lowest-confidence 5% review target을 바로 뽑을 수 있는가

## 구현 owner

- [teacher_pattern_labeling_qa.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeling_qa.py)
- [test_teacher_pattern_labeling_qa.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_teacher_pattern_labeling_qa.py)

## 구현 원칙

### 1. runtime 로직을 흔들지 않는다

Step 8은 라벨 부착 결과를 읽어 점검하는 단계다.

- entry / wait / exit 실행 로직은 건드리지 않는다
- compact row를 입력으로 받아 report만 만든다

### 2. hard fail과 warning을 분리한다

Hard fail:

- labeled row가 0개
- `teacher_label_source` 누락
- `teacher_label_version` 누락
- `teacher_lookback_bars != 20`

Warning:

- unlabeled row 존재
- rare watch pattern 1% 미만
- low-confidence review target 존재

### 3. confusion pair는 unordered pair로 센다

`12 -> 23`과 `23 -> 12`를 서로 다른 pair로 세지 않는다.
watchlist 기준은 아래 3개로 고정한다.

- `12-23`
- `5-10`
- `2-16`

### 4. low-confidence review는 lowest 5% head로 고정한다

quantile 수치만 남기지 않고 실제 review sample도 같이 남긴다.

sample에는 아래 정보를 넣는다.

- row index
- identifier (`trade_link_key`, `ticket`, `replay_row_key` 중 하나)
- symbol
- primary / secondary pattern id
- confidence

## Step 8 완료 기준

- QA report builder 추가
- watchlist pair / rare pattern / provenance / bias distribution 요약 가능
- low-confidence review target 추출 가능
- Step 8 전용 회귀 테스트 통과

## 이번 단계의 의미

Step 8이 닫히면 이제부터는
`라벨이 붙는다`
에서 끝나는 게 아니라
`붙은 라벨이 어떤 위험을 갖고 있는지 바로 보인다`
상태가 된다.

즉 다음 Step 9 experiment tuning은 감이 아니라
이 QA report를 바탕으로 진행하게 된다.
