# P4-6I confidence / explainability / cooldown 상세 계획

## 목표

`P4-6A ~ F`에서 붙인 구조형 evidence를 이제 운영 가능한 detector로 다듬는다.

이번 단계의 목적은 새 판단 로직을 넣는 것이 아니라,

- detector가 스스로 얼마나 맥락을 믿을 수 있는지 표시하고
- hindsight 전에 설명 snapshot을 보존하고
- 같은 scope가 짧은 시간에 반복 surface될 때 피로도를 줄이는 것

이다.

즉 이번 단계는 `정확도 향상`보다 `관찰 품질과 운영 품질 향상`에 가깝다.

## 이번 단계에서 다루는 것

1. `context_confidence`
2. `misread_confidence`
3. `explainability_snapshot`
4. `detector cooldown`

## 이번 단계에서 하지 않는 것

- 거래 로직 변경
- detector 결과의 자동 apply
- confidence 점수를 진입/청산 차단에 직접 사용

이번 단계의 confidence는 오직

- detector 정렬 힌트
- review 우선순위 힌트
- cooldown 우회 여부 판단

에만 사용한다.

## 입력 신호

이미 `P4-6A ~ F`에서 확보한 값을 그대로 재사용한다.

- `summary_ko`
- `why_now_ko`
- `entry_reason`
- `entry_reason_ko`
- `evidence_lines_ko`
- `transition_lines_ko`
- `result_type`
- `explanation_type`
- `feedback_scope_key`

## canonical field

이번 단계가 끝나면 detector row에는 아래 필드가 붙는다.

```python
{
    "context_flag": "breakout_context|range_context|reclaim_context|compression_context|reversion_context|unknown_context",
    "context_confidence": 0.0,
    "context_confidence_label_ko": "높음|주의|낮음",
    "misread_confidence": 0.0,
    "explainability_snapshot": {
        "why_now": "...",
        "force": "...",
        "alignment": "...",
        "context": "...",
        "context_confidence": 0.0,
        "box": "...",
        "candle": "...",
        "recent_3bar": "...",
        "reason": "...",
        "transition_hint": "...",
    },
    "cooldown_window_min": 45,
    "cooldown_state": "SURFACED|SUPPRESSED|BYPASS",
    "cooldown_reason_ko": "",
}
```

## P4-6I-A context_confidence

### 목적

`context_flag`를 무조건 확정하지 않고,
지금 detector가 그 맥락을 얼마나 자신 있게 읽는지 같이 남긴다.

### 규칙

- `summary / why_now / reason / evidence / transition`에서 context token을 모은다
- 아래 group으로 score를 만든다

```text
breakout_context: breakout, retest, sweep, probe
reclaim_context: reclaim, rebound, anchor
compression_context: compression, squeeze
range_context: range, box, mixed, edge
reversion_context: pullback, continuation, follow, runner, trend
```

- 구조 evidence 개수도 같이 반영한다
  - `위/아래 힘`
  - `박스 위치`
  - `캔들 구조`
  - `최근 3봉 흐름`

### 해석

- `>= 0.70` -> `높음`
- `0.40 ~ 0.69` -> `주의`
- `< 0.40` -> `unknown_context`

### 주의

이 값은 context 분류기의 완성판이 아니다.
이번 단계에서는 `현재 evidence만으로 context를 얼마나 신뢰할 수 있는지`를 적는 provisional layer다.

## P4-6I-B misread_confidence

### 목적

detector row를 모두 같은 무게로 보지 않고,
`이 관찰을 얼마나 먼저 봐야 하는지`를 숫자로 남긴다.

### 구성

- structural evidence 개수
- `context_confidence`
- `result_type`
- `explanation_type`
- `severity`

### 사용처

- detector 내부 정렬 힌트
- cooldown bypass 판단
- proposal review 우선순위 보조

### 금지

- 자동 apply 기준으로 사용 금지
- 매매 차단 기준으로 사용 금지

## P4-6I-C explainability_snapshot

### 목적

hindsight에서

- 그때 왜 그렇게 읽었는지
- 무엇을 evidence로 surface했는지

를 다시 복원할 수 있게 한다.

### 저장 항목

- `why_now`
- `force`
- `alignment`
- `context`
- `context_confidence`
- `box`
- `candle`
- `recent_3bar`
- `reason`
- `transition_hint`

### 주의

이 snapshot은 detector 근거 보존용이다.
새 설명을 만드는 용도가 아니라, 당시 설명을 다시 꺼내기 위한 것이다.

## P4-6I-D detector cooldown

### 목적

같은 scope가 짧은 시간에 반복 surface되며 operator 피로도를 높이는 문제를 줄인다.

### 기본 window

- `scene-aware`: `45분`
- `candle/weight`: `90분`
- `reverse`: `30분`

### 동작

- 이전 snapshot의 `cooldown_state.rows_by_scope`를 읽는다
- 같은 `feedback_scope_key`가 cooldown window 안에 있으면 suppress
- 다만 아래 조건이면 cooldown을 우회한다

```text
- severity가 더 강해짐
- misread_confidence가 0.15 이상 상승
- repeat_count가 2 이상 증가
- result_type이 misread로 격상
```

### 결과 상태

- `SURFACED`
- `SUPPRESSED`
- `BYPASS`

### 주의

cooldown은 detector를 끄는 게 아니라
같은 issue가 너무 자주 보이는 것을 줄이는 장치다.

## 구현 순서

1. detector row에 `context_confidence` / `misread_confidence` / `explainability_snapshot` 부착
2. previous snapshot 기반 cooldown layer 추가
3. payload에 `cooldown_summary` / `cooldown_state` surface
4. default builder가 이전 detector snapshot을 읽어 cooldown 상태를 이어받게 연결

## 건드릴 파일

- `backend/services/improvement_log_only_detector.py`
- `tests/unit/test_improvement_log_only_detector_p46i.py`

## 완료 조건

- detector row마다 `context_confidence`, `misread_confidence`, `explainability_snapshot`이 붙는다
- 같은 scope가 짧은 시간 안에 다시 들어오면 cooldown suppress가 동작한다
- stronger evidence는 cooldown을 우회할 수 있다
- detector snapshot에 `cooldown_summary`, `cooldown_state`가 남는다
- 거래 로직은 변하지 않는다
