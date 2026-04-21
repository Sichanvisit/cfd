# P4-6G Hindsight Validator + Fast Promotion 상세 계획

## 목표

`P4-6A ~ P4-6F`, `P4-6I`에서 쌓인 구조형 evidence를
사후 판정과 proposal 우선순위로 연결한다.

이번 단계의 목적은 detector를 곧바로 믿는 것이 아니라,

- 어떤 detector scope가 실제로 `사후 확정 오판`을 반복하는지
- 어떤 scope가 `오경보`에 가까운지
- 어떤 scope가 `타이밍 문제`인지

를 hindsight 기준으로 다시 읽고,
그 결과를 `/propose`의 review 우선순위로만 올리는 데 있다.

## 이번 단계에서 하는 일

1. detector row마다 `hindsight_status`를 붙인다.
2. `feedback_issue_refs`에 hindsight 상태를 같이 싣는다.
3. `feedback-aware promotion` 계산에서 hindsight와 confidence를 같이 읽는다.
4. 조건이 충분히 강한 scope만 `fast promotion`으로 올린다.
5. fast promotion은 `proposal 우선 검토`까지만 허용한다.

## 이번 단계에서 하지 않는 일

- 자동 apply
- 자동 전략 변경
- entry/exit/reverse 거래 로직 수정
- 다른 symbol로 자동 확대 적용

## hindsight 상태 정의

- `confirmed_misread`
  - 사후 기준으로 방향 오판이 확정된 경우
- `false_alarm`
  - detector는 문제 가능성을 surface했지만 결과적으로는 오경보인 경우
- `partial_misread`
  - 방향 자체보다 timing 쪽 불일치가 큰 경우
- `unresolved`
  - 아직 열려 있거나 근거가 부족해 사후 확정이 이른 경우

## detector 1차 판정 규칙

초기 구현에서는 이미 붙어 있는 `result_type`를 hindsight로 재해석한다.

- `result_misread` -> `confirmed_misread`
- `result_correct` -> `false_alarm`
- `result_timing` -> `partial_misread`
- 그 외 -> `unresolved`

이 단계는 최종 hindsight 엔진이 아니라,
`result/explanation` 축을 `/propose` 우선순위와 연결하기 위한 1차 validator다.

## fast promotion 기준

fast promotion은 아래 조건을 모두 충족할 때만 허용한다.

1. `hindsight_status == confirmed_misread`
2. `total_feedback >= 5`
3. `positive_ratio >= 0.70`
4. `feedback_trade_day_count >= 3`
5. `misread_confidence >= 0.65`

여기서 `positive_ratio`는

- `맞았음 + 놓쳤음`
  을 전체 detector feedback으로 나눈 비율이다.

즉 `과민했음`이 많거나,
하루에 몰린 표본만으로는 fast promotion이 되지 않는다.

## fast promotion의 효과

허용되는 것:

- `/propose`에서 우선순위 상승
- report/check 요약에서 빠른 승격 후보로 표시
- 후속 bounded proposal review 후보로 먼저 surface

허용되지 않는 것:

- 자동 patch 적용
- 자동 detector narrowing 변경
- 자동 trade rule 변경

## payload 확장

이번 단계 이후 `feedback_promotion_rows`는 아래 필드를 가진다.

- `hindsight_status`
- `hindsight_status_ko`
- `positive_ratio`
- `feedback_trade_day_count`
- `misread_confidence`
- `fast_promotion_eligible`
- `fast_promotion_reason_ko`

또한 detector snapshot에는

- `hindsight_summary`

가 top-level로 기록된다.

## 보고서 반영 방식

`/propose` 보고서에서는

- feedback-aware 우선 검토 줄에 hindsight 상태를 같이 붙이고
- fast promotion이면 `빠른 승격` 표시와 근거를 같이 남긴다.

예시:

```text
1. BTCUSD | 상하단 방향 오판 가능성 관찰 | 승격 | 맞았음 3 / 놓쳤음 2 / 과민 0 | 사후 확정 오판 | 빠른 승격
   - 제안: scene-aware detector에서 사후 확정 오판 반복이 확인되어 proposal 빠른 승격 후보로 우선 검토합니다.
   - 빠른 승격 근거: 사후 확정 오판 비율이 높고 피드백 5건이 3거래일에 걸쳐 누적되어 빠른 승격 대상으로 올립니다.
```

## 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `backend/services/trade_feedback_runtime.py`
- `tests/unit/test_improvement_log_only_detector_p46g.py`
- `tests/unit/test_trade_feedback_runtime.py`

## 완료 조건

- detector snapshot에 hindsight 상태가 일관되게 붙는다.
- `/propose`가 hindsight + feedback 기준으로 fast promotion 후보를 앞에 올린다.
- fast promotion이 있어도 readiness는 `review`까지만 올라가고 apply는 열리지 않는다.
