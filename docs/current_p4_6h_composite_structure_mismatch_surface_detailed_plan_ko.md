# P4-6H 복합 불일치 단일 Surface 상세 계획

## 목표

`P4-6B box_relative_position`, `P4-6C wick/body ratio`, `P4-6D recent_3bar_direction`에서
쌓은 구조 evidence를 같은 포지션 기준으로 한 건으로 묶어
`복합 불일치`로 surface한다.

이번 단계의 목적은 detector를 더 많이 띄우는 것이 아니라,

- 같은 포지션에서 박스 위치도 어긋나고
- 캔들 구조도 어긋나고
- 최근 3봉 흐름도 어긋나는 경우

이를 세 건으로 따로 띄우지 않고
`하나의 구조 복합 불일치`로 읽히게 만드는 데 있다.

## 왜 필요한가

기존 구조에서는 같은 장면에 대해

- 박스 위치 evidence
- 캔들 구조 evidence
- 최근 3봉 흐름 evidence

가 따로 붙는다.

이 자체는 좋은데,
운영자가 실제로 보고 싶은 것은
`어떤 evidence가 몇 개 동시에 어긋났는가`다.

따라서 이번 단계에서는

- mismatch가 1개면 개별 evidence로 남기고
- mismatch가 2개 이상이면 `복합 불일치`로 승격한다.

## 적용 범위

첫 구현은 `candle/box 방향 해석 불일치 row`에만 적용한다.

즉:

- `scene-aware detector`는 기존 방식 유지
- `reverse detector`도 기존 방식 유지
- `candle/weight detector`만 구조 evidence를 한 건으로 묶는다

이렇게 해야 알림 폭탄 없이 안전하게 체감 품질만 올릴 수 있다.

## mismatch 구성 요소

### 1. box mismatch

현재 side와 박스 위치가 구조 맥락과 어긋나면 mismatch로 본다.

- breakout 계열
  - `BUY + LOWER` -> mismatch
  - `SELL + UPPER` -> mismatch
- reversion 계열
  - `BUY + UPPER` -> mismatch
  - `SELL + LOWER` -> mismatch

단:

- `MIDDLE`은 mismatch로 잡지 않는다
- `range_too_narrow`는 mismatch 계산에서 제외한다

## 2. wick mismatch

현재 side와 반대쪽 rejection/defense 힌트가 강하면 mismatch로 본다.

- `BUY`
  - 윗꼬리 거부 우세
  - 상단 거부형 doji
- `SELL`
  - 아랫꼬리 방어 우세
  - 하단 방어형 doji

## 3. recent 3bar mismatch

현재 side와 최근 3봉 흐름이 반대로 강하면 mismatch로 본다.

- `BUY`
  - `WEAK_DOWN`
  - `STRONG_DOWN`
- `SELL`
  - `WEAK_UP`
  - `STRONG_UP`

## composite 판정

아래 규칙으로 묶는다.

- mismatch component `0개`
  - composite 아님
- mismatch component `1개`
  - 개별 evidence만 유지
- mismatch component `2개 이상`
  - `구조 복합 불일치 관찰`

## surface 방식

composite가 성립하면 row는 다음처럼 바뀐다.

- `summary_ko`
  - `{symbol} 구조 복합 불일치 관찰`
- `why_now_ko`
  - `구조 복합 불일치가 관찰됩니다. 박스 상단 0.82 위치에서 롱 + 윗꼬리 0.41 / 상단 거부 우세 + 최근 3봉 약하락.`
- `evidence_lines_ko`
  - 첫 줄에 `- 구조 복합 불일치: ...`
- `severity`
  - `1`로 상향

## row 확장 필드

이번 단계 이후 row에 아래 필드가 붙는다.

- `structure_alignment_mode`
- `structure_mismatch_components_ko`
- `structure_mismatch_component_count`
- `composite_structure_mismatch`

## 이번 단계에서 하지 않는 것

- DM에 box/wick/3bar를 상시 노출
- 거래 로직 변경
- detector 자동 apply
- composite만으로 fast promotion

## 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `tests/unit/test_improvement_log_only_detector_p46h.py`

## 완료 조건

- 같은 포지션에서 구조 mismatch가 2개 이상이면 한 건의 `복합 불일치`로 surface된다.
- report/check에서는 개별 evidence 폭탄 대신 composite row 하나로 읽힌다.
- 거래 로직은 그대로 유지된다.
