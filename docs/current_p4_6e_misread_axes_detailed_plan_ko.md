# P4-6E misread_type 2축 분리 상세 계획

## 목표

`P4-6B/C/D`가 사람 좌표계 evidence를 detector row에 붙이는 단계였다면,
이번 `P4-6E`는 그 evidence를 `결과 축`과 `설명 축`으로 분리해서
이후 feedback, `/propose`, hindsight validator가 같은 언어를 쓰게 만드는 단계다.

핵심은 모든 문제를 단순히 `오판` 하나로 뭉개지 않는 것이다.

## 왜 지금 이 단계인가

지금까지는 detector가

- 왜 이상한지
- 어떤 evidence가 붙는지

는 점점 잘 보이기 시작했지만,
그 이슈가

- 결과가 틀린 것인지
- timing이 어긋난 것인지
- 설명만 부족한 것인지

를 공통 언어로 남기지는 못했다.

`P4-6E`는 hindsight 최종판이 아니라,
현재 있는 detector evidence만으로도 provisional 분류 언어를 먼저 붙이는 단계다.
정밀한 hindsight 확정은 이후 `P4-6G`에서 다룬다.

## 2축 정의

### 결과 축

- `result_correct`
- `result_misread`
- `result_timing`
- `result_unresolved`

한국어 label:

- `result_correct` -> `결과 정합`
- `result_misread` -> `결과 오판`
- `result_timing` -> `타이밍 불일치`
- `result_unresolved` -> `결과 미확정`

### 설명 축

- `explanation_clear`
- `explanation_gap`
- `explanation_unknown`

한국어 label:

- `explanation_clear` -> `설명 명확`
- `explanation_gap` -> `설명 부족`
- `explanation_unknown` -> `설명 미확인`

## 예시 조합

- `result_correct + explanation_clear`
  - 문제 없음
- `result_correct + explanation_gap`
  - 결과는 좋았지만 설명이 부족했다
- `result_misread + explanation_clear`
  - 설명은 됐지만 판단이 틀렸다
- `result_misread + explanation_gap`
  - 설명도 안 되고 판단도 틀렸다
- `result_timing + explanation_clear`
  - 방향은 맞았지만 timing이 나빴다
- `result_unresolved + explanation_unknown`
  - 아직 확정 이르다

## 이번 단계의 구현 원칙

이번 단계는 `최종 truth engine`이 아니다.

- scene-aware detector는 우선 `result_unresolved`로 둔다
- candle/weight detector는 현재 집계된 `net_pnl`, `win_rate`를 이용해 provisional 분류
- reverse detector는 `realized_pnl_sum`이 있으면 provisional 분류
- explanation 축은 `why_now_ko + evidence_lines_ko`의 설명 충실도로 분류

즉 지금은 분류 언어를 고정하는 단계이고,
최종 hindsight 판정은 다음 단계에서 더 정교하게 들어간다.

## 결과 축 판정 규칙

### scene-aware detector

- 현재는 hindsight 최종판이 아니므로 `result_unresolved`

### candle/weight detector

- `net_pnl < 0` and `win_rate < 0.45` -> `result_misread`
- `net_pnl < 0` and `win_rate >= 0.45` -> `result_timing`
- `net_pnl > 0` and `win_rate >= 0.55` -> `result_correct`
- 그 외 -> `result_unresolved`

### reverse detector

- `realized_pnl_sum < 0` -> `result_misread`
- `realized_pnl_sum > 0` -> `result_timing`
- `realized_pnl_sum` 없음 -> `result_unresolved`

## 설명 축 판정 규칙

### 기본

- `summary_ko`, `why_now_ko` 둘 다 비어 있음 -> `explanation_unknown`

### 구조 detector 기준

scene/candle detector는 아래 evidence marker를 본다.

- `위/아래 힘:`
- `박스 위치:`
- `캔들 구조:`
- `최근 3봉 흐름:`
- `현재 체크 이유:`

판정:

- `why_now_ko` 존재 + 구조 marker 2개 이상 -> `explanation_clear`
- 그 외 -> `explanation_gap`

### reverse detector 기준

reverse는 아래 marker를 본다.

- `avg_shock_score:`
- `action:`

판정:

- `why_now_ko` 존재 + marker 1개 이상 -> `explanation_clear`
- 그 외 -> `explanation_gap`

## detector row 반영 방식

각 row에 아래 필드를 추가한다.

- `result_type`
- `result_type_ko`
- `explanation_type`
- `explanation_type_ko`
- `misread_axes_ko`

그리고 `transition_lines_ko`에 아래를 함께 붙인다.

```text
- 분류: 결과 오판 / 설명 명확
```

## 보고서 노출

`/detect` 보고서 렌더에도 `분류:` 줄을 같이 노출한다.

이유:

- detector row 내부 필드로만 있으면 운영자가 바로 못 본다
- 보고서에 같이 보여야 feedback과 proposal 우선순위 판단이 쉬워진다

## 건드릴 파일

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)
- [test_improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_improvement_log_only_detector.py)

## 완료 조건

- surfaced detector row마다 `result_type`, `explanation_type`이 붙는다
- report lines에 `분류:`가 보인다
- candle detector는 음수 순손익 패턴에 대해 provisional `result_misread`를 줄 수 있다
- reverse detector는 realized pnl 합계가 있으면 provisional 분류가 된다
- scene detector는 우선 `result_unresolved`로 남는다
- 거래 로직은 바뀌지 않는다

## 다음 단계

- `P4-6F` generic reason filter
- 그 다음 `P4-6I` confidence / explainability snapshot / cooldown

즉 `P4-6E`는 detector evidence를
단순 관찰 로그에서 `결과/설명 축을 가진 학습 입력`으로 바꾸는 단계다.
