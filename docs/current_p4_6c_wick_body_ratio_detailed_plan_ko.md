# P4-6C wick/body ratio 상세 계획

## 목표

`P4-6B`가 박스 위치 좌표를 detector evidence에 넣는 단계였다면,
이번 `P4-6C`는 캔들 구조 좌표를 detector evidence에 넣는 단계다.

핵심은

- 윗꼬리
- 아랫꼬리
- 몸통
- doji 성격

을 `현재 방향 해석과 맞는지` 보기 위한 구조 evidence로 surface하는 것이다.

## 왜 지금 이 단계인가

사용자는 차트를 볼 때 위치만 보지 않는다.

- 위꼬리가 길게 나왔는지
- 아래꼬리가 방어처럼 보이는지
- 몸통이 너무 얇아 doji처럼 보이는지

를 같이 본다.

따라서 detector가 `캔들/박스 위치 대비 방향 해석 불일치`를 말하려면
`박스 위치` 다음으로 `캔들 구조` evidence가 붙어야 설명력이 확 올라간다.

## 범위

이번 단계에서 한다.

- detector evidence에 `upper_wick_ratio`
- detector evidence에 `lower_wick_ratio`
- detector evidence에 `doji_ratio`
- detector evidence에 `body_size_pct`
- detector evidence에 `candle_type`
- detector evidence에 `structure_hint`

이번 단계에서 하지 않는다.

- 거래 로직 변경
- DM 상시 노출
- raw OHLC를 다시 계산하는 별도 캔들 엔진 구축

## 구현 원칙

첫 버전은 `runtime micro candle proxy`를 그대로 재사용한다.

사용 후보:

- `micro_upper_wick_ratio_20`
- `micro_lower_wick_ratio_20`
- `micro_doji_ratio_20`
- `micro_body_size_pct_20`

이 값들은 direct 필드가 있으면 direct로 쓰고,
필요하면 forecast/runtime bridge나 secondary harvest 경유 값도 재사용한다.

즉 이번 단계의 목적은 `새 캔들 계산기`가 아니라,
이미 런타임에서 쓰고 있는 미세 캔들 구조 값을 detector evidence로 surface하는 것이다.

## 입력 신호

- row direct
  - `micro_upper_wick_ratio_20`
  - `micro_lower_wick_ratio_20`
  - `micro_doji_ratio_20`
  - `micro_body_size_pct_20`

- forecast/runtime bridge fallback
  - `forecast_state25_runtime_bridge_v1.forecast_runtime_summary_v1.*`

- secondary harvest fallback
  - `source_micro_upper_wick_ratio_20`
  - `source_micro_lower_wick_ratio_20`
  - `source_micro_doji_ratio_20`
  - `source_micro_body_size_pct_20`

## 계산 규칙

### 1. 값 수집

우선순위:

1. row direct
2. forecast runtime summary
3. secondary source inputs

### 2. doji 판정

아래 중 하나면 doji 성격으로 본다.

- `micro_doji_ratio_20 >= 0.30`
- `micro_body_size_pct_20 <= 0.05`

### 3. structure_hint

#### doji일 때

- `upper >= max(0.45, lower + 0.10)` -> `상단 거부형 doji`
- `lower >= max(0.45, upper + 0.10)` -> `하단 방어형 doji`
- 그 외 -> `우유부단 doji`

#### 일반 캔들일 때

- `upper >= 0.25 and upper > lower` -> `윗꼬리 거부 우세`
- `lower >= 0.25 and lower > upper` -> `아랫꼬리 방어 우세`
- `max(upper, lower) >= 0.20` -> `꼬리 확장 관찰`

## detector 적용 위치

이번 step에서는 두 군데에 먼저 넣는다.

1. `scene-aware detector`
- force evidence 뒤에 `캔들 구조`를 추가

2. `candle/weight detector`
- `why_now_ko`에 현재 캔들 구조 설명 추가
- `evidence_lines_ko`에 `캔들 구조` 추가

## DM 노출 정책

이번 단계에서도 DM 상시 노출은 하지 않는다.

이유:

- 꼬리/몸통 값은 detector evidence로는 유용하지만
- 모든 실시간 DM에 계속 붙이면 noise가 커진다

따라서 지금은 detector evidence에만 넣고,
나중에 `P4-6H 복합 불일치`에서만 DM 1줄로 묶는다.

## 출력 예시

일반 캔들:

```text
- 캔들 구조: 윗꼬리 0.41 / 아랫꼬리 0.08 / 몸통 0.22 / 윗꼬리 거부 우세
```

doji 성격:

```text
- 캔들 구조: doji 0.36 / 윗꼬리 0.52 / 아랫꼬리 0.10 / 상단 거부형 doji
```

## 건드릴 파일

- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)
- [test_improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_improvement_log_only_detector.py)

## 완료 조건

- scene-aware detector evidence에 `캔들 구조`가 보인다
- candle/weight detector evidence에 `캔들 구조`가 보인다
- doji 성격이 있으면 구조 힌트가 바뀐다
- 거래 로직은 바뀌지 않는다

## 다음 단계

- `P4-6D` recent_3bar_direction
- 그 다음 `P4-6E` misread_type 2축

즉 `P4-6C`는 박스 위치 다음으로 캔들 구조 증거를 붙이는 단계이고,
이후부터는 시간축과 결과축으로 넘어간다.
