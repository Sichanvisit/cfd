# Teacher-Label State25 Compact Schema 상세 기준서

## 목적

이 문서는 `teacher-state 25`를 실제 compact dataset row에 저장하기 위한 canonical schema를 정의한다.

핵심 목적은 세 가지다.

1. `25개 패턴 정의 문서`를 실제 데이터 컬럼으로 내린다.
2. `labeling QA`와 `experiment tuning`이 같은 필드를 기준으로 움직이게 만든다.
3. 나중에 raw를 줄이더라도 compact row만으로 teacher-label 분석과 학습이 가능하게 만든다.

## 왜 지금 필요한가

현재까지는 아래가 이미 끝나 있거나 정리돼 있다.

- `micro-structure Top10` 구축
- `teacher-state 25` 패턴 정의
- `threshold v2` 정량 기준
- `labeling QA` 기준
- `experiment tuning` 순서

하지만 아직 없는 것은 `teacher-pattern을 어디에 어떤 컬럼으로 저장할지`에 대한 합의다.

즉 지금 단계는:

- 규칙은 정해졌고
- 재료도 준비됐고
- 이제 실제 row에 붙일 그릇을 정의해야 하는 단계다.

## canonical 저장 위치

### 1차 canonical home

가장 먼저 canonical home으로 삼을 곳은 `closed-history compact row`다.

대상:

- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)
- owner: [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)

이유:

- 최종 학습은 close result와 같이 보게 된다.
- `entry -> wait -> exit -> close result` 흐름과 teacher-label을 한 row에서 읽는 게 좋다.
- Step 5에서 이미 micro compact field가 closed-history까지 carry되는 구조가 닫혀 있다.

### 2차 preview surface

필요하면 나중에 `entry_decisions.csv`에 preview용 teacher-label surface를 올릴 수 있다.

하지만 1차 목표는 아니다.

원칙:

- 먼저 compact/closed-history schema를 닫는다.
- preview surface는 QA 편의가 필요할 때만 확장한다.

## schema 층 분리

### A. 필수 canonical 필드

이 필드는 반드시 들어간다.

- `teacher_pattern_id`
- `teacher_pattern_name`
- `teacher_pattern_group`
- `teacher_pattern_secondary_id`
- `teacher_pattern_secondary_name`
- `teacher_direction_bias`
- `teacher_entry_bias`
- `teacher_wait_bias`
- `teacher_exit_bias`
- `teacher_transition_risk`
- `teacher_label_confidence`
- `teacher_lookback_bars`

### B. 라벨 provenance 필드

이 필드는 “누가/어떤 버전으로 붙였는가”를 남긴다.

- `teacher_label_version`
- `teacher_label_source`
- `teacher_label_review_status`

권장 의미:

- `teacher_label_version`: `state25_v2`
- `teacher_label_source`: `rule_v2`, `manual`, `reviewed`, `hybrid`
- `teacher_label_review_status`: `unreviewed`, `reviewed`, `approved`

### C. 선택적 QA 보조 필드

초기 구현에서 꼭 넣을 필요는 없지만, QA와 confusion 분석엔 유용하다.

- `teacher_primary_score`
- `teacher_secondary_score`
- `teacher_conflict_reason`
- `teacher_review_note`

이번 스코프에서는 `선택적`으로 두고, 우선순위는 낮다.

## 필드 상세 정의

| 필드 | 타입 | 필수 | 의미 |
|---|---|---|---|
| `teacher_pattern_id` | int | 필수 | 주패턴 ID, 1~25 |
| `teacher_pattern_name` | text | 필수 | 주패턴 이름 |
| `teacher_pattern_group` | text | 필수 | `A/B/C/D/E` 또는 그룹명 |
| `teacher_pattern_secondary_id` | int/nullable | 권장 | 보조패턴 ID |
| `teacher_pattern_secondary_name` | text/nullable | 권장 | 보조패턴 이름 |
| `teacher_direction_bias` | text | 필수 | `buy_prefer`, `sell_prefer`, `both`, `neutral` |
| `teacher_entry_bias` | text | 필수 | `early`, `confirm`, `breakout`, `fade`, `avoid` |
| `teacher_wait_bias` | text | 필수 | `hold`, `short_wait`, `tight_wait`, `avoid_wait` |
| `teacher_exit_bias` | text | 필수 | `fast_cut`, `trail`, `scale_out`, `range_take`, `hold_runner` |
| `teacher_transition_risk` | text | 필수 | `low`, `mid`, `high` |
| `teacher_label_confidence` | float | 필수 | 0~1 confidence |
| `teacher_lookback_bars` | int | 필수 | 보통 20~50 |
| `teacher_label_version` | text | 필수 | `state25_v2` 같은 버전명 |
| `teacher_label_source` | text | 필수 | `rule_v2`, `manual`, `reviewed`, `hybrid` |
| `teacher_label_review_status` | text | 필수 | `unreviewed`, `reviewed`, `approved` |

## 저장 규칙

### 주패턴

- 반드시 하나만 저장한다.
- 값이 없으면 빈 문자열이 아니라 `NULL` 대신 `0/UNKNOWN` 같은 우회값도 쓰지 않는다.
- 주패턴을 못 정하면 row를 `unlabeled` 상태로 남기고, 억지로 25개 중 하나를 강제하지 않는다.

### 보조패턴

- 선택이다.
- `top2 score 차이 <= 0.10` 같은 기준을 통과한 경우에만 넣는다.
- 없으면 비워 둔다.

### confidence

- 0~1 float로 둔다.
- QA 단계에서 `하위 5%`를 최종 검수 대상으로 쓰기 때문에 필수다.

### version / source / review_status

- 같은 row가 나중에 다시 재라벨링될 수 있으므로 provenance 필드는 꼭 둔다.

예:

- `teacher_label_version = state25_v2`
- `teacher_label_source = rule_v2`
- `teacher_label_review_status = unreviewed`

## owner와 구현 경계

### schema owner

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)

할 일:

- `TRADE_COLUMNS` 확장
- text/numeric normalize 규칙 추가
- optional QA 필드 여부 결정

### open/close carry owner

- [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py)
- [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py)

할 일:

- entry/open 시점 snapshot에 teacher-label이 있으면 보존
- close row로 carry

### label attach owner

- 아직 구현 전이지만, 다음 단계 라벨러 owner는 compact builder 쪽이 된다.
- 즉 schema를 먼저 만들고, 그 다음 라벨 attach 로직을 붙인다.

## 비목표

이번 schema 단계에서 하지 않는 것:

- 25개 자동 판정 로직 구현
- XGBoost baseline 학습
- execution bias 변경
- entry_decisions hot preview surface 확장

즉 지금은 어디까지나 `그릇` 단계다.

## 결론

이 schema 문서는 다음을 위한 토대다.

1. `teacher_pattern_*` 필드 정의
2. closed-history compact row에 canonical 저장
3. QA와 실험 문서가 같은 컬럼을 보게 만들기

즉 지금 state25 본체 구현의 첫 실무 단계는 이 schema를 먼저 닫는 것이다.
