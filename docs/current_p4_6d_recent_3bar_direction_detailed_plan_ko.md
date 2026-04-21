# P4-6D recent_3bar_direction 상세 계획

## 목표

`P4-6C`가 캔들 구조를 detector evidence로 올리는 단계였다면,
이번 `P4-6D`는 사람이 차트를 볼 때 바로 체감하는
`최근 3봉이 위로 이어졌는지 / 아래로 이어졌는지 / 혼조인지`
를 detector evidence로 surface하는 단계다.

핵심은 새 매매 로직을 만드는 것이 아니라,
기존 runtime에 이미 들어오는 micro direction 계열 값을 이용해
`최근 3봉 흐름` 설명면을 하나 더 붙이는 것이다.

## 왜 지금 이 단계인가

사용자는 차트를 볼 때 아래를 함께 본다.

- 지금 박스 상단/하단 어디쯤인가
- 꼬리와 몸통이 어떤 압력으로 보이는가
- 방금 직전 몇 봉이 위로 이어졌는가 아래로 꺾였는가

`P4-6B`가 위치를,
`P4-6C`가 캔들 구조를 붙였다면,
`P4-6D`는 시간축의 짧은 방향 일관성을 붙이는 단계다.

이 값은 이후 `misread_type`에서
`true_misread`와 `timing_mismatch`를 나누는 근거로도 이어진다.

## 범위

이번 단계에서 한다.

- detector evidence에 `recent_3bar_direction`
- detector evidence에 `bull_ratio / bear_ratio / same_color_run`
- detector evidence에 `structure_hint`
- `why_now_ko`에 `현재 최근 3봉 흐름은 ...` 문장 추가

이번 단계에서 하지 않는다.

- DM 상시 노출
- raw OHLC 기반 별도 3봉 재계산 엔진 구축
- 거래 로직 변경

## 구현 원칙

첫 버전은 `runtime micro direction proxy`를 사용한다.

사용 후보:

- `micro_bull_ratio_20`
- `micro_bear_ratio_20`
- `micro_same_color_run_current`
- `micro_same_color_run_max_20`
- `micro_direction_run_stats_v1.*`

우선순위:

1. row direct
2. nested `micro_direction_run_stats_v1`
3. forecast/runtime summary
4. secondary source inputs

즉 이번 단계도 새 계산기보다는
이미 런타임에 존재하는 방향성 요약 값을 detector evidence로 surface하는 데 집중한다.

## 계산 규칙

### 방향 분류

- `bull >= 0.70 and bull > bear + 0.05` -> `STRONG_UP`
- `bull >= 0.55 and bull > bear + 0.03` -> `WEAK_UP`
- `bear >= 0.70 and bear > bull + 0.05` -> `STRONG_DOWN`
- `bear >= 0.55 and bear > bull + 0.03` -> `WEAK_DOWN`
- 그 외 -> `MIXED`

한국어 label:

- `STRONG_UP` -> `강상승`
- `WEAK_UP` -> `약상승`
- `STRONG_DOWN` -> `강하락`
- `WEAK_DOWN` -> `약하락`
- `MIXED` -> `혼조`

### 연속봉 힌트

- 상승 계열 + `same_color_run_current >= 3` -> `상승 연속 N`
- 하락 계열 + `same_color_run_current >= 3` -> `하락 연속 N`
- 혼조 + `same_color_run_current >= 3` -> `연속봉 N 관찰`

## 출력 형식

예시:

```text
- 최근 3봉 흐름: 강하락 (상승 0.18 / 하락 0.76 / 연속 3 / 최대연속 4) / 하락 연속 3
```

또는

```text
- 최근 3봉 흐름: 혼조 (상승 0.47 / 하락 0.43 / 연속 1)
```

`why_now_ko`에는 필요 시 아래 문장을 붙인다.

```text
현재 최근 3봉 흐름은 강하락 (상승 0.18 / 하락 0.76 / 연속 3 / 최대연속 4) / 하락 연속 3입니다.
```

## 적용 위치

1. `scene-aware detector`
- force / box / wick evidence 뒤에 `최근 3봉 흐름` 추가

2. `candle/weight detector`
- `why_now_ko`에 최근 3봉 흐름 문장 추가
- `evidence_lines_ko`에 최근 3봉 흐름 추가

## DM 노출 정책

이번 단계에서는 DM 상시 노출을 하지 않는다.

이유:

- `최근 3봉 흐름`은 detector evidence로는 매우 유용하지만
- 모든 실시간 DM에 계속 붙이면 noise가 커진다

따라서 이 값은 우선 detector evidence로만 surface하고,
향후 `P4-6H 복합 불일치 단일 surface` 단계에서만
필요 시 DM 1줄 요약에 포함한다.

## 건드릴 파일

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)
- [test_improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_improvement_log_only_detector.py)

## 완료 조건

- scene-aware detector evidence에 `최근 3봉 흐름`이 보인다
- candle/weight detector evidence에 `최근 3봉 흐름`이 보인다
- `why_now_ko`에 `현재 최근 3봉 흐름은 ...` 문장이 붙는다
- runtime micro direction 값이 없으면 조용히 skip한다
- 거래 로직은 바뀌지 않는다

## 다음 단계

- `P4-6E` misread_type 2축 분리
- 그 다음 `P4-6F` generic reason filter

즉 `P4-6D`는 위치와 캔들 구조 다음으로
짧은 시간축 방향 일관성을 detector evidence에 붙이는 단계이고,
이후부터는 결과 분류와 hindsight 검증 축으로 넘어간다.
