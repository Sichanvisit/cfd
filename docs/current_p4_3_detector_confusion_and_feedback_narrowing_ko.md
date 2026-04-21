# P4-3 Detector Confusion Snapshot / Feedback-Aware Narrowing

## 목표

`/detect`와 `/detect_feedback`가 단순 기록에서 끝나지 않고,

- 무엇이 `맞았음`
- 무엇이 `과민했음`
- 무엇을 `놓쳤음`

으로 누적되는지 한 장으로 보이게 만든다.

그리고 그 누적 결과를 detector surface 단계에 좁게 반영해,

- 반복적으로 `과민했음` 판정을 받은 항목은 덜 surface
- `맞았음 / 놓쳤음`이 쌓인 항목은 유지 또는 우선 관찰

되게 만든다.

## 핵심 원칙

1. detector는 여전히 `observe` 단계다.
2. feedback-aware narrowing은 `surface 우선순위`만 바꾼다.
3. feedback만으로 바로 patch/apply로 가지 않는다.
4. `과민` 누적은 억제 근거가 되지만, 자동 거부는 아니다.

## 구현 범위

### 1. confusion snapshot

누적 피드백에서 아래를 만든다.

- verdict 총합
- detector별 누적
- scope별 누적
- latest ref별 최근 verdict
- scope별 narrowing 결정

artifact:

- `data/analysis/shadow_auto/improvement_detector_confusion_latest.json`
- `data/analysis/shadow_auto/improvement_detector_confusion_latest.md`

### 2. stable feedback scope key

`feedback_key`는 개별 detector row용이고,
`feedback_scope_key`는 같은 문제 계열을 반복 추적하기 위한 안정 키다.

구성:

- `detector_key`
- `symbol`
- `summary_ko`

형태:

- `scene_aware::BTCUSD::btcusd_scene_trace_누락_반복_감지`

### 3. feedback-aware narrowing

기본 결정 규칙:

- `SUPPRESS`
  - `과민했음 >= 2`
  - 그리고 `맞았음 + 놓쳤음 = 0`
- `CAUTION`
  - `과민했음 >= 2`
  - 그리고 `과민했음 > 맞았음 + 놓쳤음`
- `PROMOTE`
  - `맞았음 + 놓쳤음 >= 2`
  - 그리고 `과민했음 = 0`
- `KEEP`
  - `맞았음 + 놓쳤음 >= 1`
- `NEUTRAL`
  - 그 외

surface 단계 반영:

- `PROMOTE`
  - severity 1단계 상향
- `CAUTION`
  - severity 1단계 하향
- `SUPPRESS`
  - 이번 `/detect` surface에서는 제외
  - 대신 `narrowed_out_rows`에 남김

## 현재 명령 흐름

1. `/detect`
   - detector snapshot 생성
   - feedback-aware narrowing 적용
   - `D1 / D2 ...` ref와 함께 report/check topic 전송

2. `/detect_feedback D1 맞았음`
   - feedback history 저장
   - feedback snapshot 갱신
   - confusion snapshot 갱신

## 완료 조건

- `/detect` 결과에 `feedback-aware` 표기가 보인다
- repeated `과민` 항목은 `narrowed_out_rows`로 빠진다
- confusion snapshot에서 detector별/항목별 누적판이 보인다
- feedback lane은 여전히 apply로 직접 연결되지 않는다

## 핵심 파일

- `backend/services/improvement_detector_feedback_runtime.py`
- `backend/services/improvement_log_only_detector.py`
- `backend/services/telegram_ops_service.py`
